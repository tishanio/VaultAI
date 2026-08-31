"""
Comprehensive seed script for Vault database.
Run: cd vault && python scripts/seed_real_data.py

Populates the database with realistic data:
- 10 users (sellers + buyers)
- 15 subscriptions across various services
- 12 marketplace listings
- 8 matches (some accepted, some proposed, some rejected)
- 4 conversations with pricing agent messages
- Reputation scores for all users
- Notifications
"""

import asyncio
import os
import sys
import uuid
import random
from datetime import datetime, timedelta, timezone

# Add vault to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Security
from vault.security import hash_password

# Models
from vault.db.models import (
    User,
    Subscription,
    MarketListing,
    Match,
    Conversation,
    Message,
    EscrowTransaction,
    ReputationScore,
    Notification,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://vault:vault_secret@localhost:5432/vault_db"
)

# ---------------------------------------------------------------------------
# Realistic data definitions
# ---------------------------------------------------------------------------

USERS = [
    {
        "email": "sarah.chen@gmail.com",
        "username": "sarahchen",
        "display_name": "Sarah Chen",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "marcus.johnson@outlook.com",
        "username": "marcusj",
        "display_name": "Marcus Johnson",
        "latitude": 37.7849,
        "longitude": -122.4094,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "priya.patel@yahoo.com",
        "username": "priyap",
        "display_name": "Priya Patel",
        "latitude": 37.7949,
        "longitude": -122.3994,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "alex.rodriguez@gmail.com",
        "username": "alexr",
        "display_name": "Alex Rodriguez",
        "latitude": 37.7649,
        "longitude": -122.4294,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "emma.wilson@icloud.com",
        "username": "emmaw",
        "display_name": "Emma Wilson",
        "latitude": 37.7549,
        "longitude": -122.4394,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "james.kim@gmail.com",
        "username": "jamesk",
        "display_name": "James Kim",
        "latitude": 37.8049,
        "longitude": -122.3894,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "olivia.brown@outlook.com",
        "username": "oliviab",
        "display_name": "Olivia Brown",
        "latitude": 37.7449,
        "longitude": -122.4494,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "david.lee@gmail.com",
        "username": "davidl",
        "display_name": "David Lee",
        "latitude": 37.8149,
        "longitude": -122.3794,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "sofia.garcia@yahoo.com",
        "username": "sofiag",
        "display_name": "Sofia Garcia",
        "latitude": 37.7349,
        "longitude": -122.4594,
        "timezone": "America/Los_Angeles",
    },
    {
        "email": "ethan.taylor@icloud.com",
        "username": "ethant",
        "display_name": "Ethan Taylor",
        "latitude": 37.8249,
        "longitude": -122.3694,
        "timezone": "America/Los_Angeles",
    },
]

