"""Integration tests for the JWT authentication endpoints and role enforcement.

Covers:
- POST /auth/token — returns 501 when JWT is not configured
- POST /auth/token — issues access + refresh tokens when JWT is configured
- POST /auth/refresh — returns new access token from valid refresh token
- POST /auth/refresh — returns 401 for expired/invalid refresh token
- Protected endpoints — return 401 when JWT is configured and no Bearer token
- Protected endpoints — return 200 with valid Bearer token
- Protected endpoints — return 403 when role is insufficient
- Protected endpoints — return 401 when Bearer token is invalid/expired
"""

from __future__ import annotations

import os
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from api.services.jwt_auth import (
    JwtSettings,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests

# ---------------------------------------------------------------------------
# RSA key pair for tests (2048-bit, generated at import time)
# ---------------------------------------------------------------------------

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_private_key_obj = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
TEST_PRIVATE_KEY: str = _private_key_obj.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
).decode()
TEST_PUBLIC_KEY: str = _private_key_obj.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_access_token(role: str, *, expire_minutes: int = 30) -> str:
    return create_access_token(
        role,
        private_key=TEST_PRIVATE_KEY,
        expire_minutes=expire_minutes,
    )


def _make_refresh_token(role: str) -> str:
    return create_refresh_token(role, private_key=TEST_PRIVATE_KEY)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# jwt_auth unit tests
# ---------------------------------------------------------------------------


