from __future__ import annotations

"""Usage Intelligence Agent — tracks subscription usage across services."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import Subscription, SubscriptionUsage, User
from vault.db.session import get_db
from vault.events import Event, EventType, EventConsumer, publisher


# ---------------------------------------------------------------------------
# Service categories and expected usage patterns
# ---------------------------------------------------------------------------
SERVICE_USAGE_PROFILES = {
    "music": {"avg_monthly_hours": 30, "peak_hours": [8, 9, 17, 18, 19, 20, 21], "max_usage_pct": 40},
    "cloud_storage": {"avg_monthly_hours": 5, "peak_hours": [10, 11, 12, 13, 14, 15], "max_usage_pct": 60},
    "streaming": {"avg_monthly_hours": 40, "peak_hours": [19, 20, 21, 22, 23], "max_usage_pct": 80},
    "wellness": {"avg_monthly_hours": 15, "peak_hours": [6, 7, 8, 20, 21], "max_usage_pct": 30},
    "education": {"avg_monthly_hours": 20, "peak_hours": [9, 10, 11, 14, 15, 16], "max_usage_pct": 50},
    "productivity": {"avg_monthly_hours": 60, "peak_hours": [9, 10, 11, 12, 13, 14, 15, 16], "max_usage_pct": 80},
    "design": {"avg_monthly_hours": 25, "peak_hours": [10, 11, 14, 15, 16], "max_usage_pct": 50},
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UsageTrend(BaseModel):
    period: str
    minutes: float
    sessions: int


class UsageInsight(BaseModel):
    subscription_id: str
    service_name: str
    service_category: str
    current_usage_pct: float
    average_daily_minutes: float
    peak_hour: int
    available_seats: int
    shareable_seats: int
    estimated_monthly_savings: float
    usage_trend: list[UsageTrend]
    recommendation: str
    sharing_potential: str  # low, medium, high


class UsageReport(BaseModel):
    user_id: str
    total_subscriptions: int
    total_monthly_cost: float
    total_usage_pct: float
    potential_monthly_savings: float
    insights: list[UsageInsight]


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Usage Intelligence Agent starting")
    await publisher.connect()

    # Start event consumer in background
    consumer_task = asyncio.create_task(start_event_consumer())

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await publisher.close()


app = FastAPI(title="Vault Usage Intelligence Agent", version=settings.APP_VERSION, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "usage-intelligence"}


# ---------------------------------------------------------------------------
# Core Analytics Logic
# ---------------------------------------------------------------------------

async def _analyze_usage(subscription: Subscription, db: AsyncSession) -> UsageInsight:
    """Analyze usage for a single subscription."""
    now = datetime.now(timezone.utc)

    # Fetch recent usage records
    thirty_days_ago = now - timedelta(days=30)
    result = await db.execute(
        select(SubscriptionUsage)
        .where(
            SubscriptionUsage.subscription_id == subscription.id,
            SubscriptionUsage.period_start >= thirty_days_ago,
        )
        .order_by(SubscriptionUsage.period_start.desc())
    )
    records = result.scalars().all()

    if records:
        avg_daily = sum(r.usage_minutes for r in records) / max(len(records), 1)
        total_minutes = sum(r.usage_minutes for r in records)
        sessions = sum(r.session_count for r in records)
        peak_hour = max(set(r.peak_usage_hour for r in records if r.peak_usage_hour is not None), default=12)
        current_pct = (total_minutes / max(len(records), 1)) / (24 * 60) * 100
    else:
        avg_daily = 0
        total_minutes = 0
        sessions = 0
        peak_hour = 12
        current_pct = subscription.usage_data.get("usage_percentage", 0) if subscription.usage_data else 0

    # Usage trend (last 7 periods)
    trend = [
        UsageTrend(
            period=r.period_start.strftime("%Y-%m-%d"),
            minutes=r.usage_minutes,
            sessions=r.session_count,
        )
        for r in records[:7]
    ]

    # Calculate sharing potential
    available_seats = subscription.max_seats - subscription.used_seats
    profile = SERVICE_USAGE_PROFILES.get(subscription.service_category, {})
    max_usage = profile.get("max_usage_pct", 50)
    shareable_seats = max(0, min(available_seats, subscription.max_seats - 1))
    estimated_savings = (shareable_seats * subscription.monthly_cost / subscription.max_seats) if shareable_seats > 0 else 0

    if current_pct < 15 and shareable_seats > 0:
        recommendation = f"You use {subscription.service_name} very lightly ({current_pct:.0f}%). Share {shareable_seats} seat(s) to save ~${estimated_savings:.2f}/month."
        sharing_potential = "high"
    elif current_pct < max_usage and shareable_seats > 0:
        recommendation = f"Moderate usage ({current_pct:.0f}%). You have room to share {shareable_seats} seat(s) without impact."
        sharing_potential = "medium"
    else:
        recommendation = f"Usage at {current_pct:.0f}% — sharing is not recommended at this level."
        sharing_potential = "low"

    return UsageInsight(
        subscription_id=str(subscription.id),
        service_name=subscription.service_name,
        service_category=subscription.service_category,
        current_usage_pct=round(min(current_pct, 100), 1),
        average_daily_minutes=round(avg_daily, 1),
        peak_hour=peak_hour,
        available_seats=available_seats,
        shareable_seats=shareable_seats,
        estimated_monthly_savings=round(estimated_savings, 2),
        usage_trend=trend,
        recommendation=recommendation,
        sharing_potential=sharing_potential,
    )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/usage/report/{user_id}", response_model=UsageReport)
async def get_usage_report(user_id: str, db: AsyncSession = Depends(get_db)):
    """Generate comprehensive usage report for a user."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    subs_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id, Subscription.status == "active")
    )
    subscriptions = subs_result.scalars().all()

    insights = []
    total_cost = 0
    total_usage = 0
    total_savings = 0

    for sub in subscriptions:
        insight = await _analyze_usage(sub, db)
        insights.append(insight)
        total_cost += sub.monthly_cost
        total_usage += insight.current_usage_pct
        total_savings += insight.estimated_monthly_savings

    avg_usage = total_usage / max(len(subscriptions), 1)

    return UsageReport(
        user_id=user_id,
        total_subscriptions=len(subscriptions),
        total_monthly_cost=round(total_cost, 2),
        total_usage_pct=round(avg_usage, 1),
        potential_monthly_savings=round(total_savings, 2),
        insights=insights,
    )


