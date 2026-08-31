"""Razorpay payment router — handles order creation, verification, refunds, and webhooks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from services.payment.razorpay_service import (
    RazorpayPaymentError,
    create_fund_account,
    create_contact,
    create_order,
    create_payout,
    create_refund,
    create_subscription_order,
    fetch_order,
    fetch_payment,
    verify_and_confirm,
    verify_payment_signature,
)
from services.payment.razorpay_webhooks import (
    process_webhook_event,
    verify_razorpay_signature,
)

router = APIRouter(prefix="/razorpay")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in INR (e.g., 499.00)")
    currency: str = Field(default="INR", description="Currency code")
    receipt: str | None = None
    match_id: str | None = None
    notes: dict[str, str] | None = None


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int  # paise
    currency: str
    key_id: str  # Razorpay key ID for frontend checkout
    receipt: str | None = None
    escrow_id: str | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    escrow_id: str | None = None


class VerifyPaymentResponse(BaseModel):
    verified: bool
    order_id: str
    payment_id: str
    amount: float
    currency: str
    status: str
    method: str
    message: str


class RefundRequest(BaseModel):
    payment_id: str
    amount: float | None = None  # None = full refund
    notes: dict[str, str] | None = None


class RefundResponse(BaseModel):
    refund_id: str
    payment_id: str
    amount: float
    status: str
    message: str


class PayoutRequest(BaseModel):
    user_id: str
    amount: float = Field(..., gt=0, description="Amount in INR")
    mode: str = Field(default="NEFT", description="NEFT, RTGS, IMPS, or UPI")
    notes: dict[str, str] | None = None


class PayoutResponse(BaseModel):
    transfer_id: str
    amount: float
    status: str
    message: str


class EscrowResponse(BaseModel):
    id: str
    match_id: str
    status: str
    amount: float
    platform_fee: float
    seller_payout: float
    fee_percentage: float
    currency: str
    payment_gateway: str
    razorpay_order_id: str | None
    razorpay_payment_id: str | None
    funded_at: str | None
    released_at: str | None
    created_at: str


class PaymentHistoryItem(BaseModel):
    id: str
    payment_gateway: str
    status: str
    amount: float
    currency: str
    created_at: str


# ---------------------------------------------------------------------------
# Order creation
# ---------------------------------------------------------------------------

@router.post("/create-order", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_razorpay_order(
    body: CreateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay order for a payment.

    If a match_id is provided, creates/uses the escrow for that match.
    Returns the order details needed by the frontend Razorpay checkout.
    """
    escrow_id = None

    # If linked to a match, create or find escrow
    if body.match_id:
        match_result = await db.execute(select(Match).where(Match.id == body.match_id))
        match = match_result.scalar_one_or_none()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match.buyer_id != user.id:
            raise HTTPException(status_code=403, detail="Only the buyer can initiate payment")

        # Check for existing escrow
        existing = await db.execute(
            select(EscrowTransaction).where(EscrowTransaction.match_id == match.id)
        )
        escrow = existing.scalar_one_or_none()

        if not escrow:
            # Create escrow
            amount = body.amount
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
                currency="INR",
                payment_gateway="razorpay",
            )
            db.add(escrow)
            await db.flush()

            await publisher.publish(Event(EventType.ESCROW_CREATED, {
                "escrow_id": str(escrow.id),
                "match_id": str(match.id),
                "amount": amount,
                "gateway": "razorpay",
            }, source="api-gateway"))

        elif escrow.status not in (EscrowStatus.CREATED,):
            raise HTTPException(
                status_code=400,
                detail=f"Escrow already in {escrow.status} status",
            )

        # Use escrow amount
        body.amount = escrow.amount
        escrow_id = str(escrow.id)

    # Create Razorpay order
    notes = body.notes or {}
    notes["vault_user_id"] = str(user.id)
    if escrow_id:
        notes["escrow_id"] = escrow_id

    try:
        order = await create_order(
            amount_rupees=body.amount,
            currency=body.currency,
            receipt=body.receipt,
            notes=notes,
        )
    except RazorpayPaymentError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # Link order to escrow
    if escrow_id:
        escrow_result = await db.execute(
            select(EscrowTransaction).where(EscrowTransaction.id == escrow_id)
        )
        escrow = escrow_result.scalar_one_or_none()
        if escrow:
            escrow.razorpay_order_id = order.order_id
            await db.flush()

    return CreateOrderResponse(
        order_id=order.order_id,
        amount=order.amount,
        currency=order.currency,
        key_id=settings.RAZORPAY_KEY_ID,
        receipt=order.receipt,
        escrow_id=escrow_id,
    )


