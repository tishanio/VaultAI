"""Tests for subscription endpoints — CRUD, usage recording, analytics."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    SubscriptionUsage,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /subscriptions
# ---------------------------------------------------------------------------

async def test_list_subscriptions_unauthorized(async_client):
    response = await async_client.get("/api/v1/subscriptions")
    assert response.status_code == 401


async def test_list_subscriptions_empty(async_client, auth_headers):
    response = await async_client.get("/api/v1/subscriptions", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


async def test_list_subscriptions_with_data(async_client, auth_headers, test_user, db_session):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={"usage_percentage": 20.0},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.get("/api/v1/subscriptions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["service_name"] == "Spotify"
    assert data[0]["monthly_cost"] == 16.99


async def test_list_subscriptions_filter_by_status(
    async_client, auth_headers, test_user, db_session,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    sub2 = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="YouTube Premium",
        service_category="streaming", tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.CANCELLED, monthly_cost=11.99,
        max_seats=5, used_seats=0, billing_cycle_day=1, usage_data={},
    )
    db_session.add(sub2)
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/subscriptions", headers=auth_headers, params={"status_filter": "active"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "active"


# ---------------------------------------------------------------------------
# POST /subscriptions
# ---------------------------------------------------------------------------

async def test_create_subscription_unauthorized(async_client):
    response = await async_client.post("/api/v1/subscriptions", json={})
    assert response.status_code == 401


async def test_create_subscription_success(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/subscriptions", headers=auth_headers, json={
            "service_name": "Spotify",
            "tier": "family",
            "monthly_cost": 16.99,
            "max_seats": 4,
            "billing_cycle_day": 15,
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["service_name"] == "Spotify"
    assert data["service_category"] == "music"
    assert data["monthly_cost"] == 16.99
    assert data["max_seats"] == 4
    assert data["status"] == "active"
    assert "id" in data


async def test_create_subscription_blocked_service(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/subscriptions", headers=auth_headers, json={
            "service_name": "Netflix",
            "tier": "premium",
            "monthly_cost": 15.99,
            "max_seats": 4,
            "billing_cycle_day": 1,
        }
    )
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"].lower()


async def test_create_subscription_unsupported_service(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/subscriptions", headers=auth_headers, json={
            "service_name": "SomeUnknownService",
            "tier": "premium",
            "monthly_cost": 9.99,
            "max_seats": 2,
            "billing_cycle_day": 1,
        }
    )
    assert response.status_code == 400
    assert "not yet supported" in response.json()["detail"].lower()


async def test_create_subscription_too_many_seats(async_client, auth_headers):
    # Pydantic rejects max_seats > 6 with 422 validation error
    response = await async_client.post(
        "/api/v1/subscriptions", headers=auth_headers, json={
            "service_name": "Spotify",
            "tier": "family",
            "monthly_cost": 16.99,
            "max_seats": 10,
            "billing_cycle_day": 15,
        }
    )
    assert response.status_code == 422


async def test_create_subscription_exceeds_service_max_seats(async_client, auth_headers):
    # Request max_seats=7 for Spotify (max is 6) — Pydantic allows it, router rejects
    response = await async_client.post(
        "/api/v1/subscriptions", headers=auth_headers, json={
            "service_name": "YouTube Premium",
            "tier": "family",
            "monthly_cost": 22.99,
            "max_seats": 6,
            "billing_cycle_day": 1,
        }
    )
    assert response.status_code == 400
    assert "max seats" in response.json()["detail"].lower()


async def test_create_subscription_all_allowed_services(async_client, auth_headers):
    """Verify all known services can be created."""
    services = [
        ("Spotify", "music", 6), ("Google One", "cloud_storage", 5),
        ("YouTube Premium", "streaming", 5), ("YouTube Music", "music", 5),
        ("Apple Music", "music", 6), ("Headspace", "wellness", 6),
        ("Calm", "wellness", 6), ("Duolingo", "education", 6),
        ("Microsoft 365", "productivity", 6), ("Canva", "design", 5),
    ]
    for name, category, max_s in services:
        response = await async_client.post(
            "/api/v1/subscriptions", headers=auth_headers, json={
                "service_name": name,
                "tier": "family",
                "monthly_cost": 9.99,
                "max_seats": 2,
                "billing_cycle_day": 1,
            }
        )
        assert response.status_code == 201, f"Failed for {name}: {response.text}"
        assert response.json()["service_category"] == category


# ---------------------------------------------------------------------------
# GET /subscriptions/{id}
# ---------------------------------------------------------------------------

async def test_get_subscription_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(
        f"/api/v1/subscriptions/{fake_id}", headers=auth_headers
    )
    assert response.status_code == 404


async def test_get_subscription_success(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/subscriptions/{sub.id}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "Spotify"
    assert data["id"] == str(sub.id)


# ---------------------------------------------------------------------------
# DELETE /subscriptions/{id}
# ---------------------------------------------------------------------------

async def test_delete_subscription_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.delete(
        f"/api/v1/subscriptions/{fake_id}", headers=auth_headers
    )
    assert response.status_code == 404


async def test_delete_subscription_success(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.delete(
        f"/api/v1/subscriptions/{sub.id}", headers=auth_headers
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# POST /subscriptions/{id}/usage
# ---------------------------------------------------------------------------

async def test_record_usage_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/subscriptions/{fake_id}/usage", headers=auth_headers,
        json={"usage_minutes": 120, "session_count": 3}
    )
    assert response.status_code == 404


async def test_record_usage_success(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/subscriptions/{sub.id}/usage", headers=auth_headers,
        json={"usage_minutes": 300, "session_count": 5, "peak_usage_hour": 20}
    )
    assert response.status_code == 201
    data = response.json()
    assert "usage_percentage" in data
    assert data["usage_percentage"] >= 0


async def test_record_usage_zero_minutes(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15, usage_data={},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/subscriptions/{sub.id}/usage", headers=auth_headers,
        json={"usage_minutes": 0, "session_count": 0}
    )
    assert response.status_code == 201
    assert response.json()["usage_percentage"] == 0.0


# ---------------------------------------------------------------------------
# GET /subscriptions/{id}/analytics
# ---------------------------------------------------------------------------

async def test_usage_analytics_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(
        f"/api/v1/subscriptions/{fake_id}/analytics", headers=auth_headers
    )
    assert response.status_code == 404


async def test_usage_analytics_empty(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15,
        usage_data={"usage_percentage": 5.0},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/subscriptions/{sub.id}/analytics", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subscription_id"] == str(sub.id)
    assert data["service_name"] == "Spotify"
    assert data["avg_daily_minutes"] == 0.0
    assert data["total_monthly_minutes"] == 0
    assert data["usage_percentage"] == 5.0
    # Very light usage should have low optimization score
    assert data["optimization_score"] == 0.2


async def test_usage_analytics_low_usage(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15,
        usage_data={"usage_percentage": 25.0},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/subscriptions/{sub.id}/analytics", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["usage_percentage"] == 25.0
    assert data["optimization_score"] == 0.4
    assert "sharing" in data["recommendation"].lower()


async def test_usage_analytics_moderate_usage(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15,
        usage_data={"usage_percentage": 45.0},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/subscriptions/{sub.id}/analytics", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["optimization_score"] == 0.7


async def test_usage_analytics_heavy_usage(
    async_client, auth_headers, db_session, test_user,
):
    sub = Subscription(
        id=uuid.uuid4(), user_id=test_user.id, service_name="Spotify",
        service_category="music", tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE, monthly_cost=16.99,
        max_seats=6, used_seats=0, billing_cycle_day=15,
        usage_data={"usage_percentage": 80.0},
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/subscriptions/{sub.id}/analytics", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["optimization_score"] == 0.9
    assert "heavy" in data["recommendation"].lower()
