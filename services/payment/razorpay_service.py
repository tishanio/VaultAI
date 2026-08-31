"""Razorpay payment service for Vault.

Provides:
  - Order creation (standard & subscription)
  - Payment verification with HMAC-SHA256 signature
  - Full & partial refunds
  - Payouts to sellers via fund accounts
  - Idempotent operations (order IDs are unique, verification is stateless)
  - Structured logging for every payment action

All amounts are in paise (INR) internally; callers pass INR rupees and we
multiply by 100, matching Razorpay's API convention.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import razorpay
from razorpay.errors import (
    BadRequestError,
    GatewayError,
    ServerError,
)

from vault.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: razorpay.Client | None = None


def get_client() -> razorpay.Client:
    """Return (and lazily create) the Razorpay API client."""
    global _client
    if _client is None:
        _client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        _client.set_app_details({"title": "Vault", "version": settings.APP_VERSION})
    return _client


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RazorpayOrder:
    """Represents a created Razorpay order."""
    order_id: str
    amount: int  # paise
    currency: str
    receipt: str
    status: str
    created_at: int
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RazorpayPaymentVerification:
    """Result of verifying a Razorpay payment."""
    verified: bool
    order_id: str
    payment_id: str
    amount: int  # paise
    currency: str
    status: str
    method: str  # card, upi, netbanking, wallet, emi
    error_description: str = ""


@dataclass
class RazorpayRefund:
    """Represents a Razorpay refund."""
    refund_id: str
    payment_id: str
    amount: int  # paise
    status: str  # pending, processed, failed
    speed_processed: str = ""
    created_at: int = 0


@dataclass
class RazorpayPayout:
    """Represents a payout to a seller's bank account."""
    transfer_id: str
    account_number: str
    fund_account_id: str
    amount: int  # paise
    currency: str
    status: str  # pending, processing, processed, reversed, cancelled
    mode: str = "NEFT"
    purpose: str = "payout"
    utr: str = ""
    created_at: int = 0


# ---------------------------------------------------------------------------
# Order Management
# ---------------------------------------------------------------------------

async def create_order(
    amount_rupees: float,
    currency: str = "INR",
    receipt: str | None = None,
    notes: dict[str, str] | None = None,
) -> RazorpayOrder:
    """Create a Razorpay order for a one-time payment.

    Args:
        amount_rupees: Amount in INR (e.g., 499.00).
        currency: Currency code (default INR).
        receipt: Unique receipt string for idempotency.
        notes: Arbitrary key-value notes attached to the order.

    Returns:
        RazorpayOrder with order_id and other details.

    Raises:
        RazorpayPaymentError: On API errors.
    """
    if receipt is None:
        receipt = f"vault_{uuid.uuid4().hex[:16]}"

    amount_paise = int(amount_rupees * 100)
    notes = notes or {}

    # Demo mode: simulate order creation without Razorpay credentials
    if settings.DEMO_MODE or not settings.RAZORPAY_KEY_ID:
        order_id = f"order_demo_{uuid.uuid4().hex[:16]}"
        logger.info("DEMO: Simulated Razorpay order %s for ₹%.2f", order_id, amount_rupees)
        return RazorpayOrder(
            order_id=order_id,
            amount=amount_paise,
            currency=currency,
            receipt=receipt,
            status="created",
            created_at=int(time.time()),
            meta={**notes, "demo": True},
        )

    try:
        client = get_client()
        response = client.order.create({
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": notes,
        })

        order = RazorpayOrder(
            order_id=response["id"],
            amount=response["amount"],
            currency=response["currency"],
            receipt=response.get("receipt", receipt),
            status=response.get("status", "created"),
            created_at=response.get("created_at", int(time.time())),
            meta=notes,
        )

        logger.info(
            "Razorpay order created: order_id=%s amount=%d currency=%s receipt=%s",
            order.order_id, order.amount, order.currency, order.receipt,
        )
        return order

    except BadRequestError as e:
        logger.error("Razorpay order creation failed (bad request): %s", e)
        raise RazorpayPaymentError(f"Invalid payment request: {e}") from e
    except GatewayError as e:
        logger.error("Razorpay order creation failed (gateway): %s", e)
        raise RazorpayPaymentError(f"Payment gateway error: {e}") from e
    except ServerError as e:
        logger.error("Razorpay order creation failed (server): %s", e)
        raise RazorpayPaymentError(f"Payment server error: {e}") from e


