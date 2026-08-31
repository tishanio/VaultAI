"""Tests for compliance endpoints — events, stats, risk scoring, resolve."""
import uuid

import pytest

from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    ReputationScore,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /compliance/events — list compliance events
# ---------------------------------------------------------------------------


async def test_compliance_events_unauthorized(async_client):
    response = await async_client.get("/api/v1/compliance/events")
    assert response.status_code == 401


async def test_compliance_events_empty(async_client, auth_headers):
    response = await async_client.get("/api/v1/compliance/events", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_compliance_events_with_data(async_client, auth_headers, db_session):
    """Events are returned when they exist."""
    event = ComplianceEvent(
        id=uuid.uuid4(),
        event_type=ComplianceEventType.TOS_VIOLATION,
        severity="high",
        title="Netflix listing blocked",
        description="User attempted to list Netflix seat sharing",
        risk_score=0.8,
    )
    db_session.add(event)
    await db_session.flush()

    response = await async_client.get("/api/v1/compliance/events", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "tos_violation"
    assert data[0]["severity"] == "high"
    assert data[0]["title"] == "Netflix listing blocked"
    assert data[0]["is_resolved"] is False


async def test_compliance_events_filter_by_type(async_client, auth_headers, db_session):
    """Filtering by event_type returns only matching events."""
    for etype in [ComplianceEventType.TOS_VIOLATION, ComplianceEventType.RISK_ALERT, ComplianceEventType.TOS_VIOLATION]:
        db_session.add(ComplianceEvent(
            id=uuid.uuid4(),
            event_type=etype,
            severity="medium",
            title=f"Event {etype.value}",
            description="Test",
            risk_score=0.5,
        ))
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/compliance/events",
        params={"event_type": "tos_violation"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(e["event_type"] == "tos_violation" for e in data)


async def test_compliance_events_filter_by_severity(async_client, auth_headers, db_session):
    db_session.add(ComplianceEvent(
        id=uuid.uuid4(), event_type=ComplianceEventType.RISK_ALERT,
        severity="critical", title="Critical", description="Test", risk_score=0.95,
    ))
    db_session.add(ComplianceEvent(
        id=uuid.uuid4(), event_type=ComplianceEventType.RISK_ALERT,
        severity="low", title="Low", description="Test", risk_score=0.1,
    ))
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/compliance/events",
        params={"severity": "critical"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["severity"] == "critical"


async def test_compliance_events_filter_by_resolved(async_client, auth_headers, db_session):
    db_session.add(ComplianceEvent(
        id=uuid.uuid4(), event_type=ComplianceEventType.AUDIT_LOG,
        severity="low", title="Open", description="Test", risk_score=0.0,
        is_resolved=False,
    ))
    db_session.add(ComplianceEvent(
        id=uuid.uuid4(), event_type=ComplianceEventType.AUDIT_LOG,
        severity="low", title="Resolved", description="Test", risk_score=0.0,
        is_resolved=True,
    ))
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/compliance/events",
        params={"resolved": "false"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["is_resolved"] is False


async def test_compliance_events_pagination(async_client, auth_headers, db_session):
    for i in range(5):
        db_session.add(ComplianceEvent(
            id=uuid.uuid4(), event_type=ComplianceEventType.AUDIT_LOG,
            severity="low", title=f"Event {i}", description="Test", risk_score=0.0,
        ))
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/compliance/events",
        params={"limit": 2, "offset": 0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 2

    response2 = await async_client.get(
        "/api/v1/compliance/events",
        params={"limit": 2, "offset": 4},
        headers=auth_headers,
    )
    assert response2.status_code == 200
    assert len(response2.json()) == 1


# ---------------------------------------------------------------------------
# GET /compliance/stats — compliance dashboard stats
# ---------------------------------------------------------------------------


async def test_compliance_stats_unauthorized(async_client):
    response = await async_client.get("/api/v1/compliance/stats")
    assert response.status_code == 401


async def test_compliance_stats_empty(async_client, auth_headers):
    response = await async_client.get("/api/v1/compliance/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 0
    assert data["unresolved_events"] == 0
    assert data["critical_events"] == 0
    assert data["high_events"] == 0
    assert data["circuit_breakers_active"] == 0


async def test_compliance_stats_with_data(async_client, auth_headers, db_session):
    events = [
        ComplianceEvent(id=uuid.uuid4(), event_type=ComplianceEventType.TOS_VIOLATION,
                        severity="critical", title="T1", description="D", risk_score=0.9),
        ComplianceEvent(id=uuid.uuid4(), event_type=ComplianceEventType.RISK_ALERT,
                        severity="high", title="T2", description="D", risk_score=0.7),
        ComplianceEvent(id=uuid.uuid4(), event_type=ComplianceEventType.AUDIT_LOG,
                        severity="low", title="T3", description="D", risk_score=0.1, is_resolved=True),
        ComplianceEvent(id=uuid.uuid4(), event_type=ComplianceEventType.CIRCUIT_BREAKER,
                        severity="high", title="T4", description="D", risk_score=0.85, is_resolved=False),
    ]
    for e in events:
        db_session.add(e)
    await db_session.flush()

    response = await async_client.get("/api/v1/compliance/stats", headers=auth_headers)
    data = response.json()
    assert data["total_events"] == 4
    assert data["critical_events"] == 1
    assert data["high_events"] == 2
    assert data["circuit_breakers_active"] == 1


# ---------------------------------------------------------------------------
# GET /compliance/risk-score/{user_id}
# ---------------------------------------------------------------------------


async def test_risk_score_unauthorized(async_client):
    response = await async_client.get("/api/v1/compliance/risk-score/some-user-id")
    assert response.status_code == 401


async def test_risk_score_new_user(async_client, auth_headers):
    """New user with no reputation should have moderate risk."""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(
        f"/api/v1/compliance/risk-score/{fake_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == fake_id
    assert "overall_risk" in data
    assert "factors" in data
    assert "recommendation" in data
    assert "is_blocked" in data
    # New user with no reputation (defaults to 0.5) and no activity
    assert data["factors"]["reputation_risk"] == 0.5
    assert data["factors"]["activity_risk"] == 1.0  # 0 matches * 0.1 = 0, 1 - 0 = 1.0
    assert data["factors"]["dispute_rate"] == 0.0


async def test_risk_score_high_reputation_user(async_client, auth_headers, db_session, test_user):
    """User with high reputation should have low risk."""
    rep = ReputationScore(
        id=uuid.uuid4(),
        user_id=test_user.id,
        overall_score=0.95,
        reliability_score=0.95,
        communication_score=0.95,
        payment_score=0.95,
        total_transactions=20,
        positive_reviews=19,
        negative_reviews=1,
    )
    db_session.add(rep)
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/compliance/risk-score/{test_user.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_risk"] < 0.3
    assert data["is_blocked"] is False
    assert "Low risk" in data["recommendation"]


async def test_risk_score_blocked_user(async_client, auth_headers, db_session, test_user):
    """User with low reputation and ToS violations should be blocked."""
    rep = ReputationScore(
        id=uuid.uuid4(),
        user_id=test_user.id,
        overall_score=0.1,
        reliability_score=0.1,
        communication_score=0.1,
        payment_score=0.1,
    )
    db_session.add(rep)
    # Add ToS violations
    for _ in range(5):
        db_session.add(ComplianceEvent(
            id=uuid.uuid4(), user_id=test_user.id,
            event_type=ComplianceEventType.TOS_VIOLATION,
            severity="high", title="Violation", description="Test", risk_score=0.9,
        ))
    await db_session.flush()

    response = await async_client.get(
        f"/api/v1/compliance/risk-score/{test_user.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_risk"] >= 0.85
    assert data["is_blocked"] is True
    assert "High risk" in data["recommendation"]


# ---------------------------------------------------------------------------
# POST /compliance/events/{event_id}/resolve
# ---------------------------------------------------------------------------


async def test_resolve_event_unauthorized(async_client):
    response = await async_client.post(
        "/api/v1/compliance/events/some-id/resolve"
    )
    assert response.status_code == 401


async def test_resolve_event_not_found(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/compliance/events/00000000-0000-0000-0000-000000000000/resolve",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_resolve_event_success(async_client, auth_headers, db_session):
    event = ComplianceEvent(
        id=uuid.uuid4(),
        event_type=ComplianceEventType.RISK_ALERT,
        severity="high",
        title="Payment failure",
        description="Stripe payment failed",
        risk_score=0.6,
        is_resolved=False,
    )
    db_session.add(event)
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/compliance/events/{event.id}/resolve",
        params={"resolution": "Investigated — false positive"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Event resolved"
    assert data["event_id"] == str(event.id)


async def test_resolve_event_default_resolution(async_client, auth_headers, db_session):
    """Without specifying resolution, should use 'Auto-resolved'."""
    event = ComplianceEvent(
        id=uuid.uuid4(),
        event_type=ComplianceEventType.AUDIT_LOG,
        severity="low",
        title="Audit entry",
        description="Auto-generated",
        risk_score=0.0,
    )
    db_session.add(event)
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/compliance/events/{event.id}/resolve",
        headers=auth_headers,
    )
    assert response.status_code == 200
