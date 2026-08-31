from __future__ import annotations

"""Admin dashboard router — platform monitoring, user management, analytics."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    ComplianceEvent,
    Dispute,
    DisputeStatus,
    EscrowTransaction,
    EscrowStatus,
    Match,
    MatchStatus,
    MarketListing,
    ListingStatus,
    Payout,
    PayoutStatus,
    Subscription,
    User,
    ComplianceEventType,
)
from vault.db.session import get_db
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/admin")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlatformStats(BaseModel):
    total_users: int
    active_users_7d: int
    total_subscriptions: int
    active_subscriptions: int
    total_listings: int
    active_listings: int
    total_matches: int
    active_matches: int
    completed_matches: int
    total_escrow_amount: float
    total_payouts: float
    platform_fees_collected: float
    open_disputes: int
    compliance_events: int
    new_users_30d: int
    revenue_30d: float


class UserListItem(BaseModel):
    id: str
    email: str
    username: str
    display_name: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login_at: str | None
    subscription_count: int
    match_count: int


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
    page: int
    page_size: int


class DisputeListItem(BaseModel):
    id: str
    match_id: str
    filed_by_id: str
    status: str
    reason: str
    description: str
    created_at: str
    resolved_at: str | None


class DisputeListResponse(BaseModel):
    disputes: list[DisputeListItem]
    total: int


class ActivityFeedItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    severity: str
    created_at: str


class RevenueChart(BaseModel):
    period: str
    revenue: float
    fees: float
    transactions: int


class HealthStatus(BaseModel):
    api_gateway: str
    database: str
    redis: str
    stripe: str
    event_bus: str
    uptime_seconds: int


# ---------------------------------------------------------------------------
# Helper: require admin
# ---------------------------------------------------------------------------

async def require_admin(user: User = Depends(get_current_user)):
    """Ensure the current user has admin role."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Platform Stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get high-level platform statistics."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    new_users_30d = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )).scalar() or 0
    active_users_7d = (await db.execute(
        select(func.count(User.id)).where(User.last_login_at >= seven_days_ago)
    )).scalar() or 0

    total_subscriptions = (await db.execute(select(func.count(Subscription.id)))).scalar() or 0
    active_subscriptions = (await db.execute(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    )).scalar() or 0

    total_listings = (await db.execute(select(func.count(MarketListing.id)))).scalar() or 0
    active_listings = (await db.execute(
        select(func.count(MarketListing.id)).where(MarketListing.status == ListingStatus.ACTIVE)
    )).scalar() or 0

    total_matches = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    active_matches = (await db.execute(
        select(func.count(Match.id)).where(
            Match.status.in_([MatchStatus.PROPOSED, MatchStatus.ACCEPTED])
        )
    )).scalar() or 0
    completed_matches = (await db.execute(
        select(func.count(Match.id)).where(Match.status == MatchStatus.COMPLETED)
    )).scalar() or 0

    total_escrow = (await db.execute(
        select(func.coalesce(func.sum(EscrowTransaction.amount), 0))
    )).scalar() or 0
    total_payouts = (await db.execute(
        select(func.coalesce(func.sum(Payout.amount), 0))
        .where(Payout.status == PayoutStatus.COMPLETED)
    )).scalar() or 0
    platform_fees = (await db.execute(
        select(func.coalesce(func.sum(EscrowTransaction.platform_fee), 0))
    )).scalar() or 0

    open_disputes = (await db.execute(
        select(func.count(Dispute.id)).where(
            Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW])
        )
    )).scalar() or 0

    compliance_events = (await db.execute(select(func.count(ComplianceEvent.id)))).scalar() or 0

    revenue_30d = (await db.execute(
        select(func.coalesce(func.sum(EscrowTransaction.platform_fee), 0))
        .where(EscrowTransaction.created_at >= thirty_days_ago)
    )).scalar() or 0

    return PlatformStats(
        total_users=total_users,
        active_users_7d=active_users_7d,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions,
        total_listings=total_listings,
        active_listings=active_listings,
        total_matches=total_matches,
        active_matches=active_matches,
        completed_matches=completed_matches,
        total_escrow_amount=float(total_escrow),
        total_payouts=float(total_payouts),
        platform_fees_collected=float(platform_fees),
        open_disputes=open_disputes,
        compliance_events=compliance_events,
        new_users_30d=new_users_30d,
        revenue_30d=float(revenue_30d),
    )


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = "",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with pagination and search."""
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_filter = User.email.ilike(f"%{search}%") | User.username.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    items = []
    for u in users:
        sub_count = (await db.execute(
            select(func.count(Subscription.id)).where(Subscription.user_id == u.id)
        )).scalar() or 0
        match_count = (await db.execute(
            select(func.count(Match.id)).where(
                (Match.buyer_id == u.id) | (Match.seller_id == u.id)
            )
        )).scalar() or 0

        items.append(UserListItem(
            id=str(u.id),
            email=u.email,
            username=u.username,
            display_name=u.display_name,
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at.isoformat(),
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            subscription_count=sub_count,
            match_count=match_count,
        ))

    return UserListResponse(users=items, total=total, page=page, page_size=page_size)


@router.post("/users/{user_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.value == "admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate admin users")
    user.is_active = False
    await db.flush()
    return {"message": f"User {user.username} deactivated"}


@router.post("/users/{user_id}/activate", status_code=status.HTTP_200_OK)
async def activate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.flush()
    return {"message": f"User {user.username} activated"}


# ---------------------------------------------------------------------------
# Dispute Management
# ---------------------------------------------------------------------------

@router.get("/disputes", response_model=DisputeListResponse)
async def list_disputes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = "",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all disputes for admin review."""
    query = select(Dispute)
    count_query = select(func.count(Dispute.id))

    if status_filter:
        query = query.where(Dispute.status == status_filter)
        count_query = count_query.where(Dispute.status == status_filter)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Dispute.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    disputes = result.scalars().all()

    return DisputeListResponse(
        disputes=[
            DisputeListItem(
                id=str(d.id),
                match_id=str(d.match_id),
                filed_by_id=str(d.filed_by_id),
                status=d.status.value,
                reason=d.reason,
                description=d.description,
                created_at=d.created_at.isoformat(),
                resolved_at=d.resolved_at.isoformat() if d.resolved_at else None,
            )
            for d in disputes
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# Compliance Activity Feed
# ---------------------------------------------------------------------------

@router.get("/activity")
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get recent platform activity for the admin feed."""
    result = await db.execute(
        select(ComplianceEvent)
        .order_by(ComplianceEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "activity": [
            ActivityFeedItem(
                id=str(e.id),
                type=e.event_type.value,
                title=e.title,
                description=e.description,
                severity=e.severity,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]
    }


# ---------------------------------------------------------------------------
# Health & Monitoring
# ---------------------------------------------------------------------------

@router.get("/health/system")
async def system_health(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed system health status."""
    # Check database
    db_status = "healthy"
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return HealthStatus(
        api_gateway="healthy",
        database=db_status,
        redis="healthy" if settings.REDIS_URL else "not_configured",
        stripe="configured" if settings.STRIPE_SECRET_KEY != "sk_test_placeholder" else "mock",
        event_bus="healthy",
        uptime_seconds=0,  # Would track from app start
    )


# ---------------------------------------------------------------------------
# Revenue Analytics
# ---------------------------------------------------------------------------

@router.get("/revenue")
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get revenue analytics over time."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(
            func.date(EscrowTransaction.created_at).label("day"),
            func.coalesce(func.sum(EscrowTransaction.platform_fee), 0).label("fees"),
            func.coalesce(func.sum(EscrowTransaction.amount), 0).label("revenue"),
            func.count(EscrowTransaction.id).label("transactions"),
        )
        .where(EscrowTransaction.created_at >= now - timedelta(days=days))
        .group_by(func.date(EscrowTransaction.created_at))
        .order_by(func.date(EscrowTransaction.created_at))
    )
    rows = result.all()

    return {
        "chart_data": [
            RevenueChart(
                period=str(row.day),
                revenue=float(row.revenue),
                fees=float(row.fees),
                transactions=row.transactions,
            )
            for row in rows
        ],
        "summary": {
            "total_revenue": sum(float(r.revenue) for r in rows),
            "total_fees": sum(float(r.fees) for r in rows),
            "total_transactions": sum(r.transactions for r in rows),
            "period_days": days,
        },
    }
