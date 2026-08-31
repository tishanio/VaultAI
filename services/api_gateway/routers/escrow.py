from __future__ import annotations

"""Escrow router — Stripe Connect payment and escrow management."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from vault.config import settings
from vault.db.models import (
    EscrowStatus,
    EscrowTransaction,
    Match,
    MatchStatus,
    Payout,
    PayoutStatus,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventType, publisher
from services.api_gateway.routers.auth import get_current_user
from services.api_gateway.stripe_webhooks import (
    process_webhook_event,
    verify_stripe_signature,
)

router = APIRouter(prefix="/escrow")

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class EscrowResponse(BaseModel):
    id: str
    match_id: str
    status: str
    amount: float
    platform_fee: float
    seller_payout: float
    fee_percentage: float
    currency: str
    stripe_payment_intent_id: Optional[str]
    funded_at: Optional[str]
    released_at: Optional[str]
    created_at: str


class CreateEscrowResponse(BaseModel):
    escrow_id: str
    client_secret: str
    payment_intent_id: str
    amount: float


@router.post("/matches/{match_id}/escrow", response_model=CreateEscrowResponse, status_code=status.HTTP_201_CREATED)
async def create_escrow(
    match_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an escrow transaction for an accepted match."""
    match_result = await db.execute(select(Match).where(Match.id == match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.buyer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the buyer can fund escrow")
    if match.status != MatchStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match must be accepted before creating escrow")

    # Check for existing escrow
    existing = await db.execute(select(EscrowTransaction).where(EscrowTransaction.match_id == match.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Escrow already exists for this match")

    # Calculate fees
    amount = match.proposed_price
    fee_pct = settings.PLATFORM_FEE_PERCENTAGE / 100.0
    platform_fee = round(amount * fee_pct, 2)
    seller_payout = round(amount - platform_fee, 2)

    escrow = EscrowTransaction(
        id=uuid.uuid4(),
        match_id=match.id,
        status=EscrowStatus.CREATED,
        amount=amount,
        platform_fee=platform_fee,
        seller_payout=seller_payout,
        fee_percentage=settings.PLATFORM_FEE_PERCENTAGE,
        currency="USD",
    )
    db.add(escrow)

    # Create Stripe PaymentIntent
    if not settings.DEMO_MODE:
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # cents
                currency="usd",
                customer=user.stripe_customer_id,
                capture_method="manual",  # Manual capture for escrow
                metadata={"escrow_id": str(escrow.id), "match_id": str(match.id)},
            )
            escrow.stripe_payment_intent_id = intent.id
            client_secret = intent.client_secret
        except stripe.StripeError as e:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e.user_message))
    else:
        # Demo mode: simulate payment
        client_secret = f"demo_secret_{uuid.uuid4().hex[:16]}"
        escrow.stripe_payment_intent_id = f"pi_demo_{uuid.uuid4().hex[:16]}"

    await db.flush()

    await publisher.publish(Event(EventType.ESCROW_CREATED, {
        "escrow_id": str(escrow.id),
        "match_id": str(match.id),
        "amount": amount,
    }, source="api-gateway"))

    return CreateEscrowResponse(
        escrow_id=str(escrow.id),
        client_secret=client_secret,
        payment_intent_id=escrow.stripe_payment_intent_id or "",
        amount=amount,
    )


@router.post("/escrows/{escrow_id}/fund")
async def fund_escrow(
    escrow_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fund the escrow (capture payment). Called after Stripe confirms payment."""
    result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")

    if not settings.DEMO_MODE and escrow.stripe_payment_intent_id:
        try:
            stripe.PaymentIntent.capture(escrow.stripe_payment_intent_id)
        except stripe.StripeError as e:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e.user_message))

    from datetime import datetime, timezone
    escrow.status = EscrowStatus.FUNDED
    escrow.funded_at = datetime.now(timezone.utc)
    await db.flush()

    await publisher.publish(Event(EventType.ESCROW_FUNDED, {"escrow_id": str(escrow.id)}, source="api-gateway"))

    return {"message": "Escrow funded successfully", "status": "funded"}


@router.post("/escrows/{escrow_id}/release")
async def release_escrow(
    escrow_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Release escrow to seller (seller confirms delivery)."""
    result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")

    match_result = await db.execute(select(Match).where(Match.id == escrow.match_id))
    match = match_result.scalar_one_or_none()
    if not match or match.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the seller can release escrow")
    if escrow.status != EscrowStatus.FUNDED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot release escrow in {escrow.status} status")

    if not settings.DEMO_MODE and escrow.stripe_transfer_id:
        try:
            seller_result = await db.execute(select(User).where(User.id == match.seller_id))
            seller = seller_result.scalar_one_or_none()
            if seller and seller.stripe_connect_account_id:
                stripe.Transfer.create(
                    amount=int(escrow.seller_payout * 100),
                    currency="usd",
                    destination=seller.stripe_connect_account_id,
                    metadata={"escrow_id": str(escrow.id)},
                )
        except stripe.StripeError as e:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e.user_message))

    from datetime import datetime, timezone
    escrow.status = EscrowStatus.RELEASED
    escrow.released_at = datetime.now(timezone.utc)
    match.status = MatchStatus.COMPLETED

    # Create payout record
    payout = Payout(
        id=uuid.uuid4(),
        user_id=match.seller_id,
        status=PayoutStatus.COMPLETED if settings.DEMO_MODE else PayoutStatus.PENDING,
        amount=escrow.seller_payout,
        currency="USD",
        payout_method="stripe_connect",
    )
    db.add(payout)

    await db.flush()

    await publisher.publish(Event(EventType.ESCROW_RELEASED, {
        "escrow_id": str(escrow.id),
        "seller_id": str(match.seller_id),
        "amount": escrow.seller_payout,
    }, source="api-gateway"))

    return {"message": "Escrow released to seller", "amount": escrow.seller_payout}


