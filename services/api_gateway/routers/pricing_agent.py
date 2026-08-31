"""Pricing Agent — generates automated messages about subscription pricing tiers, billing, and promotions."""
from __future__ import annotations

from vault.config import settings


# Subscription pricing data for known services
SERVICE_PRICING = {
    "Spotify": {
        "tiers": {
            "individual": {"price": 10.99, "seats": 1, "features": ["Ad-free music", "Offline downloads", "Unlimited skips"]},
            "duo": {"price": 14.99, "seats": 2, "features": ["Two accounts", "Duo Mix playlist", "Ad-free music"]},
            "family": {"price": 16.99, "seats": 6, "features": ["Up to 6 accounts", "Family Mix playlist", "Spotify Kids", "Ad-free music"]},
            "student": {"price": 5.99, "seats": 1, "features": ["Ad-free music", "Hulu included", "Showtime included"]},
        },
        "promotions": [
            "🎵 Get 3 months of Premium for free if you're a new user!",
            "🎁 Refer a friend and both get 1 month free.",
        ],
        "billing_note": "Billed monthly. Cancel anytime. No commitment required.",
    },
    "YouTube Premium": {
        "tiers": {
            "individual": {"price": 13.99, "seats": 1, "features": ["Ad-free videos", "Background play", "YouTube Music Premium"]},
            "family": {"price": 22.99, "seats": 5, "features": ["Up to 5 family members", "Ad-free videos", "YouTube Music Premium"]},
            "student": {"price": 7.99, "seats": 1, "features": ["Ad-free videos", "YouTube Music Premium", "Student verification required"]},
        },
        "promotions": [
            "📺 Try YouTube Premium free for 1 month — cancel anytime!",
            "🎓 Student discount available — verify with SheerID.",
        ],
        "billing_note": "Monthly billing. Family plan members must live at the same address.",
    },
    "Google One": {
        "tiers": {
            "basic": {"price": 1.99, "seats": 1, "features": ["100 GB storage", "Google experts support"]},
            "standard": {"price": 2.99, "seats": 1, "features": ["200 GB storage", "Google experts support"]},
            "premium": {"price": 9.99, "seats": 1, "features": ["2 TB storage", "Google experts support", "Google Workspace benefits"]},
            "family": {"price": 22.99, "seats": 5, "features": ["2 TB shared storage", "Up to 5 family members", "Google experts support"]},
        },
        "promotions": [
            "☁️ New subscribers get 100 GB free for 3 months.",
        ],
        "billing_note": "Monthly billing. Storage is shared across Google services (Drive, Gmail, Photos).",
    },
    "Apple Music": {
        "tiers": {
            "individual": {"price": 10.99, "seats": 1, "features": ["100M+ songs", "Lossless audio", "Spatial Audio"]},
            "family": {"price": 16.99, "seats": 6, "features": ["Up to 6 accounts", "100M+ songs", "Lossless audio"]},
            "student": {"price": 5.99, "seats": 1, "features": ["100M+ songs", "Apple TV+ included", "Student verification required"]},
        },
        "promotions": [
            "🎵 1 month free trial for new subscribers.",
            "🎓 Student plan includes Apple TV+ at no extra cost.",
        ],
        "billing_note": "Billed monthly through Apple ID. Cancel anytime.",
    },
    "Duolingo": {
        "tiers": {
            "super": {"price": 7.99, "seats": 1, "features": ["No ads", "Unlimited hearts", "Mastery quests", "Progress quizzes"]},
            "family": {"price": 9.99, "seats": 6, "features": ["Up to 6 accounts", "No ads", "Unlimited hearts", "Family challenges"]},
        },
        "promotions": [
            "🦉 Try Super Duolingo free for 14 days!",
            "🎁 Family plan saves up to $36/year vs individual.",
        ],
        "billing_note": "Monthly billing. Family members don't need to live at the same address.",
    },
    "Headspace": {
        "tiers": {
            "individual": {"price": 6.99, "seats": 1, "features": ["Guided meditation", "Sleep sounds", "Focus music"]},
            "family": {"price": 9.99, "seats": 6, "features": ["Up to 6 accounts", "All meditation content", "Sleep sounds", "Focus music"]},
        },
        "promotions": [
            "🧘 Annual plan saves 40% compared to monthly billing.",
        ],
        "billing_note": "Monthly billing. Annual plans available at discount.",
    },
    "Calm": {
        "tiers": {
            "individual": {"price": 6.99, "seats": 1, "features": ["Meditation", "Sleep stories", "Breathing exercises"]},
            "family": {"price": 9.99, "seats": 6, "features": ["Up to 6 accounts", "All content", "Sleep stories", "Masterclasses"]},
        },
        "promotions": [
            "🧘 7-day free trial for new subscribers.",
        ],
        "billing_note": "Monthly billing. Family plan available.",
    },
    "Microsoft 365": {
        "tiers": {
            "personal": {"price": 6.99, "seats": 1, "features": ["Office apps", "1 TB OneDrive", "Premium Outlook"]},
            "family": {"price": 9.99, "seats": 6, "features": ["Up to 6 users", "Office apps", "1 TB each OneDrive", "Premium Outlook"]},
        },
        "promotions": [
            "💼 1 month free trial. Annual plan available at $99.99/year.",
        ],
        "billing_note": "Monthly or annual billing. Each family member gets their own 1 TB storage.",
    },
    "Canva": {
        "tiers": {
            "pro": {"price": 12.99, "seats": 1, "features": ["Premium templates", "Background remover", "Brand kit", "100M+ photos/videos"]},
            "teams": {"price": 14.99, "seats": 5, "features": ["Up to 5 users", "All Pro features", "Team collaboration", "Admin controls"]},
        },
        "promotions": [
            "🎨 30-day free trial for Canva Pro.",
        ],
        "billing_note": "Monthly billing. Teams plan requires minimum 2 users.",
    },
    "YouTube Music": {
        "tiers": {
            "individual": {"price": 10.99, "seats": 1, "features": ["Ad-free music", "Offline downloads", "Background play"]},
            "family": {"price": 16.99, "seats": 5, "features": ["Up to 5 family members", "Ad-free music", "Offline downloads"]},
        },
        "promotions": [
            "🎵 1 month free trial for new subscribers.",
        ],
        "billing_note": "Monthly billing. Cancel anytime.",
    },
}


