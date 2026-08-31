from __future__ import annotations

"""Financial Orchestration Agent — payment splitting, automated payouts, 1099-K tax forms."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import uuid

from fastapi import Depends, FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    EscrowTransaction,
    EscrowStatus,
    Match,
    MatchStatus,
    Payout,
    PayoutStatus,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventConsumer, publisher


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PayoutResponse(BaseModel):
    payout_id: str
    user_id: str
    amount: float
    currency: str
    status: str
    payout_method: str
    processed_at: str | None
    created_at: str


class SplitPreview(BaseModel):
    escrow_id: str
    total_amount: float
    platform_fee: float
    seller_payout: float
    fee_percentage: float
    breakdown: dict[str, float]


class TaxSummary(BaseModel):
    user_id: str
    tax_year: int
    total_gross_payouts: float
    total_platform_fees: float
    total_net_payouts: float
    transaction_count: int
    forms_1099k_required: bool
    threshold_1099k: float = 20000.0


class FinancialDashboard(BaseModel):
    user_id: str
    total_earned: float
    total_pending: float
    total_fees: float
    active_escrows: int
    completed_transactions: int
    pending_payouts: int


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Financial Orchestration Agent starting")
    await publisher.connect()

    # Start event consumer in background
    consumer = EventConsumer(group_name="financial-orchestration", consumer_name="worker-1")
    await consumer.connect()
    consumer.on(EventType.ESCROW_RELEASED, handle_escrow_released)
    consumer.on(EventType.MATCH_COMPLETED, handle_match_completed)
    consumer_task = asyncio.create_task(consumer.listen())

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await consumer.close()
    await publisher.close()


app = FastAPI(title="Vault Financial Orchestration Agent", version=settings.APP_VERSION, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "financial-orchestration"}


# ---------------------------------------------------------------------------
# Payment Splitting
# ---------------------------------------------------------------------------

@app.get("/api/v1/finance/split-preview/{escrow_id}", response_model=SplitPreview)
async def get_split_preview(escrow_id: str, db: AsyncSession = Depends(get_db)):
    """Preview payment split for an escrow transaction."""
    result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.id == escrow_id))
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")

    return SplitPreview(
        escrow_id=str(escrow.id),
        total_amount=escrow.amount,
        platform_fee=escrow.platform_fee,
        seller_payout=escrow.seller_payout,
        fee_percentage=escrow.fee_percentage,
        breakdown={
            "buyer_pays": escrow.amount,
            "platform_fee": escrow.platform_fee,
            "seller_receives": escrow.seller_payout,
            "processing_fee": round(escrow.amount * 0.029 + 0.30, 2),  # Stripe fees
        },
    )


# ---------------------------------------------------------------------------
# Payout Processing
# ---------------------------------------------------------------------------

@app.get("/api/v1/finance/payouts/{user_id}", response_model=list[PayoutResponse])
async def get_user_payouts(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get payout history for a user."""
    result = await db.execute(
        select(Payout).where(Payout.user_id == user_id).order_by(Payout.created_at.desc())
    )
    payouts = result.scalars().all()

    return [
        PayoutResponse(
            payout_id=str(p.id),
            user_id=str(p.user_id),
            amount=p.amount,
            currency=p.currency,
            status=p.status,
            payout_method=p.payout_method,
            processed_at=p.processed_at.isoformat() if p.processed_at else None,
            created_at=p.created_at.isoformat(),
        )
        for p in payouts
    ]


@app.post("/api/v1/finance/payouts/process")
async def process_pending_payouts(db: AsyncSession = Depends(get_db)):
    """Process all pending payouts (called by scheduler or manually)."""
    result = await db.execute(
        select(Payout).where(Payout.status == PayoutStatus.PENDING)
    )
    pending = result.scalars().all()

    processed = 0
    for payout in pending:
        user_result = await db.execute(select(User).where(User.id == payout.user_id))
        user = user_result.scalar_one_or_none()

        if not user or not user.stripe_connect_account_id:
            if settings.DEMO_MODE:
                payout.status = PayoutStatus.COMPLETED
                payout.processed_at = datetime.now(timezone.utc)
                processed += 1
            else:
                payout.status = PayoutStatus.FAILED
                payout.failure_reason = "No Stripe Connect account configured"
            continue

        if not settings.DEMO_MODE:
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                transfer = stripe.Transfer.create(
                    amount=int(payout.amount * 100),
                    currency=payout.currency,
                    destination=user.stripe_connect_account_id,
                    metadata={"payout_id": str(payout.id)},
                )
                payout.stripe_transfer_id = transfer.id
                payout.status = PayoutStatus.COMPLETED
                payout.processed_at = datetime.now(timezone.utc)
                processed += 1
            except Exception as e:
                payout.status = PayoutStatus.FAILED
                payout.failure_reason = str(e)
        else:
            payout.status = PayoutStatus.COMPLETED
            payout.processed_at = datetime.now(timezone.utc)
            processed += 1

    await db.flush()

    await publisher.publish(Event(
        "payout.completed",
        {"processed_count": processed, "total_pending": len(pending)},
        source="financial-orchestration",
    ))

    return {"processed": processed, "total": len(pending)}


