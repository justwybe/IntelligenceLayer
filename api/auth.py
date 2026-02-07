"""Bearer-token authentication for the API."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import settings

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Validate the Bearer token against the configured API key.

    Returns the token on success; raises 401 otherwise.
    """
    api_key = settings.wybe_api_key
    if not api_key or api_key == "disabled":
        # No key configured or explicitly disabled — open access
        return ""

    if credentials is None or credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def verify_ws_token(token: str | None) -> bool:
    """Check a WebSocket query-param token."""
    api_key = settings.wybe_api_key
    if not api_key or api_key == "disabled":
        return True
    return token == api_key
