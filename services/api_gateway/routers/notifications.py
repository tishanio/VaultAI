from __future__ import annotations

"""Notifications router — CRUD, real-time push, and channel management."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from vault.db.models import Notification, User
from vault.db.session import get_db
from vault.events import Event, publisher
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/notifications")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NotificationChannel(str, PyEnum):
    PUSH = "push"
    EMAIL = "email"
    TELEGRAM = "telegram"
    IN_APP = "in_app"


class NotificationResponse(BaseModel):
    id: str
    channel: str
    title: str
    body: str
    is_read: bool
    created_at: str
    read_at: Optional[str] = None
    meta: Optional[dict] = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class MarkReadRequest(BaseModel):
    notification_ids: list[str] = Field(min_length=1, max_length=100)


class SendNotificationRequest(BaseModel):
    user_id: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2000)
    meta: Optional[dict] = None


class NotificationPreferences(BaseModel):
    push_enabled: bool = True
    email_enabled: bool = True
    telegram_enabled: bool = False
    match_notifications: bool = True
    payment_notifications: bool = True
    compliance_notifications: bool = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    channel: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated notifications for the current user."""
    query = select(Notification).where(Notification.user_id == user.id)
    count_query = select(func.count(Notification.id)).where(Notification.user_id == user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)
        count_query = count_query.where(Notification.is_read == False)

    if channel:
        query = query.where(Notification.channel == channel)
        count_query = count_query.where(Notification.channel == channel)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    notifications = result.scalars().all()

    unread_count_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    unread_count = unread_count_result.scalar() or 0

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id),
                channel=n.channel,
                title=n.title,
                body=n.body,
                is_read=n.is_read,
                created_at=n.created_at.isoformat(),
                read_at=n.read_at.isoformat() if n.read_at else None,
                meta=n.meta,
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count")
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the count of unread notifications."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    count = result.scalar() or 0
    return {"unread_count": count}


@router.post("/mark-read", status_code=status.HTTP_200_OK)
async def mark_notifications_read(
    body: MarkReadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark specific notifications as read."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            Notification.id.in_([uuid.UUID(nid) for nid in body.notification_ids]),
            Notification.user_id == user.id,
        )
        .values(is_read=True, read_at=now)
    )
    await db.flush()
    return {"message": "Notifications marked as read", "count": len(body.notification_ids)}


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True, read_at=now)
    )
    await db.flush()
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notification)
    await db.flush()


# ---------------------------------------------------------------------------
# Admin/System endpoints
# ---------------------------------------------------------------------------

@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_notification(
    body: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a notification to a user (internal/admin endpoint)."""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == body.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    notification = Notification(
        id=uuid.uuid4(),
        user_id=target_user.id,
        channel=body.channel.value,
        title=body.title,
        body=body.body,
        meta=body.meta,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    await db.flush()

    # Publish event for real-time delivery
    await publisher.publish(
        Event(
            "notification.sent",
            {
                "notification_id": str(notification.id),
                "user_id": body.user_id,
                "channel": body.channel.value,
                "title": body.title,
            },
            source="api-gateway",
        )
    )

    return {"notification_id": str(notification.id), "message": "Notification sent"}


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------

async def handle_match_event(event: Event):
    """Send notification when a match is proposed or accepted."""
    user_id = event.data.get("buyer_id") or event.data.get("seller_id")
    if not user_id:
        return

    event_type = event.event_type
    if "proposed" in event_type:
        title = "New Match Proposal"
        body = f"You have a new subscription match waiting for review."
    elif "accepted" in event_type:
        title = "Match Accepted"
        body = "A subscription match has been accepted. Escrow will be created."
    elif "completed" in event_type:
        title = "Match Completed"
        body = "A subscription match has been completed successfully."
    else:
        title = "Match Update"
        body = "There's an update on one of your matches."

    await publisher.publish(
        Event(
            "notification.send",
            {"user_id": user_id, "title": title, "body": body, "channel": "in_app"},
            source="api-gateway",
        )
    )


async def handle_escrow_event(event: Event):
    """Send notification for escrow status changes."""
    event_type = event.event_type
    if "funded" in event_type:
        title = "Escrow Funded"
        body = "Payment has been secured in escrow."
    elif "released" in event_type:
        title = "Escrow Released"
        body = "Funds have been released from escrow."
    elif "disputed" in event_type:
        title = "Escrow Disputed"
        body = "A dispute has been filed. Funds are on hold."
    else:
        title = "Escrow Update"
        body = "There's an update on your escrow transaction."

    user_id = event.data.get("buyer_id") or event.data.get("seller_id")
    if user_id:
        await publisher.publish(
            Event(
                "notification.send",
                {"user_id": user_id, "title": title, "body": body, "channel": "in_app"},
                source="api-gateway",
            )
        )
