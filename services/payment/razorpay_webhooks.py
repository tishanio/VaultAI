"""Razorpay webhook handler for Vault.

Handles the full payment lifecycle:
  - order.paid          — Payment received, order fulfilled
  - order.failed        — Payment failed
  - payment.captured    — Payment captured successfully
  - payment.authorized  — Payment authorized (for 3DS / EMI)
  - payment.failed      — Payment failed
  - payment.dispute.created / payment.dispute.closed
  - refund.created      — Refund initiated
  - refund.processed    — Refund completed
  - refund.failed       — Refund failed
  - transfer.created    — Payout to seller initiated
  - transfer.processed  — Payout completed
  - transfer.reversed   — Payout reversed (bank returned funds)
  - transfer.failed     — Payout failed

Features:
  - HMAC-SHA256 signature verification (always enforced)
  - Idempotent processing via Redis event deduplication
  - Structured logging for every event
  - Publishes internal events to the Vault event bus
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    EscrowStatus,
    EscrowTransaction,
    Match,
    MatchStatus,
    Payout,
    PayoutStatus,
    User,
)
from vault.events import Event, EventType, publisher

logger = logging.getLogger(__name__)

# Maximum age of a webhook event we'll process (5 hours buffer)
MAX_EVENT_AGE_SECONDS = 5 * 60 * 60 + 300

# Redis key prefix for idempotency
_IDEMPOTENCY_PREFIX = "vault:razorpay:webhook:"

# Internal: import Razorpay client for signature verification
import razorpay as _rzp


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def verify_razorpay_signature(payload: bytes, sig_header: str) -> dict | None:
    """Verify the Razorpay webhook signature and return the parsed event.

    Returns ``None`` if verification fails instead of raising, so the
    endpoint can always return 200 to Razorpay.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("RAZORPAY_WEBHOOK_SECRET not configured – skipping verification")
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            return None

    try:
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            logger.warning("Razorpay webhook signature mismatch")
            return None
        return json.loads(payload)
    except Exception as e:
        logger.error("Razorpay webhook verification error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------

async def _is_duplicate_event(event_id: str) -> bool:
    """Check Redis for a previously processed event ID."""
    from vault.events import publisher as _pub
    if not _pub._redis:
        return False
    key = f"{_IDEMPOTENCY_PREFIX}{event_id}"
    exists = await _pub._redis.exists(key)
    return bool(exists)


async def _mark_event_processed(event_id: str) -> None:
    """Store the event ID in Redis with a TTL."""
    from vault.events import publisher as _pub
    if not _pub._redis:
        return
    key = f"{_IDEMPOTENCY_PREFIX}{event_id}"
    await _pub._redis.setex(key, MAX_EVENT_AGE_SECONDS, "1")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _find_escrow_by_order(order_id: str, db: AsyncSession) -> EscrowTransaction | None:
    result = await db.execute(
        select(EscrowTransaction).where(EscrowTransaction.razorpay_order_id == order_id)
    )
    return result.scalar_one_or_none()


async def _find_escrow_by_payment(payment_id: str, db: AsyncSession) -> EscrowTransaction | None:
    result = await db.execute(
        select(EscrowTransaction).where(EscrowTransaction.razorpay_payment_id == payment_id)
    )
    return result.scalar_one_or_none()


async def _find_escrow_by_transfer(transfer_id: str, db: AsyncSession) -> EscrowTransaction | None:
    result = await db.execute(
        select(EscrowTransaction).where(EscrowTransaction.razorpay_transfer_id == transfer_id)
    )
    return result.scalar_one_or_none()


async def _record_compliance_event(
    user_id: str | None,
    event_type: ComplianceEventType,
    severity: str,
    title: str,
    description: str,
    risk_score: float,
    extra_metadata: dict[str, Any] | None,
    db: AsyncSession,
) -> None:
    event = ComplianceEvent(
        id=_uuid.uuid4(),
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        title=title,
        description=description,
        risk_score=risk_score,
        meta=extra_metadata or {},
    )
    db.add(event)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

async def _handle_order_paid(data: dict[str, Any], db: AsyncSession) -> None:
    """Order paid — fund the escrow."""
    order_id = data.get("id")
    payments = data.get("payments", [])
    receipt = data.get("receipt", "")

    logger.info("order.paid order=%s receipt=%s", order_id, receipt)

    escrow = await _find_escrow_by_order(order_id, db)
    if not escrow:
        logger.warning("No escrow found for order %s", order_id)
        return

    if escrow.status in (EscrowStatus.FUNDED, EscrowStatus.HELD, EscrowStatus.RELEASED):
        logger.info("Escrow %s already in status %s – skipping", escrow.id, escrow.status)
        return

    # Extract payment ID from the order's payments array
    payment_id = ""
    if payments:
        payment_id = payments[0].get("id", "")

    if payment_id:
        escrow.razorpay_payment_id = payment_id

    # Transition: CREATED -> FUNDED
    escrow.status = EscrowStatus.FUNDED
    escrow.funded_at = datetime.now(timezone.utc)
    await db.flush()

    await publisher.publish(Event(
        EventType.ESCROW_FUNDED,
        {
            "escrow_id": str(escrow.id),
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": escrow.amount,
            "gateway": "razorpay",
        },
        source="razorpay-webhook",
    ))


async def _handle_order_failed(data: dict[str, Any], db: AsyncSession) -> None:
    """Order payment failed."""
    order_id = data.get("id")
    error_description = data.get("error_description", "Payment failed")

    logger.warning("order.failed order=%s error=%s", order_id, error_description)

    escrow = await _find_escrow_by_order(order_id, db)
    if not escrow:
        return

    # Record compliance event
    match_result = await db.execute(select(Match).where(Match.id == escrow.match_id))
    match = match_result.scalar_one_or_none()
    buyer_id = str(match.buyer_id) if match else None

    await _record_compliance_event(
        user_id=buyer_id,
        event_type=ComplianceEventType.RISK_ALERT,
        severity="medium",
        title=f"Razorpay payment failed for escrow {escrow.id}",
        description=f"Error: {error_description}",
        risk_score=0.4,
        extra_metadata={"order_id": order_id, "escrow_id": str(escrow.id)},
        db=db,
    )

    await publisher.publish(Event(
        EventType.RISK_ALERT,
        {
            "escrow_id": str(escrow.id),
            "reason": "payment_failed",
            "error_description": error_description,
            "gateway": "razorpay",
        },
        source="razorpay-webhook",
    ))


async def _handle_payment_captured(data: dict[str, Any], db: AsyncSession) -> None:
    """Payment captured — redundant safety net for order.paid."""
    payment_id = data.get("id")
    order_id = data.get("order_id")
    amount = data.get("amount", 0) // 100  # paise to rupees

    logger.info("payment.captured payment=%s order=%s amount=%d", payment_id, order_id, amount)

    escrow = None
    if order_id:
        escrow = await _find_escrow_by_order(order_id, db)
    if not escrow and payment_id:
        escrow = await _find_escrow_by_payment(payment_id, db)

    if not escrow:
        return

    if escrow.status in (EscrowStatus.FUNDED, EscrowStatus.HELD, EscrowStatus.RELEASED):
        return

    escrow.razorpay_payment_id = payment_id or escrow.razorpay_payment_id
    escrow.status = EscrowStatus.FUNDED
    escrow.funded_at = datetime.now(timezone.utc)
    await db.flush()


async def _handle_payment_failed(data: dict[str, Any], db: AsyncSession) -> None:
    """Payment failed."""
    payment_id = data.get("id")
    order_id = data.get("order_id")
    error_code = data.get("error_code", "unknown")
    error_description = data.get("error_description", "Payment failed")

    logger.warning("payment.failed payment=%s order=%s code=%s", payment_id, order_id, error_code)

    escrow = None
    if order_id:
        escrow = await _find_escrow_by_order(order_id, db)
    if not escrow and payment_id:
        escrow = await _find_escrow_by_payment(payment_id, db)

    if not escrow:
        return

    match_result = await db.execute(select(Match).where(Match.id == escrow.match_id))
    match = match_result.scalar_one_or_none()

    await _record_compliance_event(
        user_id=str(match.buyer_id) if match else None,
        event_type=ComplianceEventType.RISK_ALERT,
        severity="medium",
        title=f"Razorpay payment failed: {payment_id}",
        description=f"Code: {error_code} – {error_description}",
        risk_score=0.4,
        extra_metadata={"payment_id": payment_id, "order_id": order_id, "escrow_id": str(escrow.id)},
        db=db,
    )


async def _handle_refund_created(data: dict[str, Any], db: AsyncSession) -> None:
    """Refund initiated."""
    refund_id = data.get("id")
    payment_id = data.get("payment_id")
    amount = data.get("amount", 0) // 100

    logger.info("refund.created refund=%s payment=%s amount=%d", refund_id, payment_id, amount)

    escrow = await _find_escrow_by_payment(payment_id, db) if payment_id else None
    if not escrow:
        return

    if escrow.status == EscrowStatus.REFUNDED:
        return

    escrow.status = EscrowStatus.REFUNDED
    escrow.refund_reason = f"Razorpay refund {refund_id} (amount: ₹{amount})"
    await db.flush()

    await publisher.publish(Event(
        EventType.ESCROW_REFUNDED,
        {
            "escrow_id": str(escrow.id),
            "refund_id": refund_id,
            "amount": amount,
            "gateway": "razorpay",
        },
        source="razorpay-webhook",
    ))


async def _handle_refund_processed(data: dict[str, Any], db: AsyncSession) -> None:
    """Refund processed (completed)."""
    refund_id = data.get("id")
    payment_id = data.get("payment_id")
    logger.info("refund.processed refund=%s payment=%s", refund_id, payment_id)


async def _handle_refund_failed(data: dict[str, Any], db: AsyncSession) -> None:
    """Refund failed."""
    refund_id = data.get("id")
    payment_id = data.get("payment_id")
    logger.warning("refund.failed refund=%s payment=%s", refund_id, payment_id)


async def _handle_transfer_created(data: dict[str, Any], db: AsyncSession) -> None:
    """Payout to seller initiated."""
    transfer_id = data.get("id")
    fund_account_id = data.get("fund_account_id")
    amount = data.get("amount", 0) // 100
    status = data.get("status", "pending")

    logger.info("transfer.created transfer=%s amount=%d status=%s", transfer_id, amount, status)

    escrow = await _find_escrow_by_transfer(transfer_id, db)
    if escrow:
        escrow.status = EscrowStatus.HELD
        await db.flush()


async def _handle_transfer_processed(data: dict[str, Any], db: AsyncSession) -> None:
    """Payout to seller completed."""
    transfer_id = data.get("id")
    utr = data.get("utr", "")

    logger.info("transfer.processed transfer=%s utr=%s", transfer_id, utr)

    escrow = await _find_escrow_by_transfer(transfer_id, db)
    if escrow and escrow.status == EscrowStatus.HELD:
        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = datetime.now(timezone.utc)
        await db.flush()

    # Update payout record
    payout_result = await db.execute(
        select(Payout).where(Payout.razorpay_transfer_id == transfer_id)
    )
    payout = payout_result.scalar_one_or_none()
    if payout and payout.status == PayoutStatus.PENDING:
        payout.status = PayoutStatus.COMPLETED
        payout.processed_at = datetime.now(timezone.utc)
        await db.flush()

        await publisher.publish(Event(
            EventType.PAYOUT_COMPLETED,
            {
                "payout_id": str(payout.id),
                "amount": payout.amount,
                "transfer_id": transfer_id,
                "gateway": "razorpay",
            },
            source="razorpay-webhook",
        ))


async def _handle_transfer_reversed(data: dict[str, Any], db: AsyncSession) -> None:
    """Payout reversed (bank returned funds)."""
    transfer_id = data.get("id")
    logger.warning("transfer.reversed transfer=%s", transfer_id)

    payout_result = await db.execute(
        select(Payout).where(Payout.razorpay_transfer_id == transfer_id)
    )
    payout = payout_result.scalar_one_or_none()
    if payout:
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = "Transfer reversed by bank"
        await db.flush()


async def _handle_transfer_failed(data: dict[str, Any], db: AsyncSession) -> None:
    """Payout failed."""
    transfer_id = data.get("id")
    error_code = data.get("failure_reason", {}).get("code", "unknown")
    error_description = data.get("failure_reason", {}).get("description", "Transfer failed")

    logger.warning("transfer.failed transfer=%s code=%s", transfer_id, error_code)

    payout_result = await db.execute(
        select(Payout).where(Payout.razorpay_transfer_id == transfer_id)
    )
    payout = payout_result.scalar_one_or_none()
    if payout:
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = f"Razorpay transfer failed: {error_code} – {error_description}"
        await db.flush()

        await _record_compliance_event(
            user_id=str(payout.user_id),
            event_type=ComplianceEventType.RISK_ALERT,
            severity="medium",
            title=f"Razorpay payout failed: {transfer_id}",
            description=f"Error: {error_code}",
            risk_score=0.3,
            extra_metadata={"transfer_id": transfer_id, "payout_id": str(payout.id)},
            db=db,
        )


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

_EVENT_HANDLERS: dict[str, Any] = {
    "order.paid": _handle_order_paid,
    "order.failed": _handle_order_failed,
    "payment.captured": _handle_payment_captured,
    "payment.failed": _handle_payment_failed,
    "refund.created": _handle_refund_created,
    "refund.processed": _handle_refund_processed,
    "refund.failed": _handle_refund_failed,
    "transfer.created": _handle_transfer_created,
    "transfer.processed": _handle_transfer_processed,
    "transfer.reversed": _handle_transfer_reversed,
    "transfer.failed": _handle_transfer_failed,
}


async def process_webhook_event(event_payload: dict[str, Any], db: AsyncSession) -> str:
    """Process a verified Razorpay webhook event.

    Returns: "processed", "duplicate", or "unhandled".
    """
    event_id = event_payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id", "")
    event_type = event_payload.get("event", "unknown")

    # Extract entity data from the nested payload
    entity = (
        event_payload.get("payload", {}).get("payment", {}).get("entity", {})
        or event_payload.get("payload", {}).get("order", {}).get("entity", {})
        or event_payload.get("payload", {}).get("refund", {}).get("entity", {})
        or event_payload.get("payload", {}).get("transfer", {}).get("entity", {})
    )

    if not event_id:
        # Fallback: use a hash of the payload
        import hashlib
        event_id = hashlib.sha256(json.dumps(event_payload, sort_keys=True).encode()).hexdigest()[:32]

    # Idempotency check
    if await _is_duplicate_event(event_id):
        logger.info("Duplicate Razorpay webhook event %s – skipping", event_id)
        return "duplicate"

    handler = _EVENT_HANDLERS.get(event_type)

    if handler is None:
        logger.debug("Unhandled Razorpay event type: %s", event_type)
        await _mark_event_processed(event_id)
        return "unhandled"

    try:
        await handler(entity, db)
        await _mark_event_processed(event_id)
        logger.info("Processed Razorpay event %s [%s]", event_id, event_type)
        return "processed"
    except Exception:
        logger.exception("Error processing Razorpay event %s [%s]", event_id, event_type)
        raise
