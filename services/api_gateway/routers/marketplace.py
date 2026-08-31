from __future__ import annotations

"""Marketplace router — create, browse, and manage listings."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.db.models import (
    ListingStatus,
    MarketListing,
    Subscription,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventType, publisher
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/marketplace")


class CreateListingRequest(BaseModel):
    subscription_id: str
    asking_price: float = Field(gt=0, le=100)
    seats_available: int = Field(ge=1, le=5)
    description: Optional[str] = Field(None, max_length=500)
    preferred_schedule: Optional[dict] = None
    geo_radius_km: float = Field(default=10.0, ge=1, le=100)
    min_trust_score: float = Field(default=0.6, ge=0, le=1)
    expires_in_hours: int = Field(default=168, ge=1, le=720)  # default 7 days


class ListingResponse(BaseModel):
    id: str
    seller_id: str
    service_name: str
    service_category: str
    status: str
    asking_price: float
    dynamic_price: float
    seats_available: int
    description: Optional[str]
    geo_radius_km: float
    min_trust_score: float
    expires_at: Optional[str]
    seller_name: str
    seller_reputation: float
    created_at: str


class BrowseRequest(BaseModel):
    service_name: Optional[str] = None
    service_category: Optional[str] = None
    max_price: Optional[float] = None
    min_trust_score: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 25.0


@router.get("/listings", response_model=list[ListingResponse])
async def browse_listings(
    service_name: Optional[str] = Query(None),
    service_category: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    min_trust_score: Optional[float] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(default=25.0),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse available subscription listings with optional filters."""
    query = select(MarketListing).where(MarketListing.status == ListingStatus.ACTIVE)

    if service_name:
        query = query.join(Subscription).where(Subscription.service_name == service_name)
    if service_category:
        query = query.join(Subscription).where(Subscription.service_category == service_category)
    if max_price is not None:
        query = query.where(MarketListing.dynamic_price <= max_price)
    if min_trust_score is not None:
        query = query.where(MarketListing.min_trust_score <= min_trust_score)

    query = query.order_by(MarketListing.dynamic_price.asc()).offset(offset).limit(limit)
    result = await db.execute(query)
    listings = result.scalars().all()

    responses = []
    for listing in listings:
        sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
        sub = sub_result.scalar_one_or_none()
        seller_result = await db.execute(select(User).where(User.id == listing.seller_id))
        seller = seller_result.scalar_one_or_none()

        from vault.db.models import ReputationScore
        rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == listing.seller_id))
        rep = rep_result.scalar_one_or_none()

        responses.append(ListingResponse(
            id=str(listing.id),
            seller_id=str(listing.seller_id),
            service_name=sub.service_name if sub else "Unknown",
            service_category=sub.service_category if sub else "unknown",
            status=listing.status.value,
            asking_price=listing.asking_price,
            dynamic_price=listing.dynamic_price,
            seats_available=listing.seats_available,
            description=listing.description,
            geo_radius_km=listing.geo_radius_km,
            min_trust_score=listing.min_trust_score,
            expires_at=listing.expires_at.isoformat() if listing.expires_at else None,
            seller_name=seller.display_name if seller else "Unknown",
            seller_reputation=rep.overall_score if rep else 0.5,
            created_at=listing.created_at.isoformat(),
        ))

    return responses


@router.post("/listings", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: CreateListingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new listing for available subscription seats."""
    sub_result = await db.execute(
        select(Subscription).where(Subscription.id == body.subscription_id, Subscription.user_id == user.id)
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    available_seats = sub.max_seats - sub.used_seats
    if body.seats_available > available_seats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {available_seats} seats available",
        )

    # Dynamic pricing: base price with demand adjustment
    base_price = body.asking_price
    dynamic_price = base_price * 0.9  # Start at 10% discount to attract matches

    listing = MarketListing(
        id=uuid.uuid4(),
        seller_id=user.id,
        subscription_id=sub.id,
        status=ListingStatus.ACTIVE,
        asking_price=base_price,
        dynamic_price=round(dynamic_price, 2),
        seats_available=body.seats_available,
        description=body.description,
        preferred_schedule=body.preferred_schedule,
        geo_radius_km=body.geo_radius_km,
        min_trust_score=body.min_trust_score,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours),
    )
    db.add(listing)
    await db.flush()

    await publisher.publish(Event(EventType.LISTING_CREATED, {"listing_id": str(listing.id), "seller_id": str(user.id), "service": sub.service_name}, source="api-gateway"))

    from vault.db.models import ReputationScore
    rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user.id))
    rep = rep_result.scalar_one_or_none()

    return ListingResponse(
        id=str(listing.id),
        seller_id=str(user.id),
        service_name=sub.service_name,
        service_category=sub.service_category,
        status=listing.status.value,
        asking_price=listing.asking_price,
        dynamic_price=listing.dynamic_price,
        seats_available=listing.seats_available,
        description=listing.description,
        geo_radius_km=listing.geo_radius_km,
        min_trust_score=listing.min_trust_score,
        expires_at=listing.expires_at.isoformat(),
        seller_name=user.display_name,
        seller_reputation=rep.overall_score if rep else 0.5,
        created_at=listing.created_at.isoformat(),
    )


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_listing(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a listing."""
    result = await db.execute(
        select(MarketListing).where(MarketListing.id == listing_id, MarketListing.seller_id == user.id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    listing.status = ListingStatus.REMOVED
    await db.flush()
