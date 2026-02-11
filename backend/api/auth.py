"""Auth API endpoints — register, login, me."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status, Depends

from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from auth.middleware import get_current_user
from models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from services.session_store import create_user, get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """Register a new user."""
    existing = await get_user_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    hashed = hash_password(req.password)
    user = await create_user(req.username, hashed)

    access = create_access_token({"sub": user["id"], "username": user["username"]})
    refresh = create_refresh_token({"sub": user["id"]})

    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Login with username and password."""
    user = await get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access = create_access_token({"sub": user["id"], "username": user["username"]})
    refresh = create_refresh_token({"sub": user["id"]})

    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserOut(
        id=user["id"],
        username=user["username"],
        created_at=user["created_at"],
    )
