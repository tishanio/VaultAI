from __future__ import annotations

"""Authentication router — registration, login, token refresh, logout."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import User
from vault.db.session import get_db
from vault.events import Event, EventType, publisher
from vault.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

    token = auth_header[7:]
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Check for duplicate username
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        email=body.email,
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        phone=body.phone,
    )
    db.add(user)
    await db.flush()

    await publisher.publish(Event(EventType.USER_CREATED, {"user_id": str(user.id), "email": user.email}, source="api-gateway"))

    access_token = create_access_token(str(user.id), {"username": user.username})
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    access_token = create_access_token(str(user.id), {"username": user.username})
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for new access + refresh tokens."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    access_token = create_access_token(str(user.id), {"username": user.username})
    refresh_token_new = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_new,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password_hash = hash_password(body.new_password)
    await db.flush()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: User = Depends(get_current_user)):
    """Logout current user. Client should discard tokens."""
    # In production, add token to a blacklist in Redis
    pass
