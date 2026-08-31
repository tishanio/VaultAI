from __future__ import annotations

"""Market Matching Agent — dynamic pricing, proximity/trust/schedule scoring, real-time availability."""
import math
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Depends, FastAPI, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from vault.config import settings
from vault.db.models import (
    ListingStatus,
    MarketListing,
    Match,
    MatchStatus,
    ReputationScore,
    Subscription,
    SubscriptionUsage,
    User,
)
from vault.db.session import get_db
from vault.events import Event, EventConsumer, publisher


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    buyer_id: str
    listing_id: str
    buyer_latitude: float | None = None
    buyer_longitude: float | None = None
    preferred_hours: list[int] | None = None


class MatchCandidate(BaseModel):
    listing_id: str
    seller_id: str
    service_name: str
    dynamic_price: float
    match_score: float
    trust_score: float
    proximity_score: float
    schedule_score: float
    distance_km: float | None
    seats_available: int
    seller_reputation: float
    match_reasons: list[str]


class MatchResult(BaseModel):
    buyer_id: str
    candidates: list[MatchCandidate]
    best_match: MatchCandidate | None
    search_radius_km: float
    total_listings_found: int
    pricing_adjustment: float
    generated_at: str


class PriceUpdate(BaseModel):
    listing_id: str
    old_price: float
    new_price: float
    reason: str
    demand_score: float
    supply_score: float


class AvailabilityUpdate(BaseModel):
    listing_id: str
    seats_available: int
    status: str
    last_checked: str


# ---------------------------------------------------------------------------
# Pricing Model
# ---------------------------------------------------------------------------

class DynamicPricingEngine:
    """Calculates optimal pricing based on supply, demand, and market conditions."""

    BASE_FEE_PERCENTAGE = 12.0
    MIN_PRICE_MULTIPLIER = 0.5
    MAX_PRICE_MULTIPLIER = 1.5
    DEMAND_WINDOW_HOURS = 24

    @staticmethod
    def calculate_dynamic_price(
        base_price: float,
        demand_score: float,
        supply_score: float,
        trust_score: float,
        proximity_score: float,
    ) -> float:
        """Calculate dynamic price using weighted factors."""
        # Demand-supply ratio
        ds_ratio = demand_score / max(supply_score, 0.01)

        # Trust discount — higher trust = lower price (more reliable)
        trust_factor = 1.0 - (trust_score * 0.1)  # up to 10% discount

        # Proximity bonus — closer = cheaper (less friction)
        proximity_factor = 1.0 - (proximity_score * 0.05)  # up to 5% discount

        # Combined multiplier
        multiplier = ds_ratio * trust_factor * proximity_factor
        multiplier = max(DynamicPricingEngine.MIN_PRICE_MULTIPLIER,
                        min(DynamicPricingEngine.MAX_PRICE_MULTIPLIER, multiplier))

        dynamic_price = round(base_price * multiplier, 2)
        return dynamic_price

    @staticmethod
    def calculate_demand_score(active_matches: int, max_concurrent: int = 5) -> float:
        """Score demand from 0 to 1 based on active match requests."""
        return min(1.0, active_matches / max_concurrent)

    @staticmethod
    def calculate_supply_score(seats_available: int, total_seats: int) -> float:
        """Score supply from 0 to 1 (higher = more supply)."""
        return seats_available / max(total_seats, 1)


# ---------------------------------------------------------------------------
# Matching Algorithm
# ---------------------------------------------------------------------------