# ---------------------------------------------------------------------------
# Payment verification
# ---------------------------------------------------------------------------

@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_razorpay_payment(
    body: VerifyPaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a Razorpay payment and confirm the transaction.

    This is the POST-CHECKOUT verification endpoint. The frontend calls
    this after Razorpay returns the payment details to the callback.
    """
    result = await verify_and_confirm(
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_signature=body.razorpay_signature,
    )

    if not result.verified:
        return VerifyPaymentResponse(
            verified=False,
            order_id=body.razorpay_order_id,
            payment_id=body.razorpay_payment_id,
            amount=0,
            currency="INR",
            status="verification_failed",
            method="unknown",
            message="Payment signature verification failed. Possible tampering.",
        )

    # Update escrow if linked
    escrow_id = body.escrow_id
    if not escrow_id:
        # Try to find by order ID
        escrow_result = await db.execute(
            select(EscrowTransaction).where(EscrowTransaction.razorpay_order_id == body.razorpay_order_id)
        )
        escrow = escrow_result.scalar_one_or_none()
        if escrow:
            escrow_id = str(escrow.id)

    if escrow_id:
        escrow_result = await db.execute(
            select(EscrowTransaction).where(EscrowTransaction.id == escrow_id)
        )
        escrow = escrow_result.scalar_one_or_none()
        if escrow and escrow.status == EscrowStatus.CREATED:
            escrow.razorpay_payment_id = result.payment_id
            if result.status == "captured":
                escrow.status = EscrowStatus.FUNDED
                escrow.funded_at = datetime.now(timezone.utc)
            await db.flush()

            await publisher.publish(Event(EventType.ESCROW_FUNDED, {
                "escrow_id": str(escrow.id),
                "order_id": body.razorpay_order_id,
                "payment_id": result.payment_id,
                "amount": escrow.amount,
                "gateway": "razorpay",
            }, source="api-gateway"))

    return VerifyPaymentResponse(
        verified=True,
        order_id=result.order_id,
        payment_id=result.payment_id,
        amount=result.amount / 100,  # Convert paise to INR for display
        currency=result.currency,
        status=result.status,
        method=result.method,
        message="Payment verified successfully",
    )


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------

@router.post("/refund", response_model=RefundResponse)
async def refund_razorpay_payment(
    body: RefundRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a full or partial refund."""
    # Find the escrow linked to this payment
    escrow_result = await db.execute(
        select(EscrowTransaction).where(EscrowTransaction.razorpay_payment_id == body.payment_id)
    )
    escrow = escrow_result.scalar_one_or_none()

    if not escrow:
        raise HTTPException(status_code=404, detail="No escrow found for this payment")

    if escrow.status not in (EscrowStatus.FUNDED, EscrowStatus.HELD):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund escrow in {escrow.status} status",
        )

    try:
        refund = await create_refund(
            payment_id=body.payment_id,
            amount_rupees=body.amount,
            notes=body.notes,
        )
    except RazorpayPaymentError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Update escrow status
    escrow.status = EscrowStatus.REFUNDED
    escrow.refund_reason = f"Razorpay refund {refund.refund_id}"
    await db.flush()

    await publisher.publish(Event(EventType.ESCROW_REFUNDED, {
        "escrow_id": str(escrow.id),
        "refund_id": refund.refund_id,
        "amount": refund.amount / 100,
        "gateway": "razorpay",
    }, source="api-gateway"))

    return RefundResponse(
        refund_id=refund.refund_id,
        payment_id=refund.payment_id,
        amount=refund.amount / 100,
        status=refund.status,
        message="Refund initiated successfully",
    )


# ---------------------------------------------------------------------------
# Payouts
# ---------------------------------------------------------------------------

