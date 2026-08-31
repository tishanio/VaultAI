"""Shared test configuration for agent microservice tests."""
from __future__ import annotations

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
    Match,
    MatchStatus,
    MarketListing,
    Payout,
    PayoutStatus,
    ReputationScore,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    User,
    UserRole,
)
from vault.security import hash_password

settings.DEMO_MODE = True
settings.DB_ECHO = False

TEST_DATABASE_URL = settings.DATABASE_URL.replace("vault_db", "vault_test_db")


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
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


async def _override_get_db(db_session: AsyncSession):
    async def _gen():
        yield db_session
    return _gen()


def _make_mock_publisher():
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.publish = AsyncMock(return_value="mock-msg-id")
    return mock


@pytest_asyncio.fixture(scope="function")
async def usage_intel_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from services.usage_intelligence.main import app
    from vault import events as events_module
    from services.usage_intelligence import main as ui_main

    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    mock_pub = _make_mock_publisher()
    patches = [
        patch.object(events_module, "publisher", mock_pub),
        patch.object(ui_main, "publisher", mock_pub),
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
async def trust_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from services.trust_verification.main import app
    from vault import events as events_module
    from services.trust_verification import main as tv_main

    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    mock_pub = _make_mock_publisher()
    patches = [
        patch.object(events_module, "publisher", mock_pub),
        patch.object(tv_main, "publisher", mock_pub),
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
async def matching_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from services.market_matching.main import app
    from vault import events as events_module
    from services.market_matching import main as mm_main

    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    mock_pub = _make_mock_publisher()
    patches = [
        patch.object(events_module, "publisher", mock_pub),
        patch.object(mm_main, "publisher", mock_pub),
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
async def finance_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from services.financial_orchestration.main import app
    from vault import events as events_module
    from services.financial_orchestration import main as fo_main

    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    mock_pub = _make_mock_publisher()
    patches = [
        patch.object(events_module, "publisher", mock_pub),
        patch.object(fo_main, "publisher", mock_pub),
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
async def compliance_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from services.compliance_risk.main import app
    from vault import events as events_module
    from services.compliance_risk import main as cr_main

    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    mock_pub = _make_mock_publisher()
    patches = [
        patch.object(events_module, "publisher", mock_pub),
        patch.object(cr_main, "publisher", mock_pub),
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


# ---------------------------------------------------------------------------
# Shared entity fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def agent_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="agent-test@vault.app",
        username="agenttest",
        display_name="Agent Test User",
        password_hash=hash_password("testpass123"),
        is_active=True,
        is_verified=True,
        latitude=40.7128,
        longitude=-74.0060,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def agent_seller(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="agent-seller@vault.app",
        username="agentseller",
        display_name="Agent Seller",
        password_hash=hash_password("sellerpass123"),
        is_active=True,
        is_verified=True,
        latitude=40.7150,
        longitude=-74.0090,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def agent_subscription(db_session: AsyncSession, agent_seller: User) -> Subscription:
    sub = Subscription(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        service_name="Spotify",
        service_category="music",
        tier=SubscriptionTier.FAMILY,
        status=SubscriptionStatus.ACTIVE,
        monthly_cost=16.99,
        max_seats=6,
        used_seats=0,
        billing_cycle_day=15,
        usage_data={"usage_percentage": 20.0, "peak_hours": [17, 18, 19, 20]},
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest_asyncio.fixture(scope="function")
async def agent_listing(
    db_session: AsyncSession, agent_seller: User, agent_subscription: Subscription,
) -> MarketListing:
    listing = MarketListing(
        id=uuid.uuid4(),
        seller_id=agent_seller.id,
        subscription_id=agent_subscription.id,
        status=ListingStatus.ACTIVE,
        asking_price=5.00,
        dynamic_price=4.50,
        seats_available=3,
        description="Spotify Family — 3 seats available.",
        geo_radius_km=25.0,
        min_trust_score=0.5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


@pytest_asyncio.fixture(scope="function")
async def agent_seller_reputation(db_session: AsyncSession, agent_seller: User) -> ReputationScore:
    rep = ReputationScore(
        id=uuid.uuid4(),
        user_id=agent_seller.id,
        overall_score=0.85,
        reliability_score=0.9,
        communication_score=0.8,
        payment_score=0.85,
        total_transactions=10,
        positive_reviews=8,
        negative_reviews=1,
    )
    db_session.add(rep)
    await db_session.flush()
    return rep


@pytest_asyncio.fixture(scope="function")
async def agent_match(
    db_session: AsyncSession, agent_user: User, agent_seller: User, agent_listing: MarketListing,
) -> Match:
    match = Match(
        id=uuid.uuid4(),
        listing_id=agent_listing.id,
        buyer_id=agent_user.id,
        seller_id=agent_seller.id,
        status=MatchStatus.ACCEPTED,
        match_score=0.85,
        trust_score=0.9,
        proximity_score=0.8,
        schedule_score=0.7,
        proposed_price=4.50,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(match)
    await db_session.flush()
    return match


@pytest_asyncio.fixture(scope="function")
async def agent_escrow(db_session: AsyncSession, agent_match: Match) -> EscrowTransaction:
    escrow = EscrowTransaction(
        id=uuid.uuid4(),
        match_id=agent_match.id,
        status=EscrowStatus.FUNDED,
        amount=4.50,
        platform_fee=0.54,
        seller_payout=3.96,
        fee_percentage=12.0,
        currency="USD",
        stripe_payment_intent_id=f"pi_test_{uuid.uuid4().hex[:12]}",
        funded_at=datetime.now(timezone.utc),
    )
    db_session.add(escrow)
    await db_session.flush()
    return escrow
