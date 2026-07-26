from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from api.config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_service_key,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"user_id": user_id, "email": payload.get("email", "")}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def verify_internal_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> None:
    if credentials.credentials != settings.internal_api_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token")