class MatchScorer:
    """Multi-factor match scoring algorithm."""

    WEIGHTS = {
        "trust": 0.35,
        "proximity": 0.25,
        "schedule": 0.25,
        "price": 0.15,
    }

    @staticmethod
    def calculate_trust_score(
        seller_reputation: float,
        kyc_verified: bool,
        total_transactions: int,
    ) -> float:
        """Score trust from 0 to 1."""
        base = seller_reputation
        kyc_bonus = 0.15 if kyc_verified else 0.0
        experience_bonus = min(0.1, total_transactions * 0.01)
        return min(1.0, base + kyc_bonus + experience_bonus)

    @staticmethod
    def calculate_proximity_score(distance_km: float, max_radius_km: float) -> float:
        """Score proximity from 0 to 1 (closer = higher)."""
        if distance_km is None or max_radius_km <= 0:
            return 0.5  # Default when no location data
        return max(0.0, 1.0 - (distance_km / max_radius_km))

    @staticmethod
    def calculate_schedule_score(
        seller_peak_hours: list[int] | None,
        buyer_preferred_hours: list[int] | None,
    ) -> float:
        """Score schedule compatibility from 0 to 1."""
        if not seller_peak_hours or not buyer_preferred_hours:
            return 0.5  # Default when no schedule data
        overlap = set(seller_peak_hours) & set(buyer_preferred_hours)
        total = set(seller_peak_hours) | set(buyer_preferred_hours)
        return len(overlap) / max(len(total), 1)

    @staticmethod
    def calculate_price_score(
        proposed_price: float,
        max_budget: float,
    ) -> float:
        """Score price competitiveness from 0 to 1."""
        if max_budget <= 0:
            return 0.5
        return max(0.0, 1.0 - (proposed_price / max_budget))

    @classmethod
    def calculate_match_score(
        cls,
        trust: float,
        proximity: float,
        schedule: float,
        price: float,
    ) -> float:
        """Calculate weighted total match score."""
        score = (
            trust * cls.WEIGHTS["trust"]
            + proximity * cls.WEIGHTS["proximity"]
            + schedule * cls.WEIGHTS["schedule"]
            + price * cls.WEIGHTS["price"]
        )
        return round(score, 3)

    @staticmethod
    def generate_match_reasons(
        trust_score: float,
        proximity_score: float,
        schedule_score: float,
        price_score: float,
        distance_km: float | None,
        service_name: str,
    ) -> list[str]:
        """Generate human-readable match reasons."""
        reasons = []
        if trust_score >= 0.8:
            reasons.append("Highly trusted seller")
        elif trust_score >= 0.6:
            reasons.append("Good reputation")

        if distance_km is not None and distance_km < 5:
            reasons.append(f"Very close ({distance_km:.1f} km away)")
        elif distance_km is not None and distance_km < 15:
            reasons.append(f"Nearby ({distance_km:.1f} km)")

        if schedule_score >= 0.7:
            reasons.append("Schedule aligns well")
        elif schedule_score >= 0.4:
            reasons.append("Moderate schedule overlap")

        if price_score >= 0.7:
            reasons.append("Great price")
        elif price_score >= 0.4:
            reasons.append("Fair price")

        if not reasons:
            reasons.append(f"Available {service_name} seat")

        return reasons


# ---------------------------------------------------------------------------
# Distance Calculation
# ---------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lon points using Haversine formula."""
    R = 6371.0  # Earth radius in km
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Market Matching Agent starting")
    await publisher.connect()
    yield
    await publisher.close()


app = FastAPI(title="Vault Market Matching Agent", version=settings.APP_VERSION, lifespan=lifespan)
pricing_engine = DynamicPricingEngine()
scorer = MatchScorer()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "market-matching"}


