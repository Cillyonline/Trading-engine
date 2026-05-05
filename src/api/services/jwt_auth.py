"""JWT/OAuth2 authentication utilities (RS256).

Provides token creation and validation for the Cilly Trading Engine API.

Key management
--------------
Keys are loaded from environment variables:

  CILLY_JWT_PUBLIC_KEY   — PEM-encoded RSA public key  (required for JWT mode)
  CILLY_JWT_PRIVATE_KEY  — PEM-encoded RSA private key (required for /auth/token)

When neither variable is set, JWT auth is **disabled** and the legacy
``X-Cilly-Role`` header fallback remains active.  Set both variables to
enable production-grade JWT auth.

Token types
-----------
* **access token**  — short-lived (default: 30 minutes), carries the ``role`` claim.
* **refresh token** — long-lived (default: 7 days), used to obtain a new access
  token without re-authenticating.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

ALGORITHM = "RS256"

_ACCESS_TOKEN_TYPE = "access"
_REFRESH_TOKEN_TYPE = "refresh"


@dataclass(frozen=True)
class JwtSettings:
    """Resolved JWT configuration read from environment variables."""

    public_key: str
    """PEM-encoded RSA public key (empty string → JWT auth disabled)."""
    private_key: str
    """PEM-encoded RSA private key (empty string → /auth/token disabled)."""
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    @property
    def enabled(self) -> bool:
        """Return True when a public key is available for token validation."""
        return bool(self.public_key.strip())


def build_jwt_settings() -> JwtSettings:
    """Build :class:`JwtSettings` from environment variables."""
    return JwtSettings(
        public_key=os.getenv("CILLY_JWT_PUBLIC_KEY", "").strip(),
        private_key=os.getenv("CILLY_JWT_PRIVATE_KEY", "").strip(),
        algorithm=os.getenv("CILLY_JWT_ALGORITHM", ALGORITHM).strip(),
        access_token_expire_minutes=int(
            os.getenv("CILLY_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        ),
        refresh_token_expire_days=int(
            os.getenv("CILLY_JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
        ),
    )


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def create_access_token(
    role: str,
    *,
    private_key: str,
    algorithm: str = ALGORITHM,
    expires_delta: Optional[timedelta] = None,
    expire_minutes: int = 30,
) -> str:
    """Return a signed JWT access token carrying ``role``."""
    now = datetime.now(timezone.utc)
    delta = expires_delta if expires_delta is not None else timedelta(minutes=expire_minutes)
    payload: dict = {
        "sub": role,
        "role": role,
        "type": _ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + delta,
    }
    return jwt.encode(payload, private_key, algorithm=algorithm)


def create_refresh_token(
    role: str,
    *,
    private_key: str,
    algorithm: str = ALGORITHM,
    expire_days: int = 7,
) -> str:
    """Return a signed JWT refresh token carrying ``role``."""
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": role,
        "role": role,
        "type": _REFRESH_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(days=expire_days),
    }
    return jwt.encode(payload, private_key, algorithm=algorithm)


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


class TokenValidationError(Exception):
    """Raised when a JWT cannot be validated."""


def decode_access_token(token: str, *, public_key: str, algorithm: str = ALGORITHM) -> dict:
    """Decode and validate an access token.

    Returns the token payload dict on success.

    Raises :class:`TokenValidationError` on any validation failure (expired,
    bad signature, wrong token type, …).
    """
    try:
        payload = jwt.decode(token, public_key, algorithms=[algorithm])
    except ExpiredSignatureError as exc:
        raise TokenValidationError("token expired") from exc
    except (DecodeError, InvalidTokenError) as exc:
        raise TokenValidationError("invalid token") from exc

    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise TokenValidationError("wrong token type")

    role = payload.get("role")
    if not role or not isinstance(role, str):
        raise TokenValidationError("missing role claim")

    return payload


def decode_refresh_token(token: str, *, public_key: str, algorithm: str = ALGORITHM) -> dict:
    """Decode and validate a refresh token.

    Returns the token payload dict on success.

    Raises :class:`TokenValidationError` on any validation failure.
    """
    try:
        payload = jwt.decode(token, public_key, algorithms=[algorithm])
    except ExpiredSignatureError as exc:
        raise TokenValidationError("refresh token expired") from exc
    except (DecodeError, InvalidTokenError) as exc:
        raise TokenValidationError("invalid refresh token") from exc

    if payload.get("type") != _REFRESH_TOKEN_TYPE:
        raise TokenValidationError("wrong token type")

    role = payload.get("role")
    if not role or not isinstance(role, str):
        raise TokenValidationError("missing role claim")

    return payload
