"""Request/response schemas for auth and access administration."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.phone import InvalidPhone, normalize_bd_phone
from app.modules.auth.otp import OtpPurpose
from app.modules.auth.permissions import ScopeType


def _phone(v: str) -> str:
    try:
        return normalize_bd_phone(v)
    except InvalidPhone as exc:
        raise ValueError(str(exc)) from exc


BdPhone = Annotated[str, AfterValidator(_phone), Field(examples=["01712345678"])]
OtpCode = Annotated[str, Field(pattern=r"^\d{4,8}$", examples=["123456"])]


def validate_password_strength(v: str) -> str:
    if len(v) < 10:
        raise ValueError("Password must be at least 10 characters.")
    if len(v) > 128:
        raise ValueError("Password must be at most 128 characters.")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password must contain letters and numbers.")
    return v


StrongPassword = Annotated[str, AfterValidator(validate_password_strength)]


# --- requests ---------------------------------------------------------------
class SendOtpRequest(BaseModel):
    phone: BdPhone
    purpose: Literal[OtpPurpose.LOGIN, OtpPurpose.RESET] = OtpPurpose.LOGIN


class VerifyOtpRequest(BaseModel):
    phone: BdPhone
    code: OtpCode
    #: Mobile clients that cannot use cookies receive the refresh token in the body.
    client: Literal["web", "mobile"] = "web"


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254, description="Phone or email")
    password: str = Field(min_length=1, max_length=128)
    client: Literal["web", "mobile"] = "web"

    @field_validator("identifier")
    @classmethod
    def _normalise(cls, v: str) -> str:
        v = v.strip()
        if "@" in v:
            return v.lower()
        try:
            return normalize_bd_phone(v)
        except InvalidPhone:
            return v


class TwoFactorVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=16, max_length=64)
    code: OtpCode
    client: Literal["web", "mobile"] = "web"


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(
        default=None, description="Mobile clients only; web uses the HttpOnly cookie."
    )


class ForgotPasswordRequest(BaseModel):
    phone: BdPhone


class ResetPasswordRequest(BaseModel):
    phone: BdPhone
    code: OtpCode
    new_password: StrongPassword


class ChangePasswordRequest(BaseModel):
    current_password: str | None = Field(default=None, max_length=128)
    new_password: StrongPassword


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    preferred_language: Literal["en", "bn"] | None = None


# --- responses --------------------------------------------------------------
class OtpSentResponse(BaseModel):
    sent: bool = True
    expires_in: int
    resend_after: int = 60


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105
    expires_at: datetime
    refresh_token: str | None = Field(default=None, description="Only for client=mobile")
    is_new_user: bool = False


class TwoFactorChallenge(BaseModel):
    two_factor_required: Literal[True] = True
    challenge_id: str
    phone_hint: str
    expires_in: int


class RoleGrantOut(BaseModel):
    role: str
    scope_type: str
    scope_id: uuid.UUID | None


class MeResponse(BaseModel):
    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str | None
    is_staff: bool
    preferred_language: str
    has_password: bool
    roles: list[RoleGrantOut]
    permissions: list[str]


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_agent: str | None
    ip: str | None
    created_at: datetime
    last_seen_at: datetime
    current: bool = False


# --- admin ------------------------------------------------------------------
class UserRoleOut(BaseModel):
    id: uuid.UUID
    role: str
    scope_type: str
    scope_id: uuid.UUID | None
    created_at: datetime


class UserOut(BaseModel):
    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str | None
    status: str
    is_staff: bool
    last_login_at: datetime | None
    created_at: datetime
    roles: list[UserRoleOut] = []


class CreateStaffUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: BdPhone = Field(description="Required: staff sign-in uses SMS second factor.")
    email: EmailStr | None = None
    password: StrongPassword
    role: str = Field(examples=["LAB_TECHNICIAN"])
    scope_type: ScopeType = ScopeType.GLOBAL
    scope_id: uuid.UUID | None = None


class UpdateUserStatusRequest(BaseModel):
    status: Literal["ACTIVE", "SUSPENDED", "DISABLED"]
    reason: str = Field(min_length=3, max_length=255)


class AssignRoleRequest(BaseModel):
    role: str
    scope_type: ScopeType = ScopeType.GLOBAL
    scope_id: uuid.UUID | None = None


class PermissionOut(BaseModel):
    code: str
    description: str


class RoleOut(BaseModel):
    code: str
    name: str
    description: str
    is_system: bool
    permissions: list[str]


class UpdateRolePermissionsRequest(BaseModel):
    permissions: list[str] = Field(max_length=200)
