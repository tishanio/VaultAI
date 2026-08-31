"""Tests for Usage Intelligence Agent."""
import uuid
from datetime import datetime, timezone

import pytest
from vault.db.models import (
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    SubscriptionUsage,
)

pytestmark = pytest.mark.asyncio


async def test_health(usage_intel_client):
    response = await usage_intel_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "usage-intelligence"


# ---------------------------------------------------------------------------
# GET /api/v1/usage/report/{user_id}
# ---------------------------------------------------------------------------

async def test_usage_report_user_not_found(usage_intel_client):
    fake_id = str(uuid.uuid4())
    response = await usage_intel_client.get(f"/api/v1/usage/report/{fake_id}")
    assert response.status_code == 404


async def test_usage_report_empty_subscriptions(usage_intel_client, agent_user):
    response = await usage_intel_client.get(f"/api/v1/usage/report/{agent_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(agent_user.id)
    assert data["total_subscriptions"] == 0
    assert data["insights"] == []


async def test_usage_report_with_subscription(
    usage_intel_client, db_session, agent_user, agent_seller, agent_subscription,
):
    response = await usage_intel_client.get(f"/api/v1/usage/report/{agent_seller.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_subscriptions"] >= 1
    assert data["total_monthly_cost"] == 16.99
    insight = data["insights"][0]
    assert insight["service_name"] == "Spotify"
    assert insight["service_category"] == "music"
    assert insight["available_seats"] == 6
    assert insight["shareable_seats"] == 5
    assert "recommendation" in insight
    assert insight["sharing_potential"] in ("low", "medium", "high")


async def test_usage_report_with_usage_records(
    usage_intel_client, db_session, agent_seller, agent_subscription,
):
    for i in range(3):
        usage = SubscriptionUsage(
            subscription_id=agent_subscription.id,
            period_start=datetime.now(timezone.utc).replace(day=1),
            period_end=datetime.now(timezone.utc),
            usage_minutes=120 + i * 30,
            usage_hours=2.0 + i * 0.5,
            usage_percentage=10.0 + i * 2,
            session_count=3 + i,
            peak_usage_hour=20,
        )
        db_session.add(usage)
    await db_session.flush()

    response = await usage_intel_client.get(f"/api/v1/usage/report/{agent_seller.id}")
    assert response.status_code == 200
    insight = response.json()["insights"][0]
    assert insight["average_daily_minutes"] > 0
    assert insight["peak_hour"] == 20
    assert len(insight["usage_trend"]) == 3


# ---------------------------------------------------------------------------
# POST /api/v1/usage/record
# ---------------------------------------------------------------------------

async def test_record_usage_subscription_not_found(usage_intel_client):
    fake_id = str(uuid.uuid4())
    response = await usage_intel_client.post(
        "/api/v1/usage/record",
        params={"subscription_id": fake_id, "usage_minutes": 60},
    )
    assert response.status_code == 404


async def test_record_usage_success(usage_intel_client, agent_subscription):
    response = await usage_intel_client.post(
        "/api/v1/usage/record",
        params={
            "subscription_id": str(agent_subscription.id),
            "usage_minutes": 180,
            "session_count": 4,
            "peak_hour": 20,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Usage recorded"
    assert data["usage_percentage"] >= 0


async def test_record_usage_zero_minutes(usage_intel_client, agent_subscription):
    response = await usage_intel_client.post(
        "/api/v1/usage/record",
        params={"subscription_id": str(agent_subscription.id), "usage_minutes": 0},
    )
    assert response.status_code == 200
    assert response.json()["usage_percentage"] == 0.0


# ---------------------------------------------------------------------------
# POST /api/v1/usage/plaid-sync
# ---------------------------------------------------------------------------

async def test_plaid_sync_demo_mode(usage_intel_client, db_session, agent_seller):
    response = await usage_intel_client.post(
        "/api/v1/usage/plaid-sync",
        params={"user_id": str(agent_seller.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "demo"
    assert "synced" in data["message"]
