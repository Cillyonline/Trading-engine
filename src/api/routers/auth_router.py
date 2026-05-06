"""Authentication router — JWT token issuance and refresh.

Endpoints
---------
POST /auth/token
    Issue a new access token and refresh token.
    Requires the API to be configured with a private key
    (``CILLY_JWT_PRIVATE_KEY`` env var).  The caller supplies the desired
    ``role`` in the request body.

POST /auth/refresh
    Exchange a valid refresh token for a new access token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.jwt_auth import (
    JwtSettings,
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


class TokenRequest(BaseModel):
    role: str
    """Requested role: ``read_only``, ``operator``, or ``owner``."""


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@dataclass
class AuthRouterDependencies:
    get_jwt_settings: Callable[[], JwtSettings]
    get_role_precedence: Callable[[], dict[str, int]]


def build_auth_router(*, deps: AuthRouterDependencies) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/token", response_model=TokenResponse)
    def issue_token(request: TokenRequest) -> TokenResponse:
        """Issue a JWT access token and refresh token for the requested role.

        Requires ``CILLY_JWT_PRIVATE_KEY`` to be configured.  This endpoint
        is intended for use by trusted operator tooling and automated pipelines.
        """
        jwt_settings = deps.get_jwt_settings()
        role_precedence = deps.get_role_precedence()

        if not jwt_settings.enabled:
            raise HTTPException(
                status_code=501,
                detail="jwt_not_configured",
            )
        if not jwt_settings.private_key:
            raise HTTPException(
                status_code=501,
                detail="jwt_private_key_not_configured",
            )

        role = request.role.strip().lower()
        if role not in role_precedence:
            raise HTTPException(
                status_code=400,
                detail="invalid_role",
            )

        access_token = create_access_token(
            role,
            private_key=jwt_settings.private_key,
            algorithm=jwt_settings.algorithm,
            expire_minutes=jwt_settings.access_token_expire_minutes,
        )
        refresh = create_refresh_token(
            role,
            private_key=jwt_settings.private_key,
            algorithm=jwt_settings.algorithm,
            expire_days=jwt_settings.refresh_token_expire_days,
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh)

    @router.post("/refresh", response_model=AccessTokenResponse)
    def refresh_token(request: RefreshRequest) -> AccessTokenResponse:
        """Exchange a valid refresh token for a new access token."""
        jwt_settings = deps.get_jwt_settings()

        if not jwt_settings.enabled:
            raise HTTPException(
                status_code=501,
                detail="jwt_not_configured",
            )
        if not jwt_settings.private_key:
            raise HTTPException(
                status_code=501,
                detail="jwt_private_key_not_configured",
            )

        try:
            payload = decode_refresh_token(
                request.refresh_token,
                public_key=jwt_settings.public_key,
                algorithm=jwt_settings.algorithm,
            )
        except TokenValidationError as exc:
            raise HTTPException(status_code=401, detail="invalid_refresh_token") from exc

        role = payload["role"]
        access_token = create_access_token(
            role,
            private_key=jwt_settings.private_key,
            algorithm=jwt_settings.algorithm,
            expire_minutes=jwt_settings.access_token_expire_minutes,
        )
        return AccessTokenResponse(access_token=access_token)

    return router
