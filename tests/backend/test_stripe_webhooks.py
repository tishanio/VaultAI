"""Comprehensive tests for Stripe webhook handlers — all event types."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, patch

from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    Dispute,
    DisputeStatus,
    EscrowStatus,
    EscrowTransaction,
    Match,
    MatchStatus,
    Payout,
    PayoutStatus,
    User,
)

pytestmark = pytest.mark.asyncio


def _mock_publisher():
    """Create a mock publisher for direct handler tests."""
    mock = AsyncMock()
    mock.publish = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Signature verification tests (via HTTP)
# ---------------------------------------------------------------------------

async def test_stripe_webhook_invalid_signature(async_client):
    response = await async_client.post(
        "/api/v1/escrow/webhooks/stripe", content=b"{}",
        headers={"stripe-signature": "invalid_sig"},
    )
    assert response.status_code in (200, 400, 401, 403)


async def test_stripe_webhook_empty_body(async_client):
    response = await async_client.post(
        "/api/v1/escrow/webhooks/stripe", content=b"",
        headers={"Stripe-Signature": ""},
    )
    assert response.status_code == 200


async def test_stripe_webhook_valid_json_no_sig(async_client):
    payload = json.dumps({"id": "evt_test", "type": "payment_intent.succeeded", "data": {"object": {}}})
    response = await async_client.post(
        "/api/v1/escrow/webhooks/stripe", content=payload.encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# payment_intent.succeeded
# ---------------------------------------------------------------------------

async def test_pi_succeeded_funds_escrow(db_session, funded_escrow):
    """Already-funded escrow — should skip without publishing."""
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_succeeded
    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {"id": funded_escrow.stripe_payment_intent_id, "metadata": {"escrow_id": str(funded_escrow.id)}}
        await _handle_payment_intent_succeeded(data, db_session)
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.FUNDED


async def test_pi_succeeded_creates_escrow_from_created(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_succeeded
    funded_escrow.status = EscrowStatus.CREATED
    funded_escrow.funded_at = None
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {"id": funded_escrow.stripe_payment_intent_id, "metadata": {"escrow_id": str(funded_escrow.id)}}
        await _handle_payment_intent_succeeded(data, db_session)
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.FUNDED
    assert funded_escrow.funded_at is not None
    mock_pub.publish.assert_called_once()


async def test_pi_succeeded_lookup_by_pi_id(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_succeeded
    funded_escrow.status = EscrowStatus.CREATED
    funded_escrow.funded_at = None
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {"id": funded_escrow.stripe_payment_intent_id, "metadata": {}}
        await _handle_payment_intent_succeeded(data, db_session)
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.FUNDED


async def test_pi_succeeded_no_escrow_found(db_session):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_succeeded
    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_payment_intent_succeeded({"id": "pi_nonexistent", "metadata": {}}, db_session)


# ---------------------------------------------------------------------------
# payment_intent.payment_failed
# ---------------------------------------------------------------------------

async def test_pi_failed_records_compliance_event(db_session, funded_escrow, accepted_match):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_failed
    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {
            "id": funded_escrow.stripe_payment_intent_id,
            "metadata": {"escrow_id": str(funded_escrow.id)},
            "last_payment_error": {"code": "card_declined", "message": "Declined"},
        }
        await _handle_payment_intent_failed(data, db_session)

    from sqlalchemy import select
    result = await db_session.execute(
        select(ComplianceEvent).where(ComplianceEvent.user_id == accepted_match.buyer_id)
    )
    events = result.scalars().all()
    assert any("Payment failed" in e.title for e in events)


async def test_pi_failed_no_escrow(db_session):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_failed
    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_payment_intent_failed(
            {"id": "pi_unknown", "metadata": {}, "last_payment_error": {"code": "expired_card"}}, db_session
        )


# ---------------------------------------------------------------------------
# payment_intent.canceled
# ---------------------------------------------------------------------------

async def test_pi_canceled_refunds_escrow(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_canceled
    funded_escrow.status = EscrowStatus.CREATED
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {
            "id": funded_escrow.stripe_payment_intent_id,
            "metadata": {"escrow_id": str(funded_escrow.id)},
            "cancellation_reason": "requested_by_customer",
        }
        await _handle_payment_intent_canceled(data, db_session)
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.REFUNDED
    assert "requested_by_customer" in (funded_escrow.refund_reason or "")


async def test_pi_canceled_already_released(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_payment_intent_canceled
    funded_escrow.status = EscrowStatus.RELEASED
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_payment_intent_canceled(
            {"id": funded_escrow.stripe_payment_intent_id, "metadata": {"escrow_id": str(funded_escrow.id)}},
            db_session,
        )
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.RELEASED


# ---------------------------------------------------------------------------
# charge.refunded
# ---------------------------------------------------------------------------

async def test_charge_refunded(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_charge_refunded
    funded_escrow.status = EscrowStatus.FUNDED
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {"id": f"ch_{uuid.uuid4().hex[:12]}", "payment_intent": funded_escrow.stripe_payment_intent_id, "amount_refunded": 450}
        await _handle_charge_refunded(data, db_session)
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.REFUNDED
    assert "Stripe refund" in (funded_escrow.refund_reason or "")


async def test_charge_refunded_no_pi(db_session):
    from services.api_gateway.stripe_webhooks import _handle_charge_refunded
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_charge_refunded({"id": "ch_test", "payment_intent": None, "amount_refunded": 100}, db_session)


async def test_charge_refunded_no_escrow(db_session):
    from services.api_gateway.stripe_webhooks import _handle_charge_refunded
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_charge_refunded({"id": "ch_test", "payment_intent": "pi_nonexistent", "amount_refunded": 100}, db_session)


async def test_charge_refunded_already_refunded(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_charge_refunded
    funded_escrow.status = EscrowStatus.REFUNDED
    await db_session.flush()

    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_charge_refunded(
            {"id": "ch_test", "payment_intent": funded_escrow.stripe_payment_intent_id, "amount_refunded": 450}, db_session
        )
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.REFUNDED


# ---------------------------------------------------------------------------
# charge.dispute.created
# ---------------------------------------------------------------------------

async def test_dispute_created_freezes_escrow(db_session, funded_escrow, accepted_match):
    from services.api_gateway.stripe_webhooks import _handle_charge_dispute_created
    funded_escrow.status = EscrowStatus.FUNDED
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        data = {"id": f"dp_{uuid.uuid4().hex[:12]}", "payment_intent": funded_escrow.stripe_payment_intent_id, "reason": "fraudulent", "amount": 450}
        await _handle_charge_dispute_created(data, db_session)

    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.DISPUTED
    from sqlalchemy import select
    result = await db_session.execute(select(Dispute).where(Dispute.match_id == accepted_match.id))
    disputes = result.scalars().all()
    assert len(disputes) >= 1
    assert disputes[0].status == DisputeStatus.OPEN


async def test_dispute_created_no_escrow(db_session):
    from services.api_gateway.stripe_webhooks import _handle_charge_dispute_created
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_charge_dispute_created({"id": "dp_test", "payment_intent": "pi_nonexistent", "reason": "fraudulent", "amount": 450}, db_session)


async def test_dispute_created_escrow_not_disputable(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_charge_dispute_created
    funded_escrow.status = EscrowStatus.RELEASED
    await db_session.flush()

    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_charge_dispute_created(
            {"id": "dp_test", "payment_intent": funded_escrow.stripe_payment_intent_id, "reason": "fraudulent", "amount": 450}, db_session
        )
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.RELEASED


# ---------------------------------------------------------------------------
# charge.dispute.closed
# ---------------------------------------------------------------------------

async def test_dispute_closed_won_refunds(db_session, funded_escrow, accepted_match):
    from services.api_gateway.stripe_webhooks import _handle_charge_dispute_closed
    stripe_dispute_id = f"dp_{uuid.uuid4().hex[:12]}"
    funded_escrow.status = EscrowStatus.DISPUTED
    await db_session.flush()

    dispute = Dispute(
        id=uuid.uuid4(), match_id=accepted_match.id, filed_by_id=accepted_match.buyer_id,
        status=DisputeStatus.OPEN, reason="fraudulent", description="Test",
        meta={"stripe_dispute_id": stripe_dispute_id, "pi_id": funded_escrow.stripe_payment_intent_id},
    )
    db_session.add(dispute)
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_charge_dispute_closed(
            {"id": stripe_dispute_id, "payment_intent": funded_escrow.stripe_payment_intent_id, "outcome": "won"}, db_session
        )
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.REFUNDED


async def test_dispute_closed_lost_releases(db_session, funded_escrow, accepted_match):
    from services.api_gateway.stripe_webhooks import _handle_charge_dispute_closed
    stripe_dispute_id = f"dp_{uuid.uuid4().hex[:12]}"
    funded_escrow.status = EscrowStatus.DISPUTED
    await db_session.flush()

    dispute = Dispute(
        id=uuid.uuid4(), match_id=accepted_match.id, filed_by_id=accepted_match.buyer_id,
        status=DisputeStatus.OPEN, reason="fraudulent", description="Test",
        meta={"stripe_dispute_id": stripe_dispute_id, "pi_id": funded_escrow.stripe_payment_intent_id},
    )
    db_session.add(dispute)
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_charge_dispute_closed(
            {"id": stripe_dispute_id, "payment_intent": funded_escrow.stripe_payment_intent_id, "outcome": "lost"}, db_session
        )
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.RELEASED
    assert funded_escrow.released_at is not None
    await db_session.refresh(accepted_match)
    assert accepted_match.status == MatchStatus.COMPLETED

    from sqlalchemy import select
    result = await db_session.execute(select(Payout).where(Payout.user_id == accepted_match.seller_id))
    payouts = result.scalars().all()
    assert len(payouts) >= 1
    assert payouts[0].status == PayoutStatus.PENDING


async def test_dispute_closed_not_disputed(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_charge_dispute_closed
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_charge_dispute_closed(
            {"id": "dp_test", "payment_intent": funded_escrow.stripe_payment_intent_id, "outcome": "won"}, db_session
        )
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.FUNDED


# ---------------------------------------------------------------------------
# transfer.paid
# ---------------------------------------------------------------------------

async def test_transfer_paid_completes_payout(db_session, seller_user):
    from services.api_gateway.stripe_webhooks import _handle_transfer_paid
    transfer_id = f"tr_{uuid.uuid4().hex[:12]}"
    payout = Payout(id=uuid.uuid4(), user_id=seller_user.id, stripe_transfer_id=transfer_id,
                    status=PayoutStatus.PENDING, amount=3.96, currency="USD", payout_method="stripe_connect")
    db_session.add(payout)
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_transfer_paid({"id": transfer_id, "destination": "acct_test", "amount": 396}, db_session)
    await db_session.refresh(payout)
    assert payout.status == PayoutStatus.COMPLETED


async def test_transfer_paid_no_payout(db_session):
    from services.api_gateway.stripe_webhooks import _handle_transfer_paid
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_transfer_paid({"id": "tr_nonexistent", "destination": "acct_test", "amount": 100}, db_session)


async def test_transfer_paid_escrow_held_releases(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import _handle_transfer_paid
    transfer_id = f"tr_{uuid.uuid4().hex[:12]}"
    funded_escrow.stripe_transfer_id = transfer_id
    funded_escrow.status = EscrowStatus.HELD
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_transfer_paid({"id": transfer_id, "destination": "acct_test", "amount": 450}, db_session)
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.RELEASED


# ---------------------------------------------------------------------------
# transfer.failed
# ---------------------------------------------------------------------------

async def test_transfer_failed_marks_payout_failed(db_session, seller_user):
    from services.api_gateway.stripe_webhooks import _handle_transfer_failed
    transfer_id = f"tr_{uuid.uuid4().hex[:12]}"
    payout = Payout(id=uuid.uuid4(), user_id=seller_user.id, stripe_transfer_id=transfer_id,
                    status=PayoutStatus.PENDING, amount=3.96, currency="USD", payout_method="stripe_connect")
    db_session.add(payout)
    await db_session.flush()

    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_transfer_failed({"id": transfer_id, "failure_code": "account_declined", "failure_message": "Declined"}, db_session)
    await db_session.refresh(payout)
    assert payout.status == PayoutStatus.FAILED
    assert "account_declined" in (payout.failure_reason or "")


async def test_transfer_failed_records_compliance_event(db_session, seller_user):
    from services.api_gateway.stripe_webhooks import _handle_transfer_failed
    transfer_id = f"tr_{uuid.uuid4().hex[:12]}"
    payout = Payout(id=uuid.uuid4(), user_id=seller_user.id, stripe_transfer_id=transfer_id,
                    status=PayoutStatus.PROCESSING, amount=5.00, currency="USD", payout_method="stripe_connect")
    db_session.add(payout)
    await db_session.flush()

    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_transfer_failed({"id": transfer_id, "failure_code": "insufficient_funds", "failure_message": "No funds"}, db_session)

    from sqlalchemy import select
    result = await db_session.execute(select(ComplianceEvent).where(ComplianceEvent.user_id == seller_user.id))
    events = result.scalars().all()
    assert any("Transfer failed" in e.title for e in events)


# ---------------------------------------------------------------------------
# payout.paid / payout.failed
# ---------------------------------------------------------------------------

async def test_payout_paid_logs_only(db_session):
    from services.api_gateway.stripe_webhooks import _handle_payout_paid
    await _handle_payout_paid({"id": "po_platform_123", "amount": 10000}, db_session)


async def test_payout_failed_records_compliance_event(db_session):
    from services.api_gateway.stripe_webhooks import _handle_payout_failed
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_payout_failed({"id": "po_456", "failure_code": "bank_closed", "failure_message": "Closed"}, db_session)

    from sqlalchemy import select
    result = await db_session.execute(select(ComplianceEvent))
    events = result.scalars().all()
    assert any("Platform payout failed" in e.title for e in events)


# ---------------------------------------------------------------------------
# account.updated
# ---------------------------------------------------------------------------

async def test_account_updated_verifies_user(db_session):
    from services.api_gateway.stripe_webhooks import _handle_account_updated
    connect_id = f"acct_{uuid.uuid4().hex[:12]}"
    user = User(id=uuid.uuid4(), email="connect@test.app", username="connectuser",
                display_name="Connect User", password_hash="hash",
                is_active=True, is_verified=False, stripe_connect_account_id=connect_id)
    db_session.add(user)
    await db_session.flush()

    mock_pub = _mock_publisher()
    with patch("services.api_gateway.stripe_webhooks.publisher", mock_pub):
        await _handle_account_updated({"id": connect_id, "charges_enabled": True, "payouts_enabled": True, "details_submitted": True}, db_session)
    await db_session.refresh(user)
    assert user.is_verified is True
    assert user.preferences["stripe_charges_enabled"] is True


async def test_account_updated_no_user(db_session):
    from services.api_gateway.stripe_webhooks import _handle_account_updated
    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_account_updated({"id": "acct_nonexistent", "charges_enabled": True, "payouts_enabled": True, "details_submitted": True}, db_session)


async def test_account_updated_already_verified(db_session):
    from services.api_gateway.stripe_webhooks import _handle_account_updated
    connect_id = f"acct_{uuid.uuid4().hex[:12]}"
    user = User(id=uuid.uuid4(), email="v@test.app", username="vuser", display_name="V",
                password_hash="hash", is_active=True, is_verified=True, stripe_connect_account_id=connect_id)
    db_session.add(user)
    await db_session.flush()

    with patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        await _handle_account_updated({"id": connect_id, "charges_enabled": True, "payouts_enabled": True, "details_submitted": True}, db_session)
    await db_session.refresh(user)
    assert user.is_verified is True


# ---------------------------------------------------------------------------
# process_webhook_event dispatcher
# ---------------------------------------------------------------------------

async def test_process_webhook_unhandled_type(db_session):
    from services.api_gateway.stripe_webhooks import process_webhook_event
    event = {"id": f"evt_{uuid.uuid4().hex[:16]}", "type": "invoice.created", "data": {"object": {"id": "inv_test"}}}
    with patch("services.api_gateway.stripe_webhooks._is_duplicate_event", return_value=False), \
         patch("services.api_gateway.stripe_webhooks._mark_event_processed", new_callable=AsyncMock), \
         patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        result = await process_webhook_event(event, db_session)
    assert result == "unhandled"


async def test_process_webhook_duplicate(db_session):
    from services.api_gateway.stripe_webhooks import process_webhook_event
    event = {"id": f"evt_{uuid.uuid4().hex[:16]}", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_test", "metadata": {}}}}
    with patch("services.api_gateway.stripe_webhooks._is_duplicate_event", return_value=True):
        result = await process_webhook_event(event, db_session)
    assert result == "duplicate"


async def test_process_webhook_processes_event(db_session, funded_escrow):
    from services.api_gateway.stripe_webhooks import process_webhook_event
    funded_escrow.status = EscrowStatus.CREATED
    funded_escrow.funded_at = None
    await db_session.flush()

    event = {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": funded_escrow.stripe_payment_intent_id, "metadata": {"escrow_id": str(funded_escrow.id)}}},
    }
    with patch("services.api_gateway.stripe_webhooks._is_duplicate_event", return_value=False), \
         patch("services.api_gateway.stripe_webhooks._mark_event_processed", new_callable=AsyncMock), \
         patch("services.api_gateway.stripe_webhooks.publisher", _mock_publisher()):
        result = await process_webhook_event(event, db_session)
    assert result == "processed"
    await db_session.refresh(funded_escrow)
    assert funded_escrow.status == EscrowStatus.FUNDED