async def create_subscription_order(
    amount_rupees: float,
    currency: str = "INR",
    customer_id: str | None = None,
    receipt: str | None = None,
    notes: dict[str, str] | None = None,
) -> RazorpayOrder:
    """Create an order for a subscription payment.

    This wraps create_order with subscription-specific metadata.
    """
    notes = notes or {}
    if customer_id:
        notes["customer_id"] = customer_id

    return await create_order(
        amount_rupees=amount_rupees,
        currency=currency,
        receipt=receipt or f"vault_sub_{uuid.uuid4().hex[:16]}",
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Payment Verification
# ---------------------------------------------------------------------------

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """Verify the Razorpay payment signature using HMAC-SHA256.

    This is the PRIMARY security check. Razorpay signs the response with
    order_id|payment_id using the key secret. We recompute and compare.

    Args:
        razorpay_order_id: The order ID from the checkout.
        razorpay_payment_id: The payment ID from the checkout.
        razorpay_signature: The signature from the checkout callback.

    Returns:
        True if signature is valid, False otherwise.
    """
    try:
        client = get_client()
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        client.utility.verify_payment_signature(params_dict)
        logger.info(
            "Razorpay payment signature verified: order=%s payment=%s",
            razorpay_order_id, razorpay_payment_id,
        )
        return True
    except Exception as e:
        logger.warning(
            "Razorpay payment signature verification failed: order=%s payment=%s error=%s",
            razorpay_order_id, razorpay_payment_id, e,
        )
        return False


async def fetch_payment(payment_id: str) -> dict[str, Any]:
    """Fetch payment details from Razorpay API."""
    try:
        client = get_client()
        payment = client.payment.fetch(payment_id)
        logger.info("Razorpay payment fetched: payment_id=%s status=%s", payment_id, payment.get("status"))
        return payment
    except Exception as e:
        logger.error("Failed to fetch Razorpay payment %s: %s", payment_id, e)
        raise RazorpayPaymentError(f"Failed to fetch payment: {e}") from e


async def fetch_order(order_id: str) -> dict[str, Any]:
    """Fetch order details from Razorpay API."""
    try:
        client = get_client()
        order = client.order.fetch(order_id)
        return order
    except Exception as e:
        logger.error("Failed to fetch Razorpay order %s: %s", order_id, e)
        raise RazorpayPaymentError(f"Failed to fetch order: {e}") from e


async def verify_and_confirm(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> RazorpayPaymentVerification:
    """Verify signature AND fetch payment details for full confirmation.

    Returns a RazorpayPaymentVerification with all payment info.
    """
    # Demo mode: simulate successful verification
    if settings.DEMO_MODE or not settings.RAZORPAY_KEY_SECRET:
        logger.info("DEMO: Simulated payment verification for order=%s payment=%s", razorpay_order_id, razorpay_payment_id)
        return RazorpayPaymentVerification(
            verified=True,
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id or f"pay_demo_{uuid.uuid4().hex[:12]}",
            amount=49900,  # ₹499 in paise
            currency="INR",
            status="captured",
            method="upi",
        )

    verified = verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)

    if not verified:
        return RazorpayPaymentVerification(
            verified=False,
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            amount=0,
            currency="INR",
            status="verification_failed",
            method="unknown",
            error_description="Payment signature verification failed",
        )

    payment = await fetch_payment(razorpay_payment_id)

    return RazorpayPaymentVerification(
        verified=True,
        order_id=razorpay_order_id,
        payment_id=razorpay_payment_id,
        amount=payment.get("amount", 0),
        currency=payment.get("currency", "INR"),
        status=payment.get("status", "unknown"),
        method=payment.get("method", "unknown"),
    )


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------

async def create_refund(
    payment_id: str,
    amount_rupees: float | None = None,
    notes: dict[str, str] | None = None,
) -> RazorpayRefund:
    """Create a full or partial refund.

    Args:
        payment_id: The Razorpay payment ID to refund.
        amount_rupees: Partial refund amount in INR. None = full refund.
        notes: Arbitrary notes attached to the refund.

    Returns:
        RazorpayRefund with refund details.
    """
    refund_body: dict[str, Any] = {}
    if amount_rupees is not None:
        refund_body["amount"] = int(amount_rupees * 100)
    if notes:
        refund_body["notes"] = notes

    try:
        client = get_client()
        response = client.payment.refund(payment_id, refund_body)

        refund = RazorpayRefund(
            refund_id=response["id"],
            payment_id=response.get("payment_id", payment_id),
            amount=response.get("amount", 0),
            status=response.get("status", "pending"),
            speed_processed=response.get("speed_processed", ""),
            created_at=response.get("created_at", int(time.time())),
        )

        logger.info(
            "Razorpay refund created: refund_id=%s payment=%s amount=%d status=%s",
            refund.refund_id, refund.payment_id, refund.amount, refund.status,
        )
        return refund

    except Exception as e:
        logger.error("Razorpay refund failed for payment %s: %s", payment_id, e)
        raise RazorpayPaymentError(f"Refund failed: {e}") from e


async def fetch_refund(refund_id: str) -> dict[str, Any]:
    """Fetch refund details from Razorpay."""
    try:
        client = get_client()
        return client.refund.fetch(refund_id)
    except Exception as e:
        logger.error("Failed to fetch Razorpay refund %s: %s", refund_id, e)
        raise RazorpayPaymentError(f"Failed to fetch refund: {e}") from e


# ---------------------------------------------------------------------------
# Payouts (Transfers to sellers)
# ---------------------------------------------------------------------------

async def create_fund_account(
    contact_id: str,
    account_type: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a fund account for payouts (bank account or VPA/UPI)."""
    try:
        client = get_client()
        fund_account = client.fund_account.create({
            "contact_id": contact_id,
            "account_type": account_type,
            **kwargs,
        })
        logger.info("Razorpay fund account created: id=%s contact=%s", fund_account["id"], contact_id)
        return fund_account
    except Exception as e:
        logger.error("Failed to create Razorpay fund account: %s", e)
        raise RazorpayPaymentError(f"Failed to create fund account: {e}") from e


async def create_contact(
    name: str,
    email: str | None = None,
    phone: str | None = None,
    contact_type: str = "customer",
    notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a Razorpay contact for payouts."""
    try:
        client = get_client()
        body: dict[str, Any] = {
            "name": name,
            "type": contact_type,
        }
        if email:
            body["email"] = email
        if phone:
            body["contact"] = phone
        if notes:
            body["notes"] = notes

        contact = client.contact.create(body)
        logger.info("Razorpay contact created: id=%s name=%s", contact["id"], name)
        return contact
    except Exception as e:
        logger.error("Failed to create Razorpay contact: %s", e)
        raise RazorpayPaymentError(f"Failed to create contact: {e}") from e


async def create_payout(
    fund_account_id: str,
    amount_rupees: float,
    currency: str = "INR",
    mode: str = "NEFT",
    purpose: str = "payout",
    reference_id: str | None = None,
    notes: dict[str, str] | None = None,
) -> RazorpayPayout:
    """Create a payout to a seller's bank account via Razorpay.

    Args:
        fund_account_id: The seller's fund account ID.
        amount_rupees: Amount in INR.
        currency: Currency code.
        mode: NEFT, RTGS, IMPS, or UPI.
        purpose: payout, salary, refund, cashback, expense, loan, advance.
        reference_id: Unique reference for idempotency.
        notes: Arbitrary notes.

    Returns:
        RazorpayPayout with transfer details.
    """
    if reference_id is None:
        reference_id = f"payout_{uuid.uuid4().hex[:16]}"

    body: dict[str, Any] = {
        "fund_account_id": fund_account_id,
        "amount": int(amount_rupees * 100),
        "currency": currency,
        "mode": mode,
        "purpose": purpose,
        "reference_id": reference_id,
    }
    if notes:
        body["notes"] = notes

    try:
        client = get_client()
        response = client.transfer.create(body)

        payout = RazorpayPayout(
            transfer_id=response["id"],
            account_number=response.get("account_number", ""),
            fund_account_id=response.get("fund_account_id", fund_account_id),
            amount=response.get("amount", 0),
            currency=response.get("currency", currency),
            status=response.get("status", "pending"),
            mode=response.get("mode", mode),
            purpose=response.get("purpose", purpose),
            utr=response.get("utr", ""),
            created_at=response.get("created_at", int(time.time())),
        )

        logger.info(
            "Razorpay payout created: transfer_id=%s amount=%d status=%s",
            payout.transfer_id, payout.amount, payout.status,
        )
        return payout

    except Exception as e:
        logger.error("Razorpay payout failed: %s", e)
        raise RazorpayPaymentError(f"Payout failed: {e}") from e


# ---------------------------------------------------------------------------
# Webhook Signature Verification
# ---------------------------------------------------------------------------

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str | None = None,
) -> bool:
    """Verify Razorpay webhook signature.

    Razorpay computes HMAC-SHA256(secret, body) and sends it as
    X-Razorpay-Signature header.
    """
    secret = secret or settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        logger.warning("RAZORPAY_WEBHOOK_SECRET not configured – skipping verification")
        return True  # Allow in development

    try:
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error("Webhook signature verification error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RazorpayPaymentError(Exception):
    """Raised when a Razorpay API call fails."""
    pass
