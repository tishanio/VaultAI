from __future__ import annotations

"""Compliance & Risk Agent — ToS monitoring, risk scoring, circuit breakers."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Depends, FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    Dispute,
    DisputeStatus,
    Match,
    MatchStatus,
    MarketListing,
    ReputationScore,
    Subscription,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventConsumer, publisher


# ---------------------------------------------------------------------------
# Blocked Services (ToS-violating)
# ---------------------------------------------------------------------------

BLOCKED_SERVICES = {
    "Netflix": {"reason": "ToS prohibits account sharing outside household"},
    "Adobe": {"reason": "ToS prohibits license sharing"},
    "Hulu": {"reason": "ToS restricts sharing to household members"},
    "HBO Max": {"reason": "ToS prohibits sharing outside household"},
    "Disney+": {"reason": "ToS restricts sharing to household"},
    "Amazon Prime Video": {"reason": "ToS restricts household sharing"},
    "Paramount+": {"reason": "ToS restricts sharing"},
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RiskAssessment(BaseModel):
    entity_type: str  # user, listing, match, transaction
    entity_id: str
    risk_score: float
    risk_level: str  # low, medium, high, critical
    factors: list[str]
    recommended_actions: list[str]
    is_blocked: bool
    assessed_at: str


class CircuitBreakerStatus(BaseModel):
    breaker_id: str
    name: str
    is_active: bool
    trigger_count: int
    threshold: float
    window_minutes: int
    last_triggered: str | None
    affected_entities: int


class ToSCheckResult(BaseModel):
    service_name: str
    is_allowed: bool
    reason: str
    compliance_status: str  # compliant, non_compliant, warning
    details: str


class ComplianceReport(BaseModel):
    total_checks: int
    violations: int
    warnings: int
    blocked_entities: int
    active_circuit_breakers: int
    risk_distribution: dict[str, int]


# ---------------------------------------------------------------------------
# Risk Scoring Engine
# ---------------------------------------------------------------------------

class RiskScoringEngine:
    """Multi-factor risk scoring system."""

    RISK_WEIGHTS = {
        "reputation": 0.25,
        "transaction_velocity": 0.20,
        "dispute_history": 0.25,
        "tos_violations": 0.20,
        "account_age": 0.10,
    }

    @staticmethod
    async def assess_user_risk(user_id: str, db: AsyncSession) -> RiskAssessment:
        """Comprehensive risk assessment for a user."""
        factors = []
        scores = {}

        # Reputation factor
        rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user_id))
        rep = rep_result.scalar_one_or_none()
        if rep:
            scores["reputation"] = 1.0 - rep.overall_score
            if rep.overall_score < 0.4:
                factors.append("Low reputation score")
            if rep.dispute_count > 3:
                factors.append("Excessive dispute history")
        else:
            scores["reputation"] = 0.5

        # Transaction velocity
        match_count = (await db.execute(
            select(func.count(Match.id)).where(
                Match.buyer_id == user_id,
                Match.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
            )
        )).scalar() or 0
        scores["transaction_velocity"] = min(1.0, match_count / 20)
        if match_count > 15:
            factors.append("Unusually high transaction velocity")

        # Dispute history
        dispute_count = (await db.execute(
            select(func.count(Dispute.id)).where(
                Dispute.filed_by_id == user_id,
                Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]),
            )
        )).scalar() or 0
        scores["dispute_history"] = min(1.0, dispute_count / 5)
        if dispute_count > 2:
            factors.append("Multiple active disputes")

        # ToS violations
        tos_count = (await db.execute(
            select(func.count(ComplianceEvent.id)).where(
                ComplianceEvent.user_id == user_id,
                ComplianceEvent.event_type == ComplianceEventType.TOS_VIOLATION,
            )
        )).scalar() or 0
        scores["tos_violations"] = min(1.0, tos_count / 3)
        if tos_count > 0:
            factors.append(f"{tos_count} ToS violation(s)")

        # Account age
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.created_at:
            age_days = (datetime.now(timezone.utc) - user.created_at).days
            scores["account_age"] = max(0.0, 1.0 - (age_days / 365))
            if age_days < 7:
                factors.append("New account (< 7 days)")
        else:
            scores["account_age"] = 0.5

        # Weighted total
        total = sum(
            scores.get(k, 0.5) * v
            for k, v in RiskScoringEngine.RISK_WEIGHTS.items()
        )
        total = round(min(1.0, max(0.0, total)), 3)

        if total < 0.3:
            risk_level = "low"
            recommended_actions = []
            is_blocked = False
        elif total < 0.6:
            risk_level = "medium"
            recommended_actions = ["Monitor activity", "Require additional verification for high-value transactions"]
            is_blocked = False
        elif total < 0.85:
            risk_level = "high"
            recommended_actions = ["Restrict new matches", "Require manual review", "Send warning notification"]
            is_blocked = False
        else:
            risk_level = "critical"
            recommended_actions = ["Block all transactions", "Escalate to compliance team", "Initiate account review"]
            is_blocked = True

        return RiskAssessment(
            entity_type="user",
            entity_id=user_id,
            risk_score=total,
            risk_level=risk_level,
            factors=factors,
            recommended_actions=recommended_actions,
            is_blocked=is_blocked,
            assessed_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Compliance & Risk Agent starting")
    await publisher.connect()
    yield
    await publisher.close()


app = FastAPI(title="Vault Compliance & Risk Agent", version=settings.APP_VERSION, lifespan=lifespan)
risk_engine = RiskScoringEngine()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "compliance-risk"}


# ---------------------------------------------------------------------------
# ToS Monitoring
# ---------------------------------------------------------------------------

@app.get("/api/v1/compliance/tos/check/{service_name}", response_model=ToSCheckResult)
async def check_tos_compliance(service_name: str):
    """Check if a service is compliant with Vault's ToS."""
    block_info = BLOCKED_SERVICES.get(service_name)
    if block_info:
        return ToSCheckResult(
            service_name=service_name,
            is_allowed=False,
            reason=block_info["reason"],
            compliance_status="non_compliant",
            details=f"{service_name} is blocked due to: {block_info['reason']}. Vault only supports family-plan-compliant services.",
        )

    # Services in the allowed list are compliant
    allowed = {"Spotify", "Google One", "YouTube Premium", "YouTube Music", "Apple Music",
               "Headspace", "Calm", "Duolingo", "Microsoft 365", "Canva"}
    if service_name in allowed:
        return ToSCheckResult(
            service_name=service_name,
            is_allowed=True,
            reason="Service is family-plan compliant",
            compliance_status="compliant",
            details=f"{service_name} allows family sharing. Vault can facilitate safe seat sharing.",
        )

    return ToSCheckResult(
        service_name=service_name,
        is_allowed=False,
        reason="Service not yet vetted by Vault compliance team",
        compliance_status="warning",
        details=f"{service_name} has not been reviewed. Submit a request to have it added.",
    )


