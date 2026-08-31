from __future__ import annotations

"""Trust & Verification Agent — KYC, escrow management, reputation scoring, dispute resolution."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Depends, FastAPI, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    Dispute,
    DisputeStatus,
    EscrowTransaction,
    EscrowStatus,
    KYCStatus,
    KYCVerification,
    Match,
    MatchStatus,
    ReputationScore,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventConsumer, publisher


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class KYCRequest(BaseModel):
    document_type: str = Field(description="passport, drivers_license, national_id")
    document_country: str = Field(max_length=2)


class KYCResponse(BaseModel):
    verification_id: str
    status: str
    onfido_check_id: str | None
    message: str


class ReputationResponse(BaseModel):
    user_id: str
    overall_score: float
    reliability_score: float
    communication_score: float
    payment_score: float
    total_transactions: int
    positive_reviews: int
    negative_reviews: int
    trust_tier: str  # bronze, silver, gold, platinum


class DisputeRequest(BaseModel):
    match_id: str
    reason: str = Field(min_length=5, max_length=50)
    description: str = Field(min_length=10, max_length=2000)


class DisputeResponse(BaseModel):
    dispute_id: str
    status: str
    message: str


class TrustVerificationResult(BaseModel):
    user_id: str
    kyc_status: str
    reputation_score: float
    trust_tier: str
    is_verified: bool
    can_transact: bool
    risk_flags: list[str]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Trust & Verification Agent starting")
    await publisher.connect()
    yield
    await publisher.close()


app = FastAPI(title="Vault Trust & Verification Agent", version=settings.APP_VERSION, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "trust-verification"}


# ---------------------------------------------------------------------------
# Reputation Scoring
# ---------------------------------------------------------------------------

def _calculate_reputation_tier(score: float) -> str:
    if score >= 0.9:
        return "platinum"
    elif score >= 0.75:
        return "gold"
    elif score >= 0.6:
        return "silver"
    return "bronze"


async def _get_or_create_reputation(user_id: str, db: AsyncSession) -> ReputationScore:
    result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user_id))
    rep = result.scalar_one_or_none()
    if not rep:
        rep = ReputationScore(
            id=uuid.uuid4(),
            user_id=user_id,
            overall_score=0.5,
            reliability_score=0.5,
            communication_score=0.5,
            payment_score=0.5,
        )
        db.add(rep)
        await db.flush()
    return rep


def _update_reputation_score(rep: ReputationScore):
    """Recalculate overall reputation score from component scores."""
    weights = {"reliability": 0.4, "communication": 0.3, "payment": 0.3}
    rep.overall_score = round(
        rep.reliability_score * weights["reliability"]
        + rep.communication_score * weights["communication"]
        + rep.payment_score * weights["payment"],
        3,
    )
    # Apply dispute penalty
    if rep.dispute_count > 0:
        penalty = min(0.3, rep.dispute_count * 0.05)
        rep.overall_score = round(max(0.0, rep.overall_score - penalty), 3)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/trust/kyc/initiate", response_model=KYCResponse)
async def initiate_kyc(body: KYCRequest, user_id: str, db: AsyncSession = Depends(get_db)):
    """Initiate KYC verification via Onfido (or mock in demo mode)."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check existing verification
    existing = await db.execute(
        select(KYCVerification).where(
            KYCVerification.user_id == user_id,
            KYCVerification.status.in_([KYCStatus.PENDING, KYCStatus.VERIFIED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Active KYC verification already exists")

    if settings.ONFIDO_MOCK_MODE or settings.DEMO_MODE:
        # Mock KYC verification
        verification = KYCVerification(
            id=uuid.uuid4(),
            user_id=user.id,
            onfido_check_id=f"mock_check_{uuid.uuid4().hex[:12]}",
            status=KYCStatus.VERIFIED,
            document_type=body.document_type,
            document_country=body.document_country,
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(verification)
        user.is_verified = True
        await db.flush()

        await publisher.publish(Event(
            "user.kyc.completed",
            {"user_id": user_id, "status": "verified", "method": "mock"},
            source="trust-verification",
        ))

        return KYCResponse(
            verification_id=str(verification.id),
            status="verified",
            onfido_check_id=verification.onfido_check_id,
            message="KYC verification completed (demo mode)",
        )

    # Production: Onfido API integration
    verification = KYCVerification(
        id=uuid.uuid4(),
        user_id=user.id,
        status=KYCStatus.PENDING,
        document_type=body.document_type,
        document_country=body.document_country,
    )
    db.add(verification)
    await db.flush()

    return KYCResponse(
        verification_id=str(verification.id),
        status="pending",
        onfido_check_id=None,
        message="KYC verification initiated. Complete document upload.",
    )


@app.get("/api/v1/trust/kyc/{user_id}", response_model=KYCResponse)
async def get_kyc_status(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get KYC verification status for a user."""
    result = await db.execute(
        select(KYCVerification)
        .where(KYCVerification.user_id == user_id)
        .order_by(KYCVerification.created_at.desc())
        .limit(1)
    )
    verification = result.scalar_one_or_none()
    if not verification:
        raise HTTPException(status_code=404, detail="No KYC verification found")

    return KYCResponse(
        verification_id=str(verification.id),
        status=verification.status.value,
        onfido_check_id=verification.onfido_check_id,
        message=f"KYC status: {verification.status.value}",
    )


@app.get("/api/v1/trust/reputation/{user_id}", response_model=ReputationResponse)
async def get_reputation(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get reputation score for a user."""
    rep = await _get_or_create_reputation(user_id, db)
    _update_reputation_score(rep)
    await db.flush()

    return ReputationResponse(
        user_id=user_id,
        overall_score=rep.overall_score,
        reliability_score=rep.reliability_score,
        communication_score=rep.communication_score,
        payment_score=rep.payment_score,
        total_transactions=rep.total_transactions,
        positive_reviews=rep.positive_reviews,
        negative_reviews=rep.negative_reviews,
        trust_tier=_calculate_reputation_tier(rep.overall_score),
    )


@app.post("/api/v1/trust/reputation/update")
async def update_reputation(
    user_id: str,
    rating_type: str,  # positive, negative
    category: str,  # reliability, communication, payment
    db: AsyncSession = Depends(get_db),
):
    """Update reputation score after a transaction."""
    rep = await _get_or_create_reputation(user_id, db)

    delta = 0.05 if rating_type == "positive" else -0.08

    if category == "reliability":
        rep.reliability_score = max(0.0, min(1.0, rep.reliability_score + delta))
    elif category == "communication":
        rep.communication_score = max(0.0, min(1.0, rep.communication_score + delta))
    elif category == "payment":
        rep.payment_score = max(0.0, min(1.0, rep.payment_score + delta))

    rep.total_transactions += 1
    if rating_type == "positive":
        rep.positive_reviews += 1
    else:
        rep.negative_reviews += 1

    _update_reputation_score(rep)
    await db.flush()

    return {"message": "Reputation updated", "overall_score": rep.overall_score}


@app.get("/api/v1/trust/verify/{user_id}", response_model=TrustVerificationResult)
async def verify_user_trust(user_id: str, db: AsyncSession = Depends(get_db)):
    """Complete trust verification check — combines KYC + reputation + risk."""
    # KYC check
    kyc_result = await db.execute(
        select(KYCVerification)
        .where(KYCVerification.user_id == user_id)
        .order_by(KYCVerification.created_at.desc())
        .limit(1)
    )
    kyc = kyc_result.scalar_one_or_none()
    kyc_status = kyc.status.value if kyc else "not_started"
    is_verified = kyc_status == "verified"

    # Reputation check
    rep = await _get_or_create_reputation(user_id, db)
    _update_reputation_score(rep)

    # Risk flags
    risk_flags = []
    if not is_verified:
        risk_flags.append("kyc_not_verified")
    if rep.overall_score < 0.4:
        risk_flags.append("low_reputation")
    if rep.dispute_count > 3:
        risk_flags.append("excessive_disputes")

    can_transact = is_verified and rep.overall_score >= 0.3 and len(risk_flags) == 0

    return TrustVerificationResult(
        user_id=user_id,
        kyc_status=kyc_status,
        reputation_score=rep.overall_score,
        trust_tier=_calculate_reputation_tier(rep.overall_score),
        is_verified=is_verified,
        can_transact=can_transact,
        risk_flags=risk_flags,
    )


@app.post("/api/v1/trust/disputes", response_model=DisputeResponse, status_code=201)
async def file_dispute(body: DisputeRequest, user_id: str, db: AsyncSession = Depends(get_db)):
    """File a dispute for a match."""
    match_result = await db.execute(select(Match).where(Match.id == body.match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if str(match.buyer_id) != user_id and str(match.seller_id) != user_id:
        raise HTTPException(status_code=403, detail="Not a party to this match")

    dispute = Dispute(
        id=uuid.uuid4(),
        match_id=match.id,
        filed_by_id=user_id,
        status=DisputeStatus.OPEN,
        reason=body.reason,
        description=body.description,
    )
    db.add(dispute)

    # Escrow protection
    escrow_result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.match_id == match.id))
    escrow = escrow_result.scalar_one_or_none()
    if escrow and escrow.status in (EscrowStatus.FUNDED, EscrowStatus.HELD):
        escrow.status = EscrowStatus.DISPUTED

    await db.flush()

    await publisher.publish(Event(
        "escrow.disputed",
        {"dispute_id": str(dispute.id), "match_id": str(match.id), "filed_by": user_id},
        source="trust-verification",
    ))

    return DisputeResponse(dispute_id=str(dispute.id), status="open", message="Dispute filed. Funds held in escrow.")


@app.post("/api/v1/trust/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    resolution: str,
    winner_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Resolve a dispute."""
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    dispute.status = DisputeStatus.RESOLVED
    dispute.resolution = resolution
    dispute.resolved_at = datetime.now(timezone.utc)
    dispute.resolved_by = winner_id

    # Update loser's reputation
    if winner_id:
        match_result = await db.execute(select(Match).where(Match.id == dispute.match_id))
        match = match_result.scalar_one_or_none()
        if match:
            loser_id = str(match.seller_id) if str(match.buyer_id) == winner_id else str(match.buyer_id)
            rep = await _get_or_create_reputation(loser_id, db)
            rep.dispute_count += 1
            rep.reliability_score = max(0.0, rep.reliability_score - 0.05)
            _update_reputation_score(rep)

    await db.flush()
    return {"message": "Dispute resolved", "dispute_id": dispute_id, "resolution": resolution}
