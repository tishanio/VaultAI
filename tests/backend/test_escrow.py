"""Tests for escrow endpoints — full lifecycle coverage."""
import uuid

import pytest

from vault.db.models import EscrowStatus, EscrowTransaction, PayoutStatus
from vault.config import settings
from vault.security import create_access_token

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /escrow/escrows/{escrow_id}
# ---------------------------------------------------------------------------


async def test_get_escrow_unauthorized(async_client):
    response = await async_client.get("/api/v1/escrow/escrows/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


async def test_get_escrow_not_found(async_client, auth_headers):
    response = await async_client.get(
        "/api/v1/escrow/escrows/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_get_escrow_success(async_client, auth_headers, funded_escrow):
    response = await async_client.get(
        f"/api/v1/escrow/escrows/{funded_escrow.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(funded_escrow.id)
    assert data["status"] == "funded"
    assert data["amount"] == funded_escrow.amount
    assert data["currency"] == "USD"
    assert data["fee_percentage"] == 12.0
    assert data["funded_at"] is not None
    assert data["released_at"] is None


# ---------------------------------------------------------------------------
# POST /escrow/matches/{match_id}/escrow — create escrow
# ---------------------------------------------------------------------------


async def test_create_escrow_unauthorized(async_client, accepted_match):
    response = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow"
    )
    assert response.status_code == 401


async def test_create_escrow_match_not_found(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/escrow/matches/00000000-0000-0000-0000-000000000000/escrow",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_create_escrow_not_buyer(async_client, seller_auth_headers, accepted_match):
    """Only the buyer can create escrow for a match."""
    response = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=seller_auth_headers,
    )
    assert response.status_code == 403


async def test_create_escrow_match_not_accepted(async_client, auth_headers, proposed_match):
    """Escrow can only be created for accepted matches."""
    response = await async_client.post(
        f"/api/v1/escrow/matches/{proposed_match.id}/escrow",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "accepted" in response.json()["detail"].lower()


async def test_create_escrow_success(async_client, auth_headers, accepted_match):
    response = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "escrow_id" in data
    assert data["amount"] == accepted_match.proposed_price
    assert data["client_secret"].startswith("demo_secret_")
    assert data["payment_intent_id"].startswith("pi_demo_")


async def test_create_escrow_duplicate(async_client, auth_headers, accepted_match, funded_escrow):
    """Creating escrow for a match that already has one should fail."""
    response = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=auth_headers,
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /escrow/escrows/{escrow_id}/fund
# ---------------------------------------------------------------------------


async def test_fund_escrow_unauthorized(async_client):
    response = await async_client.post("/api/v1/escrow/escrows/some-id/fund")
    assert response.status_code == 401


async def test_fund_escrow_not_found(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/escrow/escrows/00000000-0000-0000-0000-000000000000/fund",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_fund_escrow_success(async_client, auth_headers, db_session, accepted_match):
    """Create an escrow in CREATED state, then fund it."""
    # First create an escrow
    create_resp = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    escrow_id = create_resp.json()["escrow_id"]

    # Now fund it
    fund_resp = await async_client.post(
        f"/api/v1/escrow/escrows/{escrow_id}/fund",
        headers=auth_headers,
    )
    assert fund_resp.status_code == 200
    assert fund_resp.json()["status"] == "funded"


# ---------------------------------------------------------------------------
# POST /escrow/escrows/{escrow_id}/release
# ---------------------------------------------------------------------------


async def test_release_escrow_unauthorized(async_client, funded_escrow):
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{funded_escrow.id}/release"
    )
    assert response.status_code == 401


async def test_release_escrow_not_found(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/escrow/escrows/00000000-0000-0000-0000-000000000000/release",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_release_escrow_not_seller(async_client, auth_headers, funded_escrow):
    """Only the seller can release escrow."""
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{funded_escrow.id}/release",
        headers=auth_headers,  # buyer's headers
    )
    assert response.status_code == 403


async def test_release_escrow_wrong_status(async_client, seller_auth_headers, db_session, accepted_match):
    """Cannot release an escrow that is in CREATED status."""
    # Create escrow (CREATED status)
    create_resp = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers={"Authorization": f"Bearer {create_access_token(str(accepted_match.buyer_id), {})}"},
    )
    escrow_id = create_resp.json()["escrow_id"]

    # Try to release without funding first
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{escrow_id}/release",
        headers=seller_auth_headers,
    )
    assert response.status_code == 400
    assert "created" in response.json()["detail"].lower()


async def test_release_escrow_success(async_client, seller_auth_headers, funded_escrow):
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{funded_escrow.id}/release",
        headers=seller_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Escrow released to seller"
    assert data["amount"] == funded_escrow.seller_payout


# ---------------------------------------------------------------------------
# POST /escrow/escrows/{escrow_id}/refund
# ---------------------------------------------------------------------------


async def test_refund_escrow_unauthorized(async_client, funded_escrow):
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{funded_escrow.id}/refund"
    )
    assert response.status_code == 401


