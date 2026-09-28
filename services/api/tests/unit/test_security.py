import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.ids import uuid7
from app.core.security import (
    TokenExpired,
    TokenInvalid,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip_and_argon2id() -> None:
    hashed = hash_password("correct horse 42")
    assert hashed.startswith("$argon2id$")
    assert "correct horse" not in hashed
    assert verify_password("correct horse 42", hashed)
    assert not verify_password("wrong horse 42", hashed)


def test_verify_password_without_hash_is_false() -> None:
    assert not verify_password("anything", None)
    assert not verify_password("anything", "not-a-hash")


def test_access_token_roundtrip() -> None:
    uid, sid = uuid.uuid4(), uuid.uuid4()
    token, exp = create_access_token(uid, sid)
    claims = decode_access_token(token)
    assert claims.user_id == uid and claims.session_id == sid
    assert claims.expires_at == exp.replace(microsecond=0)


def _encode(**overrides: object) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "typ": "access",
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    payload.update(overrides)
    return jwt.encode(payload, s.jwt_secret.get_secret_value(), algorithm=s.jwt_algorithm)


def test_expired_token_rejected() -> None:
    past = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
    with pytest.raises(TokenExpired):
        decode_access_token(_encode(exp=past))


@pytest.mark.parametrize("override", [{"typ": "refresh"}, {"aud": "other"}, {"iss": "evil"}])
def test_wrong_claims_rejected(override: dict[str, object]) -> None:
    with pytest.raises(TokenInvalid):
        decode_access_token(_encode(**override))


def test_tampered_signature_rejected() -> None:
    token = _encode()
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(TokenInvalid):
        decode_access_token(tampered)


def test_alg_none_rejected() -> None:
    unsigned = jwt.encode({"sub": str(uuid.uuid4()), "typ": "access"}, key="", algorithm="none")
    with pytest.raises(TokenInvalid):
        decode_access_token(unsigned)


def test_refresh_tokens_are_random_and_hashed() -> None:
    a, b = new_refresh_token(), new_refresh_token()
    assert a != b and len(a) >= 43
    assert hash_refresh_token(a) != a and len(hash_refresh_token(a)) == 64


def test_uuid7_is_version_7_and_time_ordered() -> None:
    ids = [uuid7() for _ in range(50)]
    assert all(i.version == 7 and i.variant == uuid.RFC_4122 for i in ids)
    timestamps = [i.int >> 80 for i in ids]
    assert timestamps == sorted(timestamps)
    assert len(set(ids)) == 50
