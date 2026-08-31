"""Vault database models — complete schema for all entities."""
from __future__ import annotations

from vault.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = [
    "User",
    "Subscription",
    "SubscriptionUsage",
    "MarketListing",
    "Match",
    "Conversation",
    "Message",
    "EscrowTransaction",
    "KYCVerification",
    "ReputationScore",
    "Dispute",
    "Payout",
    "ComplianceEvent",
    "Notification",
]

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, PyEnum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class SubscriptionTier(str, PyEnum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    FAMILY = "family"


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PENDING = "pending"


class ListingStatus(str, PyEnum):
    ACTIVE = "active"
    MATCHED = "matched"
    PAUSED = "paused"
    REMOVED = "removed"


class MatchStatus(str, PyEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    COMPLETED = "completed"


class ConversationStatus(str, PyEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"
    CLOSED = "closed"


class EscrowStatus(str, PyEnum):
    CREATED = "created"
    FUNDED = "funded"
    HELD = "held"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class KYCStatus(str, PyEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DisputeStatus(str, PyEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class PayoutStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceEventType(str, PyEnum):
    TOS_VIOLATION = "tos_violation"
    RISK_ALERT = "risk_alert"
    CIRCUIT_BREAKER = "circuit_breaker"
    AUDIT_LOG = "audit_log"


# ---------------------------------------------------------------------------
# User & Authentication
# ---------------------------------------------------------------------------

class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en-US", nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stripe_connect_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_contact_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_fund_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    listings: Mapped[list["MarketListing"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    matches_as_buyer: Mapped[list["Match"]] = relationship(
        back_populates="buyer", foreign_keys="Match.buyer_id", cascade="all, delete-orphan"
    )
    matches_as_seller: Mapped[list["Match"]] = relationship(
        back_populates="seller", foreign_keys="Match.seller_id", cascade="all, delete-orphan"
    )
    kyc: Mapped[list["KYCVerification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reputation: Mapped["Optional[ReputationScore]"] = relationship(back_populates="user", uselist=False)

    __table_args__ = (
        Index("ix_users_location", "latitude", "longitude"),
    )


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    service_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tier: Mapped[SubscriptionTier] = mapped_column(String(20), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(String(20), default=SubscriptionStatus.ACTIVE, nullable=False)
    monthly_cost: Mapped[float] = mapped_column(Float, nullable=False)
    max_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    used_seats: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    billing_cycle_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-28
    next_billing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    usage_records: Mapped[list["SubscriptionUsage"]] = relationship(back_populates="subscription", cascade="all, delete-orphan")
    listings: Mapped[list["MarketListing"]] = relationship(back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_subscriptions_service_user", "service_name", "user_id"),
    )


# ---------------------------------------------------------------------------
# Usage Tracking
# ---------------------------------------------------------------------------

class SubscriptionUsage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_usage"

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usage_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    usage_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100
    session_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    peak_usage_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-23
    device_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    subscription: Mapped["Subscription"] = relationship(back_populates="usage_records")

    __table_args__ = (
        Index("ix_usage_period", "subscription_id", "period_start", "period_end"),
    )


# ---------------------------------------------------------------------------
# Market Listings
# ---------------------------------------------------------------------------

class MarketListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_listings"

    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    status: Mapped[ListingStatus] = mapped_column(String(20), default=ListingStatus.ACTIVE, nullable=False)
    asking_price: Mapped[float] = mapped_column(Float, nullable=False)
    dynamic_price: Mapped[float] = mapped_column(Float, nullable=False)
    seats_available: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_schedule: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    geo_radius_km: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    min_trust_score: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    seller: Mapped["User"] = relationship(back_populates="listings")
    subscription: Mapped["Subscription"] = relationship(back_populates="listings")
    matches: Mapped[list["Match"]] = relationship(back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_listings_active_status", "status"),
        Index("ix_listings_price", "dynamic_price"),
    )


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

class Match(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "matches"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market_listings.id"), nullable=False, index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[MatchStatus] = mapped_column(String(20), default=MatchStatus.PROPOSED, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    proximity_score: Mapped[float] = mapped_column(Float, nullable=False)
    schedule_score: Mapped[float] = mapped_column(Float, nullable=False)
    proposed_price: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    listing: Mapped["MarketListing"] = relationship(back_populates="matches")
    buyer: Mapped["User"] = relationship(foreign_keys=[buyer_id], back_populates="matches_as_buyer")
    seller: Mapped["User"] = relationship(foreign_keys=[seller_id], back_populates="matches_as_seller")
    escrow: Mapped["Optional[EscrowTransaction]"] = relationship(back_populates="match", uselist=False)

    __table_args__ = (
        Index("ix_matches_status", "status"),
        Index("ix_matches_score", "match_score"),
    )


# ---------------------------------------------------------------------------
# Escrow / Payments
# ---------------------------------------------------------------------------

class EscrowTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "escrow_transactions"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, unique=True, index=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_transfer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_gateway: Mapped[str] = mapped_column(String(20), default="stripe", nullable=False)  # stripe | razorpay
    status: Mapped[EscrowStatus] = mapped_column(String(20), default=EscrowStatus.CREATED, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, nullable=False)
    seller_payout: Mapped[float] = mapped_column(Float, nullable=False)
    fee_percentage: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 0.12 = 12%
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    funded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="escrow")


# ---------------------------------------------------------------------------
# KYC / Verification
# ---------------------------------------------------------------------------

class KYCVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kyc_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    onfido_check_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[KYCStatus] = mapped_column(String(20), default=KYCStatus.PENDING, nullable=False)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    document_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_flags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship(back_populates="kyc")


# ---------------------------------------------------------------------------
# Reputation
# ---------------------------------------------------------------------------

class ReputationScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reputation_scores"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0.0 - 1.0
    reliability_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    communication_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    payment_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    positive_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dispute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    account_age_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="reputation")


# ---------------------------------------------------------------------------
# Disputes
# ---------------------------------------------------------------------------

class Dispute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "disputes"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    filed_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(String(20), default=DisputeStatus.OPEN, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_urls: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Payouts
# ---------------------------------------------------------------------------

class Payout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payouts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[PayoutStatus] = mapped_column(String(20), default=PayoutStatus.PENDING, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payout_method: Mapped[str] = mapped_column(String(50), nullable=False)  # bank_transfer, stripe_balance
    tax_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tax_form_1099k: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Compliance & Risk
# ---------------------------------------------------------------------------

class ComplianceEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compliance_events"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[ComplianceEventType] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    action_taken: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_compliance_severity", "severity", "is_resolved"),
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # push, email, telegram
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Conversations (Match-to-Payment Flow)
# ---------------------------------------------------------------------------

class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, unique=True, index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[ConversationStatus] = mapped_column(String(20), default=ConversationStatus.ACTIVE, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "subscription_pricing", "payment_confirmation"
    subscription_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # pricing, tiers, etc
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    match: Mapped["Match"] = relationship(foreign_keys=[match_id])
    buyer: Mapped["User"] = relationship(foreign_keys=[buyer_id])
    seller: Mapped["User"] = relationship(foreign_keys=[seller_id])
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_conversations_status", "status"),
        Index("ix_conversations_topic", "topic"),
    )


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user", "agent", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)  # "text", "payment_request", "action"
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # payment details, action data, etc
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship(foreign_keys=[sender_id])

    __table_args__ = (
        Index("ix_messages_conversation", "conversation_id"),
        Index("ix_messages_sender", "sender_id"),
    )

