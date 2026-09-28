"""Public authentication endpoints and the caller's own profile/sessions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import REFRESH_COOKIE, get_settings
from app.core.context import get_request_context
from app.core.db import get_session
from app.core.errors import error_responses
from app.core.rate_limit import hit
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal
from app.modules.auth.otp import OtpPurpose
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    OtpSentResponse,
    RefreshRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    SessionOut,
    TokenResponse,
    TwoFactorChallenge,
    TwoFactorVerifyRequest,
    UpdateProfileRequest,
    VerifyOtpRequest,
)
from app.modules.auth.service import AuthService, IssuedTokens, RefreshInvalid

router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(prefix="/me", tags=["me"])

Db = Annotated[AsyncSession, Depends(get_session)]


def _client_ip() -> str | None:
    ctx = get_request_context()
    return ctx.ip if ctx else None


def _set_refresh_cookie(response: Response, tokens: IssuedTokens) -> None:
    if tokens.refresh_token is None or tokens.refresh_expires_at is None:
        return
    s = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        expires=tokens.refresh_expires_at,
        path=s.refresh_cookie_path,
        secure=s.refresh_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=s.refresh_cookie_path,
        secure=s.refresh_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _token_response(response: Response, tokens: IssuedTokens, client: str) -> TokenResponse:
    if client == "web":
        _set_refresh_cookie(response, tokens)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_at=tokens.expires_at,
        refresh_token=tokens.refresh_token if client == "mobile" else None,
        is_new_user=tokens.is_new_user,
    )


@router.post(
    "/send-otp",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a one-time code by SMS",
    description="Public. Responds identically whether or not the number is registered. "
    "Rate-limited per phone and per IP.",
    responses=error_responses(400, 429),
)
async def send_otp(body: SendOtpRequest, db: Db) -> Envelope[OtpSentResponse]:
    await AuthService(db).send_otp(body.phone, OtpPurpose(body.purpose), _client_ip())
    return ok(OtpSentResponse(expires_in=get_settings().otp_ttl_seconds))


@router.post(
    "/verify-otp",
    summary="Sign in (or register) a patient with an SMS code",
    description="Public. Creates a patient account on first sign-in. Staff accounts are "
    "rejected with `STAFF_PASSWORD_LOGIN_REQUIRED`.",
    responses=error_responses(400, 401, 403, 429),
)
async def verify_otp(body: VerifyOtpRequest, response: Response, db: Db) -> Envelope[TokenResponse]:
    tokens = await AuthService(db).verify_login_otp(body.phone, body.code)
    return ok(_token_response(response, tokens, body.client))


@router.post(
    "/login",
    summary="Sign in with phone/email and password",
    description="Public. Staff accounts receive a two-factor challenge instead of tokens; "
    "complete it with `POST /auth/2fa/verify`.",
    responses=error_responses(400, 401, 429),
)
async def login(
    body: LoginRequest, response: Response, db: Db
) -> Envelope[TokenResponse | TwoFactorChallenge]:
    result = await AuthService(db).password_login(body.identifier, body.password, ip=_client_ip())
    if isinstance(result, TwoFactorChallenge):
        return ok(result)
    return ok(_token_response(response, result, body.client))


@router.post(
    "/2fa/verify",
    summary="Complete staff sign-in with the SMS code",
    responses=error_responses(400, 401, 429),
)
async def verify_two_factor(
    body: TwoFactorVerifyRequest, response: Response, db: Db
) -> Envelope[TokenResponse]:
    tokens = await AuthService(db).verify_two_factor(body.challenge_id, body.code)
    return ok(_token_response(response, tokens, body.client))


@router.post(
    "/refresh",
    summary="Rotate the refresh token and get a new access token",
    description="Web: reads the HttpOnly cookie. Mobile: send `refresh_token` in the body. "
    "Replaying a rotated token revokes the session (`TOKEN_REUSED`).",
    responses=error_responses(401, 429),
)
async def refresh(
    response: Response,
    db: Db,
    body: RefreshRequest | None = None,
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Envelope[TokenResponse]:
    ip = _client_ip()
    if ip:
        await hit(f"refresh-ip:{ip}", limit=120, window_seconds=60)
    raw = (body.refresh_token if body else None) or cookie_token
    client = "mobile" if body and body.refresh_token else "web"
    if not raw:
        raise RefreshInvalid()
    tokens = await AuthService(db).refresh(raw)
    return ok(_token_response(response, tokens, client))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End the current session",
    responses=error_responses(401),
)
async def logout(principal: CurrentPrincipal, db: Db) -> Response:
    await AuthService(db).logout(principal)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(resp)
    return resp


@router.post(
    "/logout-cookie",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End the session identified by the refresh cookie (access token expired)",
)
async def logout_with_cookie(
    db: Db, cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None
) -> Response:
    if cookie_token:
        await AuthService(db).revoke_refresh_cookie_session(cookie_token)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(resp)
    return resp


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End every session of the current user",
    responses=error_responses(401),
)
async def logout_all(principal: CurrentPrincipal, db: Db) -> Response:
    await AuthService(db).logout(principal, everywhere=True)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(resp)
    return resp


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a password-reset code",
    responses=error_responses(400, 429),
)
async def forgot_password(body: ForgotPasswordRequest, db: Db) -> Envelope[OtpSentResponse]:
    await AuthService(db).send_otp(body.phone, OtpPurpose.RESET, _client_ip())
    return ok(OtpSentResponse(expires_in=get_settings().otp_ttl_seconds))


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset the password with an SMS code (signs out all sessions)",
    responses=error_responses(400, 401, 429),
)
async def reset_password(body: ResetPasswordRequest, db: Db) -> Response:
    await AuthService(db).reset_password(body.phone, body.code, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change or set the password (signs out other sessions)",
    responses=error_responses(400, 401),
)
async def change_password(
    body: ChangePasswordRequest, principal: CurrentPrincipal, db: Db
) -> Response:
    await AuthService(db).change_password(principal, body.current_password, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions", summary="List my active sessions/devices", responses=error_responses(401))
async def list_sessions(principal: CurrentPrincipal, db: Db) -> Envelope[list[SessionOut]]:
    sessions = await AuthService(db).list_sessions(principal)
    return ok(
        [
            SessionOut.model_validate(s).model_copy(
                update={"current": s.id == principal.session_id}
            )
            for s in sessions
        ]
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out one of my sessions",
    responses=error_responses(401, 404),
)
async def revoke_session(session_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    await AuthService(db).revoke_session(principal, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@me_router.get(
    "", summary="My profile, roles and effective permissions", responses=error_responses(401)
)
async def me(principal: CurrentPrincipal, db: Db) -> Envelope[MeResponse]:
    return ok(await AuthService(db).me(principal))


@me_router.patch("", summary="Update my profile", responses=error_responses(400, 401))
async def update_me(
    body: UpdateProfileRequest, principal: CurrentPrincipal, db: Db
) -> Envelope[MeResponse]:
    return ok(
        await AuthService(db).update_profile(principal, body.full_name, body.preferred_language)
    )