SUBSCRIPTIONS = [
    # Sarah - seller with multiple subscriptions
    {"user_idx": 0, "service_name": "Spotify", "service_category": "music", "tier": "family", "monthly_cost": 16.99, "max_seats": 6, "used_seats": 2, "billing_cycle_day": 15},
    {"user_idx": 0, "service_name": "YouTube Premium", "service_category": "streaming", "tier": "family", "monthly_cost": 22.99, "max_seats": 5, "used_seats": 1, "billing_cycle_day": 20},
    # Marcus - seller
    {"user_idx": 1, "service_name": "Google One", "service_category": "cloud_storage", "tier": "family", "monthly_cost": 22.99, "max_seats": 5, "used_seats": 3, "billing_cycle_day": 10},
    {"user_idx": 1, "service_name": "Microsoft 365", "service_category": "productivity", "tier": "family", "monthly_cost": 9.99, "max_seats": 6, "used_seats": 2, "billing_cycle_day": 5},
    # Priya - seller
    {"user_idx": 2, "service_name": "Netflix", "service_category": "streaming", "tier": "premium", "monthly_cost": 22.99, "max_seats": 4, "used_seats": 2, "billing_cycle_day": 12},
    {"user_idx": 2, "service_name": "Canva", "service_category": "design", "tier": "pro", "monthly_cost": 12.99, "max_seats": 5, "used_seats": 1, "billing_cycle_day": 8},
    # Alex - seller
    {"user_idx": 3, "service_name": "Duolingo", "service_category": "education", "tier": "family", "monthly_cost": 9.99, "max_seats": 6, "used_seats": 3, "billing_cycle_day": 18},
    {"user_idx": 3, "service_name": "Headspace", "service_category": "wellness", "tier": "family", "monthly_cost": 14.99, "max_seats": 6, "used_seats": 2, "billing_cycle_day": 22},
    # Emma - buyer (has subscriptions to share too)
    {"user_idx": 4, "service_name": "Spotify", "service_category": "music", "tier": "duo", "monthly_cost": 14.99, "max_seats": 2, "used_seats": 1, "billing_cycle_day": 15},
    # James - seller
    {"user_idx": 5, "service_name": "Apple Music", "service_category": "music", "tier": "family", "monthly_cost": 16.99, "max_seats": 6, "used_seats": 4, "billing_cycle_day": 3},
    # Olivia - buyer
    {"user_idx": 6, "service_name": "Calm", "service_category": "wellness", "tier": "family", "monthly_cost": 9.99, "max_seats": 6, "used_seats": 2, "billing_cycle_day": 25},
    # David - seller
    {"user_idx": 7, "service_name": "YouTube Premium", "service_category": "streaming", "tier": "family", "monthly_cost": 22.99, "max_seats": 5, "used_seats": 3, "billing_cycle_day": 20},
    # Sofia - buyer
    {"user_idx": 8, "service_name": "Netflix", "service_category": "streaming", "tier": "standard", "monthly_cost": 15.49, "max_seats": 2, "used_seats": 1, "billing_cycle_day": 12},
    # Ethan - buyer
    {"user_idx": 9, "service_name": "Google One", "service_category": "cloud_storage", "tier": "basic", "monthly_cost": 1.99, "max_seats": 1, "used_seats": 0, "billing_cycle_day": 10},
    {"user_idx": 9, "service_name": "Duolingo", "service_category": "education", "tier": "individual", "monthly_cost": 6.99, "max_seats": 1, "used_seats": 0, "billing_cycle_day": 18},
]

LISTINGS = [
    {"sub_idx": 0, "asking_price": 5.00, "dynamic_price": 4.50, "seats_available": 4, "description": "Spotify Family — 4 seats available. Late evening usage preferred. All genres welcome!"},
    {"sub_idx": 1, "asking_price": 6.00, "dynamic_price": 5.50, "seats_available": 4, "description": "YouTube Premium — 4 seats. Ad-free videos + YouTube Music. Heavy viewer preferred."},
    {"sub_idx": 2, "asking_price": 7.00, "dynamic_price": 6.50, "seats_available": 2, "description": "Google One 2TB — 2 seats left. Great for photo backup and cloud storage."},
    {"sub_idx": 3, "asking_price": 3.00, "dynamic_price": 2.75, "seats_available": 4, "description": "Microsoft 365 — 4 seats. Full Office suite + 1TB OneDrive each."},
    {"sub_idx": 4, "asking_price": 8.00, "dynamic_price": 7.25, "seats_available": 2, "description": "Netflix Premium 4K — 2 seats. Perfect for movie buffs. No 4K TV required."},
    {"sub_idx": 5, "asking_price": 4.00, "dynamic_price": 3.50, "seats_available": 4, "description": "Canva Pro — 4 seats. Unlimited templates, brand kits, and BG remover."},
    {"sub_idx": 6, "asking_price": 3.00, "dynamic_price": 2.50, "seats_available": 3, "description": "Duolingo Super Family — 3 seats. Learn any language ad-free with streak repair."},
    {"sub_idx": 7, "asking_price": 4.50, "dynamic_price": 4.00, "seats_available": 4, "description": "Headspace Family — 4 seats. Meditation, sleep, and focus exercises."},
    {"sub_idx": 9, "asking_price": 5.00, "dynamic_price": 4.75, "seats_available": 2, "description": "Apple Music Family — 2 seats. Lossless audio, spatial audio, 100M+ songs."},
    {"sub_idx": 11, "asking_price": 7.00, "dynamic_price": 6.25, "seats_available": 2, "description": "YouTube Premium — 2 seats. Ad-free + background play + YouTube Music."},
    {"sub_idx": 8, "asking_price": 5.50, "dynamic_price": 5.00, "seats_available": 1, "description": "Spotify Duo — 1 seat. Duo Mix playlist + 2 accounts. Couples preferred."},
    {"sub_idx": 12, "asking_price": 5.50, "dynamic_price": 5.00, "seats_available": 1, "description": "Netflix Standard — 1 seat. HD streaming, 2 simultaneous screens."},
]