# ---------------------------------------------------------------------------
# Risk Assessment
# ---------------------------------------------------------------------------

@app.get("/api/v1/compliance/risk/{user_id}", response_model=RiskAssessment)
async def assess_risk(user_id: str, db: AsyncSession = Depends(get_db)):
    """Perform risk assessment on a user."""
    return await risk_engine.assess_user_risk(user_id, db)


@app.post("/api/v1/compliance/risk/batch")
async def batch_risk_assessment(user_ids: list[str], db: AsyncSession = Depends(get_db)):
    """Batch risk assessment for multiple users."""
    results = []
    for uid in user_ids:
        assessment = await risk_engine.assess_user_risk(uid, db)
        results.append(assessment)

    blocked = [r for r in results if r.is_blocked]
    return {
        "total_assessed": len(results),
        "blocked_count": len(blocked),
        "results": [r.model_dump() for r in results],
    }


# ---------------------------------------------------------------------------
# Circuit Breakers
# ---------------------------------------------------------------------------

@app.get("/api/v1/compliance/circuit-breakers")
async def get_circuit_breakers():
    """Get status of all circuit breakers."""
    breakers = [
        CircuitBreakerStatus(
            breaker_id="cb_velocity",
            name="Transaction Velocity Breaker",
            is_active=False,
            trigger_count=0,
            threshold=0.85,
            window_minutes=60,
            last_triggered=None,
            affected_entities=0,
        ),
        CircuitBreakerStatus(
            breaker_id="cb_risk",
            name="Aggregate Risk Breaker",
            is_active=False,
            trigger_count=0,
            threshold=0.85,
            window_minutes=30,
            last_triggered=None,
            affected_entities=0,
        ),
        CircuitBreakerStatus(
            breaker_id="cb_disputes",
            name="Dispute Rate Breaker",
            is_active=False,
            trigger_count=0,
            threshold=0.85,
            window_minutes=1440,
            last_triggered=None,
            affected_entities=0,
        ),
        CircuitBreakerStatus(
            breaker_id="cb_payment",
            name="Payment Failure Breaker",
            is_active=False,
            trigger_count=0,
            threshold=0.85,
            window_minutes=30,
            last_triggered=None,
            affected_entities=0,
        ),
    ]
    return {"breakers": [b.model_dump() for b in breakers]}


