import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.errors import Conflict, install_error_handlers
from app.core.logging import redact_processor
from app.core.middleware import RequestContextMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(RequestContextMiddleware)

    class Body(BaseModel):
        age: int

    @app.post("/validate")
    async def validate(body: Body) -> dict[str, int]:
        return {"age": body.age}

    @app.get("/conflict")
    async def conflict() -> None:
        raise Conflict("Slot taken.", code="BOOKING_SLOT_UNAVAILABLE")

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("database password is hunter2")

    return app


client = TestClient(_app(), raise_server_exceptions=False)


def test_app_error_uses_standard_envelope_with_request_id() -> None:
    res = client.get("/conflict", headers={"X-Request-ID": "req-abc-12345"})
    assert res.status_code == 409
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "BOOKING_SLOT_UNAVAILABLE"
    assert body["error"]["request_id"] == "req-abc-12345"
    assert res.headers["x-request-id"] == "req-abc-12345"


def test_validation_errors_list_fields() -> None:
    res = client.post("/validate", json={"age": "old"})
    assert res.status_code == 400
    err = res.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["details"][0]["field"] == "age"


def test_unhandled_errors_do_not_leak_internals_and_keep_request_id() -> None:
    res = client.get("/boom", headers={"X-Request-ID": "req-boom-1234"})
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "INTERNAL_ERROR"
    assert res.json()["error"]["request_id"] == "req-boom-1234"
    assert res.headers["x-request-id"] == "req-boom-1234"
    assert "hunter2" not in res.text


def test_invalid_incoming_request_id_is_replaced() -> None:
    res = client.get("/conflict", headers={"X-Request-ID": "bad id\n<script>"})
    assert res.headers["x-request-id"] != "bad id\n<script>"
    assert len(res.headers["x-request-id"]) == 32


def test_security_headers_present() -> None:
    res = client.get("/conflict")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"


def test_log_redaction_masks_secrets_recursively() -> None:
    event = redact_processor(
        None,
        "info",
        {
            "event": "x",
            "password": "p",
            "otp_code": "123456",
            "refresh_token": "t",
            "nested": {"authorization": "Bearer abc", "status": 200},
            "status_code": 200,
        },
    )
    assert event["password"] == event["otp_code"] == event["refresh_token"] == "[REDACTED]"
    assert event["nested"] == {"authorization": "[REDACTED]", "status": 200}
    assert event["status_code"] == 200


@pytest.mark.parametrize("secret", ["", "short", "x" * 31])
def test_settings_require_strong_secrets(secret: str) -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret=secret, otp_hmac_secret="y" * 40)  # type: ignore[arg-type]


def test_production_rejects_placeholder_secrets_and_console_sms() -> None:
    strong = "k" * 48
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret="change-me-" + strong,  # type: ignore[arg-type]
            otp_hmac_secret=strong,
            sms_provider="disabled",
        )
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret=strong,  # type: ignore[arg-type]
            otp_hmac_secret=strong,
            sms_provider="console",
        )
