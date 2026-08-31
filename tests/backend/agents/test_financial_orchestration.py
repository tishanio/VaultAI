"""Tests for Financial Orchestration Agent."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    EscrowStatus,
    MatchStatus,
    Payout,
    PayoutStatus,
)

pytestmark = pytest.mark.asyncio


async def test_health(finance_client):
    response = await finance_client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "financial-orchestration"


# ---------------------------------------------------------------------------
# GET /api/v1/finance/split-preview/{escrow_id}
# ---------------------------------------------------------------------------

async def test_split_preview_not_found(finance_client):
    fake_id = str(uuid.uuid4())
    response = await finance_client.get(f"/api/v1/finance/split-preview/{fake_id}")
    assert response.status_code == 404


async def test_split_preview_success(finance_client, agent_escrow):
    response = await finance_client.get(f"/api/v1/finance/split-preview/{agent_escrow.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_amount"] == 4.50
    assert data["platform_fee"] == 0.54
    assert data["seller_payout"] == 3.96
    assert data["fee_percentage"] == 12.0
    assert "buyer_pays" in data["breakdown"]
    assert "platform_fee" in data["breakdown"]
    assert "seller_receives" in data["breakdown"]
    assert "processing_fee" in data["breakdown"]


# ---------------------------------------------------------------------------
# GET /api/v1/finance/payouts/{user_id}
# ---------------------------------------------------------------------------

async def test_user_payouts_empty(finance_client, agent_seller):
    response = await finance_client.get(f"/api/v1/finance/payouts/{agent_seller.id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


async def test_user_payouts_with_data(finance_client, db_session, agent_seller):
    payout = Payout(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        status=PayoutStatus.COMPLETED,
        amount=3.96,
        currency="USD",
        payout_method="bank_transfer",
        processed_at=datetime.now(timezone.utc),
    )
    db_session.add(payout)
    await db_session.flush()

    response = await finance_client.get(f"/api/v1/finance/payouts/{agent_seller.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["amount"] == 3.96
    assert data[0]["status"] == "completed"
    assert data[0]["payout_method"] == "bank_transfer"


# ---------------------------------------------------------------------------
# POST /api/v1/finance/payouts/process
# ---------------------------------------------------------------------------

async def test_process_payouts_empty(finance_client):
    response = await finance_client.post("/api/v1/finance/payouts/process")
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] == 0
    assert data["total"] == 0


async def test_process_payouts_demo_mode(finance_client, db_session, agent_seller):
    payout = Payout(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        status=PayoutStatus.PENDING,
        amount=3.96,
        currency="USD",
        payout_method="bank_transfer",
    )
    db_session.add(payout)
    await db_session.flush()

    response = await finance_client.post("/api/v1/finance/payouts/process")
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] == 1
    assert data["total"] == 1


# ---------------------------------------------------------------------------
# GET /api/v1/finance/tax-summary/{user_id}
# ---------------------------------------------------------------------------

async def test_tax_summary_empty(finance_client, agent_seller):
    response = await finance_client.get(
        f"/api/v1/finance/tax-summary/{agent_seller.id}",
        params={"tax_year": 2024},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(agent_seller.id)
    assert data["total_gross_payouts"] == 0
    assert data["transaction_count"] == 0
    assert data["forms_1099k_required"] is False


async def test_tax_summary_with_payouts(finance_client, db_session, agent_seller):
    for i in range(3):
        payout = Payout(
            id=uuid.uuid4(),
            user_id=agent_seller.id,
            status=PayoutStatus.COMPLETED,
            amount=100.00,
            currency="USD",
            payout_method="bank_transfer",
            processed_at=datetime.now(timezone.utc),
        )
        db_session.add(payout)
    await db_session.flush()

    response = await finance_client.get(
        f"/api/v1/finance/tax-summary/{agent_seller.id}",
        params={"tax_year": datetime.now(timezone.utc).year},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_gross_payouts"] == 300.00
    assert data["transaction_count"] == 3
    assert data["total_platform_fees"] > 0
    assert data["total_net_payouts"] > 0


async def test_tax_summary_1099k_threshold(finance_client, db_session, agent_seller):
    payout = Payout(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        status=PayoutStatus.COMPLETED,
        amount=25000.00,
        currency="USD",
        payout_method="bank_transfer",
        processed_at=datetime.now(timezone.utc),
    )
    db_session.add(payout)
    await db_session.flush()

    response = await finance_client.get(
        f"/api/v1/finance/tax-summary/{agent_seller.id}",
        params={"tax_year": datetime.now(timezone.utc).year},
    )
    assert response.json()["forms_1099k_required"] is True


# ---------------------------------------------------------------------------
# GET /api/v1/finance/dashboard/{user_id}
# ---------------------------------------------------------------------------

async def test_dashboard_empty(finance_client, agent_seller):
    response = await finance_client.get(f"/api/v1/finance/dashboard/{agent_seller.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(agent_seller.id)
    assert data["total_earned"] == 0
    assert data["total_pending"] == 0
    assert data["active_escrows"] == 0
    assert data["completed_transactions"] == 0
    assert data["pending_payouts"] == 0


async def test_dashboard_with_data(
    finance_client, db_session, agent_seller, agent_user, agent_escrow, agent_match,
):
    # Add completed payout
    payout = Payout(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        status=PayoutStatus.COMPLETED,
        amount=3.96,
        currency="USD",
        payout_method="bank_transfer",
        processed_at=datetime.now(timezone.utc),
    )
    db_session.add(payout)
    # Add pending payout
    pending = Payout(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        status=PayoutStatus.PENDING,
        amount=2.50,
        currency="USD",
        payout_method="bank_transfer",
    )
    db_session.add(pending)
    await db_session.flush()

    response = await finance_client.get(f"/api/v1/finance/dashboard/{agent_seller.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_earned"] == 3.96
    assert data["total_pending"] == 2.50
    assert data["pending_payouts"] == 1
    assert data["total_fees"] > 0
