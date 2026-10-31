from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gotrue.errors import AuthApiError
from api.config import settings
import secrets

security = HTTPBearer()

# Lazy-initialized Supabase client for token validation
_auth_client = None


def _get_auth_client():
    global _auth_client
    if _auth_client is None:
        from supabase import create_client

        _auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _auth_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        response = _get_auth_client().auth.get_user(token)
        user = response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return {"user_id": str(user.id), "email": user.email or ""}
    except HTTPException:
        raise
    except AuthApiError as exc:
        if exc.status in {401, 403}:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify your session. Please try again.",
        ) from exc
    except Exception:
        # Network failures, throttling, and malformed upstream responses do not
        # establish that the athlete's credentials are invalid. Fail closed,
        # while allowing the same session to retry after service recovery.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify your session. Please try again.",
        )


def verify_internal_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> None:
    if not secrets.compare_digest(
        credentials.credentials, settings.internal_api_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token"
        )
