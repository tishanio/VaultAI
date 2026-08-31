"""Tests for marketplace endpoints — browse, create, and remove listings."""
import uuid

import pytest

from vault.db.models import (
    ListingStatus,
    MarketListing,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /marketplace/listings — browse listings
# ---------------------------------------------------------------------------


async def test_list_listings_empty(async_client):
    response = await async_client.get("/api/v1/marketplace/listings")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_listings_returns_data(async_client, db_session, seller_user, seller_subscription):
    listing = MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id,
        subscription_id=seller_subscription.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=2, geo_radius_km=10.0, min_trust_score=0.5,
    )
    db_session.add(listing)
    await db_session.flush()

    response = await async_client.get("/api/v1/marketplace/listings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(listing.id)
    assert data[0]["service_name"] == "Spotify"
    assert data[0]["seller_name"] == "Seller User"
    assert data[0]["asking_price"] == 5.00
    assert data[0]["dynamic_price"] == 4.50


async def test_list_listings_filter_by_category(async_client, db_session, seller_user, seller_subscription):
    # Create a music listing
    db_session.add(MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id,
        subscription_id=seller_subscription.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=2, geo_radius_km=10.0, min_trust_score=0.5,
    ))
    # Create a different subscription + listing in another category
    other_sub = Subscription(
        id=uuid.uuid4(), user_id=seller_user.id,
        service_name="Google One", service_category="cloud_storage",
        tier=SubscriptionTier.FAMILY, status=SubscriptionStatus.ACTIVE,
        monthly_cost=22.99, max_seats=5, used_seats=0, billing_cycle_day=10,
    )
    db_session.add(other_sub)
    await db_session.flush()
    db_session.add(MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id,
        subscription_id=other_sub.id,
        status=ListingStatus.ACTIVE, asking_price=8.00, dynamic_price=7.20,
        seats_available=1, geo_radius_km=10.0, min_trust_score=0.5,
    ))
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/marketplace/listings",
        params={"service_category": "music"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service_category"] == "music"


async def test_list_listings_filter_by_max_price(async_client, db_session, seller_user, seller_subscription):
    db_session.add(MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id,
        subscription_id=seller_subscription.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=2, geo_radius_km=10.0, min_trust_score=0.5,
    ))
    await db_session.flush()

    # Filter: max price 3.0 — listing at 4.50 should not appear
    response = await async_client.get(
        "/api/v1/marketplace/listings",
        params={"max_price": 3.0},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Filter: max price 10.0 — should appear
    response2 = await async_client.get(
        "/api/v1/marketplace/listings",
        params={"max_price": 10.0},
    )
    assert response2.status_code == 200
    assert len(response2.json()) == 1


async def test_list_listings_filter_by_min_trust(async_client, db_session, seller_user, seller_subscription):
    db_session.add(MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id,
        subscription_id=seller_subscription.id,
        status=ListingStatus.ACTIVE, asking_price=5.00, dynamic_price=4.50,
        seats_available=2, geo_radius_km=10.0, min_trust_score=0.8,
    ))
    await db_session.flush()

    # Listings with min_trust_score=0.8 should appear when querying with min_trust_score <= 0.8
    response = await async_client.get(
        "/api/v1/marketplace/listings",
        params={"min_trust_score": 0.8},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_listings_pagination(async_client, db_session, seller_user, seller_subscription):
    for i in range(3):
        db_session.add(MarketListing(
            id=uuid.uuid4(), seller_id=seller_user.id,
            subscription_id=seller_subscription.id,
            status=ListingStatus.ACTIVE, asking_price=3.00 + i,
            dynamic_price=2.70 + i, seats_available=1,
            geo_radius_km=10.0, min_trust_score=0.5,
        ))
    await db_session.flush()

    # Page 1
    response = await async_client.get(
        "/api/v1/marketplace/listings",
        params={"limit": 2, "offset": 0},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Page 2
    response2 = await async_client.get(
        "/api/v1/marketplace/listings",
        params={"limit": 2, "offset": 2},
    )
    assert response2.status_code == 200
    assert len(response2.json()) == 1


async def test_list_listings_ignores_removed(async_client, db_session, seller_user, seller_subscription):
    """Removed listings should not appear in browse results."""
    db_session.add(MarketListing(
        id=uuid.uuid4(), seller_id=seller_user.id,
        subscription_id=seller_subscription.id,
        status=ListingStatus.REMOVED, asking_price=5.00, dynamic_price=4.50,
        seats_available=1, geo_radius_km=10.0, min_trust_score=0.5,
    ))
    await db_session.flush()

    response = await async_client.get("/api/v1/marketplace/listings")
    assert response.status_code == 200
    assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# POST /marketplace/listings — create listing
# ---------------------------------------------------------------------------


async def test_create_listing_unauthorized(async_client):
    response = await async_client.post("/api/v1/marketplace/listings", json={
        "subscription_id": str(uuid.uuid4()),
        "asking_price": 5.00,
        "seats_available": 1,
    })
    assert response.status_code == 401


async def test_create_listing_subscription_not_found(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/marketplace/listings",
        json={
            "subscription_id": str(uuid.uuid4()),
            "asking_price": 5.00,
            "seats_available": 1,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_create_listing_too_many_seats(async_client, seller_auth_headers, db_session, seller_user):
    """Cannot list more seats than available."""
    # Create a subscription with only 1 seat available
    sub = Subscription(
        id=uuid.uuid4(), user_id=seller_user.id,
        service_name="Google One", service_category="cloud_storage",
        tier=SubscriptionTier.FAMILY, status=SubscriptionStatus.ACTIVE,
        monthly_cost=22.99, max_seats=5, used_seats=4, billing_cycle_day=10,
    )
    db_session.add(sub)
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/marketplace/listings",
        json={
            "subscription_id": str(sub.id),
            "asking_price": 5.00,
            "seats_available": 2,  # Only 1 available (5-4=1)
        },
        headers=seller_auth_headers,
    )
    assert response.status_code == 400
    assert "seats" in response.json()["detail"].lower()


async def test_create_listing_success(async_client, seller_auth_headers, seller_subscription):
    response = await async_client.post(
        "/api/v1/marketplace/listings",
        json={
            "subscription_id": str(seller_subscription.id),
            "asking_price": 5.00,
            "seats_available": 2,
            "description": "Family plan seats",
        },
        headers=seller_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["asking_price"] == 5.00
    assert data["dynamic_price"] == 4.50  # 10% discount
    assert data["seats_available"] == 2
    assert data["description"] == "Family plan seats"
    assert data["seller_name"] == "Seller User"
    assert data["expires_at"] is not None


async def test_create_listing_sets_dynamic_price(async_client, seller_auth_headers, seller_subscription):
    """Dynamic price should be 90% of asking price."""
    response = await async_client.post(
        "/api/v1/marketplace/listings",
        json={
            "subscription_id": str(seller_subscription.id),
            "asking_price": 10.00,
            "seats_available": 1,
        },
        headers=seller_auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["dynamic_price"] == 9.00


async def test_create_listing_with_schedule(async_client, seller_auth_headers, seller_subscription):
    response = await async_client.post(
        "/api/v1/marketplace/listings",
        json={
            "subscription_id": str(seller_subscription.id),
            "asking_price": 5.00,
            "seats_available": 1,
            "preferred_schedule": {"peak_hours": [20, 21, 22]},
        },
        headers=seller_auth_headers,
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# DELETE /marketplace/listings/{listing_id} — remove listing
# ---------------------------------------------------------------------------


async def test_remove_listing_unauthorized(async_client, active_listing):
    response = await async_client.delete(
        f"/api/v1/marketplace/listings/{active_listing.id}"
    )
    assert response.status_code == 401


async def test_remove_listing_not_found(async_client, auth_headers):
    response = await async_client.delete(
        "/api/v1/marketplace/listings/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_remove_listing_not_owner(async_client, auth_headers, active_listing):
    """Only the listing owner can remove it."""
    # auth_headers belongs to test_user (buyer), not the seller who owns the listing
    response = await async_client.delete(
        f"/api/v1/marketplace/listings/{active_listing.id}",
        headers=auth_headers,
    )
    assert response.status_code == 404  # Not found because owner check fails


async def test_remove_listing_success(async_client, seller_auth_headers, active_listing):
    response = await async_client.delete(
        f"/api/v1/marketplace/listings/{active_listing.id}",
        headers=seller_auth_headers,
    )
    assert response.status_code == 204

    # Verify it's gone from browse
    browse_resp = await async_client.get("/api/v1/marketplace/listings")
    assert browse_resp.status_code == 200
    assert len(browse_resp.json()) == 0
