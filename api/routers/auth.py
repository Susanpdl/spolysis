from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from api.database import get_supabase_client
from api.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest):
    client = get_supabase_client()
    try:
        result = client.auth.sign_up({"email": body.email, "password": body.password})
        if result.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")
        return {
            "access_token": result.session.access_token if result.session else None,
            "user": {"id": result.user.id, "email": result.user.email},
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest):
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token": result.session.access_token,
            "user": {"id": result.user.id, "email": result.user.email},
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"message": "Logged out"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
