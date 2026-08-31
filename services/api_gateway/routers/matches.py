from __future__ import annotations

"""Matches router — propose, accept, reject, and view matches."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.db.models import (
    Conversation,
    ConversationStatus,
    EscrowStatus,
    Match,
    MatchStatus,
    MarketListing,
    Message,
    ListingStatus,
    Subscription,
    User,
)
from services.api_gateway.routers.pricing_agent import generate_pricing_messages
from vault.db.session import get_db
from vault.events import Event, EventType, publisher
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/matches")


class MatchResponse(BaseModel):
    id: str
    listing_id: str
    buyer_id: str
    seller_id: str
    status: str
    match_score: float
    trust_score: float
    proximity_score: float
    schedule_score: float
    proposed_price: float
    service_name: str
    seller_name: str
    expires_at: str
    accepted_at: Optional[str]
    created_at: str


class MatchActionResponse(BaseModel):
    message: str
    match_id: str
    status: str


@router.get("", response_model=list[MatchResponse])
async def list_my_matches(
    role: Optional[str] = Query(None, description="Filter as 'buyer' or 'seller'"),
    status_filter: Optional[MatchStatus] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List matches where the current user is buyer or seller."""
    query = select(Match)
    if role == "buyer":
        query = query.where(Match.buyer_id == user.id)
    elif role == "seller":
        query = query.where(Match.seller_id == user.id)
    else:
        query = query.where((Match.buyer_id == user.id) | (Match.seller_id == user.id))

    if status_filter:
        query = query.where(Match.status == status_filter)

    query = query.order_by(Match.created_at.desc())
    result = await db.execute(query)
    matches = result.scalars().all()

    responses = []
    for m in matches:
        listing_result = await db.execute(select(MarketListing).where(MarketListing.id == m.listing_id))
        listing = listing_result.scalar_one_or_none()
        sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id)) if listing else None
        sub = sub_result.scalar_one_or_none() if sub_result else None
        seller_result = await db.execute(select(User).where(User.id == m.seller_id))
        seller = seller_result.scalar_one_or_none()

        responses.append(MatchResponse(
            id=str(m.id),
            listing_id=str(m.listing_id),
            buyer_id=str(m.buyer_id),
            seller_id=str(m.seller_id),
            status=m.status.value,
            match_score=m.match_score,
            trust_score=m.trust_score,
            proximity_score=m.proximity_score,
            schedule_score=m.schedule_score,
            proposed_price=m.proposed_price,
            service_name=sub.service_name if sub else "Unknown",
            seller_name=seller.display_name if seller else "Unknown",
            expires_at=m.expires_at.isoformat(),
            accepted_at=m.accepted_at.isoformat() if m.accepted_at else None,
            created_at=m.created_at.isoformat(),
        ))

    return responses


