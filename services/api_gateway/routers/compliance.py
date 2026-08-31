from __future__ import annotations

"""Compliance & Risk router — risk monitoring, circuit breakers, ToS enforcement."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    User,
)
from vault.db.session import get_db
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/compliance")


class ComplianceEventResponse(BaseModel):
    id: str
    event_type: str
    severity: str
    title: str
    description: str
    risk_score: float
    action_taken: Optional[str]
    is_resolved: bool
    created_at: str


class RiskScoreResponse(BaseModel):
    user_id: str
    overall_risk: float
    factors: dict[str, float]
    recommendation: str
    is_blocked: bool


class ComplianceStats(BaseModel):
    total_events: int
    unresolved_events: int
    critical_events: int
    high_events: int
    circuit_breakers_active: int


@router.get("/events", response_model=list[ComplianceEventResponse])
async def list_compliance_events(
    event_type: Optional[ComplianceEventType] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List compliance events (admin-only in production)."""
    query = select(ComplianceEvent)
    if event_type:
        query = query.where(ComplianceEvent.event_type == event_type)
    if severity:
        query = query.where(ComplianceEvent.severity == severity)
    if resolved is not None:
        query = query.where(ComplianceEvent.is_resolved == resolved)
    query = query.order_by(ComplianceEvent.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        ComplianceEventResponse(
            id=str(e.id),
            event_type=e.event_type,
            severity=e.severity,
            title=e.title,
            description=e.description,
            risk_score=e.risk_score,
            action_taken=e.action_taken,
            is_resolved=e.is_resolved,
            created_at=e.created_at.isoformat(),
        )
        for e in events
    ]


@router.get("/stats", response_model=ComplianceStats)
async def get_compliance_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get compliance dashboard statistics."""
    total_q = await db.execute(select(func.count(ComplianceEvent.id)))
    total = total_q.scalar() or 0

    unresolved_q = await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.is_resolved == False)
    )
    unresolved = unresolved_q.scalar() or 0

    critical_q = await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.severity == "critical")
    )
    critical = critical_q.scalar() or 0

    high_q = await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.severity == "high")
    )
    high = high_q.scalar() or 0

    cb_q = await db.execute(
        select(func.count(ComplianceEvent.id)).where(
            ComplianceEvent.event_type == ComplianceEventType.CIRCUIT_BREAKER,
            ComplianceEvent.is_resolved == False,
        )
    )
    circuit_breakers = cb_q.scalar() or 0

    return ComplianceStats(
        total_events=total,
        unresolved_events=unresolved,
        critical_events=critical,
        high_events=high,
        circuit_breakers_active=circuit_breakers,
    )


@router.get("/risk-score/{user_id}", response_model=RiskScoreResponse)
async def get_risk_score(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get risk score for a user (simplified risk model)."""
    from vault.db.models import Match, EscrowTransaction, EscrowStatus, ReputationScore

    # Gather risk factors
    matches_result = await db.execute(select(func.count(Match.id)).where(Match.buyer_id == user_id))
    total_matches = matches_result.scalar() or 0

    disputes_result = await db.execute(
        select(func.count(ComplianceEvent.id)).where(
            ComplianceEvent.user_id == user_id,
            ComplianceEvent.event_type == ComplianceEventType.TOS_VIOLATION,
        )
    )
    tos_violations = disputes_result.scalar() or 0

    rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user_id))
    rep = rep_result.scalar_one_or_none()
    reputation = rep.overall_score if rep else 0.5

    # Calculate risk factors
    dispute_risk = min(1.0, tos_violations * 0.3)
    reputation_risk = 1.0 - reputation
    activity_risk = max(0.0, 1.0 - (total_matches * 0.1))

    factors = {
        "dispute_rate": round(dispute_risk, 3),
        "reputation_risk": round(reputation_risk, 3),
        "activity_risk": round(activity_risk, 3),
    }

    overall = round((dispute_risk * 0.4 + reputation_risk * 0.4 + activity_risk * 0.2), 3)
    is_blocked = overall >= 0.85

    if overall < 0.3:
        recommendation = "Low risk. User is in good standing."
    elif overall < 0.6:
        recommendation = "Moderate risk. Monitor activity."
    elif overall < 0.85:
        recommendation = "Elevated risk. Consider additional verification."
    else:
        recommendation = "High risk. Circuit breaker recommended."

    return RiskScoreResponse(
        user_id=user_id,
        overall_risk=overall,
        factors=factors,
        recommendation=recommendation,
        is_blocked=is_blocked,
    )


@router.post("/events/{event_id}/resolve")
async def resolve_compliance_event(
    event_id: str,
    resolution: str = "Auto-resolved",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a compliance event."""
    result = await db.execute(select(ComplianceEvent).where(ComplianceEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance event not found")

    event.is_resolved = True
    event.action_taken = resolution
    await db.flush()

    return {"message": "Event resolved", "event_id": event_id}
