"""Tests for database models."""
import uuid

from vault.db.models import (
    User,
    Subscription,
    MarketListing,
    Match,
    EscrowTransaction,
    KYCVerification,
    ReputationScore,
    Dispute,
    Payout,
    ComplianceEvent,
    Notification,
    UserRole,
    SubscriptionTier,
    SubscriptionStatus,
    ListingStatus,
    MatchStatus,
    EscrowStatus,
    KYCStatus,
    DisputeStatus,
    PayoutStatus,
    ComplianceEventType,
)
from vault.security import hash_password


def test_user_role_enum():
    assert UserRole.USER == "user"
    assert UserRole.ADMIN == "admin"


def test_subscription_tier_enum():
    assert SubscriptionTier.FREE == "free"
    assert SubscriptionTier.PREMIUM == "premium"


def test_subscription_status_enum():
    assert SubscriptionStatus.ACTIVE == "active"
    assert SubscriptionStatus.CANCELLED == "cancelled"


def test_listing_status_enum():
    assert ListingStatus.ACTIVE == "active"
    assert ListingStatus.MATCHED == "matched"


def test_match_status_enum():
    assert MatchStatus.PROPOSED == "proposed"
    assert MatchStatus.ACCEPTED == "accepted"
    assert MatchStatus.COMPLETED == "completed"


def test_escrow_status_enum():
    assert EscrowStatus.CREATED == "created"
    assert EscrowStatus.RELEASED == "released"


def test_kyc_status_enum():
    assert KYCStatus.PENDING == "pending"
    assert KYCStatus.VERIFIED == "verified"


def test_dispute_status_enum():
    assert DisputeStatus.OPEN == "open"
    assert DisputeStatus.RESOLVED == "resolved"


def test_payout_status_enum():
    assert PayoutStatus.PENDING == "pending"
    assert PayoutStatus.COMPLETED == "completed"


def test_compliance_event_type_enum():
    assert ComplianceEventType.TOS_VIOLATION == "tos_violation"
    assert ComplianceEventType.RISK_ALERT == "risk_alert"


def test_create_user_model():
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        display_name="Test User",
        password_hash=hash_password("password123"),
        is_active=True,
        is_verified=False,
    )
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.is_active is True
    # role defaults to the column default (UserRole.USER), but SQLAlchemy
    # doesn't apply server-side defaults until flush, so it may be None in-memory.
    assert user.role is None or user.role == UserRole.USER


def test_user_model_table_name():
    assert User.__tablename__ == "users"


def test_subscription_model_table_name():
    assert Subscription.__tablename__ == "subscriptions"


def test_market_listing_model_table_name():
    assert MarketListing.__tablename__ == "market_listings"


def test_match_model_table_name():
    assert Match.__tablename__ == "matches"


def test_escrow_model_table_name():
    assert EscrowTransaction.__tablename__ == "escrow_transactions"


def test_kyc_model_table_name():
    assert KYCVerification.__tablename__ == "kyc_verifications"


def test_reputation_model_table_name():
    assert ReputationScore.__tablename__ == "reputation_scores"