@router.post("/propose/{listing_id}", response_model=MatchActionResponse, status_code=status.HTTP_201_CREATED)
async def propose_match(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Propose a match for a listing (initiate the matching process)."""
    listing_result = await db.execute(select(MarketListing).where(MarketListing.id == listing_id))
    listing = listing_result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Listing is no longer active")
    if listing.seller_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot match with your own listing")
    if listing.seats_available < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No seats available")

    # Check for existing active match
    existing = await db.execute(
        select(Match).where(
            Match.listing_id == listing.id,
            Match.buyer_id == user.id,
            Match.status.in_([MatchStatus.PROPOSED, MatchStatus.ACCEPTED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an active match for this listing")

    # Calculate scores
    trust_score = 0.8  # Will be calculated by Trust Agent in production
    proximity_score = 0.9  # Will be calculated using geolocation
    schedule_score = 0.7  # Will be calculated using usage patterns
    match_score = (trust_score * 0.4 + proximity_score * 0.3 + schedule_score * 0.3)

    match = Match(
        id=uuid.uuid4(),
        listing_id=listing.id,
        buyer_id=user.id,
        seller_id=listing.seller_id,
        status=MatchStatus.PROPOSED,
        match_score=round(match_score, 3),
        trust_score=trust_score,
        proximity_score=proximity_score,
        schedule_score=schedule_score,
        proposed_price=listing.dynamic_price,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(match)
    await db.flush()

    await publisher.publish(Event(EventType.MATCH_PROPOSED, {
        "match_id": str(match.id),
        "listing_id": str(listing.id),
        "buyer_id": str(user.id),
        "seller_id": str(listing.seller_id),
    }, source="api-gateway"))

    return MatchActionResponse(
        message="Match proposed successfully",
        match_id=str(match.id),
        status=match.status.value,
    )


@router.post("/{match_id}/accept", response_model=MatchActionResponse)
async def accept_match(
    match_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a proposed match (seller action)."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the seller can accept a match")
    if match.status != MatchStatus.PROPOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot accept match in {match.status.value} status")
    if match.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match has expired")

    match.status = MatchStatus.ACCEPTED
    match.accepted_at = datetime.now(timezone.utc)

    # Update listing seats
    listing_result = await db.execute(select(MarketListing).where(MarketListing.id == match.listing_id))
    listing = listing_result.scalar_one_or_none()
    service_name = "Unknown Service"
    subscription_tier = "family"
    monthly_cost = 0.0
    if listing:
        listing.seats_available -= 1
        if listing.seats_available <= 0:
            listing.status = ListingStatus.MATCHED
        # Fetch real subscription details
        sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
        sub = sub_result.scalar_one_or_none()
        if sub:
            service_name = sub.service_name
            subscription_tier = sub.tier.value
            monthly_cost = sub.monthly_cost

    # Auto-create conversation for match negotiation with full subscription details
    subscription_details = {
        "service_name": service_name,
        "proposed_price": match.proposed_price,
        "subscription_tier": subscription_tier,
        "total_subscription_cost": monthly_cost,
        "seats_included": 1,
        "billing_cycle": "monthly",
        "service_category": listing.meta.get("category", "general") if listing and listing.meta else "general",
    }
    conversation = Conversation(
        id=uuid.uuid4(),
        match_id=match.id,
        buyer_id=match.buyer_id,
        seller_id=match.seller_id,
        status=ConversationStatus.ACTIVE,
        topic="subscription_pricing",
        subscription_details=subscription_details,
    )
    db.add(conversation)
    await db.flush()

    # Generate and store pricing agent messages
    agent_messages = generate_pricing_messages(
        service_name=service_name,
        proposed_price=match.proposed_price,
        total_cost=monthly_cost,
        tier=subscription_tier,
        match_id=str(match.id),
    )
    for msg_data in agent_messages:
        db.add(Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            sender_id=match.seller_id,
            role="agent",
            content=msg_data["content"],
            message_type=msg_data.get("type", "pricing_info"),
            meta=msg_data.get("meta", {}),
        ))

    await db.flush()

    await publisher.publish(Event(EventType.MATCH_ACCEPTED, {
        "match_id": str(match.id),
        "buyer_id": str(match.buyer_id),
        "seller_id": str(match.seller_id),
        "price": match.proposed_price,
        "conversation_id": str(conversation.id),
    }, source="api-gateway"))

    return MatchActionResponse(
        message=f"Match accepted. Conversation initiated for {service_name} subscription pricing.",
        match_id=str(match.id),
        status=match.status.value,
    )


@router.post("/{match_id}/reject", response_model=MatchActionResponse)
async def reject_match(
    match_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposed match."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.seller_id != user.id and match.buyer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reject this match")
    if match.status != MatchStatus.PROPOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot reject match in {match.status.value} status")

    match.status = MatchStatus.REJECTED
    await db.flush()

    await publisher.publish(Event(EventType.MATCH_REJECTED, {"match_id": str(match.id)}, source="api-gateway"))

    return MatchActionResponse(
        message="Match rejected",
        match_id=str(match.id),
        status=match.status.value,
    )