class TestJwtAuthUnit:
    def test_create_and_decode_access_token(self) -> None:
        token = _make_access_token("read_only")
        payload = decode_access_token(token, public_key=TEST_PUBLIC_KEY)
        assert payload["role"] == "read_only"
        assert payload["type"] == "access"

    def test_expired_access_token_raises(self) -> None:
        from api.services.jwt_auth import TokenValidationError

        token = create_access_token(
            "operator",
            private_key=TEST_PRIVATE_KEY,
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(TokenValidationError, match="expired"):
            decode_access_token(token, public_key=TEST_PUBLIC_KEY)

    def test_wrong_algorithm_raises(self) -> None:
        """A HS256 token must not validate against an RS256 public key."""
        import jwt as pyjwt
        from api.services.jwt_auth import TokenValidationError

        hs_token = pyjwt.encode(
            {"sub": "owner", "role": "owner", "type": "access"},
            "secret",
            algorithm="HS256",
        )
        with pytest.raises(TokenValidationError):
            decode_access_token(hs_token, public_key=TEST_PUBLIC_KEY)

    def test_jwt_settings_enabled_when_public_key_present(self) -> None:
        settings = JwtSettings(
            public_key=TEST_PUBLIC_KEY,
            private_key=TEST_PRIVATE_KEY,
            algorithm="RS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )
        assert settings.enabled is True

    def test_jwt_settings_disabled_when_no_public_key(self) -> None:
        settings = JwtSettings(
            public_key="",
            private_key="",
            algorithm="RS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )
        assert settings.enabled is False


# ---------------------------------------------------------------------------
# /auth/token — no JWT configured (default)
# ---------------------------------------------------------------------------


def test_auth_token_returns_501_when_jwt_not_configured() -> None:
    import api.main as api_main

    with TestClient(api_main.app) as client:
        response = client.post("/auth/token", json={"role": "read_only"})

    assert response.status_code == 501
    assert response.json()["detail"] == "jwt_not_configured"


def test_auth_refresh_returns_501_when_jwt_not_configured() -> None:
    import api.main as api_main

    with TestClient(api_main.app) as client:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "dummy"},
        )

    assert response.status_code == 501
    assert response.json()["detail"] == "jwt_not_configured"


# ---------------------------------------------------------------------------
# /auth/token — JWT configured
# ---------------------------------------------------------------------------


def test_auth_token_issues_tokens_for_valid_role(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.main as api_main

    jwt_settings = JwtSettings(
        public_key=TEST_PUBLIC_KEY,
        private_key=TEST_PRIVATE_KEY,
        algorithm="RS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    monkeypatch.setattr(api_main, "JWT_SETTINGS", jwt_settings)

    with TestClient(api_main.app) as client:
        response = client.post("/auth/token", json={"role": "read_only"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_auth_token_rejects_unknown_role(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.main as api_main

    jwt_settings = JwtSettings(
        public_key=TEST_PUBLIC_KEY,
        private_key=TEST_PRIVATE_KEY,
        algorithm="RS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    monkeypatch.setattr(api_main, "JWT_SETTINGS", jwt_settings)

    with TestClient(api_main.app) as client:
        response = client.post("/auth/token", json={"role": "superuser"})

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_role"


def test_auth_token_access_token_carries_correct_role(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.main as api_main

    jwt_settings = JwtSettings(
        public_key=TEST_PUBLIC_KEY,
        private_key=TEST_PRIVATE_KEY,
        algorithm="RS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    monkeypatch.setattr(api_main, "JWT_SETTINGS", jwt_settings)

    with TestClient(api_main.app) as client:
        response = client.post("/auth/token", json={"role": "operator"})

    body = response.json()
    payload = decode_access_token(body["access_token"], public_key=TEST_PUBLIC_KEY)
    assert payload["role"] == "operator"


def test_auth_refresh_issues_new_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.main as api_main

    jwt_settings = JwtSettings(
        public_key=TEST_PUBLIC_KEY,
        private_key=TEST_PRIVATE_KEY,
        algorithm="RS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    monkeypatch.setattr(api_main, "JWT_SETTINGS", jwt_settings)

    with TestClient(api_main.app) as client:
        issue_resp = client.post("/auth/token", json={"role": "owner"})
        refresh_token = issue_resp.json()["refresh_token"]
        refresh_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    assert refresh_resp.status_code == 200
    body = refresh_resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_auth_refresh_with_invalid_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.main as api_main

    jwt_settings = JwtSettings(
        public_key=TEST_PUBLIC_KEY,
        private_key=TEST_PRIVATE_KEY,
        algorithm="RS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    monkeypatch.setattr(api_main, "JWT_SETTINGS", jwt_settings)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_refresh_token"


# ---------------------------------------------------------------------------
# Role enforcement — JWT mode
# ---------------------------------------------------------------------------


def _jwt_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> JwtSettings:
    """Activate JWT mode on the running api.main module."""
    import api.main as api_main

    jwt_settings = JwtSettings(
        public_key=TEST_PUBLIC_KEY,
        private_key=TEST_PRIVATE_KEY,
        algorithm="RS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    monkeypatch.setattr(api_main, "JWT_SETTINGS", jwt_settings)
    monkeypatch.setattr(api_main._runtime_service, "jwt_settings", jwt_settings)
    return jwt_settings


def test_jwt_mode_rejects_request_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 401


def test_jwt_mode_rejects_legacy_role_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """When JWT is configured, X-Cilly-Role header must not grant access."""
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    with TestClient(api_main.app) as client:
        response = client.get(
            "/health",
            headers={"X-Cilly-Role": "owner"},
        )

    assert response.status_code == 401


def test_jwt_mode_accepts_valid_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    token = _make_access_token("read_only")
    with TestClient(api_main.app) as client:
        response = client.get("/health", headers=_bearer(token))

    assert response.status_code == 200


def test_jwt_mode_rejects_insufficient_role(monkeypatch: pytest.MonkeyPatch) -> None:
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    token = _make_access_token("read_only")
    with TestClient(api_main.app) as client:
        response = client.post("/execution/start", headers=_bearer(token))

    assert response.status_code == 403


def test_jwt_mode_accepts_elevated_role(monkeypatch: pytest.MonkeyPatch) -> None:
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    token = _make_access_token("owner")
    with TestClient(api_main.app) as client:
        response = client.post("/execution/start", headers=_bearer(token))

    assert response.status_code in (200, 409)


def test_jwt_mode_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    token = create_access_token(
        "owner",
        private_key=TEST_PRIVATE_KEY,
        expires_delta=timedelta(seconds=-1),
    )
    with TestClient(api_main.app) as client:
        response = client.get("/health", headers=_bearer(token))

    assert response.status_code == 401


def test_jwt_mode_rejects_malformed_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _jwt_monkeypatch(monkeypatch)
    import api.main as api_main

    with TestClient(api_main.app) as client:
        response = client.get(
            "/health",
            headers={"Authorization": "Bearer this.is.garbage"},
        )

    assert response.status_code == 401

