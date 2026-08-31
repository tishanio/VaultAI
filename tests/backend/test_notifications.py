"""Tests for notification endpoints — CRUD, mark-read, send, unread count."""
import uuid
from datetime import datetime, timezone

import pytest
from vault.db.models import Notification

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper: create a notification in the DB
# ---------------------------------------------------------------------------

async def _create_notification(
    db_session, user_id, title="Test Notification", body="Test body",
    channel="in_app", is_read=False,
):
    n = Notification(
        id=uuid.uuid4(), user_id=user_id, channel=channel,
        title=title, body=body, is_read=is_read,
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add(n)
    await db_session.flush()
    return n


# ---------------------------------------------------------------------------
# GET /notifications
# ---------------------------------------------------------------------------

async def test_list_notifications_unauthorized(async_client):
    response = await async_client.get("/api/v1/notifications")
    assert response.status_code == 401


async def test_list_notifications_empty(async_client, auth_headers):
    response = await async_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert data["total"] == 0
    assert data["unread_count"] == 0


async def test_list_notifications_with_data(
    async_client, auth_headers, db_session, test_user,
):
    await _create_notification(db_session, test_user.id, "First", "Body 1")
    await _create_notification(db_session, test_user.id, "Second", "Body 2", is_read=True)
    await db_session.flush()

    response = await async_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["unread_count"] == 1


async def test_list_notifications_unread_only(
    async_client, auth_headers, db_session, test_user,
):
    await _create_notification(db_session, test_user.id, "Unread", is_read=False)
    await _create_notification(db_session, test_user.id, "Read", is_read=True)
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/notifications", headers=auth_headers, params={"unread_only": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["title"] == "Unread"


async def test_list_notifications_filter_by_channel(
    async_client, auth_headers, db_session, test_user,
):
    await _create_notification(db_session, test_user.id, "Push", channel="push")
    await _create_notification(db_session, test_user.id, "Email", channel="email")
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/notifications", headers=auth_headers, params={"channel": "push"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["channel"] == "push"


async def test_list_notifications_pagination(
    async_client, auth_headers, db_session, test_user,
):
    for i in range(5):
        await _create_notification(db_session, test_user.id, f"Note {i}")

    response = await async_client.get(
        "/api/v1/notifications", headers=auth_headers,
        params={"page": 1, "page_size": 2}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["notifications"]) == 2
    assert data["total"] == 5


async def test_list_notifications_own_only(
    async_client, auth_headers, db_session, test_user, seller_user,
):
    """Notifications for other users should not appear."""
    await _create_notification(db_session, test_user.id, "My Notification")
    await _create_notification(db_session, seller_user.id, "Seller Notification")
    await db_session.flush()

    response = await async_client.get("/api/v1/notifications", headers=auth_headers)
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["title"] == "My Notification"


# ---------------------------------------------------------------------------
# GET /notifications/unread-count
# ---------------------------------------------------------------------------

async def test_unread_count_unauthorized(async_client):
    response = await async_client.get("/api/v1/notifications/unread-count")
    assert response.status_code == 401


async def test_unread_count_zero(async_client, auth_headers):
    response = await async_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["unread_count"] == 0


async def test_unread_count_with_data(
    async_client, auth_headers, db_session, test_user,
):
    await _create_notification(db_session, test_user.id, "Unread 1", is_read=False)
    await _create_notification(db_session, test_user.id, "Unread 2", is_read=False)
    await _create_notification(db_session, test_user.id, "Read 1", is_read=True)
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["unread_count"] == 2


# ---------------------------------------------------------------------------
# POST /notifications/mark-read
# ---------------------------------------------------------------------------

async def test_mark_read_unauthorized(async_client):
    response = await async_client.post("/api/v1/notifications/mark-read", json={"notification_ids": []})
    assert response.status_code == 401


async def test_mark_read_success(
    async_client, auth_headers, db_session, test_user,
):
    n1 = await _create_notification(db_session, test_user.id, "N1", is_read=False)
    n2 = await _create_notification(db_session, test_user.id, "N2", is_read=False)
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/notifications/mark-read", headers=auth_headers,
        json={"notification_ids": [str(n1.id), str(n2.id)]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2


async def test_mark_read_partial(
    async_client, auth_headers, db_session, test_user,
):
    n1 = await _create_notification(db_session, test_user.id, "N1", is_read=False)
    n2 = await _create_notification(db_session, test_user.id, "N2", is_read=False)
    await db_session.flush()

    await async_client.post(
        "/api/v1/notifications/mark-read", headers=auth_headers,
        json={"notification_ids": [str(n1.id)]}
    )

    # Verify n2 is still unread
    response = await async_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert response.json()["unread_count"] == 1


async def test_mark_read_own_only(
    async_client, auth_headers, db_session, test_user, seller_user,
):
    """Marking read should only affect own notifications."""
    my_notif = await _create_notification(db_session, test_user.id, "Mine", is_read=False)
    seller_notif = await _create_notification(db_session, seller_user.id, "Seller's", is_read=False)
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/notifications/mark-read", headers=auth_headers,
        json={"notification_ids": [str(my_notif.id), str(seller_notif.id)]}
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /notifications/mark-all-read
# ---------------------------------------------------------------------------

async def test_mark_all_read_unauthorized(async_client):
    response = await async_client.post("/api/v1/notifications/mark-all-read")
    assert response.status_code == 401


async def test_mark_all_read_success(
    async_client, auth_headers, db_session, test_user,
):
    await _create_notification(db_session, test_user.id, "N1", is_read=False)
    await _create_notification(db_session, test_user.id, "N2", is_read=False)
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/notifications/mark-all-read", headers=auth_headers
    )
    assert response.status_code == 200

    # Verify all are read
    response = await async_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert response.json()["unread_count"] == 0


async def test_mark_all_read_idempotent(
    async_client, auth_headers, db_session, test_user,
):
    """Calling mark-all-read when already all read should work."""
    await _create_notification(db_session, test_user.id, "N1", is_read=True)
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/notifications/mark-all-read", headers=auth_headers
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /notifications/{id}
# ---------------------------------------------------------------------------

async def test_delete_notification_unauthorized(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.delete(f"/api/v1/notifications/{fake_id}")
    assert response.status_code == 401


async def test_delete_notification_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.delete(
        f"/api/v1/notifications/{fake_id}", headers=auth_headers
    )
    assert response.status_code == 404


async def test_delete_notification_success(
    async_client, auth_headers, db_session, test_user,
):
    n = await _create_notification(db_session, test_user.id, "To Delete")
    await db_session.flush()

    response = await async_client.delete(
        f"/api/v1/notifications/{n.id}", headers=auth_headers
    )
    assert response.status_code == 204

    # Verify it's gone
    response = await async_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.json()["total"] == 0


async def test_delete_notification_own_only(
    async_client, auth_headers, db_session, test_user, seller_user,
):
    """Cannot delete another user's notification."""
    seller_notif = await _create_notification(db_session, seller_user.id, "Seller's")
    await db_session.flush()

    response = await async_client.delete(
        f"/api/v1/notifications/{seller_notif.id}", headers=auth_headers
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /notifications/send
# ---------------------------------------------------------------------------

async def test_send_notification_not_found(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        "/api/v1/notifications/send",
        json={"user_id": fake_id, "title": "Test", "body": "Body"}
    )
    assert response.status_code == 404


async def test_send_notification_success(
    async_client, db_session, test_user,
):
    response = await async_client.post(
        "/api/v1/notifications/send",
        json={
            "user_id": str(test_user.id),
            "title": "System Alert",
            "body": "Your account has been reviewed.",
            "channel": "in_app",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "notification_id" in data
    assert data["message"] == "Notification sent"


async def test_send_notification_with_meta(
    async_client, db_session, test_user,
):
    response = await async_client.post(
        "/api/v1/notifications/send",
        json={
            "user_id": str(test_user.id),
            "title": "Match Update",
            "body": "New match found.",
            "channel": "push",
            "meta": {"match_id": str(uuid.uuid4()), "type": "new_match"},
        }
    )
    assert response.status_code == 201
