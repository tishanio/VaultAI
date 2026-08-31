from __future__ import annotations

"""Vault API Gateway — central REST API service."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.session import get_db
from vault.events import publisher

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting Vault API Gateway v{}", settings.APP_VERSION)
    await publisher.connect()
    yield
    await publisher.close()
    logger.info("Vault API Gateway shut down")


app = FastAPI(
    title="Vault API",
    description="AI-Powered Peer-to-Peer Subscription Liquidity Platform",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all incoming requests."""
    start = datetime.now(timezone.utc)
    response = await call_next(request)
    duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    logger.info(
        "method={} path={} status={} duration_ms={:.1f}",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "not ready", "error": str(e)})


# ---------------------------------------------------------------------------
# Demo Mode
# ---------------------------------------------------------------------------

@app.post("/api/v1/demo/toggle")
async def toggle_demo_mode():
    """Toggle demo mode for hackathon presentations."""
    settings.DEMO_MODE = not settings.DEMO_MODE
    return {"demo_mode": settings.DEMO_MODE, "message": "Demo mode toggled"}


@app.post("/api/v1/demo/login")
async def demo_login(username: str = "sarahchen", db: AsyncSession = Depends(get_db)):
    """Quick login for demo users (no password required)."""
    from vault.db.models import User
    from services.api_gateway.routers.auth import create_access_token, create_refresh_token
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"Demo user '{username}' not found. Seed data first.")

    access_token = create_access_token(str(user.id), {"username": user.username})
    refresh_token = create_refresh_token(str(user.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user_id": str(user.id),
        "username": user.username,
    }


@app.post("/api/v1/demo/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """Seed database with realistic demo data for hackathon."""
    from vault.db.models import User, Subscription, MarketListing, ReputationScore
    from sqlalchemy import select
    import uuid

    # Idempotent: check if already seeded
    existing = await db.execute(select(User).where(User.username == "demo_user"))
    if existing.scalar_one_or_none():
        return {"message": "Demo data already seeded", "users": 2, "subscriptions": 3, "listings": 1}

    demo_users = [
        User(
            id=uuid.uuid4(),
            email="demo@vault.app",
            username="demo_user",
            display_name="Demo User",
            password_hash="not_a_real_hash",
            is_active=True,
            is_verified=True,
            latitude=37.7749,
            longitude=-122.4194,
        ),
        User(
            id=uuid.uuid4(),
            email="partner@vault.app",
            username="demo_partner",
            display_name="Demo Partner",
            password_hash="not_a_real_hash",
            is_active=True,
            is_verified=True,
            latitude=37.7849,
            longitude=-122.4094,
        ),
    ]

    for user in demo_users:
        db.add(user)

    await db.flush()

    demo_subscriptions = [
        Subscription(
            id=uuid.uuid4(),
            user_id=demo_users[0].id,
            service_name="Spotify",
            service_category="music",
            tier="family",
            status="active",
            monthly_cost=16.99,
            max_seats=6,
            used_seats=2,
            billing_cycle_day=15,
            usage_data={"avg_monthly_minutes": 420, "peak_hours": [21, 22, 23]},
        ),
        Subscription(
            id=uuid.uuid4(),
            user_id=demo_users[0].id,
            service_name="Google One",
            service_category="cloud_storage",
            tier="family",
            status="active",
            monthly_cost=22.99,
            max_seats=5,
            used_seats=3,
            billing_cycle_day=10,
            usage_data={"storage_used_gb": 45, "storage_total_tb": 2},
        ),
        Subscription(
            id=uuid.uuid4(),
            user_id=demo_users[0].id,
            service_name="YouTube Premium",
            service_category="streaming",
            tier="family",
            status="active",
            monthly_cost=22.99,
            max_seats=5,
            used_seats=1,
            billing_cycle_day=20,
            usage_data={"avg_monthly_hours": 8.5, "content_types": ["music", "education"]},
        ),
    ]

    for sub in demo_subscriptions:
        db.add(sub)

    await db.flush()

    demo_listings = [
        MarketListing(
            id=uuid.uuid4(),
            seller_id=demo_users[0].id,
            subscription_id=demo_subscriptions[0].id,
            status="active",
            asking_price=5.00,
            dynamic_price=4.50,
            seats_available=2,
            description="Spotify Family — 2 seats available. Late evening usage preferred.",
            geo_radius_km=15.0,
            min_trust_score=0.5,
            meta={"service_logo": "🎵", "demo": True},
        ),
    ]

    for listing in demo_listings:
        db.add(listing)

    await db.flush()

    for user in demo_users:
        rep = ReputationScore(
            id=uuid.uuid4(),
            user_id=user.id,
            overall_score=0.85,
            reliability_score=0.90,
            communication_score=0.80,
            payment_score=0.88,
            total_transactions=12,
            positive_reviews=11,
            negative_reviews=1,
        )
        db.add(rep)

    await db.commit()

    return {"message": "Demo data seeded successfully", "users": len(demo_users), "subscriptions": len(demo_subscriptions), "listings": len(demo_listings)}


# ---------------------------------------------------------------------------
# Include Routers
# ---------------------------------------------------------------------------

from services.api_gateway.routers import (
    auth,
    users,
    subscriptions,
    marketplace,
    matches,
    escrow,
    compliance,
    notifications,
    admin,
    agent,
    conversations,
)
from services.api_gateway.routers.razorpay import router as razorpay_router
from services.api_gateway.websocket import router as ws_router, ws_forwarder

app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["Auth"])
app.include_router(users.router, prefix=settings.API_PREFIX, tags=["Users"])
app.include_router(subscriptions.router, prefix=settings.API_PREFIX, tags=["Subscriptions"])
app.include_router(marketplace.router, prefix=settings.API_PREFIX, tags=["Marketplace"])
app.include_router(matches.router, prefix=settings.API_PREFIX, tags=["Matches"])
app.include_router(escrow.router, prefix=settings.API_PREFIX, tags=["Escrow"])
app.include_router(razorpay_router, prefix=settings.API_PREFIX, tags=["Razorpay"])
app.include_router(conversations.router, prefix=settings.API_PREFIX, tags=["Conversations"])
app.include_router(compliance.router, prefix=settings.API_PREFIX, tags=["Compliance"])
app.include_router(notifications.router, prefix=settings.API_PREFIX, tags=["Notifications"])
app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["Admin"])
app.include_router(agent.router, prefix=settings.API_PREFIX, tags=["Agent"])
app.include_router(ws_router, tags=["WebSocket"])
