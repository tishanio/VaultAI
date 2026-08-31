"""Initial database schema for Vault

Revision ID: 001_initial
Revises:
Create Date: 2024-01-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("phone", sa.String(20), unique=True, nullable=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en-US"),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("stripe_connect_account_id", sa.String(100), nullable=True),
        sa.Column("telegram_chat_id", sa.String(50), nullable=True),
        sa.Column("fcm_token", sa.String(500), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_location", "users", ["latitude", "longitude"])

    # --- Subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("service_name", sa.String(100), nullable=False, index=True),
        sa.Column("service_category", sa.String(50), nullable=False, index=True),
        sa.Column("service_logo_url", sa.String(500), nullable=True),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("monthly_cost", sa.Float, nullable=False),
        sa.Column("max_seats", sa.Integer, nullable=False),
        sa.Column("used_seats", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("billing_cycle_day", sa.Integer, nullable=False),
        sa.Column("next_billing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_service_user", "subscriptions", ["service_name", "user_id"])

    # --- Subscription Usage ---
    op.create_table(
        "subscription_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("subscriptions.id"), nullable=False, index=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_minutes", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("usage_hours", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("usage_percentage", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("session_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("peak_usage_hour", sa.Integer, nullable=True),
        sa.Column("device_info", JSONB, nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_usage_period", "subscription_usage", ["subscription_id", "period_start", "period_end"])

    # --- Market Listings ---
    op.create_table(
        "market_listings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("seller_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("subscriptions.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("asking_price", sa.Float, nullable=False),
        sa.Column("dynamic_price", sa.Float, nullable=False),
        sa.Column("seats_available", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("preferred_schedule", JSONB, nullable=True),
        sa.Column("geo_radius_km", sa.Float, nullable=False, server_default=sa.text("10.0")),
        sa.Column("min_trust_score", sa.Float, nullable=False, server_default=sa.text("0.6")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_listings_active_status", "market_listings", ["status"])
    op.create_index("ix_listings_price", "market_listings", ["dynamic_price"])

    # --- Matches ---
    op.create_table(
        "matches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("listing_id", UUID(as_uuid=True), sa.ForeignKey("market_listings.id"), nullable=False, index=True),
        sa.Column("buyer_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("seller_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("match_score", sa.Float, nullable=False),
        sa.Column("trust_score", sa.Float, nullable=False),
        sa.Column("proximity_score", sa.Float, nullable=False),
        sa.Column("schedule_score", sa.Float, nullable=False),
        sa.Column("proposed_price", sa.Float, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_matches_status", "matches", ["status"])
    op.create_index("ix_matches_score", "matches", ["match_score"])

    # --- Escrow Transactions ---
    op.create_table(
        "escrow_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", UUID(as_uuid=True), sa.ForeignKey("matches.id"), nullable=False, unique=True, index=True),
        sa.Column("stripe_payment_intent_id", sa.String(100), nullable=True, unique=True),
        sa.Column("stripe_transfer_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("platform_fee", sa.Float, nullable=False),
        sa.Column("seller_payout", sa.Float, nullable=False),
        sa.Column("fee_percentage", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("funded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_reason", sa.Text, nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- KYC Verifications ---
    op.create_table(
        "kyc_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("onfido_check_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("document_country", sa.String(2), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("risk_flags", JSONB, nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Reputation Scores ---
    op.create_table(
        "reputation_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("overall_score", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("reliability_score", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("communication_score", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("payment_score", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("total_transactions", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("positive_reviews", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("negative_reviews", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("dispute_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("account_age_days", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Disputes ---
    op.create_table(
        "disputes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", UUID(as_uuid=True), sa.ForeignKey("matches.id"), nullable=False, index=True),
        sa.Column("filed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence_urls", JSONB, nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Payouts ---
    op.create_table(
        "payouts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("stripe_transfer_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("payout_method", sa.String(50), nullable=False),
        sa.Column("tax_year", sa.Integer, nullable=True),
        sa.Column("tax_form_1099k", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Compliance Events ---
    op.create_table(
        "compliance_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("event_type", sa.String(30), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("action_taken", sa.String(100), nullable=True),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_compliance_severity", "compliance_events", ["severity", "is_resolved"])

    # --- Notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("compliance_events")
    op.drop_table("payouts")
    op.drop_table("disputes")
    op.drop_table("reputation_scores")
    op.drop_table("kyc_verifications")
    op.drop_table("escrow_transactions")
    op.drop_table("matches")
    op.drop_table("market_listings")
    op.drop_table("subscription_usage")
    op.drop_table("subscriptions")
    op.drop_index("ix_users_location", table_name="users")
    op.drop_table("users")
