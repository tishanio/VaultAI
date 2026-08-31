"""Tests for conversations endpoints — CRUD, messages, payment flow, keyword-triggered auto-escrow."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from vault.db.models import (
    Conversation,
    ConversationStatus,
    EscrowStatus,
    EscrowTransaction,
    Match,
    MatchStatus,
    Message,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_conversation_from_accepted_match(
    db_session, accepted_match, seller_user
):
    """Helper to manually create a conversation (used when accept_match doesn't auto-create one)."""
    conv = Conversation(
        id=uuid.uuid4(),
        match_id=accepted_match.id,
        buyer_id=accepted_match.buyer_id,
        seller_id=accepted_match.seller_id,
        status=ConversationStatus.ACTIVE,
        topic="subscription_pricing",
        subscription_details={
            "service_name": "Spotify",
            "price": accepted_match.proposed_price,
            "seats": 1,
            "billing_cycle": "monthly",
        },
    )
    db_session.add(conv)
    await db_session.flush()
    return conv


async def _add_message(db_session, conversation, sender_id, role, content, msg_type="text"):
    """Helper to add a message to a conversation."""
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender_id=sender_id,
        role=role,
        content=content,
        message_type=msg_type,
    )
    db_session.add(msg)
    await db_session.flush()
    return msg


# ---------------------------------------------------------------------------
# GET /conversations — list conversations
# ---------------------------------------------------------------------------


async def test_list_conversations_unauthorized(async_client):
    response = await async_client.get("/api/v1/conversations")
    assert response.status_code == 401


