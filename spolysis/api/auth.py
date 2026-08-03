from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from api.config import settings

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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"user_id": str(user.id), "email": user.email or ""}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def verify_internal_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> None:
    if credentials.credentials != settings.internal_api_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token")