def generate_pricing_messages(
    service_name: str,
    proposed_price: float,
    total_cost: float,
    tier: str,
    match_id: str,
) -> list[dict]:
    """Generate a sequence of agent messages about subscription pricing.

    Returns a list of message dicts with 'content', 'type', and 'meta' keys.
    """
    service_data = SERVICE_PRICING.get(service_name, None)
    messages: list[dict] = []

    # 1. Welcome message with pricing summary
    messages.append({
        "content": (
            f"🎉 Welcome! Your match for {service_name} ({tier.title()} plan) has been accepted.\n\n"
            f"**Your share price:** ${proposed_price:.2f}/month\n"
            f"**Total subscription cost:** ${total_cost:.2f}/month\n"
            f"**Your seat:** 1 of {tier} plan\n\n"
            "Below are the available subscription tiers and pricing details."
        ),
        "type": "pricing_welcome",
        "meta": {
            "action": "show_pricing",
            "match_id": match_id,
            "proposed_price": proposed_price,
        },
    })

    # 2. Detailed tier breakdown
    if service_data and "tiers" in service_data:
        tier_lines = []
        for tier_name, details in service_data["tiers"].items():
            features_str = ", ".join(details["features"][:3])
            tier_lines.append(
                f"  • **{tier_name.title()}** — ${details['price']:.2f}/mo "
                f"({details['seats']} seat{'s' if details['seats'] > 1 else ''}) "
                f"— {features_str}"
            )
        tier_text = "\n".join(tier_lines)
        messages.append({
            "content": (
                f"📋 **{service_name} — Available Subscription Tiers**\n\n"
                f"{tier_text}\n\n"
                f"💡 **Your seat** is on the **{tier.title()}** plan at **${proposed_price:.2f}/month**. "
                "This is a great value compared to the full plan price!"
            ),
            "type": "pricing_tiers",
            "meta": {
                "tiers": service_data["tiers"],
                "selected_tier": tier,
            },
        })

        # 3. Billing cycle information
        messages.append({
            "content": (
                f"📅 **Billing Information**\n\n"
                f"• **Billing cycle:** Monthly (recurring)\n"
                f"• **Your payment:** ${proposed_price:.2f} due each billing cycle\n"
                f"• **Platform fee:** {settings.PLATFORM_FEE_PERCENTAGE:.0f}% service fee included\n"
                f"• **Billing note:** {service_data.get('billing_note', 'Billed monthly. Cancel anytime.')}\n\n"
                "Your payment is secured through our escrow system until the seat is confirmed active."
            ),
            "type": "billing_info",
            "meta": {
                "billing_cycle": "monthly",
                "platform_fee_pct": settings.PLATFORM_FEE_PERCENTAGE,
            },
        })

        # 4. Promotions / discounts
        if service_data.get("promotions"):
            promo_text = "\n".join(f"  {p}" for p in service_data["promotions"])
            messages.append({
                "content": (
                    f"🎁 **Available Promotions & Discounts**\n\n"
                    f"{promo_text}\n\n"
                    "Some promotions may apply to you as a new subscriber. "
                    "Contact the subscription owner for more details on eligibility."
                ),
                "type": "promotions",
                "meta": {"promotions": service_data["promotions"]},
            })
    else:
        # Generic pricing message for unknown services
        messages.append({
            "content": (
                f"📋 **{service_name} — Pricing Details**\n\n"
                f"• **Your share:** ${proposed_price:.2f}/month\n"
                f"• **Plan tier:** {tier.title()}\n"
                f"• **Billing:** Monthly, recurring\n"
                f"• **Platform fee:** {settings.PLATFORM_FEE_PERCENTAGE:.0f}% included in your share price\n\n"
                "The subscription owner can provide additional details about the specific plan features."
            ),
            "type": "pricing_details",
            "meta": {"proposed_price": proposed_price},
        })

    # 5. Payment action prompt
    messages.append({
        "content": (
            "💳 **Ready to proceed with payment?**\n\n"
            "When you're ready, click the payment button below to fund the escrow and secure your seat. "
            "Your payment will be held safely in escrow until the subscription seat is confirmed.\n\n"
            "• ✅ Secure escrow payment\n"
            "• ✅ Instant access upon confirmation\n"
            "• ✅ Full refund if seat is not delivered\n\n"
            "Type **\"pay now\"** or click the button below to proceed."
        ),
        "type": "payment_prompt",
        "meta": {
            "action": "create_escrow",
            "match_id": match_id,
            "amount": proposed_price,
        },
    })

    return messages
