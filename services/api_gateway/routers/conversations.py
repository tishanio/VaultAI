"""Conversations router — Real-time messaging for match negotiations with payment integration."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    Conversation,
    ConversationStatus,
    EscrowStatus,
    EscrowTransaction,
    MarketListing,
    Match,
    MatchStatus,
    Message,
    Subscription,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventType, publisher
from services.api_gateway.routers.auth import get_current_user

router = APIRouter(prefix="/conversations")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    id: str
    sender_id: str
    role: str
    content: str
    message_type: str
    is_read: bool
    meta: Optional[dict] = None
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    match_id: str
    buyer_id: str
    seller_id: str
    status: str
    topic: str
    subscription_details: Optional[dict] = None
    message_count: int = 0
    messages: list[MessageResponse] = Field(default_factory=list)
    created_at: str


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text", description="text, payment_request, or action")
    meta: Optional[dict] = None


class PaymentRequest(BaseModel):
    """Request to initiate payment within a conversation."""
    conversation_id: str
    payment_method: str = Field(default="card", description="card, bank_transfer, or demo")


class PaymentResponse(BaseModel):
    """Response after initiating payment from conversation."""
    escrow_id: str
    client_secret: str
    payment_intent_id: str
    amount: float
    platform_fee: float
    seller_payout: str
    status: str
    access_granted: bool
    message: str


class PaymentStatusResponse(BaseModel):
    """Payment status check response."""
    escrow_id: str
    status: str
    amount: float
    funded: bool
    access_granted: bool
    subscription_active: bool
    message: str


# ---------------------------------------------------------------------------
# Conversation Endpoints
# ---------------------------------------------------------------------------

@router.post("/{match_id}", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    match_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a conversation for a match (seller accepts match)."""
    match_result = await db.execute(select(Match).where(Match.id == match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    if match.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the seller can initiate this conversation")

    existing = await db.execute(select(Conversation).where(Conversation.match_id == match.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation already exists for this match")

    # Fetch subscription details from listing
    listing_result = await db.execute(select(MarketListing).where(MarketListing.id == match.listing_id))
    listing = listing_result.scalar_one_or_none()
    service_name = "Unknown"
    if listing:
        sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
        sub = sub_result.scalar_one_or_none()
        if sub:
            service_name = sub.service_name

    conversation = Conversation(
        id=uuid.uuid4(),
        match_id=match.id,
        buyer_id=match.buyer_id,
        seller_id=match.seller_id,
        status=ConversationStatus.ACTIVE,
        topic="subscription_pricing",
        subscription_details={
            "service_name": service_name,
            "price": match.proposed_price,
            "seats": 1,
            "billing_cycle": "monthly",
        },
    )
    db.add(conversation)
    await db.flush()

    await publisher.publish(Event(
        EventType.MATCH_ACCEPTED,
        {
            "conversation_id": str(conversation.id),
            "match_id": str(match.id),
            "buyer_id": str(match.buyer_id),
            "seller_id": str(match.seller_id),
        },
        source="api-gateway",
    ))

    return ConversationResponse(
        id=str(conversation.id),
        match_id=str(conversation.match_id),
        buyer_id=str(conversation.buyer_id),
        seller_id=str(conversation.seller_id),
        status=conversation.status.value,
        topic=conversation.topic,
        subscription_details=conversation.subscription_details,
        created_at=conversation.created_at.isoformat(),
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    status_filter: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user (as buyer or seller)."""
    query = select(Conversation).where(
        (Conversation.buyer_id == user.id) | (Conversation.seller_id == user.id)
    )

    if status_filter:
        query = query.where(Conversation.status == status_filter)

    query = query.order_by(Conversation.created_at.desc())
    result = await db.execute(query)
    conversations = result.scalars().all()

    # Count messages per conversation using a subquery to avoid lazy loading
    conv_ids = [c.id for c in conversations]
    if conv_ids:
        count_result = await db.execute(
            select(
                Message.conversation_id,
                func.count(Message.id).label("msg_count"),
            )
            .where(Message.conversation_id.in_(conv_ids))
            .group_by(Message.conversation_id)
        )
        msg_counts = {row.conversation_id: row.msg_count for row in count_result}
    else:
        msg_counts = {}

    return [
        ConversationResponse(
            id=str(c.id),
            match_id=str(c.match_id),
            buyer_id=str(c.buyer_id),
            seller_id=str(c.seller_id),
            status=c.status.value,
            topic=c.topic,
            subscription_details=c.subscription_details,
            message_count=msg_counts.get(c.id, 0),
            created_at=c.created_at.isoformat(),
        )
        for c in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation with all messages."""
    conversation_result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conversation = conversation_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.buyer_id != user.id and conversation.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this conversation")

    # Mark messages as read for current user
    if conversation.messages:
        for msg in conversation.messages:
            if msg.sender_id != user.id and not msg.is_read:
                msg.is_read = True
        await db.flush()

    return ConversationResponse(
        id=str(conversation.id),
        match_id=str(conversation.match_id),
        buyer_id=str(conversation.buyer_id),
        seller_id=str(conversation.seller_id),
        status=conversation.status.value,
        topic=conversation.topic,
        subscription_details=conversation.subscription_details,
        message_count=len(conversation.messages) if conversation.messages else 0,
        messages=[
            MessageResponse(
                id=str(m.id),
                sender_id=str(m.sender_id),
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                meta=m.meta,
                is_read=m.is_read,
                created_at=m.created_at.isoformat(),
            )
            for m in (conversation.messages or [])
        ],
        created_at=conversation.created_at.isoformat(),
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a conversation."""
    conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.buyer_id == user.id:
        role = "buyer"
    elif conversation.seller_id == user.id:
        role = "seller"
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this conversation")

    if conversation.status != ConversationStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This conversation is no longer active")

    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender_id=user.id,
        role=role,
        content=body.content,
        message_type=body.message_type,
        meta=body.meta,
    )
    db.add(message)
    await db.flush()

    # Check for payment intent keywords and auto-generate agent response
    lower_content = body.content.lower().strip()
    if lower_content in ("pay now", "pay", "confirm payment", "proceed to payment", "buy now"):
        # Auto-create escrow and respond with payment details
        match_result = await db.execute(select(Match).where(Match.id == conversation.match_id))
        match = match_result.scalar_one_or_none()
        if match and match.status == MatchStatus.ACCEPTED:
            # Check for existing escrow
            existing_escrow = await db.execute(
                select(EscrowTransaction).where(EscrowTransaction.match_id == match.id)
            )
            if not existing_escrow.scalar_one_or_none():
                # Calculate fees
                amount = match.proposed_price
                fee_pct = settings.PLATFORM_FEE_PERCENTAGE / 100.0
                platform_fee = round(amount * fee_pct, 2)
                seller_payout = round(amount - platform_fee, 2)

                escrow = EscrowTransaction(
                    id=uuid.uuid4(),
                    match_id=match.id,
                    status=EscrowStatus.CREATED,
                    amount=amount,
                    platform_fee=platform_fee,
                    seller_payout=seller_payout,
                    fee_percentage=settings.PLATFORM_FEE_PERCENTAGE,
                    currency="USD",
                )
                db.add(escrow)

                # In demo mode, auto-fund the escrow
                if settings.DEMO_MODE:
                    escrow.status = EscrowStatus.FUNDED
                    escrow.funded_at = datetime.now(timezone.utc)
                    escrow.stripe_payment_intent_id = f"pi_demo_{uuid.uuid4().hex[:16]}"

                    # Mark match as completed
                    match.status = MatchStatus.COMPLETED

                    # Update subscription used_seats
                    listing_result = await db.execute(
                        select(MarketListing).where(MarketListing.id == match.listing_id)
                    )
                    listing = listing_result.scalar_one_or_none()
                    if listing:
                        sub_result = await db.execute(
                            select(Subscription).where(Subscription.id == listing.subscription_id)
                        )
                        sub = sub_result.scalar_one_or_none()
                        if sub:
                            sub.used_seats = min(sub.used_seats + 1, sub.max_seats)

                    await db.flush()

                    # Agent payment confirmation message
                    agent_msg = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation.id,
                        sender_id=user.id,
                        role="agent",
                        content=(
                            f"✅ **Payment Confirmed!**\n\n"
                            f"• **Amount:** ${amount:.2f}\n"
                            f"• **Platform fee:** ${platform_fee:.2f}\n"
                            f"• **Seller payout:** ${seller_payout:.2f}\n"
                            f"• **Status:** Funded & Released (Demo Mode)\n\n"
                            f"🎉 Your subscription seat is now **ACTIVE**! "
                            f"You have been granted immediate access to the {conversation.subscription_details.get('service_name', 'subscription')} service.\n\n"
                            f"• 🔑 Access granted — use your existing {conversation.subscription_details.get('service_name', '')} login\n"
                            f"• 📅 Next billing cycle: 30 days from now\n"
                            f"• 🛡️ Protected by Vault escrow guarantee\n\n"
                            f"Enjoy your subscription! If you have any issues, this conversation is your support channel."
                        ),
                        message_type="payment_confirmation",
                        meta={
                            "action": "access_granted",
                            "escrow_id": str(escrow.id),
                            "amount": amount,
                            "access_granted": True,
                        },
                    )
                    db.add(agent_msg)

                    await publisher.publish(Event(
                        EventType.ESCROW_FUNDED,
                        {"escrow_id": str(escrow.id), "match_id": str(match.id), "amount": amount},
                        source="api-gateway",
                    ))
                else:
                    client_secret = f"secret_{uuid.uuid4().hex[:16]}"
                    escrow.stripe_payment_intent_id = f"pi_{uuid.uuid4().hex[:16]}"
                    await db.flush()

                    agent_msg = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation.id,
                        sender_id=user.id,
                        role="agent",
                        content=(
                            f"💳 **Payment Initiated**\n\n"
                            f"• **Amount:** ${amount:.2f}/month\n"
                            f"• **Platform fee:** ${platform_fee:.2f}\n"
                            f"• **Seller will receive:** ${seller_payout:.2f}\n\n"
                            f"Complete payment using the secure checkout. "
                            f"Your seat will be activated immediately upon successful payment."
                        ),
                        message_type="payment_initiated",
                        meta={
                            "action": "payment_pending",
                            "escrow_id": str(escrow.id),
                            "client_secret": client_secret,
                            "amount": amount,
                        },
                    )
                    db.add(agent_msg)

    # Publish event for WebSocket delivery
    await publisher.publish(Event(
        "message.sent",
        {
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "sender_id": str(user.id),
            "role": role,
            "content": body.content[:100],
        },
        source="api-gateway",
    ))

    return MessageResponse(
        id=str(message.id),
        sender_id=str(message.sender_id),
        role=message.role,
        content=message.content,
        message_type=message.message_type,
        meta=message.meta,
        is_read=message.is_read,
        created_at=message.created_at.isoformat(),
    )


@router.post("/{conversation_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a conversation as resolved."""
    conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.buyer_id != user.id and conversation.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this conversation")

    conversation.status = ConversationStatus.RESOLVED
    conversation.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    await publisher.publish(Event(
        "conversation.resolved",
        {"conversation_id": str(conversation.id)},
        source="api-gateway",
    ))

    return {"message": "Conversation resolved", "status": "resolved"}


# ---------------------------------------------------------------------------
# Payment Endpoints (within conversation flow)
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/pay", response_model=PaymentResponse)
async def initiate_payment_from_conversation(
    conversation_id: str,
    body: PaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate payment directly from a conversation — creates escrow and processes payment."""
    conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.buyer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the buyer can initiate payment")

    if conversation.status != ConversationStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conversation is no longer active")

    # Get the associated match
    match_result = await db.execute(select(Match).where(Match.id == conversation.match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    if match.status != MatchStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match must be accepted before payment")

    # Check for existing escrow
    existing = await db.execute(select(EscrowTransaction).where(EscrowTransaction.match_id == match.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already initiated for this match")

    # Calculate fees
    amount = match.proposed_price
    fee_pct = settings.PLATFORM_FEE_PERCENTAGE / 100.0
    platform_fee = round(amount * fee_pct, 2)
    seller_payout = round(amount - platform_fee, 2)

    escrow = EscrowTransaction(
        id=uuid.uuid4(),
        match_id=match.id,
        status=EscrowStatus.CREATED,
        amount=amount,
        platform_fee=platform_fee,
        seller_payout=seller_payout,
        fee_percentage=settings.PLATFORM_FEE_PERCENTAGE,
        currency="USD",
    )
    db.add(escrow)

    access_granted = False
    client_secret = ""

    if settings.DEMO_MODE or body.payment_method == "demo":
        # Demo mode: simulate instant payment and grant access
        escrow.status = EscrowStatus.FUNDED
        escrow.funded_at = datetime.now(timezone.utc)
        escrow.stripe_payment_intent_id = f"pi_demo_{uuid.uuid4().hex[:16]}"
        client_secret = f"demo_secret_{uuid.uuid4().hex[:16]}"
        access_granted = True

        # Mark match as completed
        match.status = MatchStatus.COMPLETED

        # Update subscription used_seats
        listing_result = await db.execute(select(MarketListing).where(MarketListing.id == match.listing_id))
        listing = listing_result.scalar_one_or_none()
        if listing:
            sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
            sub = sub_result.scalar_one_or_none()
            if sub:
                sub.used_seats = min(sub.used_seats + 1, sub.max_seats)

        await db.flush()

        # Send agent payment confirmation message
        agent_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            sender_id=user.id,
            role="agent",
            content=(
                f"✅ **Payment Complete — Access Granted!**\n\n"
                f"You've successfully paid **${amount:.2f}** for the "
                f"{conversation.subscription_details.get('service_name', 'subscription')} seat.\n\n"
                f"🔑 **Your access is now active!** Use your existing credentials to log in.\n\n"
                f"• Escrow ID: `{escrow.id}`\n"
                f"• Amount: ${amount:.2f}/month\n"
                f"• Platform fee: ${platform_fee:.2f}\n"
                f"• Next billing: 30 days\n\n"
                f"🛡️ Your payment is protected by Vault's escrow guarantee. "
                f"Contact support through this chat if you experience any issues."
            ),
            message_type="payment_confirmation",
            meta={
                "action": "access_granted",
                "escrow_id": str(escrow.id),
                "amount": amount,
                "access_granted": True,
            },
        )
        db.add(agent_msg)

        await publisher.publish(Event(
            EventType.ESCROW_FUNDED,
            {"escrow_id": str(escrow.id), "match_id": str(match.id), "amount": amount},
            source="api-gateway",
        ))
        await publisher.publish(Event(
            EventType.MATCH_COMPLETED,
            {"match_id": str(match.id), "buyer_id": str(user.id), "seller_id": str(match.seller_id)},
            source="api-gateway",
        ))
    else:
        # Production: create Stripe PaymentIntent
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency="usd",
                customer=user.stripe_customer_id,
                capture_method="manual",
                metadata={"escrow_id": str(escrow.id), "match_id": str(match.id)},
            )
            escrow.stripe_payment_intent_id = intent.id
            client_secret = intent.client_secret
        except Exception as e:
            logger.error("Stripe payment creation failed: {}", e)
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=f"Payment processing failed: {str(e)}")

        await db.flush()

        await publisher.publish(Event(
            EventType.ESCROW_CREATED,
            {"escrow_id": str(escrow.id), "match_id": str(match.id), "amount": amount},
            source="api-gateway",
        ))

    return PaymentResponse(
        escrow_id=str(escrow.id),
        client_secret=client_secret,
        payment_intent_id=escrow.stripe_payment_intent_id or "",
        amount=amount,
        platform_fee=platform_fee,
        seller_payout=str(seller_payout),
        status=escrow.status.value,
        access_granted=access_granted,
        message=(
            "Payment complete! Access granted."
            if access_granted
            else "Payment initiated. Complete checkout to grant access."
        ),
    )


@router.get("/{conversation_id}/payment-status", response_model=PaymentStatusResponse)
async def check_payment_status(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check payment and subscription access status for a conversation."""
    conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.buyer_id != user.id and conversation.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this conversation")

    # Find escrow for this match
    match_result = await db.execute(select(Match).where(Match.id == conversation.match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    escrow_result = await db.execute(select(EscrowTransaction).where(EscrowTransaction.match_id == match.id))
    escrow = escrow_result.scalar_one_or_none()

    if not escrow:
        return PaymentStatusResponse(
            escrow_id="",
            status="not_initiated",
            amount=match.proposed_price,
            funded=False,
            access_granted=False,
            subscription_active=False,
            message="Payment has not been initiated yet.",
        )

    funded = escrow.status in (EscrowStatus.FUNDED, EscrowStatus.RELEASED, EscrowStatus.HELD)
    access_granted = funded  # Access is granted once escrow is funded

    # Check subscription status
    listing_result = await db.execute(select(MarketListing).where(MarketListing.id == match.listing_id))
    listing = listing_result.scalar_one_or_none()
    sub_active = False
    if listing:
        sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
        sub = sub_result.scalar_one_or_none()
        if sub and sub.status.value == "active":
            sub_active = True

    messages = []
    if funded:
        messages.append("Payment confirmed. Your access is active!")
    elif escrow.status == EscrowStatus.CREATED:
        messages.append("Payment pending. Complete checkout to activate access.")
    elif escrow.status == EscrowStatus.REFUNDED:
        messages.append("Payment was refunded. Contact support for details.")
    elif escrow.status == EscrowStatus.DISPUTED:
        messages.append("Payment is under review due to a dispute.")

    return PaymentStatusResponse(
        escrow_id=str(escrow.id),
        status=escrow.status.value,
        amount=escrow.amount,
        funded=funded,
        access_granted=access_granted,
        subscription_active=sub_active,
        message=" ".join(messages),
    )