@app.post("/api/v1/usage/record")
async def record_usage(
    subscription_id: str,
    usage_minutes: int,
    session_count: int = 1,
    peak_hour: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Record usage for a subscription (called by Plaid transaction scanning or manual entry)."""
    sub_result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    sub = sub_result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    now = datetime.now(timezone.utc)
    usage = SubscriptionUsage(
        subscription_id=sub.id,
        period_start=now.replace(day=1),
        period_end=now,
        usage_minutes=usage_minutes,
        usage_hours=usage_minutes / 60.0,
        usage_percentage=min(100.0, (usage_minutes / (30 * 24 * 60)) * 100),
        session_count=session_count,
        peak_usage_hour=peak_hour,
    )
    db.add(usage)

    # Update subscription usage_data
    sub.usage_data = {
        "usage_percentage": round(usage.usage_percentage, 2),
        "last_recorded": now.isoformat(),
        "avg_daily_minutes": usage_minutes,
    }
    await db.flush()

    await publisher.publish(Event(
        EventType.SUBSCRIPTION_USAGE_RECORDED,
        {"subscription_id": str(sub.id), "usage_minutes": usage_minutes, "usage_pct": usage.usage_percentage},
        source="usage-intelligence",
    ))

    return {"message": "Usage recorded", "usage_percentage": usage.usage_percentage}


@app.post("/api/v1/usage/plaid-sync")
async def sync_plaid_transactions(user_id: str, db: AsyncSession = Depends(get_db)):
    """Sync and categorize transactions from Plaid for usage tracking."""
    # In demo mode, generate synthetic usage data
    if settings.DEMO_MODE:
        subs_result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscriptions = subs_result.scalars().all()

        recorded = 0
        for sub in subscriptions:
            profile = SERVICE_USAGE_PROFILES.get(sub.service_category, {})
            avg_hours = profile.get("avg_monthly_hours", 20)
            import random
            daily_minutes = int((avg_hours * 60 / 30) * random.uniform(0.5, 1.5))

            now = datetime.now(timezone.utc)
            usage = SubscriptionUsage(
                subscription_id=sub.id,
                period_start=now.replace(day=1),
                period_end=now,
                usage_minutes=daily_minutes,
                usage_hours=round(daily_minutes / 60.0, 1),
                usage_percentage=round(min(100.0, (daily_minutes / (24 * 60)) * 100), 1),
                session_count=random.randint(1, 5),
                peak_usage_hour=random.choice(profile.get("peak_hours", [12])),
            )
            db.add(usage)
            recorded += 1

        await db.flush()
        return {"message": f"Demo: synced {recorded} usage records", "mode": "demo"}

    # Production: integrate with Plaid API
    return {"message": "Plaid sync not configured", "mode": "production"}


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------

async def handle_subscription_created(event: Event):
    """When a new subscription is created, schedule initial usage tracking."""
    logger.info("New subscription detected: {}", event.data.get("subscription_id"))


async def handle_listing_expired(event: Event):
    """When a listing expires, update usage analytics."""
    logger.info("Listing expired: {}", event.data.get("listing_id"))


# ---------------------------------------------------------------------------
# Event Consumer Background Task
# ---------------------------------------------------------------------------

import asyncio

async def start_event_consumer():
    """Start consuming events in background."""
    consumer = EventConsumer(group_name="usage-intelligence", consumer_name="worker-1")
    await consumer.connect()
    consumer.on(EventType.SUBSCRIPTION_CREATED, handle_subscription_created)
    consumer.on(EventType.LISTING_EXPIRED, handle_listing_expired)
    await consumer.listen()
