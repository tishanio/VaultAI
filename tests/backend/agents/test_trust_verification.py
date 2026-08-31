"""Tests for Trust & Verification Agent."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    Dispute,
    DisputeStatus,
    EscrowStatus,
    EscrowTransaction,
    KYCStatus,
    KYCVerification,
    Match,
    MatchStatus,
    ReputationScore,
)

pytestmark = pytest.mark.asyncio


async def test_health(trust_client):
    response = await trust_client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "trust-verification"


# ---------------------------------------------------------------------------
# POST /api/v1/trust/kyc/initiate
# ---------------------------------------------------------------------------

async def test_kyc_initiate_user_not_found(trust_client):
    fake_id = str(uuid.uuid4())
    response = await trust_client.post(
        "/api/v1/trust/kyc/initiate",
        params={"user_id": fake_id},
        json={"document_type": "passport", "document_country": "US"},
    )
    assert response.status_code == 404


async def test_kyc_initiate_success(trust_client, agent_user):
    response = await trust_client.post(
        "/api/v1/trust/kyc/initiate",
        params={"user_id": str(agent_user.id)},
        json={"document_type": "passport", "document_country": "US"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"  # demo mode
    assert "verification_id" in data
    assert "mock_check_" in data["onfido_check_id"]


async def test_kyc_initiate_duplicate(trust_client, agent_user):
    # First initiation succeeds
    await trust_client.post(
        "/api/v1/trust/kyc/initiate",
        params={"user_id": str(agent_user.id)},
        json={"document_type": "passport", "document_country": "US"},
    )
    # Second initiation fails
    response = await trust_client.post(
        "/api/v1/trust/kyc/initiate",
        params={"user_id": str(agent_user.id)},
        json={"document_type": "drivers_license", "document_country": "US"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/v1/trust/kyc/{user_id}
# ---------------------------------------------------------------------------

async def test_kyc_status_not_found(trust_client):
    fake_id = str(uuid.uuid4())
    response = await trust_client.get(f"/api/v1/trust/kyc/{fake_id}")
    assert response.status_code == 404


async def test_kyc_status_success(trust_client, agent_user):
    # Initiate first
    await trust_client.post(
        "/api/v1/trust/kyc/initiate",
        params={"user_id": str(agent_user.id)},
        json={"document_type": "passport", "document_country": "US"},
    )
    response = await trust_client.get(f"/api/v1/trust/kyc/{agent_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"


# ---------------------------------------------------------------------------
# GET /api/v1/trust/reputation/{user_id}
# ---------------------------------------------------------------------------

async def test_reputation_new_user(trust_client, agent_user):
    response = await trust_client.get(f"/api/v1/trust/reputation/{agent_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(agent_user.id)
    assert data["overall_score"] == 0.5
    assert data["trust_tier"] == "bronze"


async def test_reputation_existing_user(
    trust_client, agent_user, agent_seller, agent_seller_reputation,
):
    response = await trust_client.get(f"/api/v1/trust/reputation/{agent_seller.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] >= 0.85
    assert data["trust_tier"] == "gold"
    assert data["total_transactions"] == 10


async def test_reputation_platinum_tier(trust_client, db_session, agent_user):
    rep = ReputationScore(
        id=uuid.uuid4(), user_id=agent_user.id,
        overall_score=0.95, reliability_score=0.95,
        communication_score=0.9, payment_score=0.95,
        total_transactions=50, positive_reviews=48, negative_reviews=0,
    )
    db_session.add(rep)
    await db_session.flush()

    response = await trust_client.get(f"/api/v1/trust/reputation/{agent_user.id}")
    assert response.json()["trust_tier"] == "platinum"


# ---------------------------------------------------------------------------
# POST /api/v1/trust/reputation/update
# ---------------------------------------------------------------------------

async def test_reputation_update_positive(trust_client, agent_user):
    response = await trust_client.post(
        "/api/v1/trust/reputation/update",
        params={"user_id": str(agent_user.id), "rating_type": "positive", "category": "reliability"},
    )
    assert response.status_code == 200
    assert response.json()["overall_score"] >= 0.5


async def test_reputation_update_negative(trust_client, agent_user):
    response = await trust_client.post(
        "/api/v1/trust/reputation/update",
        params={"user_id": str(agent_user.id), "rating_type": "negative", "category": "payment"},
    )
    assert response.status_code == 200
    assert response.json()["overall_score"] <= 0.5


async def test_reputation_update_all_categories(trust_client, agent_user):
    for cat in ("reliability", "communication", "payment"):
        response = await trust_client.post(
            "/api/v1/trust/reputation/update",
            params={"user_id": str(agent_user.id), "rating_type": "positive", "category": cat},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/trust/verify/{user_id}
# ---------------------------------------------------------------------------

async def test_verify_trust_no_kyc(trust_client, agent_user):
    response = await trust_client.get(f"/api/v1/trust/verify/{agent_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["kyc_status"] == "not_started"
    assert data["is_verified"] is False
    assert "kyc_not_verified" in data["risk_flags"]


async def test_verify_trust_with_kyc(trust_client, agent_user):
    await trust_client.post(
        "/api/v1/trust/kyc/initiate",
        params={"user_id": str(agent_user.id)},
        json={"document_type": "passport", "document_country": "US"},
    )
    response = await trust_client.get(f"/api/v1/trust/verify/{agent_user.id}")
    data = response.json()
    assert data["kyc_status"] == "verified"
    assert data["is_verified"] is True
    assert "can_transact" in data


# ---------------------------------------------------------------------------
# POST /api/v1/trust/disputes
# ---------------------------------------------------------------------------

async def test_file_dispute_match_not_found(trust_client, agent_user):
    fake_id = str(uuid.uuid4())
    response = await trust_client.post(
        "/api/v1/trust/disputes",
        params={"user_id": str(agent_user.id)},
        json={"match_id": fake_id, "reason": "Service not delivered", "description": "I did not receive access to the subscription service at all."},
    )
    assert response.status_code == 404


async def test_file_dispute_not_party(trust_client, agent_match):
    outsider_id = str(uuid.uuid4())
    response = await trust_client.post(
        "/api/v1/trust/disputes",
        params={"user_id": outsider_id},
        json={"match_id": str(agent_match.id), "reason": "Bad service", "description": "The subscription service was not delivered as expected."},
    )
    assert response.status_code == 403


async def test_file_dispute_success(trust_client, agent_match, agent_user):
    response = await trust_client.post(
        "/api/v1/trust/disputes",
        params={"user_id": str(agent_user.id)},
        json={"match_id": str(agent_match.id), "reason": "No access", "description": "I never received access to the Spotify family seat after payment."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "open"
    assert "dispute_id" in data


async def test_file_dispute_escrow_held(
    trust_client, agent_match, agent_escrow, agent_user,
):
    response = await trust_client.post(
        "/api/v1/trust/disputes",
        params={"user_id": str(agent_user.id)},
        json={"match_id": str(agent_match.id), "reason": "Fraud", "description": "This transaction appears to be fraudulent and needs immediate investigation."},
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST /api/v1/trust/disputes/{dispute_id}/resolve
# ---------------------------------------------------------------------------

async def test_resolve_dispute_not_found(trust_client):
    fake_id = str(uuid.uuid4())
    response = await trust_client.post(
        f"/api/v1/trust/disputes/{fake_id}/resolve",
        params={"resolution": "Refunded"},
    )
    assert response.status_code == 404


async def test_resolve_dispute_success(
    trust_client, agent_match, agent_user, agent_seller,
):
    # File dispute first
    file_resp = await trust_client.post(
        "/api/v1/trust/disputes",
        params={"user_id": str(agent_user.id)},
        json={"match_id": str(agent_match.id), "reason": "Late delivery", "description": "The service was delivered late and caused issues with my workflow."},
    )
    dispute_id = file_resp.json()["dispute_id"]

    response = await trust_client.post(
        f"/api/v1/trust/disputes/{dispute_id}/resolve",
        params={"resolution": "Refunded to buyer", "winner_id": str(agent_user.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resolution"] == "Refunded to buyer"