@router.post("/payout", response_model=PayoutResponse)
async def create_razorpay_payout(
    body: PayoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a payout to a seller's bank account."""
    seller_result = await db.execute(select(User).where(User.id == body.user_id))
    seller = seller_result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Create Razorpay contact if not exists
    if not seller.razorpay_contact_id:
        try:
            contact = await create_contact(
                name=seller.display_name,
                email=seller.email,
                contact_type="vendor",
                notes={"vault_user_id": str(seller.id)},
            )
            seller.razorpay_contact_id = contact["id"]
            await db.flush()
        except RazorpayPaymentError as e:
            raise HTTPException(status_code=502, detail=f"Failed to create Razorpay contact: {e}")

    if not seller.razorpay_fund_account_id:
        raise HTTPException(
            status_code=400,
            detail="Seller has no Razorpay fund account configured. Please add bank details.",
        )

    try:
        payout = await create_payout(
            fund_account_id=seller.razorpay_fund_account_id,
            amount_rupees=body.amount,
            mode=body.mode,
            purpose="payout",
            notes=body.notes,
        )
    except RazorpayPaymentError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Create payout record
    payout_record = Payout(
        id=uuid.uuid4(),
        user_id=body.user_id,
        razorpay_transfer_id=payout.transfer_id,
        status=PayoutStatus.PENDING,
        amount=body.amount,
        currency="INR",
        payout_method="razorpay",
        tax_year=datetime.now(timezone.utc).year,
    )
    db.add(payout_record)
    await db.flush()

    return PayoutResponse(
        transfer_id=payout.transfer_id,
        amount=body.amount,
        status=payout.status,
        message="Payout initiated",
    )


# ---------------------------------------------------------------------------
# Payment history
# ---------------------------------------------------------------------------

@router.get("/payment-history", response_model=list[PaymentHistoryItem])
async def get_razorpay_payment_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment history for the current user via Razorpay."""
    result = await db.execute(
        select(EscrowTransaction)
        .where(EscrowTransaction.payment_gateway == "razorpay")
        .order_by(EscrowTransaction.created_at.desc())
        .limit(50)
    )
    escrows = result.scalars().all()

    history = []
    for escrow in escrows:
        # Only include escrows where user is buyer or seller
        match_result = await db.execute(select(Match).where(Match.id == escrow.match_id))
        match = match_result.scalar_one_or_none()
        if match and (match.buyer_id == user.id or match.seller_id == user.id):
            history.append(PaymentHistoryItem(
                id=str(escrow.id),
                payment_gateway="razorpay",
                status=escrow.status,
                amount=escrow.amount,
                currency=escrow.currency,
                created_at=escrow.created_at.isoformat() if escrow.created_at else "",
            ))

    return history


# ---------------------------------------------------------------------------
# Escrow details
# ---------------------------------------------------------------------------

@router.get("/escrows/{escrow_id}", response_model=EscrowResponse)
async def get_razorpay_escrow(
    escrow_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get escrow details for a Razorpay transaction."""
    result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")

    return EscrowResponse(
        id=str(escrow.id),
        match_id=str(escrow.match_id),
        status=escrow.status,
        amount=escrow.amount,
        platform_fee=escrow.platform_fee,
        seller_payout=escrow.seller_payout,
        fee_percentage=escrow.fee_percentage,
        currency=escrow.currency,
        payment_gateway=escrow.payment_gateway,
        razorpay_order_id=escrow.razorpay_order_id,
        razorpay_payment_id=escrow.razorpay_payment_id,
        funded_at=escrow.funded_at.isoformat() if escrow.funded_at else None,
        released_at=escrow.released_at.isoformat() if escrow.released_at else None,
        created_at=escrow.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhook events.

    Signature verification is always enforced (even in demo mode).
    Razorpay expects a 200 response within 30s.
    """
    payload = await request.body()
    sig_header = request.headers.get("X-Razorpay-Signature", "")

    event = verify_razorpay_signature(payload, sig_header)
    if event is None:
        logger.warning("Razorpay webhook: signature verification failed")
        return {"status": "ignored", "reason": "invalid_signature"}

    event_type = event.get("event", "unknown")
    logger.info("Razorpay webhook received: %s", event_type)

    # Demo mode shortcut
    if settings.DEMO_MODE:
        logger.info("Demo mode: accepting webhook without processing")
        return {"status": "ok", "demo": True, "event_type": event_type}

    # Route to handler
    try:
        result = await process_webhook_event(event, db)
    except Exception:
        logger.exception("Unhandled error processing Razorpay webhook")
        return {"status": "error"}

    return {"status": "ok", "processing": result, "event_type": event_type}


import logging
logger = logging.getLogger(__name__)
