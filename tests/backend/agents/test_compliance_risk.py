"""Tests for Compliance & Risk Agent."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    Dispute,
    DisputeStatus,
)

pytestmark = pytest.mark.asyncio


async def test_health(compliance_client):
    response = await compliance_client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "compliance-risk"


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/tos/check/{service_name}
# ---------------------------------------------------------------------------

async def test_tos_check_blocked_service(compliance_client):
    response = await compliance_client.get("/api/v1/compliance/tos/check/Netflix")
    assert response.status_code == 200
    data = response.json()
    assert data["is_allowed"] is False
    assert data["compliance_status"] == "non_compliant"
    assert "ToS" in data["reason"]


async def test_tos_check_allowed_service(compliance_client):
    for service in ("Spotify", "YouTube Premium", "Duolingo", "Canva"):
        response = await compliance_client.get(f"/api/v1/compliance/tos/check/{service}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_allowed"] is True
        assert data["compliance_status"] == "compliant"


async def test_tos_check_unknown_service(compliance_client):
    response = await compliance_client.get("/api/v1/compliance/tos/check/SomeNewService")
    assert response.status_code == 200
    data = response.json()
    assert data["is_allowed"] is False
    assert data["compliance_status"] == "warning"


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/risk/{user_id}
# ---------------------------------------------------------------------------

async def test_risk_assessment_new_user(compliance_client, agent_user):
    response = await compliance_client.get(f"/api/v1/compliance/risk/{agent_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "user"
    assert data["entity_id"] == str(agent_user.id)
    assert 0 <= data["risk_score"] <= 1
    assert data["risk_level"] in ("low", "medium", "high", "critical")
    assert isinstance(data["factors"], list)
    assert isinstance(data["recommended_actions"], list)


async def test_risk_assessment_with_reputation(
    compliance_client, agent_user, agent_seller_reputation,
):
    response = await compliance_client.get(f"/api/v1/compliance/risk/{agent_seller_reputation.user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] < 0.5  # High reputation = low risk


async def test_risk_assessment_with_violations(
    compliance_client, db_session, agent_user,
):
    # Add ToS violation
    event = ComplianceEvent(
        id=uuid.uuid4(),
        user_id=agent_user.id,
        event_type=ComplianceEventType.TOS_VIOLATION,
        severity="high",
        title="TOS Violation",
        description="Shared credentials outside household",
        risk_score=0.8,
    )
    db_session.add(event)
    await db_session.flush()

    response = await compliance_client.get(f"/api/v1/compliance/risk/{agent_user.id}")
    data = response.json()
    assert any("ToS" in f for f in data["factors"])


# ---------------------------------------------------------------------------
# POST /api/v1/compliance/risk/batch
# ---------------------------------------------------------------------------

async def test_batch_risk_assessment(compliance_client, agent_user, agent_seller):
    response = await compliance_client.post(
        "/api/v1/compliance/risk/batch",
        params={},
        json=[str(agent_user.id), str(agent_seller.id)],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_assessed"] == 2
    assert isinstance(data["results"], list)


async def test_batch_risk_assessment_empty(compliance_client):
    response = await compliance_client.post(
        "/api/v1/compliance/risk/batch",
        params={},
        json=[],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_assessed"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/circuit-breakers
# ---------------------------------------------------------------------------

async def test_circuit_breakers(compliance_client):
    response = await compliance_client.get("/api/v1/compliance/circuit-breakers")
    assert response.status_code == 200
    data = response.json()
    breakers = data["breakers"]
    assert len(breakers) >= 4
    names = [b["name"] for b in breakers]
    assert "Transaction Velocity Breaker" in names
    assert "Aggregate Risk Breaker" in names
    assert all(b["is_active"] is False for b in breakers)


# ---------------------------------------------------------------------------
# POST /api/v1/compliance/circuit-breakers/{breaker_id}/trigger
# ---------------------------------------------------------------------------

async def test_trigger_circuit_breaker(compliance_client):
    response = await compliance_client.post(
        "/api/v1/compliance/circuit-breakers/cb_velocity/trigger",
        params={"reason": "Suspicious activity detected"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cb_velocity" in data["message"]


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/report
# ---------------------------------------------------------------------------

async def test_compliance_report_empty(compliance_client):
    response = await compliance_client.get("/api/v1/compliance/report")
    assert response.status_code == 200
    data = response.json()
    assert data["total_checks"] == 0
    assert data["violations"] == 0
    assert data["warnings"] == 0


async def test_compliance_report_with_data(compliance_client, db_session, agent_user):
    # Add various compliance events
    events = [
        ComplianceEvent(
            id=uuid.uuid4(), user_id=agent_user.id,
            event_type=ComplianceEventType.TOS_VIOLATION,
            severity="high", title="TOS Violation",
            description="Shared credentials", risk_score=0.8,
        ),
        ComplianceEvent(
            id=uuid.uuid4(), user_id=agent_user.id,
            event_type=ComplianceEventType.RISK_ALERT,
            severity="medium", title="Risk Alert",
            description="Unusual activity", risk_score=0.5,
        ),
        ComplianceEvent(
            id=uuid.uuid4(),
            event_type=ComplianceEventType.CIRCUIT_BREAKER,
            severity="critical", title="CB Triggered",
            description="Rate limit exceeded", risk_score=1.0,
            is_resolved=False,
        ),
    ]
    for e in events:
        db_session.add(e)
    await db_session.flush()

    response = await compliance_client.get("/api/v1/compliance/report")
    assert response.status_code == 200
    data = response.json()
    assert data["total_checks"] == 3
    assert data["violations"] == 1
    assert data["warnings"] == 1
    assert data["active_circuit_breakers"] == 1
    assert "risk_distribution" in data