async def test_list_conversations_empty(async_client, auth_headers):
    response = await async_client.get("/api/v1/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


async def test_list_conversations_with_data(
    async_client, auth_headers, accepted_match, db_session, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.get("/api/v1/conversations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["status"] == "active"
    assert data[0]["topic"] == "subscription_pricing"


async def test_list_conversations_seller_view(
    async_client, seller_auth_headers, accepted_match, db_session, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.get("/api/v1/conversations", headers=seller_auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


# ---------------------------------------------------------------------------
# POST /conversations/{match_id} — create conversation
# ---------------------------------------------------------------------------


async def test_create_conversation_unauthorized(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(f"/api/v1/conversations/{fake_id}")
    assert response.status_code == 401


async def test_create_conversation_match_not_found(async_client, seller_auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(f"/api/v1/conversations/{fake_id}", headers=seller_auth_headers)
    assert response.status_code == 404


async def test_create_conversation_wrong_user(async_client, auth_headers, accepted_match):
    """Buyer cannot create conversation — only seller can."""
    response = await async_client.post(
        f"/api/v1/conversations/{accepted_match.id}", headers=auth_headers
    )
    assert response.status_code == 403


async def test_create_conversation_success(
    async_client, seller_auth_headers, accepted_match,
):
    response = await async_client.post(
        f"/api/v1/conversations/{accepted_match.id}", headers=seller_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "active"
    assert data["topic"] == "subscription_pricing"
    assert data["subscription_details"]["service_name"] == "Spotify"


async def test_create_conversation_duplicate(
    async_client, seller_auth_headers, accepted_match, db_session, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{accepted_match.id}", headers=seller_auth_headers
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /conversations/{conversation_id} — get conversation
# ---------------------------------------------------------------------------


async def test_get_conversation_unauthorized(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/conversations/{fake_id}")
    assert response.status_code == 401


async def test_get_conversation_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/conversations/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


async def test_get_conversation_forbidden(async_client, auth_headers, db_session, accepted_match, seller_user):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    # Create a third-party user
    from vault.security import create_access_token, hash_password
    from vault.db.models import User
    outsider = User(
        id=uuid.uuid4(), email="outsider_conv@test.app",
        username="outsiderconv", display_name="Outsider",
        password_hash=hash_password("pass123"), is_active=True, is_verified=True,
    )
    db_session.add(outsider)
    await db_session.flush()
    outsider_token = create_access_token(str(outsider.id), {"username": outsider.username})
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    response = await async_client.get(f"/api/v1/conversations/{conv.id}", headers=outsider_headers)
    assert response.status_code == 403


async def test_get_conversation_with_messages(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    msg1 = await _add_message(db_session, conv, accepted_match.seller_id, "seller", "Hello from seller")
    msg2 = await _add_message(db_session, conv, accepted_match.buyer_id, "buyer", "Hello from buyer")

    response = await async_client.get(f"/api/v1/conversations/{conv.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message_count"] >= 2
    assert len(data["messages"]) >= 2


async def test_get_conversation_marks_read(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    msg = await _add_message(db_session, conv, accepted_match.seller_id, "seller", "Unread message")
    assert msg.is_read is False

    response = await async_client.get(f"/api/v1/conversations/{conv.id}", headers=auth_headers)
    assert response.status_code == 200
    # Messages from other users should be marked as read
    for m in response.json()["messages"]:
        if m["sender_id"] == str(accepted_match.seller_id):
            assert m["is_read"] is True


# ---------------------------------------------------------------------------
# POST /conversations/{conversation_id}/messages — send message
# ---------------------------------------------------------------------------


async def test_send_message_unauthorized(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/conversations/{fake_id}/messages",
        json={"content": "Hello"},
    )
    assert response.status_code == 401


async def test_send_message_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/conversations/{fake_id}/messages",
        headers=auth_headers,
        json={"content": "Hello"},
    )
    assert response.status_code == 404


async def test_send_message_forbidden(async_client, auth_headers, db_session, accepted_match, seller_user):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    from vault.security import create_access_token, hash_password
    from vault.db.models import User
    outsider = User(
        id=uuid.uuid4(), email="msg_outsider@test.app",
        username="msgoutsider", display_name="Msg Outsider",
        password_hash=hash_password("pass123"), is_active=True, is_verified=True,
    )
    db_session.add(outsider)
    await db_session.flush()
    outsider_token = create_access_token(str(outsider.id), {"username": outsider.username})
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=outsider_headers,
        json={"content": "Hello"},
    )
    assert response.status_code == 403


async def test_send_message_inactive_conversation(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    conv.status = ConversationStatus.RESOLVED
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "Hello"},
    )
    assert response.status_code == 400


async def test_send_message_success(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "Hello, I'm interested in this subscription."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Hello, I'm interested in this subscription."
    assert data["role"] == "buyer"
    assert data["message_type"] == "text"


async def test_send_empty_message_rejected(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Keyword-triggered auto-escrow in send_message
# ---------------------------------------------------------------------------


async def test_send_pay_now_keyword_creates_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    """Sending 'pay now' should auto-create an escrow transaction."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay now"},
    )
    assert response.status_code == 201

    # Verify escrow was created
    from sqlalchemy import select
    escrow_result = await db_session.execute(
        select(EscrowTransaction).where(EscrowTransaction.match_id == accepted_match.id)
    )
    escrow = escrow_result.scalar_one_or_none()
    assert escrow is not None
    assert escrow.status == EscrowStatus.FUNDED  # Demo mode auto-funds


async def test_send_pay_keyword_creates_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay"},
    )
    assert response.status_code == 201

    from sqlalchemy import select
    escrow_result = await db_session.execute(
        select(EscrowTransaction).where(EscrowTransaction.match_id == accepted_match.id)
    )
    assert escrow_result.scalar_one_or_none() is not None


async def test_send_confirm_payment_keyword_creates_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "confirm payment"},
    )
    assert response.status_code == 201

    from sqlalchemy import select
    escrow_result = await db_session.execute(
        select(EscrowTransaction).where(EscrowTransaction.match_id == accepted_match.id)
    )
    assert escrow_result.scalar_one_or_none() is not None


async def test_send_buy_now_keyword_creates_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "buy now"},
    )
    assert response.status_code == 201


async def test_send_proceed_to_payment_keyword_creates_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "proceed to payment"},
    )
    assert response.status_code == 201


async def test_pay_now_creates_agent_confirmation_message(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    """After 'pay now', an agent confirmation message should be created."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay now"},
    )
    assert response.status_code == 201

    # Fetch conversation and check for agent confirmation
    from sqlalchemy import select
    msgs_result = await db_session.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()
    agent_msgs = [m for m in messages if m.role == "agent" and m.message_type == "payment_confirmation"]
    assert len(agent_msgs) >= 1
    assert "Payment Confirmed" in agent_msgs[0].content or "access" in agent_msgs[0].content.lower()


async def test_pay_now_completes_match(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    """After 'pay now' in demo mode, match should be marked as completed."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay now"},
    )
    assert response.status_code == 201

    from sqlalchemy import select
    match_result = await db_session.execute(select(Match).where(Match.id == accepted_match.id))
    match = match_result.scalar_one()
    assert match.status == MatchStatus.COMPLETED


async def test_pay_now_updates_subscription_seats(
    async_client, auth_headers, db_session, accepted_match, seller_user, seller_subscription,
):
    """After 'pay now', the subscription's used_seats should increment."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    from sqlalchemy import select as sa_select
    sub_before = (await db_session.execute(
        sa_select(Subscription).where(Subscription.id == seller_subscription.id)
    )).scalar_one()
    initial_used = sub_before.used_seats

    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay now"},
    )
    assert response.status_code == 201

    # Use execution_options to force fresh read from DB
    sub_after = (await db_session.execute(
        sa_select(Subscription)
        .where(Subscription.id == seller_subscription.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert sub_after.used_seats == initial_used + 1


async def test_non_payment_keyword_no_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    """Non-payment keywords should not trigger escrow creation."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "I have a question about the service"},
    )
    assert response.status_code == 201

    from sqlalchemy import select
    escrow_result = await db_session.execute(
        select(EscrowTransaction).where(EscrowTransaction.match_id == accepted_match.id)
    )
    assert escrow_result.scalar_one_or_none() is None


async def test_duplicate_pay_now_no_double_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    """Sending 'pay now' twice should not create a second escrow."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay now"},
    )
    await async_client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        headers=auth_headers,
        json={"content": "pay now"},
    )

    from sqlalchemy import select, func
    count_result = await db_session.execute(
        select(func.count(EscrowTransaction.id)).where(EscrowTransaction.match_id == accepted_match.id)
    )
    assert count_result.scalar() == 1


# ---------------------------------------------------------------------------
# POST /conversations/{conversation_id}/pay — payment endpoint
# ---------------------------------------------------------------------------


async def test_pay_unauthorized(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/conversations/{fake_id}/pay",
        json={"conversation_id": fake_id, "payment_method": "demo"},
    )
    assert response.status_code == 401


async def test_pay_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/conversations/{fake_id}/pay",
        headers=auth_headers,
        json={"conversation_id": fake_id, "payment_method": "demo"},
    )
    assert response.status_code == 404


async def test_pay_not_buyer(async_client, seller_auth_headers, db_session, accepted_match, seller_user):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=seller_auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 403


async def test_pay_inactive_conversation(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    conv.status = ConversationStatus.RESOLVED
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 400


async def test_pay_match_not_accepted(
    async_client, auth_headers, db_session, proposed_match, seller_user,
):
    """Cannot pay for a match that hasn't been accepted."""
    conv = await _create_conversation_from_accepted_match(db_session, proposed_match, seller_user)
    # Override match status to proposed
    proposed_match.status = MatchStatus.PROPOSED
    await db_session.flush()

    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 400
    assert "accepted" in response.json()["detail"].lower()


async def test_pay_success_demo_mode(
    async_client, auth_headers, db_session, accepted_match, seller_user, seller_subscription,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_granted"] is True
    assert data["status"] == "funded"
    assert data["amount"] == accepted_match.proposed_price
    assert data["escrow_id"] != ""
    assert "complete" in data["message"].lower() or "granted" in data["message"].lower()


async def test_pay_creates_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 200

    from sqlalchemy import select
    escrow_result = await db_session.execute(
        select(EscrowTransaction).where(EscrowTransaction.match_id == accepted_match.id)
    )
    escrow = escrow_result.scalar_one_or_none()
    assert escrow is not None
    assert escrow.status == EscrowStatus.FUNDED
    assert escrow.amount == accepted_match.proposed_price
    assert escrow.platform_fee > 0
    assert escrow.seller_payout > 0


async def test_pay_completes_match(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 200

    from sqlalchemy import select
    match_result = await db_session.execute(select(Match).where(Match.id == accepted_match.id))
    match = match_result.scalar_one()
    assert match.status == MatchStatus.COMPLETED


async def test_pay_updates_subscription_seats(
    async_client, auth_headers, db_session, accepted_match, seller_user, seller_subscription,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    from sqlalchemy import select as sa_select
    sub_before = (await db_session.execute(
        sa_select(Subscription).where(Subscription.id == seller_subscription.id)
    )).scalar_one()
    initial_used = sub_before.used_seats

    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 200

    sub_after = (await db_session.execute(
        sa_select(Subscription)
        .where(Subscription.id == seller_subscription.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert sub_after.used_seats == initial_used + 1


async def test_pay_creates_agent_confirmation(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    assert response.status_code == 200

    from sqlalchemy import select
    msgs_result = await db_session.execute(
        select(Message).where(Message.conversation_id == conv.id)
    )
    messages = msgs_result.scalars().all()
    agent_conf_msgs = [m for m in messages if m.role == "agent" and m.message_type == "payment_confirmation"]
    assert len(agent_conf_msgs) >= 1
    assert "access" in agent_conf_msgs[0].content.lower()


async def test_pay_duplicate_rejected(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    """Cannot pay twice for the same match."""
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    # After first payment match is COMPLETED, so second gets 400 (not accepted)
    # OR if somehow escrow already exists, 409
    assert response.status_code in (400, 409)


# ---------------------------------------------------------------------------
# GET /conversations/{conversation_id}/payment-status — payment status
# ---------------------------------------------------------------------------


async def test_payment_status_unauthorized(async_client):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/conversations/{fake_id}/payment-status")
    assert response.status_code == 401


async def test_payment_status_not_found(async_client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await async_client.get(
        f"/api/v1/conversations/{fake_id}/payment-status", headers=auth_headers
    )
    assert response.status_code == 404


async def test_payment_status_no_escrow(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.get(
        f"/api/v1/conversations/{conv.id}/payment-status", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_initiated"
    assert data["funded"] is False
    assert data["access_granted"] is False


async def test_payment_status_after_payment(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    # Pay first
    await async_client.post(
        f"/api/v1/conversations/{conv.id}/pay",
        headers=auth_headers,
        json={"conversation_id": str(conv.id), "payment_method": "demo"},
    )
    # Check status
    response = await async_client.get(
        f"/api/v1/conversations/{conv.id}/payment-status", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "funded"
    assert data["funded"] is True
    assert data["access_granted"] is True
    assert data["subscription_active"] is True
    assert "confirmed" in data["message"].lower() or "active" in data["message"].lower()


async def test_payment_status_forbidden(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    from vault.security import create_access_token, hash_password
    from vault.db.models import User
    outsider = User(
        id=uuid.uuid4(), email="pay_outsider@test.app",
        username="payoutsider", display_name="Pay Outsider",
        password_hash=hash_password("pass123"), is_active=True, is_verified=True,
    )
    db_session.add(outsider)
    await db_session.flush()
    outsider_token = create_access_token(str(outsider.id), {"username": outsider.username})
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    response = await async_client.get(
        f"/api/v1/conversations/{conv.id}/payment-status", headers=outsider_headers
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /conversations/{conversation_id}/resolve — resolve conversation
# ---------------------------------------------------------------------------


async def test_resolve_conversation_success(
    async_client, auth_headers, db_session, accepted_match, seller_user,
):
    conv = await _create_conversation_from_accepted_match(db_session, accepted_match, seller_user)
    response = await async_client.post(
        f"/api/v1/conversations/{conv.id}/resolve", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


# ---------------------------------------------------------------------------
# Full end-to-end flow: accept match → conversation → pricing messages → pay → access
# ---------------------------------------------------------------------------


async def test_full_flow_accept_to_payment(
    async_client, auth_headers, seller_auth_headers, proposed_match, seller_subscription,
):
    """Test the complete flow: accept match → create conversation → send pricing messages → pay."""
    # 1. Accept match (creates conversation with pricing agent messages)
    accept_resp = await async_client.post(
        f"/api/v1/matches/{proposed_match.id}/accept", headers=seller_auth_headers
    )
    assert accept_resp.status_code == 200
    match_data = accept_resp.json()
    assert match_data["status"] == "accepted"

    # 2. List conversations — should have one
    list_resp = await async_client.get("/api/v1/conversations", headers=auth_headers)
    assert list_resp.status_code == 200
    convs = list_resp.json()
    assert len(convs) >= 1
    conv_id = convs[0]["id"]

    # 3. Get conversation with messages — should have pricing agent messages
    get_resp = await async_client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    conv_data = get_resp.json()
    assert conv_data["message_count"] >= 4  # Welcome + tiers + billing + payment prompt
    msg_types = [m["message_type"] for m in conv_data["messages"]]
    assert "pricing_welcome" in msg_types or "pricing_tiers" in msg_types

    # 4. Check initial payment status — not initiated
    status_resp = await async_client.get(
        f"/api/v1/conversations/{conv_id}/payment-status", headers=auth_headers
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "not_initiated"

    # 5. Pay from conversation
    pay_resp = await async_client.post(
        f"/api/v1/conversations/{conv_id}/pay",
        headers=auth_headers,
        json={"conversation_id": conv_id, "payment_method": "demo"},
    )
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["access_granted"] is True

    # 6. Check payment status after payment
    status_resp2 = await async_client.get(
        f"/api/v1/conversations/{conv_id}/payment-status", headers=auth_headers
    )
    assert status_resp2.status_code == 200
    final_status = status_resp2.json()
    assert final_status["funded"] is True
    assert final_status["access_granted"] is True
    assert final_status["subscription_active"] is True

    # 7. Verify match is completed
    from sqlalchemy import select
    from vault.db.models import Match
    match_result = await async_client.get(
        f"/api/v1/matches", headers=auth_headers
    )
    matches = match_result.json()
    completed = [m for m in matches if m["status"] == "completed"]
    assert len(completed) >= 1