@app.post("/api/v1/matching/search", response_model=MatchResult)
async def search_matches(body: MatchRequest, db: AsyncSession = Depends(get_db)):
    """Search for the best matching listings for a buyer."""
    buyer_result = await db.execute(select(User).where(User.id == body.buyer_id))
    buyer = buyer_result.scalar_one_or_none()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    buyer_lat = body.buyer_latitude or buyer.latitude
    buyer_lon = body.buyer_longitude or buyer.longitude

    # Fetch active listings
    listings_result = await db.execute(
        select(MarketListing).where(MarketListing.status == ListingStatus.ACTIVE)
    )
    listings = listings_result.scalars().all()

    candidates = []
    for listing in listings:
        # Get subscription details
        sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
        sub = sub_result.scalar_one_or_none()
        if not sub or sub.status != "active":
            continue

        # Get seller info
        seller_result = await db.execute(select(User).where(User.id == listing.seller_id))
        seller = seller_result.scalar_one_or_none()
        if not seller:
            continue

        # Get seller reputation
        rep_result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == listing.seller_id))
        rep = rep_result.scalar_one_or_none()

        # Calculate scores
        seller_rep_score = rep.overall_score if rep else 0.5
        kyc_verified = seller.is_verified
        total_tx = rep.total_transactions if rep else 0

        trust_score = scorer.calculate_trust_score(seller_rep_score, kyc_verified, total_tx)

        # Proximity
        distance_km = None
        proximity_score = 0.5
        if buyer_lat and buyer_lon and seller.latitude and seller.longitude:
            distance_km = haversine_distance(buyer_lat, buyer_lon, seller.latitude, seller.longitude)
            proximity_score = scorer.calculate_proximity_score(distance_km, listing.geo_radius_km)
            if distance_km > listing.geo_radius_km:
                continue  # Outside radius

        # Schedule
        schedule_score = scorer.calculate_schedule_score(
            sub.usage_data.get("peak_hours") if sub.usage_data else None,
            body.preferred_hours,
        )

        # Price
        max_budget = sub.monthly_cost * 0.8  # Max share price
        price_score = scorer.calculate_price_score(listing.dynamic_price, max_budget)

        # Total match score
        match_score = scorer.calculate_match_score(trust_score, proximity_score, schedule_score, price_score)

        # Generate reasons
        reasons = scorer.generate_match_reasons(
            trust_score, proximity_score, schedule_score, price_score,
            distance_km, sub.service_name,
        )

        candidates.append(MatchCandidate(
            listing_id=str(listing.id),
            seller_id=str(listing.seller_id),
            service_name=sub.service_name,
            dynamic_price=listing.dynamic_price,
            match_score=match_score,
            trust_score=round(trust_score, 3),
            proximity_score=round(proximity_score, 3),
            schedule_score=round(schedule_score, 3),
            distance_km=round(distance_km, 1) if distance_km else None,
            seats_available=listing.seats_available,
            seller_reputation=seller_rep_score,
            match_reasons=reasons,
        ))

    # Sort by match score
    candidates.sort(key=lambda c: c.match_score, reverse=True)
    best = candidates[0] if candidates else None

    # Dynamic pricing adjustment
    pricing_adj = 1.0
    if candidates:
        avg_score = sum(c.match_score for c in candidates) / len(candidates)
        pricing_adj = 1.0 + (avg_score - 0.5) * 0.2  # ±10% based on match quality

    return MatchResult(
        buyer_id=body.buyer_id,
        candidates=candidates,
        best_match=best,
        search_radius_km=25.0,
        total_listings_found=len(listings),
        pricing_adjustment=round(pricing_adj, 2),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/v1/matching/availability/{listing_id}", response_model=AvailabilityUpdate)
async def check_availability(listing_id: str, db: AsyncSession = Depends(get_db)):
    """Check real-time availability for a listing."""
    result = await db.execute(select(MarketListing).where(MarketListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Check active matches for real-time seat count
    active_count = (await db.execute(
        select(func.count(Match.id)).where(
            Match.listing_id == listing.id,
            Match.status.in_([MatchStatus.PROPOSED, MatchStatus.ACCEPTED]),
        )
    )).scalar() or 0

    sub_result = await db.execute(select(Subscription).where(Subscription.id == listing.subscription_id))
    sub = sub_result.scalar_one_or_none()
    total_seats = sub.max_seats if sub else listing.seats_available
    available = max(0, listing.seats_available - active_count)

    return AvailabilityUpdate(
        listing_id=listing_id,
        seats_available=available,
        status=listing.status.value,
        last_checked=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/api/v1/matching/pricing/update")
async def update_pricing(db: AsyncSession = Depends(get_db)):
    """Recalculate dynamic pricing for all active listings."""
    result = await db.execute(select(MarketListing).where(MarketListing.status == ListingStatus.ACTIVE))
    listings = result.scalars().all()

    updates = []
    for listing in listings:
        # Get demand from active matches
        from sqlalchemy import func
        match_count = (await db.execute(
            select(func.count(Match.id)).where(
                Match.listing_id == listing.id,
                Match.status == MatchStatus.PROPOSED,
            )
        )).scalar() or 0

        demand_score = pricing_engine.calculate_demand_score(match_count)
        supply_score = pricing_engine.calculate_supply_score(listing.seats_available, listing.seats_available + 2)

        new_price = pricing_engine.calculate_dynamic_price(
            base_price=listing.asking_price,
            demand_score=demand_score,
            supply_score=supply_score,
            trust_score=0.7,  # Default
            proximity_score=0.5,  # Default
        )

        old_price = listing.dynamic_price
        if abs(new_price - old_price) > 0.01:
            listing.dynamic_price = new_price
            updates.append(PriceUpdate(
                listing_id=str(listing.id),
                old_price=old_price,
                new_price=new_price,
                reason=f"Demand: {demand_score:.2f}, Supply: {supply_score:.2f}",
                demand_score=demand_score,
                supply_score=supply_score,
            ))

    await db.flush()
    return {"updated": len(updates), "updates": [u.model_dump() for u in updates]}
