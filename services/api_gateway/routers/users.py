from __future__ import annotations

"""User profile management router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.db.models import User, ReputationScore
from vault.db.session import get_db
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/users")


class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: str
    locale: str
    is_verified: bool
    created_at: str
    reputation_score: Optional[float] = None


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    timezone: Optional[str] = None
    locale: Optional[str] = None


@router.get("/me", response_model=UserProfile)
async def get_my_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get the current user's profile."""
    rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user.id))
    rep = rep_result.scalar_one_or_none()

    return UserProfile(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        latitude=user.latitude,
        longitude=user.longitude,
        timezone=user.timezone,
        locale=user.locale,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        reputation_score=rep.overall_score if rep else None,
    )


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()

    rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user.id))
    rep = rep_result.scalar_one_or_none()

    return UserProfile(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        latitude=user.latitude,
        longitude=user.longitude,
        timezone=user.timezone,
        locale=user.locale,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        reputation_score=rep.overall_score if rep else None,
    )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get a public user profile by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user.id))
    rep = rep_result.scalar_one_or_none()

    return UserProfile(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        latitude=user.latitude,
        longitude=user.longitude,
        timezone=user.timezone,
        locale=user.locale,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        reputation_score=rep.overall_score if rep else None,
    )