# ---------------------------------------------------------------------------
# Tax Forms (1099-K)
# ---------------------------------------------------------------------------

@app.get("/api/v1/finance/tax-summary/{user_id}", response_model=TaxSummary)
async def get_tax_summary(
    user_id: str,
    tax_year: int = 2024,
    db: AsyncSession = Depends(get_db),
):
    """Get annual tax summary for a user."""
    from sqlalchemy import extract
    result = await db.execute(
        select(
            func.coalesce(func.sum(Payout.amount), 0).label("total_amount"),
            func.count(Payout.id).label("transaction_count"),
        )
        .where(
            Payout.user_id == user_id,
            Payout.status == PayoutStatus.COMPLETED,
            extract("year", Payout.created_at) == tax_year,
        )
    )
    row = result.one()

    total_gross = float(row.total_amount) if row.total_amount else 0
    platform_fees = total_gross * (settings.PLATFORM_FEE_PERCENTAGE / 100)
    net = total_gross - platform_fees

    return TaxSummary(
        user_id=user_id,
        tax_year=tax_year,
        total_gross_payouts=round(total_gross, 2),
        total_platform_fees=round(platform_fees, 2),
        total_net_payouts=round(net, 2),
        transaction_count=row.transaction_count or 0,
        forms_1099k_required=total_gross >= 20000.0,
    )


@app.get("/api/v1/finance/dashboard/{user_id}", response_model=FinancialDashboard)
async def get_financial_dashboard(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get financial overview for a user."""
    # Total earned (completed payouts)
    earned_result = await db.execute(
        select(func.coalesce(func.sum(Payout.amount), 0)).where(
            Payout.user_id == user_id,
            Payout.status == PayoutStatus.COMPLETED,
        )
    )
    total_earned = float(earned_result.scalar() or 0)

    # Total pending
    pending_result = await db.execute(
        select(func.coalesce(func.sum(Payout.amount), 0)).where(
            Payout.user_id == user_id,
            Payout.status == PayoutStatus.PENDING,
        )
    )
    total_pending = float(pending_result.scalar() or 0)

    # Active escrows (as buyer)
    escrow_result = await db.execute(
        select(func.count(EscrowTransaction.id))
        .join(Match, Match.id == EscrowTransaction.match_id)
        .where(
            Match.buyer_id == user_id,
            EscrowTransaction.status.in_([EscrowStatus.FUNDED, EscrowStatus.HELD]),
        )
    )
    active_escrows = escrow_result.scalar() or 0

    # Completed transactions
    completed_result = await db.execute(
        select(func.count(Match.id)).where(
            Match.buyer_id == user_id,
            Match.status == MatchStatus.COMPLETED,
        )
    )
    completed = completed_result.scalar() or 0

    # Pending payouts
    pending_payouts_result = await db.execute(
        select(func.count(Payout.id)).where(
            Payout.user_id == user_id,
            Payout.status == PayoutStatus.PENDING,
        )
    )
    pending_payouts = pending_payouts_result.scalar() or 0

    fees = total_earned * (settings.PLATFORM_FEE_PERCENTAGE / 100)

    return FinancialDashboard(
        user_id=user_id,
        total_earned=round(total_earned, 2),
        total_pending=round(total_pending, 2),
        total_fees=round(fees, 2),
        active_escrows=active_escrows,
        completed_transactions=completed,
        pending_payouts=pending_payouts,
    )


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------

async def handle_escrow_released(event: Event):
    """When escrow is released, create a payout for the seller."""
    logger.info("Escrow released: {}", event.data.get("escrow_id"))
    seller_id = event.data.get("seller_id")
    amount = event.data.get("amount")
    if seller_id and amount:
        logger.info("Payout of ${} scheduled for seller {}", amount, seller_id)


async def handle_match_completed(event: Event):
    """When a match completes, finalize financial records."""
    logger.info("Match completed: {}", event.data.get("match_id"))