@router.post("/escrows/{escrow_id}/refund")
async def refund_escrow(
    escrow_id: str,
    reason: str = "Buyer requested refund",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refund escrow to buyer."""
    result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")

    if escrow.status not in (EscrowStatus.FUNDED, EscrowStatus.HELD):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot refund escrow in {escrow.status} status")

    if not settings.DEMO_MODE and escrow.stripe_payment_intent_id:
        try:
            stripe.Refund.create(payment_intent=escrow.stripe_payment_intent_id)
        except stripe.StripeError as e:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e.user_message))

    from datetime import datetime, timezone
    escrow.status = EscrowStatus.REFUNDED
    escrow.refund_reason = reason
    await db.flush()

    await publisher.publish(Event(EventType.ESCROW_REFUNDED, {"escrow_id": str(escrow.id), "reason": reason}, source="api-gateway"))

    return {"message": "Escrow refunded"}


@router.get("/escrows/{escrow_id}", response_model=EscrowResponse)
async def get_escrow(
    escrow_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get escrow details."""
    result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")

    return EscrowResponse(
        id=str(escrow.id),
        match_id=str(escrow.match_id),
        status=escrow.status,
        amount=escrow.amount,
        platform_fee=escrow.platform_fee,
        seller_payout=escrow.seller_payout,
        fee_percentage=escrow.fee_percentage,
        currency=escrow.currency,
        stripe_payment_intent_id=escrow.stripe_payment_intent_id,
        funded_at=escrow.funded_at.isoformat() if escrow.funded_at else None,
        released_at=escrow.released_at.isoformat() if escrow.released_at else None,
        created_at=escrow.created_at.isoformat(),
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events.

    Signature verification is always enforced (even in demo mode) so that
    the endpoint behaves identically in staging and production.  If the
    webhook secret is not configured we skip verification with a warning
    and return early.

    Stripe expects a 200 response within 30 s, so we catch and log errors
    instead of letting them bubble up as 5xx.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    # --- Verify signature ---
    event = verify_stripe_signature(payload, sig_header)
    if event is None:
        logger.warning("Stripe webhook: signature verification failed or invalid payload")
        # Return 200 so Stripe doesn't retry; the event is logged.
        return {"status": "ignored", "reason": "invalid_signature"}

    event_type = event.get("type", "unknown")
    event_id = event.get("id", "unknown")
    logger.info("Stripe webhook received: %s [%s]", event_type, event_id)

    # --- Demo mode shortcut ---
    if settings.DEMO_MODE:
        logger.info("Demo mode: accepting webhook without processing")
        return {"status": "ok", "demo": True, "event_type": event_type}

    # --- Route to handler ---
    try:
        result = await process_webhook_event(event, db)
    except Exception:
        logger.exception("Unhandled error processing Stripe webhook %s", event_id)
        # Return 200 so Stripe doesn't keep retrying; error is logged.
        return {"status": "error", "event_id": event_id}

    return {"status": "ok", "processing": result, "event_type": event_type}