# (buyer_idx, listing_idx, proposed_price, status, match_score)
MATCHES = [
    (4, 0, 4.50, "accepted", 0.92),   # Emma buys Spotify from Sarah
    (8, 4, 7.25, "accepted", 0.88),    # Sofia buys Netflix from Priya
    (9, 2, 6.50, "accepted", 0.85),    # Ethan buys Google One from Marcus
    (6, 7, 4.00, "accepted", 0.91),    # Olivia buys Headspace from Alex
    (5, 1, 5.50, "proposed", 0.78),    # James proposes YouTube Premium from Sarah
    (8, 8, 5.00, "proposed", 0.74),    # Sofia proposes Spotify Duo from Emma
    (4, 6, 2.50, "rejected", 0.62),    # Emma rejects Duolingo from Alex
    (9, 10, 4.75, "proposed", 0.81),   # Ethan proposes Apple Music from James
]


async def seed():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Clear existing data
    async with engine.begin() as conn:
        await conn.execute(text("SET session_replication_role = 'replica'"))
        for table in [
            "messages", "conversations", "escrow_transactions", "subscription_usage",
            "notifications", "compliance_events", "payouts", "disputes",
            "matches", "market_listings", "reputation_scores", "kyc_verifications",
            "subscriptions", "users",
        ]:
            await conn.execute(text(f"TRUNCATE {table} CASCADE"))
        await conn.execute(text("SET session_replication_role = 'origin'"))
    print("✓ Cleared existing data")

    async with async_session() as db:
        now = datetime.now(timezone.utc)

        # --- Users ---
        users = []
        for u in USERS:
            user = User(
                id=uuid.uuid4(),
                email=u["email"],
                username=u["username"],
                display_name=u["display_name"],
                password_hash=hash_password("demo123"),
                role="user",
                is_active=True,
                is_verified=True,
                latitude=u["latitude"],
                longitude=u["longitude"],
                timezone=u.get("timezone", "UTC"),
                locale="en-US",
                last_login_at=now - timedelta(hours=random.randint(1, 48)),
                preferences={"notifications_enabled": True, "email_digest": "weekly"},
            )
            db.add(user)
            users.append(user)
        await db.flush()
        print(f"✓ Created {len(users)} users")

        # --- Subscriptions ---
        subscriptions = []
        for s in SUBSCRIPTIONS:
            sub = Subscription(
                id=uuid.uuid4(),
                user_id=users[s["user_idx"]].id,
                service_name=s["service_name"],
                service_category=s["service_category"],
                tier=s["tier"],
                status="active",
                monthly_cost=s["monthly_cost"],
                max_seats=s["max_seats"],
                used_seats=s["used_seats"],
                billing_cycle_day=s["billing_cycle_day"],
                usage_data={
                    "avg_monthly_hours": round(random.uniform(5, 40), 1),
                    "peak_hours": random.sample(range(18, 24), 3),
                    "last_active": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
                },
            )
            db.add(sub)
            subscriptions.append(sub)
        await db.flush()
        print(f"✓ Created {len(subscriptions)} subscriptions")

        # --- Listings ---
        listings = []
        for l in LISTINGS:
            sub = subscriptions[l["sub_idx"]]
            listing = MarketListing(
                id=uuid.uuid4(),
                seller_id=sub.user_id,
                subscription_id=sub.id,
                status="active",
                asking_price=l["asking_price"],
                dynamic_price=l["dynamic_price"],
                seats_available=l["seats_available"],
                description=l["description"],
                geo_radius_km=random.choice([5.0, 10.0, 15.0, 20.0]),
                min_trust_score=random.choice([0.5, 0.6, 0.7]),
                meta={
                    "service_logo": _logo(sub.service_name),
                    "avg_response_time": f"{random.randint(5, 60)}min",
                    "verified_seller": random.choice([True, True, False]),
                },
            )
            db.add(listing)
            listings.append(listing)
        await db.flush()
        print(f"✓ Created {len(listings)} listings")

        # --- Matches ---
        matches = []
        for m in MATCHES:
            buyer_idx, listing_idx, price, status, score = m
            listing = listings[listing_idx]
            sub = subscriptions[listing.subscription_id == sub.id and sub.id == listing.subscription_id and True]  # find sub
            # Find the subscription for this listing
            sub = None
            for s in subscriptions:
                if s.id == listing.subscription_id:
                    sub = s
                    break

            match = Match(
                id=uuid.uuid4(),
                listing_id=listing.id,
                buyer_id=users[buyer_idx].id,
                seller_id=listing.seller_id,
                status=status,
                match_score=score,
                trust_score=round(random.uniform(0.7, 0.95), 2),
                proximity_score=round(random.uniform(0.6, 0.95), 2),
                schedule_score=round(random.uniform(0.5, 0.9), 2),
                proposed_price=price,
                expires_at=now + timedelta(days=7),
                accepted_at=now - timedelta(hours=random.randint(1, 72)) if status == "accepted" else None,
            )
            db.add(match)
            matches.append(match)
        await db.flush()
        print(f"✓ Created {len(matches)} matches")

        # --- Conversations + Messages (for accepted matches) ---
        conv_count = 0
        msg_count = 0
        for match in matches:
            if match.status != "accepted":
                continue

            # Get listing's subscription
            listing_obj = None
            for l in listings:
                if l.id == match.listing_id:
                    listing_obj = l
                    break
            if not listing_obj:
                continue
            sub = None
            for s in subscriptions:
                if s.id == listing_obj.subscription_id:
                    sub = s
                    break
            if not sub:
                continue

            conv = Conversation(
                id=uuid.uuid4(),
                match_id=match.id,
                buyer_id=match.buyer_id,
                seller_id=match.seller_id,
                status="active",
                topic="subscription_pricing",
                subscription_details={
                    "service_name": sub.service_name,
                    "tier": sub.tier,
                    "price": match.proposed_price,
                    "total_cost": sub.monthly_cost,
                    "seats": 1,
                    "billing_cycle": "monthly",
                    "platform_fee_pct": 12,
                },
            )
            db.add(conv)
            conv_count += 1

            # Generate pricing agent messages
            agent_id = match.seller_id
            buyer_id = match.buyer_id

            tier_prices = _tier_prices(sub.service_name)
            tiers_text = "\n".join(
                f"  • **{t['name']}** — ${t['price']:.2f}/mo ({t['seats']} seat{'s' if t['seats'] > 1 else ''}) — {t['features']}"
                for t in tier_prices
            )

            messages_data = [
                {
                    "sender_id": agent_id,
                    "role": "agent",
                    "content": (
                        f"🎉 Welcome! Your match for {sub.service_name} ({sub.tier.title()} plan) has been accepted.\n\n"
                        f"**Your share price:** ${match.proposed_price:.2f}/month\n"
                        f"**Total subscription cost:** ${sub.monthly_cost:.2f}/month\n"
                        f"**Your seat:** 1 of {sub.tier} plan\n\n"
                        "Below are the available subscription tiers and pricing details."
                    ),
                    "message_type": "pricing_welcome",
                    "meta": {"action": "show_pricing", "match_id": str(match.id), "proposed_price": match.proposed_price},
                },
                {
                    "sender_id": agent_id,
                    "role": "agent",
                    "content": f"📋 **{sub.service_name} — Available Subscription Tiers**\n\n{tiers_text}\n\n"
                        f"💡 **Your seat** is on the **{sub.tier.title()}** plan at **${match.proposed_price:.2f}/month**.",
                    "message_type": "pricing_tiers",
                    "meta": {"tiers": {t["name"].lower(): {"price": t["price"], "seats": t["seats"]} for t in tier_prices}},
                },
                {
                    "sender_id": agent_id,
                    "role": "agent",
                    "content": (
                        "📅 **Billing Information**\n\n"
                        "• **Billing cycle:** Monthly (recurring)\n"
                        f"• **Your payment:** ${match.proposed_price:.2f} due each billing cycle\n"
                        "• **Platform fee:** 12% service fee included\n"
                        "• **Billing note:** Billed monthly. Cancel anytime.\n\n"
                        "Your payment is secured through our escrow system until the seat is confirmed active."
                    ),
                    "message_type": "billing_info",
                    "meta": {"billing_cycle": "monthly", "platform_fee_pct": 12},
                },
                {
                    "sender_id": agent_id,
                    "role": "agent",
                    "content": (
                        "🎁 **Available Promotions & Discounts**\n\n"
                        f"  🎵 Get 3 months of {sub.service_name} free if you're a new user!\n"
                        "  🎁 Refer a friend and both get 1 month free.\n\n"
                        "Some promotions may apply to you as a new subscriber."
                    ),
                    "message_type": "promotions",
                    "meta": {"promotions": [f"3 months free for new users", "Refer a friend for 1 month free"]},
                },
                {
                    "sender_id": agent_id,
                    "role": "agent",
                    "content": (
                        "💳 **Ready to proceed with payment?**\n\n"
                        "When you're ready, click the payment button below to fund the escrow and secure your seat.\n\n"
                        "• ✅ Secure escrow payment\n"
                        "• ✅ Instant access upon confirmation\n"
                        "• ✅ Full refund if seat is not delivered\n\n"
                        'Type **"pay now"** or click the button below to proceed.'
                    ),
                    "message_type": "payment_prompt",
                    "meta": {"action": "create_escrow", "match_id": str(match.id), "amount": match.proposed_price},
                },
            ]

            for i, md in enumerate(messages_data):
                msg = Message(
                    id=uuid.uuid4(),
                    conversation_id=conv.id,
                    sender_id=md["sender_id"],
                    role=md["role"],
                    content=md["content"],
                    message_type=md["message_type"],
                    meta=md["meta"],
                    is_read=True,
                    created_at=now - timedelta(minutes=(5 - i) * 5),
                )
                db.add(msg)
                msg_count += 1

        await db.flush()
        print(f"✓ Created {conv_count} conversations with {msg_count} messages")

        # --- Reputation Scores ---
        rep_count = 0
        for user in users:
            rep = ReputationScore(
                id=uuid.uuid4(),
                user_id=user.id,
                overall_score=round(random.uniform(0.65, 0.95), 2),
                reliability_score=round(random.uniform(0.7, 0.98), 2),
                communication_score=round(random.uniform(0.6, 0.95), 2),
                payment_score=round(random.uniform(0.7, 0.99), 2),
                total_transactions=random.randint(3, 50),
                positive_reviews=random.randint(2, 45),
                negative_reviews=random.randint(0, 3),
                dispute_count=random.randint(0, 2),
                account_age_days=random.randint(30, 365),
            )
            db.add(rep)
            rep_count += 1
        await db.flush()
        print(f"✓ Created {rep_count} reputation scores")

        # --- Notifications ---
        notif_count = 0
        notif_templates = [
            ("match", "New match found!", "You have a new match for {service} at ${price:.2f}/mo"),
            ("payment", "Payment received", "Your payment of ${price:.2f} for {service} has been processed"),
            ("message", "New message", "You have a new message about your {service} subscription"),
            ("subscription", "Seat available", "A new seat just opened up on {service}!"),
        ]
        for user in users[:6]:
            for _ in range(random.randint(1, 4)):
                tmpl = random.choice(notif_templates)
                notif = Notification(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    channel=random.choice(["push", "email"]),
                    title=tmpl[1],
                    body=tmpl[2].format(service=random.choice(["Spotify", "Netflix", "YouTube Premium"]), price=random.uniform(3, 8)),
                    is_read=random.choice([True, False]),
                    sent_at=now - timedelta(hours=random.randint(1, 72)),
                )
                db.add(notif)
                notif_count += 1
        await db.flush()
        print(f"✓ Created {notif_count} notifications")

        # --- Commit ---
        await db.commit()
        print(f"\n{'='*60}")
        print(f"✅ Seed complete!")
        print(f"   Users:           {len(users)}")
        print(f"   Subscriptions:   {len(subscriptions)}")
        print(f"   Listings:        {len(listings)}")
        print(f"   Matches:         {len(matches)}")
        print(f"   Conversations:   {conv_count}")
        print(f"   Messages:        {msg_count}")
        print(f"   Reputation:      {rep_count}")
        print(f"   Notifications:   {notif_count}")
        print(f"{'='*60}")

    await engine.dispose()


