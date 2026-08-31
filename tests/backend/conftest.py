from __future__ import annotations

"""Pytest configuration and fixtures for backend tests."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from unittest.mock import AsyncMock, patch

from vault.config import settings
from vault.db.base import Base
from vault.db.session import get_db
from vault.db.models import (
    ComplianceEvent,
    ComplianceEventType,
    Dispute,
    DisputeStatus,
    EscrowStatus,
    EscrowTransaction,
    ListingStatus,
    MarketListing,
    Match,
    MatchStatus,
    Notification,
    Payout,
    PayoutStatus,
    ReputationScore,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    User,
    UserRole,
)
from vault.security import create_access_token, hash_password

# Override settings for testing
settings.DEMO_MODE = True
settings.DB_ECHO = False

# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("vault_db", "vault_test_db")


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database override."""
    from services.api_gateway.main import app
    from vault import events as events_module

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Mock the event publisher so tests don't need Redis
    mock_publisher = AsyncMock()
    mock_publisher.connect = AsyncMock()
    mock_publisher.close = AsyncMock()
    mock_publisher.publish = AsyncMock(return_value="mock-msg-id")

    # Patch publisher in all modules that import it directly
    patches = [
        patch.object(events_module, "publisher", mock_publisher),
        patch("services.api_gateway.routers.escrow.publisher", mock_publisher),
        patch("services.api_gateway.routers.marketplace.publisher", mock_publisher),
        patch("services.api_gateway.routers.subscriptions.publisher", mock_publisher),
        patch("services.api_gateway.routers.auth.publisher", mock_publisher),
        patch("services.api_gateway.routers.matches.publisher", mock_publisher),
        patch("services.api_gateway.routers.notifications.publisher", mock_publisher),
        patch("services.api_gateway.routers.conversations.publisher", mock_publisher),
    ]
    for p in patches:
        p.start()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        for p in patches:
            p.stop()
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user (acts as buyer)."""
    user = User(
        id=uuid.uuid4(),
        email="test@vault.app",
        username="testuser",
        display_name="Test User",
        password_hash=hash_password("testpassword123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> dict:
    """Create auth headers for the test user."""
    token = create_access_token(str(test_user.id), {"username": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    user = User(
        id=uuid.uuid4(),
        email="admin@vault.app",
        username="adminuser",
        display_name="Admin User",
        password_hash=hash_password("adminpass123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_auth_headers(admin_user: User) -> dict:
    """Create auth headers for the admin user."""
    token = create_access_token(str(admin_user.id), {"username": admin_user.username})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Shared fixtures for multi-entity tests (escrow, marketplace, matches)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def seller_user(db_session: AsyncSession) -> User:
    """Create a seller user."""
    user = User(
        id=uuid.uuid4(),
        email="seller@vault.app",
        username="selleruser",
        display_name="Seller User",
        password_hash=hash_password("sellerpass123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def seller_auth_headers(seller_user: User) -> dict:
    """Create auth headers for the seller."""
    token = create_access_token(str(seller_user.id), {"username": seller_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def seller_subscription(db_session: AsyncSession, seller_user: User) -> Subscription:
    """Create a subscription owned by the seller."""
    sub = Subscription(
        id=uuid.uuid4(),
        user_id=seller_user.id,
        service_name="Spotify",
        service_category="music",
        tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE,
        monthly_cost=16.99,
        max_seats=6,
        used_seats=0,
        billing_cycle_day=15,
        usage_data={"usage_percentage": 20.0},
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest_asyncio.fixture(scope="function")
async def active_listing(
    db_session: AsyncSession, seller_user: User, seller_subscription: Subscription
) -> MarketListing:
    """Create an active marketplace listing."""
    listing = MarketListing(
        id=uuid.uuid4(),
        seller_id=seller_user.id,
        subscription_id=seller_subscription.id,
        status=ListingStatus.ACTIVE,
        asking_price=5.00,
        dynamic_price=4.50,
        seats_available=3,
        description="Spotify Family — 3 seats available.",
        geo_radius_km=15.0,
        min_trust_score=0.5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


@pytest_asyncio.fixture(scope="function")
async def proposed_match(
    db_session: AsyncSession,
    test_user: User,
    seller_user: User,
    active_listing: MarketListing,
) -> Match:
    """Create a proposed match between buyer (test_user) and seller."""
    match = Match(
        id=uuid.uuid4(),
        listing_id=active_listing.id,
        buyer_id=test_user.id,
        seller_id=seller_user.id,
        status=MatchStatus.PROPOSED,
        match_score=0.85,
        trust_score=0.9,
        proximity_score=0.8,
        schedule_score=0.7,
        proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(match)
    await db_session.flush()
    return match


@pytest_asyncio.fixture(scope="function")
async def accepted_match(
    db_session: AsyncSession,
    test_user: User,
    seller_user: User,
    active_listing: MarketListing,
) -> Match:
    """Create an accepted match between buyer (test_user) and seller."""
    match = Match(
        id=uuid.uuid4(),
        listing_id=active_listing.id,
        buyer_id=test_user.id,
        seller_id=seller_user.id,
        status=MatchStatus.ACCEPTED,
        match_score=0.85,
        trust_score=0.9,
        proximity_score=0.8,
        schedule_score=0.7,
        proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(match)
    await db_session.flush()
    return match


@pytest_asyncio.fixture(scope="function")
async def funded_escrow(
    db_session: AsyncSession, accepted_match: Match
) -> EscrowTransaction:
    """Create a funded escrow for an accepted match."""
    escrow = EscrowTransaction(
        id=uuid.uuid4(),
        match_id=accepted_match.id,
        status=EscrowStatus.FUNDED,
        amount=accepted_match.proposed_price,
        platform_fee=round(accepted_match.proposed_price * 0.12, 2),
        seller_payout=round(accepted_match.proposed_price * 0.88, 2),
        fee_percentage=12.0,
        currency="USD",
        stripe_payment_intent_id=f"pi_test_{uuid.uuid4().hex[:12]}",
        funded_at=datetime.now(timezone.utc),
    )
    db_session.add(escrow)
    await db_session.flush()
    return escrow