async def test_refund_escrow_not_found(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/escrow/escrows/00000000-0000-0000-0000-000000000000/refund",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_refund_escrow_wrong_status(async_client, auth_headers, db_session, accepted_match):
    """Cannot refund an escrow that is in CREATED status."""
    create_resp = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=auth_headers,
    )
    escrow_id = create_resp.json()["escrow_id"]

    response = await async_client.post(
        f"/api/v1/escrow/escrows/{escrow_id}/refund",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "created" in response.json()["detail"].lower()


async def test_refund_escrow_success(async_client, auth_headers, funded_escrow):
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{funded_escrow.id}/refund",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Escrow refunded"


async def test_refund_escrow_with_reason(async_client, auth_headers, funded_escrow):
    response = await async_client.post(
        f"/api/v1/escrow/escrows/{funded_escrow.id}/refund",
        params={"reason": "Service not provided"},
        headers=auth_headers,
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /escrow/webhooks/stripe — Stripe webhook
# ---------------------------------------------------------------------------


async def test_stripe_webhook_invalid_signature(async_client):
    response = await async_client.post(
        "/api/v1/escrow/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "invalid_sig"},
    )
    # In demo mode, webhook accepts or ignores without crashing
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "ignored")


async def test_stripe_webhook_empty_body(async_client):
    response = await async_client.post(
        "/api/v1/escrow/webhooks/stripe",
        content=b"",
        headers={"Stripe-Signature": ""},
    )
    assert response.status_code == 200


async def test_stripe_webhook_valid_json_no_sig(async_client):
    """Valid JSON but no signature — should be handled gracefully."""
    import json
    payload = json.dumps({"id": "evt_test", "type": "payment_intent.succeeded", "data": {"object": {}}})
    response = await async_client.post(
        "/api/v1/escrow/webhooks/stripe",
        content=payload.encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Full lifecycle test: create → fund → release → verify
# ---------------------------------------------------------------------------


async def test_escrow_full_lifecycle(async_client, auth_headers, seller_auth_headers, accepted_match):
    """Test the complete escrow lifecycle: create → fund → release."""
    buyer_id = str(accepted_match.buyer_id)

    # 1. Create escrow
    create_resp = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    escrow_id = create_resp.json()["escrow_id"]

    # 2. Verify initial state
    get_resp = await async_client.get(
        f"/api/v1/escrow/escrows/{escrow_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "created"

    # 3. Fund escrow
    fund_resp = await async_client.post(
        f"/api/v1/escrow/escrows/{escrow_id}/fund",
        headers=auth_headers,
    )
    assert fund_resp.status_code == 200

    # 4. Verify funded state
    get_resp2 = await async_client.get(
        f"/api/v1/escrow/escrows/{escrow_id}",
        headers=auth_headers,
    )
    assert get_resp2.json()["status"] == "funded"
    assert get_resp2.json()["funded_at"] is not None

    # 5. Release escrow (seller action)
    release_resp = await async_client.post(
        f"/api/v1/escrow/escrows/{escrow_id}/release",
        headers=seller_auth_headers,
    )
    assert release_resp.status_code == 200

    # 6. Verify final state
    get_resp3 = await async_client.get(
        f"/api/v1/escrow/escrows/{escrow_id}",
        headers=auth_headers,
    )
    assert get_resp3.json()["status"] == "released"
    assert get_resp3.json()["released_at"] is not None


# ---------------------------------------------------------------------------
# Escrow fee calculation
# ---------------------------------------------------------------------------


async def test_escrow_fee_calculation(async_client, auth_headers, accepted_match):
    """Verify platform fee is correctly calculated at 12%."""
    response = await async_client.post(
        f"/api/v1/escrow/matches/{accepted_match.id}/escrow",
        headers=auth_headers,
    )
    assert response.status_code == 201
    escrow_id = response.json()["escrow_id"]

    # Get escrow details
    get_resp = await async_client.get(
        f"/api/v1/escrow/escrows/{escrow_id}",
        headers=auth_headers,
    )
    data = get_resp.json()
    amount = data["amount"]
    fee = data["platform_fee"]
    payout = data["seller_payout"]

    # 12% platform fee
    assert fee == round(amount * 0.12, 2)
    # Seller payout = amount - fee
    assert payout == round(amount - fee, 2)
    # Fee percentage
    assert data["fee_percentage"] == 12.0