@app.post("/api/v1/compliance/circuit-breakers/{breaker_id}/trigger")
async def trigger_circuit_breaker(breaker_id: str, reason: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger a circuit breaker."""
    event = ComplianceEvent(
        id=uuid.uuid4(),
        event_type=ComplianceEventType.CIRCUIT_BREAKER,
        severity="critical",
        title=f"Circuit breaker triggered: {breaker_id}",
        description=reason,
        risk_score=1.0,
        action_taken="circuit_breaker_activated",
    )
    db.add(event)
    await db.flush()

    await publisher.publish(Event(
        "compliance.circuit_breaker",
        {"breaker_id": breaker_id, "reason": reason},
        source="compliance-risk",
    ))

    return {"message": f"Circuit breaker {breaker_id} triggered", "reason": reason}


# ---------------------------------------------------------------------------
# Monitoring & Audit
# ---------------------------------------------------------------------------

@app.get("/api/v1/compliance/report", response_model=ComplianceReport)
async def get_compliance_report(db: AsyncSession = Depends(get_db)):
    """Generate compliance status report."""
    total = (await db.execute(select(func.count(ComplianceEvent.id)))).scalar() or 0
    violations = (await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.event_type == ComplianceEventType.TOS_VIOLATION)
    )).scalar() or 0
    warnings = (await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.severity == "medium")
    )).scalar() or 0
    cb_active = (await db.execute(
        select(func.count(ComplianceEvent.id)).where(
            ComplianceEvent.event_type == ComplianceEventType.CIRCUIT_BREAKER,
            ComplianceEvent.is_resolved == False,
        )
    )).scalar() or 0

    # Risk distribution
    critical = (await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.severity == "critical")
    )).scalar() or 0
    high = (await db.execute(
        select(func.count(ComplianceEvent.id)).where(ComplianceEvent.severity == "high")
    )).scalar() or 0

    return ComplianceReport(
        total_checks=total,
        violations=violations,
        warnings=warnings,
        blocked_entities=0,
        active_circuit_breakers=cb_active,
        risk_distribution={
            "low": total - critical - high - warnings,
            "medium": warnings,
            "high": high,
            "critical": critical,
        },
    )


@app.post("/api/v1/compliance/audit-log")
async def log_audit_event(
    event_type: str,
    title: str,
    description: str,
    severity: str = "low",
    db: AsyncSession = Depends(get_db),
):
    """Log a compliance audit event."""
    event = ComplianceEvent(
        id=uuid.uuid4(),
        event_type=ComplianceEventType.AUDIT_LOG,
        severity=severity,
        title=title,
        description=description,
        risk_score=0.0,
    )
    db.add(event)
    await db.flush()
    return {"message": "Audit event logged", "event_id": str(event.id)}
