"""Tests for Market Matching Agent."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    ListingStatus,
    Match,
    MatchStatus,
    ReputationScore,
)

pytestmark = pytest.mark.asyncio


async def test_health(matching_client):
    response = await matching_client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "market-matching"


# ---------------------------------------------------------------------------
# POST /api/v1/matching/search
# ---------------------------------------------------------------------------

async def test_search_buyer_not_found(matching_client):
    fake_id = str(uuid.uuid4())
    response = await matching_client.post(
        "/api/v1/matching/search",
        json={"buyer_id": fake_id, "listing_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


async def test_search_no_listings(matching_client, agent_user):
    response = await matching_client.post(
        "/api/v1/matching/search",
        json={"buyer_id": str(agent_user.id), "listing_id": "none"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["buyer_id"] == str(agent_user.id)
    assert data["candidates"] == []
    assert data["best_match"] is None
    assert data["total_listings_found"] == 0


async def test_search_with_listing(
    matching_client, agent_user, agent_seller, agent_listing, agent_seller_reputation,
):
    response = await matching_client.post(
        "/api/v1/matching/search",
        json={
            "buyer_id": str(agent_user.id),
            "listing_id": str(agent_listing.id),
            "buyer_latitude": 40.7128,
            "buyer_longitude": -74.0060,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["buyer_id"] == str(agent_user.id)
    assert len(data["candidates"]) >= 1
    assert data["best_match"] is not None
    candidate = data["candidates"][0]
    assert candidate["service_name"] == "Spotify"
    assert candidate["dynamic_price"] == 4.50
    assert candidate["seats_available"] == 3
    assert candidate["trust_score"] > 0
    assert candidate["proximity_score"] >= 0
    assert candidate["match_score"] > 0
    assert len(candidate["match_reasons"]) >= 1


async def test_search_generates_reasons(
    matching_client, agent_user, agent_listing, agent_seller_reputation,
):
    response = await matching_client.post(
        "/api/v1/matching/search",
        json={
            "buyer_id": str(agent_user.id),
            "listing_id": str(agent_listing.id),
            "buyer_latitude": 40.7128,
            "buyer_longitude": -74.0060,
            "preferred_hours": [17, 18, 19, 20],
        },
    )
    candidate = response.json()["candidates"][0]
    # With high reputation and nearby distance, should get reasons
    reasons = candidate["match_reasons"]
    assert any("trusted" in r.lower() or "reputation" in r.lower() or "close" in r.lower() or "nearby" in r.lower() for r in reasons)


# ---------------------------------------------------------------------------
# GET /api/v1/matching/availability/{listing_id}
# ---------------------------------------------------------------------------

async def test_availability_not_found(matching_client):
    fake_id = str(uuid.uuid4())
    response = await matching_client.get(f"/api/v1/matching/availability/{fake_id}")
    assert response.status_code == 404


async def test_availability_success(matching_client, agent_listing):
    response = await matching_client.get(f"/api/v1/matching/availability/{agent_listing.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["listing_id"] == str(agent_listing.id)
    assert data["seats_available"] >= 0
    assert data["status"] == "active"
    assert "last_checked" in data


async def test_availability_with_active_matches(
    matching_client, db_session, agent_listing, agent_user, agent_seller,
):
    # Create a proposed match
    match = Match(
        id=uuid.uuid4(),
        listing_id=agent_listing.id,
        buyer_id=agent_user.id,
        seller_id=agent_seller.id,
        status=MatchStatus.PROPOSED,
        match_score=0.8,
        trust_score=0.8,
        proximity_score=0.8,
        schedule_score=0.8,
        proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(match)
    await db_session.flush()

    response = await matching_client.get(f"/api/v1/matching/availability/{agent_listing.id}")
    data = response.json()
    # Active match should reduce available seats
    assert data["seats_available"] <= agent_listing.seats_available


# ---------------------------------------------------------------------------
# POST /api/v1/matching/pricing/update
# ---------------------------------------------------------------------------

async def test_pricing_update_empty(matching_client):
    response = await matching_client.post("/api/v1/matching/pricing/update")
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 0


async def test_pricing_update_with_listing(
    matching_client, agent_listing,
):
    response = await matching_client.post("/api/v1/matching/pricing/update")
    assert response.status_code == 200
    data = response.json()
    assert "updated" in data
    assert "updates" in data


# ---------------------------------------------------------------------------
# DynamicPricingEngine unit tests
# ---------------------------------------------------------------------------

async def test_pricing_engine_calculations():
    from services.market_matching.main import DynamicPricingEngine, MatchScorer

    # Dynamic pricing
    price = DynamicPricingEngine.calculate_dynamic_price(
        base_price=10.0, demand_score=0.8, supply_score=0.3,
        trust_score=0.9, proximity_score=0.7,
    )
    assert price > 0
    assert isinstance(price, float)

    # Demand score
    assert DynamicPricingEngine.calculate_demand_score(3, 5) == 0.6
    assert DynamicPricingEngine.calculate_demand_score(0, 5) == 0.0

    # Supply score
    assert DynamicPricingEngine.calculate_supply_score(3, 6) == 0.5

    # Match scorer
    trust = MatchScorer.calculate_trust_score(0.8, True, 10)
    assert 0.8 <= trust <= 1.0

    proximity = MatchScorer.calculate_proximity_score(5.0, 25.0)
    assert proximity == 0.8

    schedule = MatchScorer.calculate_schedule_score([9, 10, 11], [10, 11, 12])
    assert 0 < schedule < 1

    price_score = MatchScorer.calculate_price_score(4.0, 10.0)
    assert price_score == 0.6

    total = MatchScorer.calculate_match_score(trust, proximity, schedule, price_score)
    assert 0 <= total <= 1


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

async def test_haversine_distance():
    from services.market_matching.main import haversine_distance

    # Same point
    assert haversine_distance(40.7128, -74.0060, 40.7128, -74.0060) == 0.0

    # NYC to LA ~3944 km
    dist = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
    assert 3900 < dist < 4000