def _logo(name: str) -> str:
    logos = {
        "Spotify": "🎵", "YouTube Premium": "📺", "Netflix": "🎬",
        "Google One": "☁️", "Microsoft 365": "💼", "Canva": "🎨",
        "Duolingo": "🦉", "Headspace": "🧘", "Calm": "🧘",
        "Apple Music": "🎵",
    }
    return logos.get(name, "📦")


def _tier_prices(service: str) -> list:
    tiers = {
        "Spotify": [
            {"name": "Individual", "price": 10.99, "seats": 1, "features": "Ad-free music, Offline downloads, Unlimited skips"},
            {"name": "Duo", "price": 14.99, "seats": 2, "features": "Two accounts, Duo Mix playlist, Ad-free music"},
            {"name": "Family", "price": 16.99, "seats": 6, "features": "Up to 6 accounts, Family Mix, Spotify Kids"},
            {"name": "Student", "price": 5.99, "seats": 1, "features": "Ad-free music, Hulu included"},
        ],
        "Netflix": [
            {"name": "Basic", "price": 8.99, "seats": 1, "features": "720p, 1 screen"},
            {"name": "Standard", "price": 15.49, "seats": 2, "features": "1080p, 2 screens"},
            {"name": "Premium", "price": 22.99, "seats": 4, "features": "4K HDR, 4 screens, Spatial audio"},
        ],
        "YouTube Premium": [
            {"name": "Individual", "price": 13.99, "seats": 1, "features": "Ad-free, Background play, YouTube Music"},
            {"name": "Family", "price": 22.99, "seats": 5, "features": "Up to 5 members, Family Mix"},
            {"name": "Student", "price": 7.99, "seats": 1, "features": "Ad-free, Student discount"},
        ],
        "Google One": [
            {"name": "Basic 100GB", "price": 1.99, "seats": 1, "features": "100GB storage, VPN, Magic Eraser"},
            {"name": "Standard 200GB", "price": 2.99, "seats": 1, "features": "200GB storage, VPN, Family sharing"},
            {"name": "Premium 2TB", "price": 9.99, "seats": 5, "features": "2TB storage, VPN, Family sharing, Google Experts"},
        ],
        "Microsoft 365": [
            {"name": "Personal", "price": 6.99, "seats": 1, "features": "Office apps, 1TB OneDrive"},
            {"name": "Family", "price": 9.99, "seats": 6, "features": "Office apps, 1TB each, Family Safety"},
        ],
        "Canva": [
            {"name": "Free", "price": 0, "seats": 1, "features": "Basic templates, 5GB storage"},
            {"name": "Pro", "price": 12.99, "seats": 1, "features": "Unlimited templates, Brand kit, BG remover"},
            {"name": "Teams", "price": 14.99, "seats": 5, "features": "Everything in Pro + Team collaboration"},
        ],
        "Duolingo": [
            {"name": "Free", "price": 0, "seats": 1, "features": "Basic lessons, Ads"},
            {"name": "Super", "price": 6.99, "seats": 1, "features": "Ad-free, Streak repair, Unlimited hearts"},
            {"name": "Super Family", "price": 9.99, "seats": 6, "features": "Up to 6 members, All Super features"},
        ],
        "Headspace": [
            {"name": "Free", "price": 0, "seats": 1, "features": "Basic meditation, Limited content"},
            {"name": "Plus", "price": 12.99, "seats": 1, "features": "Full library, Sleep sounds, Focus music"},
            {"name": "Family", "price": 14.99, "seats": 6, "features": "Up to 6 members, All Plus features"},
        ],
        "Calm": [
            {"name": "Free", "price": 0, "seats": 1, "features": "Basic meditation, Limited sleep stories"},
            {"name": "Premium", "price": 6.99, "seats": 1, "features": "Full library, Sleep stories, Masterclasses"},
            {"name": "Family", "price": 9.99, "seats": 6, "features": "Up to 6 members, All Premium features"},
        ],
        "Apple Music": [
            {"name": "Individual", "price": 10.99, "seats": 1, "features": "100M+ songs, Lossless, Spatial audio"},
            {"name": "Family", "price": 16.99, "seats": 6, "features": "Up to 6 members, Apple Music Kids"},
            {"name": "Student", "price": 5.99, "seats": 1, "features": "Discounted, Apple TV+ included"},
        ],
    }
    return tiers.get(service, [{"name": "Standard", "price": 9.99, "seats": 1, "features": "Standard plan"}])


if __name__ == "__main__":
    asyncio.run(seed())
