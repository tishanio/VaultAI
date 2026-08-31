"""Tests for admin endpoints — stats, users, disputes, activity, health, revenue."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    Dispute,
    DisputeStatus,
    EscrowStatus,
    EscrowTransaction,
    ListingStatus,
    Match,
    MatchStatus,
    MarketListing,
    Payout,
    PayoutStatus,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /admin/stats
# ---------------------------------------------------------------------------

async def test_admin_stats_unauthorized(async_client):
    response = await async_client.get("/api/v1/admin/stats")
    assert response.status_code == 401


async def test_admin_stats_non_admin(async_client, auth_headers):
    response = await async_client.get("/api/v1/admin/stats", headers=auth_headers)
    assert response.status_code == 403


async def test_admin_stats_empty_db(async_client, admin_auth_headers):
    response = await async_client.get("/api/v1/admin/stats", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    # admin_user fixture exists in DB, so total_users >= 1
    assert data["total_users"] >= 1
    assert data["total_subscriptions"] == 0
    assert data["total_listings"] == 0
    assert data["total_matches"] == 0
    assert data["total_escrow_amount"] == 0
    assert data["total_payouts"] == 0
    assert data["platform_fees_collected"] == 0
    assert data["open_disputes"] == 0
    assert data["compliance_events"] == 0


async def test_admin_stats_with_data(
    async_client, admin_auth_headers, db_session, test_user, seller_user,
):
    # Create subscription
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)

    # Create listing
    listing = MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id, subscription_id=sub.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=3, geo_radius_km=15.0, min_trust_score=0.5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(listing)

    # Create match
    match = Match(
        id=uuid.uuid4(), listing_id=listing.id, buyer_id=seller_user.id,
        seller_id=test_user.id, status=MatchStatus.COMPLETED,
        match_score=0.85, trust_score=0.9, proximity_score=0.8,
        schedule_score=0.7, proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(match)

    # Create escrow
    escrow = EscrowTransaction(
        id=uuid.uuid4(), match_id=match.id, status=EscrowStatus.RELEASED,
        amount=4.50, platform_fee=0.54, seller_payout=3.96,
        fee_percentage=12.0, funded_at=datetime.now(timezone.utc),
        released_at=datetime.now(timezone.utc),
    )
    db_session.add(escrow)

    # Create compliance event
    event = ComplianceEvent(
        id=uuid.uuid4(), event_type=ComplianceEventType.RISK_ALERT,
        severity="medium", title="Test alert", description="Test",
        risk_score=0.5,
    )
    db_session.add(event)
    await db_session.flush()

    response = await async_client.get("/api/v1/admin/stats", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] >= 2
    assert data["total_subscriptions"] >= 1
    assert data["active_subscriptions"] >= 1
    assert data["total_listings"] >= 1
    assert data["active_listings"] >= 1
    assert data["total_matches"] >= 1
    assert data["completed_matches"] >= 1
    assert data["total_escrow_amount"] >= 4.50
    assert data["compliance_events"] >= 1


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

async def test_admin_users_unauthorized(async_client):
    response = await async_client.get("/api/v1/admin/users")
    assert response.status_code == 401


async def test_admin_users_empty(async_client, admin_auth_headers):
    response = await async_client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    # admin_user fixture exists in DB
    assert data["total"] >= 1


async def test_admin_users_returns_data(async_client, admin_auth_headers, test_user):
    response = await async_client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    user_item = data["users"][0]
    assert "id" in user_item
    assert "email" in user_item
    assert "username" in user_item
    assert "subscription_count" in user_item
    assert "match_count" in user_item


async def test_admin_users_search(async_client, admin_auth_headers, test_user):
    response = await async_client.get(
        "/api/v1/admin/users", headers=admin_auth_headers, params={"search": "testuser"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    response = await async_client.get(
        "/api/v1/admin/users", headers=admin_auth_headers, params={"search": "nonexistent"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


async def test_admin_users_pagination(async_client, admin_auth_headers, test_user):
    response = await async_client.get(
        "/api/v1/admin/users", headers=admin_auth_headers,
        params={"page": 1, "page_size": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["users"]) <= 1


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/deactivate
# ---------------------------------------------------------------------------

async def test_admin_deactivate_user_not_found(async_client, admin_auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/admin/users/{fake_id}/deactivate", headers=admin_auth_headers
    )
    assert response.status_code == 404


async def test_admin_deactivate_user_success(async_client, admin_auth_headers, test_user):
    response = await async_client.post(
        f"/api/v1/admin/users/{test_user.id}/deactivate", headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "deactivated" in data["message"]


async def test_admin_deactivate_admin_user_fails(async_client, admin_auth_headers, admin_user):
    response = await async_client.post(
        f"/api/v1/admin/users/{admin_user.id}/deactivate", headers=admin_auth_headers
    )
    assert response.status_code == 400
    assert "admin" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/activate
# ---------------------------------------------------------------------------

async def test_admin_activate_user_not_found(async_client, admin_auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/admin/users/{fake_id}/activate", headers=admin_auth_headers
    )
    assert response.status_code == 404


async def test_admin_activate_user_success(async_client, admin_auth_headers, test_user):
    response = await async_client.post(
        f"/api/v1/admin/users/{test_user.id}/activate", headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "activated" in data["message"]


# ---------------------------------------------------------------------------
# GET /admin/disputes
# ---------------------------------------------------------------------------

async def test_admin_disputes_unauthorized(async_client):
    response = await async_client.get("/api/v1/admin/disputes")
    assert response.status_code == 401


async def test_admin_disputes_empty(async_client, admin_auth_headers):
    response = await async_client.get("/api/v1/admin/disputes", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


async def test_admin_disputes_with_data(
    async_client, admin_auth_headers, db_session, test_user, seller_user,
):
    # Create match for dispute
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    listing = MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id, subscription_id=sub.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=3, geo_radius_km=15.0, min_trust_score=0.5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(listing)
    match = Match(
        id=uuid.uuid4(), listing_id=listing.id, buyer_id=test_user.id,
        seller_id=seller_user.id, status=MatchStatus.ACCEPTED,
        match_score=0.85, trust_score=0.9, proximity_score=0.8,
        schedule_score=0.7, proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(match)
    await db_session.flush()
    dispute = Dispute(
        id=uuid.uuid4(), match_id=match.id, filed_by_id=test_user.id,
        status=DisputeStatus.OPEN, reason="Service not delivered",
        description="I did not receive access to the subscription.",
    )
    db_session.add(dispute)
    await db_session.flush()

    response = await async_client.get("/api/v1/admin/disputes", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    d = data["disputes"][0]
    assert d["status"] == "open"
    assert d["reason"] == "Service not delivered"


async def test_admin_disputes_filter_by_status(
    async_client, admin_auth_headers, db_session, test_user, seller_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    listing = MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id, subscription_id=sub.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=3, geo_radius_km=15.0, min_trust_score=0.5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(listing)
    match = Match(
        id=uuid.uuid4(), listing_id=listing.id, buyer_id=test_user.id,
        seller_id=seller_user.id, status=MatchStatus.ACCEPTED,
        match_score=0.85, trust_score=0.9, proximity_score=0.8,
        schedule_score=0.7, proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(match)
    await db_session.flush()
    dispute = Dispute(
        id=uuid.uuid4(), match_id=match.id, filed_by_id=test_user.id,
        status=DisputeStatus.OPEN, reason="Issue",
        description="Test dispute",
    )
    db_session.add(dispute)
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/admin/disputes",
        headers=admin_auth_headers,
        params={"status_filter": "open"},
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    response = await async_client.get(
        "/api/v1/admin/disputes",
        headers=admin_auth_headers,
        params={"status_filter": "resolved"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /admin/activity
# ---------------------------------------------------------------------------

async def test_admin_activity_unauthorized(async_client):
    response = await async_client.get("/api/v1/admin/activity")
    assert response.status_code == 401


async def test_admin_activity_empty(async_client, admin_auth_headers):
    response = await async_client.get("/api/v1/admin/activity", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "activity" in data


async def test_admin_activity_with_data(async_client, admin_auth_headers, db_session):
    event = ComplianceEvent(
        id=uuid.uuid4(), event_type=ComplianceEventType.TOS_VIOLATION,
        severity="high", title="TOS Violation", description="User violated TOS",
        risk_score=0.8, action_taken="warning",
    )
    db_session.add(event)
    await db_session.flush()

    response = await async_client.get("/api/v1/admin/activity", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["activity"]) >= 1
    item = data["activity"][0]
    assert item["type"] == "tos_violation"
    assert item["title"] == "TOS Violation"
    assert item["severity"] == "high"


async def test_admin_activity_limit(async_client, admin_auth_headers, db_session):
    for _ in range(5):
        db_session.add(ComplianceEvent(
            id=uuid.uuid4(), event_type=ComplianceEventType.AUDIT_LOG,
            severity="low", title="Audit", description="Audit entry",
            risk_score=0.1,
        ))
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/admin/activity", headers=admin_auth_headers, params={"limit": 2}
    )
    assert response.status_code == 200
    assert len(response.json()["activity"]) <= 2


# ---------------------------------------------------------------------------
# GET /admin/health/system
# ---------------------------------------------------------------------------

async def test_admin_health_unauthorized(async_client):
    response = await async_client.get("/api/v1/admin/health/system")
    assert response.status_code == 401


async def test_admin_health_system(async_client, admin_auth_headers):
    response = await async_client.get("/api/v1/admin/health/system", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["api_gateway"] == "healthy"
    assert data["database"] == "healthy"
    assert "uptime_seconds" in data


# ---------------------------------------------------------------------------
# GET /admin/revenue
# ---------------------------------------------------------------------------

async def test_admin_revenue_unauthorized(async_client):
    response = await async_client.get("/api/v1/admin/revenue")
    assert response.status_code == 401


async def test_admin_revenue_empty(async_client, admin_auth_headers):
    response = await async_client.get("/api/v1/admin/revenue", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "chart_data" in data
    assert "summary" in data
    assert data["summary"]["total_revenue"] == 0


async def test_admin_revenue_with_data(
    async_client, admin_auth_headers, db_session, test_user, seller_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    listing = MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id, subscription_id=sub.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=3, geo_radius_km=15.0, min_trust_score=0.5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(listing)
    match = Match(
        id=uuid.uuid4(), listing_id=listing.id, buyer_id=test_user.id,
        seller_id=seller_user.id, status=MatchStatus.COMPLETED,
        match_score=0.85, trust_score=0.9, proximity_score=0.8,
        schedule_score=0.7, proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(match)
    escrow = EscrowTransaction(
        id=uuid.uuid4(), match_id=match.id, status=EscrowStatus.RELEASED,
        amount=4.50, platform_fee=0.54, seller_payout=3.96,
        fee_percentage=12.0, funded_at=datetime.now(timezone.utc),
        released_at=datetime.now(timezone.utc),
    )
    db_session.add(escrow)
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/admin/revenue", headers=admin_auth_headers, params={"days": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_transactions"] >= 1


async def test_admin_revenue_days_param(async_client, admin_auth_headers):
    response = await async_client.get(
        "/api/v1/admin/revenue", headers=admin_auth_headers, params={"days": 7}
    )
    assert response.status_code == 200
    assert response.json()["summary"]["period_days"] == 7
