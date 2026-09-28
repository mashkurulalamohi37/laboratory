"""Authentication use-cases: OTP and password login, staff 2FA, refresh-token rotation with
reuse detection, sessions, and password management."""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import get_request_context
from app.core.db import independent_transaction, on_commit
from app.core.errors import AppError, BusinessRuleViolation, NotFound
from app.core.phone import mask_phone
from app.core.rate_limit import hit
from app.core.rate_limit import reset as reset_rate_limit
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from app.modules.audit import service as audit
from app.modules.auth.dependencies import (
    AccountDisabled,
    build_principal,
    invalidate_principal,
    mark_sessions_revoked,
)
from app.modules.auth.models import RefreshToken, Session, User, UserRole
from app.modules.auth.otp import OtpInvalid, OtpPurpose, deliver_nothing, issue_otp, verify_otp
from app.modules.auth.permissions import Role, ScopeType
from app.modules.auth.principal import Principal
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import MeResponse, RoleGrantOut, TwoFactorChallenge

#: A rotated refresh token presented again within this window is treated as a benign race
#: (two browser tabs refreshing at once), not theft.
REFRESH_REUSE_GRACE = timedelta(seconds=30)


class InvalidCredentials(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "The phone/email or password is incorrect."


class StaffPasswordRequired(AppError):
    status_code = 403
    code = "STAFF_PASSWORD_LOGIN_REQUIRED"
    message = "Staff accounts must sign in with a password."


class RefreshInvalid(AppError):
    status_code = 401
    code = "REFRESH_INVALID"
    message = "Your session has expired. Please sign in again."


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    expires_at: datetime
    refresh_token: str | None
    refresh_expires_at: datetime | None
    session_id: uuid.UUID
    is_new_user: bool = False


def _now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session
        self.repo = AuthRepository(session)
        self.settings = get_settings()

    # ------------------------------------------------------------------ OTP login
    async def send_otp(self, phone: str, purpose: OtpPurpose, ip: str | None) -> None:
        """Always behaves identically from the client's view (no account enumeration)."""
        user = await self.repo.get_user_by_phone(phone)
        deliverable = {
            # Staff must use password + 2FA; unknown phones may self-register as patients.
            OtpPurpose.LOGIN: user is None or (user.status == "ACTIVE" and not user.is_staff),
            OtpPurpose.RESET: user is not None and user.status == "ACTIVE",
        }.get(purpose, False)
        if deliverable:
            await issue_otp(purpose, phone, ip=ip)
        else:
            await deliver_nothing(purpose, phone, ip=ip)

    async def verify_login_otp(self, phone: str, code: str) -> IssuedTokens:
        await verify_otp(OtpPurpose.LOGIN, phone, code)
        user = await self.repo.get_user_by_phone(phone)
        is_new = False
        if user is None:
            user = await self._register_patient(phone)
            is_new = True
        elif user.is_staff:
            raise StaffPasswordRequired()
        elif user.status != "ACTIVE":
            raise AccountDisabled()
        if user.phone_verified_at is None:
            user.phone_verified_at = _now()
        tokens = await self._start_session(user, is_new_user=is_new)
        audit.record(
            self.s,
            action="auth.login",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            after={"method": "otp", "session_id": tokens.session_id},
        )
        return tokens

    async def _register_patient(self, phone: str) -> User:
        user = User(phone=phone, phone_verified_at=_now(), is_staff=False)
        self.s.add(user)
        await self.s.flush()
        role = await self.repo.get_role_by_code(Role.PATIENT)
        if role is None:  # pragma: no cover - seed invariant
            raise RuntimeError("PATIENT role missing; run the seed script")
        self.s.add(UserRole(user_id=user.id, role_id=role.id, scope_type=ScopeType.GLOBAL))
        audit.record(
            self.s,
            action="user.registered",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            after={"phone": mask_phone(phone)},
        )
        return user

    # ------------------------------------------------------------- password login
    async def password_login(
        self, identifier: str, password: str, *, ip: str | None
    ) -> IssuedTokens | TwoFactorChallenge:
        s = self.settings
        limiter_key = f"login:{identifier.lower()}"
        await hit(
            limiter_key, limit=s.login_attempt_limit, window_seconds=s.login_attempt_window_seconds
        )
        if ip:
            await hit(
                f"login-ip:{ip}",
                limit=s.login_attempt_limit * 6,
                window_seconds=s.login_attempt_window_seconds,
            )

        user = await self.repo.get_user_by_identifier(identifier)
        if not verify_password(password, user.password_hash if user else None) or user is None:
            if user is not None:
                await self._audit_independently(
                    "auth.login_failed", user.id, {"method": "password"}
                )
            raise InvalidCredentials()
        if user.status != "ACTIVE":
            raise AccountDisabled()

        await reset_rate_limit(limiter_key)
        if user.password_hash and password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        if user.is_staff and s.staff_two_factor_required:
            return await self._start_two_factor(user, ip)

        tokens = await self._start_session(user)
        audit.record(
            self.s,
            action="auth.login",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            after={"method": "password", "session_id": tokens.session_id},
        )
        return tokens

    async def _start_two_factor(self, user: User, ip: str | None) -> TwoFactorChallenge:
        if not user.phone:
            raise BusinessRuleViolation(
                "This staff account has no phone for verification.", code="TWO_FACTOR_UNAVAILABLE"
            )
        challenge_id = secrets.token_urlsafe(24)
        await get_redis().set(
            f"2fa:{challenge_id}",
            json.dumps({"user_id": str(user.id)}),
            ex=self.settings.otp_ttl_seconds,
        )
        await issue_otp(OtpPurpose.TWO_FACTOR, user.phone, ip=ip, subject=challenge_id)
        return TwoFactorChallenge(
            challenge_id=challenge_id,
            phone_hint=mask_phone(user.phone),
            expires_in=self.settings.otp_ttl_seconds,
        )

    async def verify_two_factor(self, challenge_id: str, code: str) -> IssuedTokens:
        redis = get_redis()
        raw = await redis.get(f"2fa:{challenge_id}")
        if raw is None:
            raise OtpInvalid()
        await verify_otp(OtpPurpose.TWO_FACTOR, challenge_id, code)
        await redis.delete(f"2fa:{challenge_id}")
        user = await self.repo.get_user(uuid.UUID(json.loads(raw)["user_id"]))
        if user is None or user.status != "ACTIVE":
            raise AccountDisabled()
        tokens = await self._start_session(user)
        audit.record(
            self.s,
            action="auth.login",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            after={"method": "password+otp", "session_id": tokens.session_id},
        )
        return tokens

    # ------------------------------------------------------------------ sessions
    async def _start_session(self, user: User, *, is_new_user: bool = False) -> IssuedTokens:
        now = _now()
        ctx = get_request_context()
        refresh_expires = now + timedelta(days=self.settings.refresh_token_ttl_days)
        session = Session(
            user_id=user.id,
            user_agent=ctx.user_agent if ctx else None,
            ip=ctx.ip if ctx else None,
            expires_at=refresh_expires,
        )
        self.s.add(session)
        await self.s.flush()
        refresh = new_refresh_token()
        self.s.add(
            RefreshToken(
                session_id=session.id,
                token_hash=hash_refresh_token(refresh),
                expires_at=refresh_expires,
            )
        )
        user.last_login_at = now
        access, access_exp = create_access_token(user.id, session.id)
        return IssuedTokens(access, access_exp, refresh, refresh_expires, session.id, is_new_user)

    async def refresh(self, raw_token: str) -> IssuedTokens:
        now = _now()
        token = await self.repo.get_refresh_token_for_update(hash_refresh_token(raw_token))
        if token is None:
            raise RefreshInvalid()
        session = await self.repo.get_session(token.session_id)
        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= now
            or token.expires_at <= now
        ):
            raise RefreshInvalid()

        if token.used_at is not None:
            if now - token.used_at <= REFRESH_REUSE_GRACE:
                # Concurrent refresh: issue an access token only; the newer refresh token
                # (already delivered to this client) stays current.
                access, exp = create_access_token(session.user_id, session.id)
                return IssuedTokens(access, exp, None, None, session.id)
            await self._revoke_for_reuse(session)
            raise RefreshInvalid(code="TOKEN_REUSED")

        user = await self.repo.get_user(session.user_id)
        if user is None or user.status != "ACTIVE":
            raise AccountDisabled()

        token.used_at = now
        session.last_seen_at = now
        new_raw = new_refresh_token()
        self.s.add(
            RefreshToken(
                session_id=session.id,
                token_hash=hash_refresh_token(new_raw),
                expires_at=session.expires_at,
            )
        )
        access, access_exp = create_access_token(user.id, session.id)
        return IssuedTokens(access, access_exp, new_raw, session.expires_at, session.id)

    async def _revoke_for_reuse(self, session: Session) -> None:
        """A rotated token was replayed: assume theft and kill the whole session family.
        Committed independently because the request itself fails."""
        async with independent_transaction() as tx:
            await AuthRepository(tx).revoke_sessions(
                session.user_id, reason="refresh_reuse", now=_now(), only=session.id
            )
            audit.record(
                tx,
                action="auth.refresh_reuse_detected",
                entity_type="session",
                entity_id=session.id,
                actor_user_id=session.user_id,
            )
        await mark_sessions_revoked([session.id])

    async def _audit_independently(
        self, action: str, user_id: uuid.UUID, after: dict[str, str]
    ) -> None:
        async with independent_transaction() as tx:
            audit.record(
                tx,
                action=action,
                entity_type="user",
                entity_id=user_id,
                actor_user_id=user_id,
                after=after,
            )

    async def logout(self, principal: Principal, *, everywhere: bool = False) -> None:
        revoked = await self.repo.revoke_sessions(
            principal.user_id,
            reason="logout_all" if everywhere else "logout",
            now=_now(),
            only=None if everywhere else principal.session_id,
        )
        audit.record(
            self.s,
            action="auth.logout_all" if everywhere else "auth.logout",
            entity_type="user",
            entity_id=principal.user_id,
            actor_user_id=principal.user_id,
            actor_roles=principal.role_codes,
        )
        on_commit(self.s, lambda: mark_sessions_revoked(revoked))

    async def revoke_refresh_cookie_session(self, raw_token: str) -> None:
        """Logout for a client whose access token already expired: revoke via refresh token."""
        token = await self.repo.get_refresh_token_for_update(hash_refresh_token(raw_token))
        if token is None:
            return
        session = await self.repo.get_session(token.session_id)
        if session is None or session.revoked_at is not None:
            return
        revoked = await self.repo.revoke_sessions(
            session.user_id, reason="logout", now=_now(), only=session.id
        )
        on_commit(self.s, lambda: mark_sessions_revoked(revoked))

    async def list_sessions(self, principal: Principal) -> list[Session]:
        return list(await self.repo.list_active_sessions(principal.user_id))

    async def revoke_session(self, principal: Principal, session_id: uuid.UUID) -> None:
        session = await self.repo.get_session(session_id)
        if session is None or session.user_id != principal.user_id:
            raise NotFound()
        revoked = await self.repo.revoke_sessions(
            principal.user_id, reason="user_revoked", now=_now(), only=session_id
        )
        audit.record(
            self.s,
            action="auth.session_revoked",
            entity_type="session",
            entity_id=session_id,
            actor_user_id=principal.user_id,
            actor_roles=principal.role_codes,
        )
        on_commit(self.s, lambda: mark_sessions_revoked(revoked))

    # ------------------------------------------------------------------ passwords
    async def reset_password(self, phone: str, code: str, new_password: str) -> None:
        await verify_otp(OtpPurpose.RESET, phone, code)
        user = await self.repo.get_user_by_phone(phone)
        if user is None or user.status != "ACTIVE":
            raise OtpInvalid()
        user.password_hash = hash_password(new_password)
        user.version += 1
        revoked = await self.repo.revoke_sessions(user.id, reason="password_reset", now=_now())
        audit.record(
            self.s,
            action="auth.password_reset",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
        )
        on_commit(self.s, lambda: mark_sessions_revoked(revoked))

    async def change_password(self, principal: Principal, current: str | None, new: str) -> None:
        user = await self.repo.get_user(principal.user_id, for_update=True)
        if user is None:
            raise NotFound()
        if user.password_hash is not None and (
            current is None or not verify_password(current, user.password_hash)
        ):
            raise InvalidCredentials("The current password is incorrect.")
        user.password_hash = hash_password(new)
        user.version += 1
        revoked = await self.repo.revoke_sessions(
            user.id, reason="password_changed", now=_now(), except_session=principal.session_id
        )
        audit.record(
            self.s,
            action="auth.password_changed",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            actor_roles=principal.role_codes,
        )
        on_commit(self.s, lambda: mark_sessions_revoked(revoked))

    # ------------------------------------------------------------------ profile
    async def me(self, principal: Principal) -> MeResponse:
        user = await self.repo.get_user(principal.user_id)
        if user is None:
            raise NotFound()
        # Rebuild from the DB so /me always reflects the latest grants.
        fresh = await build_principal(self.repo, user.id, principal.session_id) or principal
        return MeResponse(
            id=user.id,
            phone=user.phone,
            email=user.email,
            full_name=user.full_name,
            is_staff=user.is_staff,
            preferred_language=user.preferred_language,
            has_password=user.password_hash is not None,
            roles=[
                RoleGrantOut(role=g.role, scope_type=g.scope_type, scope_id=g.scope_id)
                for g in fresh.grants
            ],
            permissions=sorted(fresh.permissions),
        )

    async def update_profile(
        self, principal: Principal, full_name: str | None, preferred_language: str | None
    ) -> MeResponse:
        user = await self.repo.get_user(principal.user_id, for_update=True)
        if user is None:
            raise NotFound()
        before = {"full_name": user.full_name, "preferred_language": user.preferred_language}
        if full_name is not None:
            user.full_name = full_name.strip()
        if preferred_language is not None:
            user.preferred_language = preferred_language
        user.version += 1
        audit.record(
            self.s,
            action="user.profile_updated",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            before=before,
            after={"full_name": user.full_name, "preferred_language": user.preferred_language},
        )
        await self.s.flush()
        on_commit(self.s, lambda: invalidate_principal(user.id))
        return await self.me(principal)
