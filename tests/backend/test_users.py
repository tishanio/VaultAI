"""Tests for user profile endpoints — get, update, public profile."""
import uuid

import pytest
from vault.db.models import ReputationScore, User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

async def test_get_profile_unauthorized(async_client):
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_get_profile_authorized(async_client, auth_headers):
    response = await async_client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@vault.app"
    assert data["display_name"] == "Test User"
    assert data["is_verified"] is True
    assert "id" in data
    assert "created_at" in data


async def test_get_profile_with_reputation(
    async_client, auth_headers, db_session, test_user,
):
    rep = ReputationScore(
        id=uuid.uuid4(), user_id=test_user.id,
        overall_score=0.85, reliability_score=0.9,
        communication_score=0.8, payment_score=0.85,
        total_transactions=10, positive_reviews=8, negative_reviews=1,
    )
    db_session.add(rep)
    await db_session.flush()

    response = await async_client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["reputation_score"] == 0.85


async def test_get_profile_without_reputation(async_client, auth_headers):
    response = await async_client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["reputation_score"] is None


# ---------------------------------------------------------------------------
# PATCH /users/me
# ---------------------------------------------------------------------------

async def test_update_profile_unauthorized(async_client):
    response = await async_client.patch("/api/v1/users/me", json={})
    assert response.status_code == 401


async def test_update_profile_display_name(async_client, auth_headers):
    response = await async_client.patch(
        "/api/v1/users/me", headers=auth_headers,
        json={"display_name": "New Display Name"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "New Display Name"


async def test_update_profile_location(async_client, auth_headers):
    response = await async_client.patch(
        "/api/v1/users/me", headers=auth_headers,
        json={"latitude": 40.7128, "longitude": -74.0060}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latitude"] == 40.7128
    assert data["longitude"] == -74.0060


async def test_update_profile_timezone_and_locale(async_client, auth_headers):
    response = await async_client.patch(
        "/api/v1/users/me", headers=auth_headers,
        json={"timezone": "America/New_York", "locale": "en-US"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "America/New_York"
    assert data["locale"] == "en-US"


async def test_update_profile_avatar(async_client, auth_headers):
    response = await async_client.patch(
        "/api/v1/users/me", headers=auth_headers,
        json={"avatar_url": "https://example.com/avatar.png"}
    )
    assert response.status_code == 200
    assert response.json()["avatar_url"] == "https://example.com/avatar.png"


async def test_update_profile_partial(async_client, auth_headers):
    """Only sending some fields should update only those fields."""
    # First set location
    await async_client.patch(
        "/api/v1/users/me", headers=auth_headers,
        json={"latitude": 40.7128, "longitude": -74.0060}
    )
    # Now only update display_name — location should remain
    response = await async_client.patch(
        "/api/v1/users/me", headers=auth_headers,
        json={"display_name": "Partially Updated"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Partially Updated"
    assert data["latitude"] == 40.7128


async def test_update_profile_empty_body(async_client, auth_headers):
    response = await async_client.patch(
        "/api/v1/users/me", headers=auth_headers, json={}
    )
    assert response.status_code == 200
    # Nothing should change
    data = response.json()
    assert data["display_name"] == "Test User"


# ---------------------------------------------------------------------------
# GET /users/{user_id} (public profile)
# ---------------------------------------------------------------------------

async def test_get_user_profile_not_found(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/users/{fake_id}")
    assert response.status_code == 404


async def test_get_user_profile_public(async_client, db_session, seller_user):
    response = await async_client.get(f"/api/v1/users/{seller_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "selleruser"
    assert data["display_name"] == "Seller User"
    # Public profile should not expose sensitive fields
    assert "password_hash" not in data
    assert "stripe_customer_id" not in data


async def test_get_user_profile_with_reputation(
    async_client, db_session, test_user,
):
    rep = ReputationScore(
        id=uuid.uuid4(), user_id=test_user.id,
        overall_score=0.72, reliability_score=0.8,
        communication_score=0.7, payment_score=0.65,
        total_transactions=5, positive_reviews=4, negative_reviews=0,
    )
    db_session.add(rep)
    await db_session.flush()

    response = await async_client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["reputation_score"] == 0.72
