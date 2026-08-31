from __future__ import annotations

"""Subscriptions router — CRUD, usage tracking, analytics."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.db.models import (
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    SubscriptionUsage,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventType, publisher
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/subscriptions")

ALLOWED_SERVICES = {
    "Spotify": {"category": "music", "tiers": ["family", "premium"], "max_seats": 6},
    "Google One": {"category": "cloud_storage", "tiers": ["family", "premium"], "max_seats": 5},
    "YouTube Premium": {"category": "streaming", "tiers": ["family", "premium"], "max_seats": 5},
    "YouTube Music": {"category": "music", "tiers": ["family", "premium"], "max_seats": 5},
    "Apple Music": {"category": "music", "tiers": ["family", "premium"], "max_seats": 6},
    "Headspace": {"category": "wellness", "tiers": ["family", "premium"], "max_seats": 6},
    "Calm": {"category": "wellness", "tiers": ["family", "premium"], "max_seats": 6},
    "Duolingo": {"category": "education", "tiers": ["family", "premium"], "max_seats": 6},
    "Microsoft 365": {"category": "productivity", "tiers": ["family", "premium"], "max_seats": 6},
    "Canva": {"category": "design", "tiers": ["family", "premium"], "max_seats": 5},
}

BLOCKED_SERVICES = {"Netflix", "Adobe", "Hulu", "HBO Max", "Disney+", "Amazon Prime Video", "Paramount+"}


class CreateSubscriptionRequest(BaseModel):
    service_name: str
    tier: SubscriptionTier
    monthly_cost: float = Field(gt=0)
    max_seats: int = Field(ge=2, le=6)
    billing_cycle_day: int = Field(ge=1, le=28)


class SubscriptionResponse(BaseModel):
    id: str
    service_name: str
    service_category: str
    service_logo_url: Optional[str] = None
    tier: str
    status: str
    monthly_cost: float
    max_seats: int
    used_seats: int
    billing_cycle_day: int
    usage_percentage: float = 0.0
    created_at: str


class UsageRecordRequest(BaseModel):
    usage_minutes: int = Field(ge=0)
    session_count: int = Field(ge=0, default=1)
    peak_usage_hour: Optional[int] = Field(None, ge=0, le=23)


class UsageAnalytics(BaseModel):
    subscription_id: str
    service_name: str
    avg_daily_minutes: float
    total_monthly_minutes: int
    usage_percentage: float
    optimization_score: float  # 0-1, how well the user is using the sub
    recommendation: str


@router.get("", response_model=list[SubscriptionResponse])
async def list_my_subscriptions(
    status_filter: Optional[SubscriptionStatus] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's subscriptions."""
    query = select(Subscription).where(Subscription.user_id == user.id)
    if status_filter:
        query = query.where(Subscription.status == status_filter)
    query = query.order_by(Subscription.created_at.desc())

    result = await db.execute(query)
    subs = result.scalars().all()

    return [
        SubscriptionResponse(
            id=str(s.id),
            service_name=s.service_name,
            service_category=s.service_category,
            service_logo_url=s.service_logo_url,
            tier=s.tier.value,
            status=s.status.value,
            monthly_cost=s.monthly_cost,
            max_seats=s.max_seats,
            used_seats=s.used_seats,
            billing_cycle_day=s.billing_cycle_day,
            usage_percentage=s.usage_data.get("usage_percentage", 0) if s.usage_data else 0,
            created_at=s.created_at.isoformat(),
        )
        for s in subs
    ]


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    body: CreateSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a subscription to track."""
    if body.service_name in BLOCKED_SERVICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.service_name} is not supported. Vault only supports family-plan-compliant services.",
        )

    service_info = ALLOWED_SERVICES.get(body.service_name)
    if not service_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.service_name} is not yet supported. Supported: {', '.join(ALLOWED_SERVICES.keys())}",
        )

    if body.max_seats > service_info["max_seats"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max seats for {body.service_name} is {service_info['max_seats']}",
        )

    sub = Subscription(
        id=uuid.uuid4(),
        user_id=user.id,
        service_name=body.service_name,
        service_category=service_info["category"],
        tier=body.tier,
        status=SubscriptionStatus.ACTIVE,
        monthly_cost=body.monthly_cost,
        max_seats=body.max_seats,
        used_seats=0,
        billing_cycle_day=body.billing_cycle_day,
        usage_data={},
    )
    db.add(sub)
    await db.flush()

    await publisher.publish(Event(EventType.SUBSCRIPTION_CREATED, {"subscription_id": str(sub.id), "user_id": str(user.id), "service": body.service_name}, source="api-gateway"))

    return SubscriptionResponse(
        id=str(sub.id),
        service_name=sub.service_name,
        service_category=sub.service_category,
        tier=sub.tier.value,
        status=sub.status.value,
        monthly_cost=sub.monthly_cost,
        max_seats=sub.max_seats,
        used_seats=sub.used_seats,
        billing_cycle_day=sub.billing_cycle_day,
        created_at=sub.created_at.isoformat(),
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific subscription."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    return SubscriptionResponse(
        id=str(sub.id),
        service_name=sub.service_name,
        service_category=sub.service_category,
        tier=sub.tier.value,
        status=sub.status.value,
        monthly_cost=sub.monthly_cost,
        max_seats=sub.max_seats,
        used_seats=sub.used_seats,
        billing_cycle_day=sub.billing_cycle_day,
        created_at=sub.created_at.isoformat(),
    )


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a subscription."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    sub.status = SubscriptionStatus.CANCELLED
    await db.flush()


@router.post("/{subscription_id}/usage", status_code=status.HTTP_201_CREATED)
async def record_usage(
    subscription_id: str,
    body: UsageRecordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record usage for a subscription period."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    now = datetime.now(timezone.utc)
    usage = SubscriptionUsage(
        subscription_id=sub.id,
        period_start=now.replace(day=1),
        period_end=now,
        usage_minutes=body.usage_minutes,
        usage_hours=body.usage_minutes / 60.0,
        usage_percentage=min(100.0, (body.usage_minutes / (30 * 24 * 60)) * 100),
        session_count=body.session_count,
        peak_usage_hour=body.peak_usage_hour,
    )
    db.add(usage)

    # Update subscription usage data
    sub.usage_data = {
        "last_usage_minutes": body.usage_minutes,
        "usage_percentage": round(usage.usage_percentage, 2),
        "updated_at": now.isoformat(),
    }
    await db.flush()

    await publisher.publish(Event(EventType.SUBSCRIPTION_USAGE_RECORDED, {"subscription_id": str(sub.id), "usage_minutes": body.usage_minutes}, source="api-gateway"))

    return {"message": "Usage recorded", "usage_percentage": round(usage.usage_percentage, 2)}


@router.get("/{subscription_id}/analytics", response_model=UsageAnalytics)
async def get_usage_analytics(
    subscription_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage analytics and optimization recommendations."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Get usage history
    usage_result = await db.execute(
        select(SubscriptionUsage)
        .where(SubscriptionUsage.subscription_id == sub.id)
        .order_by(SubscriptionUsage.period_start.desc())
        .limit(30)
    )
    usage_records = usage_result.scalars().all()

    total_minutes = sum(u.usage_minutes for u in usage_records) if usage_records else 0
    avg_daily = total_minutes / max(len(usage_records), 1)
    usage_pct = sub.usage_data.get("usage_percentage", 0) if sub.usage_data else 0

    # Generate recommendation
    if usage_pct < 10:
        recommendation = f"You're using {sub.service_name} very lightly. Consider sharing unused seats to earn back ${sub.monthly_cost * 0.5:.2f}/month."
        opt_score = 0.2
    elif usage_pct < 30:
        recommendation = f"Moderate usage detected. Sharing 2-3 seats could offset ${sub.monthly_cost * 0.4:.2f}/month of your subscription cost."
        opt_score = 0.4
    elif usage_pct < 60:
        recommendation = f"Good usage level. You have room to share without impacting your experience."
        opt_score = 0.7
    else:
        recommendation = f"Heavy usage — sharing may not be ideal. Consider a family plan if available."
        opt_score = 0.9

    return UsageAnalytics(
        subscription_id=str(sub.id),
        service_name=sub.service_name,
        avg_daily_minutes=round(avg_daily, 1),
        total_monthly_minutes=total_minutes,
        usage_percentage=usage_pct,
        optimization_score=opt_score,
        recommendation=recommendation,
    )
