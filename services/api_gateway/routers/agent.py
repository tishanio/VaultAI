"""Vault AI Agent — conversational interface for all platform features."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from vault.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    context: Optional[dict[str, Any]] = None


class CardType(str, Enum):
    SUBSCRIPTION = "subscription"
    LISTING = "listing"
    MATCH = "match"
    ESCROW = "escrow"
    STATS = "stats"
    ACTION = "action"


class ResultCard(BaseModel):
    type: CardType
    title: str
    subtitle: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    cards: list[ResultCard] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Demo Data (used when backend services are not fully wired)
# ---------------------------------------------------------------------------

DEMO_SUBSCRIPTIONS = [
    {"id": "sub-1", "name": "Spotify", "category": "music", "logo": "🎵", "tier": "Family", "cost": 16.99, "max_seats": 6, "used_seats": 2, "status": "active", "usage_pct": 35},
    {"id": "sub-2", "name": "Google One", "category": "cloud_storage", "logo": "☁️", "tier": "Family", "cost": 22.99, "max_seats": 5, "used_seats": 3, "status": "active", "usage_pct": 72},
    {"id": "sub-3", "name": "YouTube Premium", "category": "streaming", "logo": "📺", "tier": "Family", "cost": 22.99, "max_seats": 5, "used_seats": 1, "status": "active", "usage_pct": 18},
    {"id": "sub-4", "name": "Headspace", "category": "wellness", "logo": "🧘", "tier": "Family", "cost": 9.99, "max_seats": 6, "used_seats": 4, "status": "active", "usage_pct": 55},
    {"id": "sub-5", "name": "Duolingo", "category": "education", "logo": "🦉", "tier": "Super", "cost": 7.99, "max_seats": 6, "used_seats": 2, "status": "active", "usage_pct": 28},
]

DEMO_LISTINGS = [
    {"id": "list-1", "service": "Spotify", "logo": "🎵", "seller": "Alex Chen", "reputation": 0.92, "price": 4.50, "seats": 2, "distance_km": 3.2, "match_score": 0.87, "reasons": ["High trust", "Nearby", "Good price"]},
    {"id": "list-2", "service": "Google One", "logo": "☁️", "seller": "Maria Santos", "reputation": 0.88, "price": 5.75, "seats": 1, "distance_km": 7.8, "match_score": 0.79, "reasons": ["Verified seller", "Flexible schedule"]},
    {"id": "list-3", "service": "YouTube Premium", "logo": "📺", "seller": "James Wilson", "reputation": 0.85, "price": 5.00, "seats": 3, "distance_km": 12.1, "match_score": 0.74, "reasons": ["Active user", "Good reviews"]},
]

DEMO_MATCHES = [
    {"id": "match-1", "service": "Spotify", "logo": "🎵", "seller": "Alex Chen", "status": "accepted", "score": 0.847, "price": 4.50, "created": "2024-01-15T10:30:00Z"},
    {"id": "match-2", "service": "Google One", "logo": "☁️", "seller": "Maria Santos", "status": "proposed", "score": 0.792, "price": 5.75, "created": "2024-01-15T08:15:00Z"},
]

DEMO_ESCROWS = [
    {"id": "esc-1", "service": "Spotify", "logo": "🎵", "seller": "Alex Chen", "amount": 4.50, "fee": 0.54, "payout": 3.96, "status": "released"},
    {"id": "esc-2", "service": "Google One", "logo": "☁️", "seller": "Maria Santos", "amount": 5.75, "fee": 0.69, "payout": 5.06, "status": "funded"},
    {"id": "esc-3", "service": "YouTube Premium", "logo": "📺", "seller": "James Wilson", "amount": 5.00, "fee": 0.60, "payout": 4.40, "status": "held"},
]

TOTAL_MONTHLY_COST = sum(s["cost"] for s in DEMO_SUBSCRIPTIONS)
UNUSED_SEATS = sum(s["max_seats"] - s["used_seats"] for s in DEMO_SUBSCRIPTIONS)
TOTAL_SAVINGS_POTENTIAL = sum(
    (s["max_seats"] - s["used_seats"]) * (s["cost"] / s["max_seats"] * 0.5)
    for s in DEMO_SUBSCRIPTIONS
)


# ---------------------------------------------------------------------------
# Agent System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are Vault Agent — an AI assistant for the Vault subscription-sharing platform.

Your role: Help users manage their subscriptions, find marketplace matches, handle escrow payments, and optimize their spending. You are conversational, helpful, and proactive.

## Current User Context (Demo Data)
- {len(DEMO_SUBSCRIPTIONS)} active subscriptions (${TOTAL_MONTHLY_COST:.2f}/mo total)
- {UNUSED_SEATS} unused seats across all subscriptions
- ~${TOTAL_SAVINGS_POTENTIAL:.2f}/mo potential savings by sharing unused seats
- {len(DEMO_LISTINGS)} marketplace listings nearby
- {len(DEMO_MATCHES)} active matches ({sum(1 for m in DEMO_MATCHES if m['status']=='accepted')} accepted)
- {len(DEMO_ESCROWS)} escrow transactions

## Capabilities
When the user asks about something, respond naturally AND include structured card data in a JSON block at the end of your response.

### Card Types You Can Return
Embed a JSON block at the end of your response with this format:
```json
{{
  "cards": [{{"type": "...", "title": "...", "subtitle": "...", "data": {{...}}}}],
  "suggestions": ["suggestion 1", "suggestion 2"]
}}
```

Card types:
- "subscription" — for showing subscription info (data: name, logo, tier, cost, seats, usage_pct)
- "listing" — for marketplace results (data: service, logo, seller, reputation, price, seats, distance_km)
- "match" — for match results (data: service, logo, seller, status, score, price)
- "escrow" — for payment/escrow info (data: service, logo, seller, amount, status)
- "stats" — for dashboard-style stats (data: title, value, change)
- "action" — for action buttons (data: label, variant)

### Guidelines
- Be concise and helpful
- When showing subscriptions, mention unused seats and savings potential
- When finding matches, highlight the best options and explain why
- When discussing escrow, explain the current status clearly
- Proactively suggest optimizations (sharing unused seats, etc.)
- If the user asks to do something (create listing, accept match, etc.), confirm the action and describe what would happen
- Always be encouraging about savings opportunities

## Conversation Style
- Friendly and professional
- Use emojis sparingly but effectively
- Break complex info into digestible chunks
- Lead with the most important info
"""


# ---------------------------------------------------------------------------
# Agent Logic
# ---------------------------------------------------------------------------

async def call_openai_agent(
    message: str,
    conversation_history: list[ChatMessage],
) -> tuple[str, list[ResultCard], list[str]]:
    """Call OpenAI API to generate agent response."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history (last 20 messages max)
        for msg in conversation_history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=settings.AGENT_MAX_TOKENS,
            temperature=settings.AGENT_TEMPERATURE,
        )

        content = response.choices[0].message.content or ""

        # Parse structured cards from response
        cards, suggestions = parse_agent_response(content)

        return content, cards, suggestions

    except Exception as e:
        logger.error("OpenAI agent call failed: {}", e)
        raise


def parse_agent_response(content: str) -> tuple[list[ResultCard], list[str]]:
    """Extract structured card data from agent response."""
    cards: list[ResultCard] = []
    suggestions: list[str] = []

    # Look for JSON block in response
    try:
        # Find JSON block between ```json and ```
        import re
        json_match = re.search(r"```json\s*\n(.*?)\n\s*```", content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(1))

            for card_data in parsed.get("cards", []):
                cards.append(ResultCard(
                    type=CardType(card_data.get("type", "stats")),
                    title=card_data.get("title", ""),
                    subtitle=card_data.get("subtitle"),
                    data=card_data.get("data", {}),
                    actions=card_data.get("actions", []),
                ))

            suggestions = parsed.get("suggestions", [])
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.debug("Could not parse agent JSON response: {}", e)

    return cards, suggestions


async def handle_with_demo_data(
    message: str,
    conversation_history: list[ChatMessage],
) -> ChatResponse:
    """Handle agent request using demo data (fallback when OpenAI is not configured)."""
    lower = message.lower()
    cards: list[ResultCard] = []
    suggestions: list[str] = []
    reply = ""

    # --- Intent Detection ---

    if any(w in lower for w in ["subscription", "subscriptions", "my subs", "what do i have"]):
        cards = [
            ResultCard(
                type=CardType.SUBSCRIPTION,
                title=f"{s['logo']} {s['name']}",
                subtitle=f"{s['tier']} — {s['used_seats']}/{s['max_seats']} seats",
                data=s,
            )
            for s in DEMO_SUBSCRIPTIONS
        ]
        reply = (
            f"You have {len(DEMO_SUBSCRIPTIONS)} active subscriptions totaling ${TOTAL_MONTHLY_COST:.2f}/mo. "
            f"You're using {sum(s['used_seats'] for s in DEMO_SUBSCRIPTIONS)} out of "
            f"{sum(s['max_seats'] for s in DEMO_SUBSCRIPTIONS)} total seats. "
            f"You have {UNUSED_SEATS} unused seats that could save you ~${TOTAL_SAVINGS_POTENTIAL:.2f}/mo!"
        )
        suggestions = ["Show me savings opportunities", "Find matches for unused seats", "Optimize my spending"]

    elif any(w in lower for w in ["marketplace", "find", "search", "available", "listing", "listings"]):
        cards = [
            ResultCard(
                type=CardType.LISTING,
                title=f"{l['logo']} {l['service']}",
                subtitle=f"by {l['seller']}",
                data=l,
            )
            for l in DEMO_LISTINGS
        ]
        reply = (
            f"I found {len(DEMO_LISTINGS)} marketplace listings near you. "
            f"Here are the best matches based on your preferences — high trust scores, competitive prices, and nearby sellers."
        )
        suggestions = ["Accept the best match", "Show more details", "Filter by category"]

    elif any(w in lower for w in ["match", "matches", "paired", "connected"]):
        cards = [
            ResultCard(
                type=CardType.MATCH,
                title=f"{m['logo']} {m['service']}",
                subtitle=f"with {m['seller']}",
                data=m,
            )
            for m in DEMO_MATCHES
        ]
        reply = (
            f"You have {len(DEMO_MATCHES)} active matches. "
            f"{sum(1 for m in DEMO_MATCHES if m['status']=='accepted')} have been accepted and are ready for escrow."
        )
        suggestions = ["Fund the escrow", "View match details", "Find more matches"]

    elif any(w in lower for w in ["escrow", "payment", "pay", "transaction", "transactions"]):
        cards = [
            ResultCard(
                type=CardType.ESCROW,
                title=f"{e['logo']} {e['service']}",
                subtitle=f"with {e['seller']}",
                data=e,
            )
            for e in DEMO_ESCROWS
        ]
        total_earned = sum(e["payout"] for e in DEMO_ESCROWS if e["status"] == "released")
        total_pending = sum(e["amount"] for e in DEMO_ESCROWS if e["status"] in ("funded", "held"))
        reply = (
            f"Here's your escrow overview: ${total_earned:.2f} earned from completed transactions, "
            f"${total_pending:.2f} currently in escrow. "
            f"You have {len(DEMO_ESCROWS)} total transactions."
        )
        suggestions = ["View payout history", "Release funds", "Dispute a transaction"]

    elif any(w in lower for w in ["savings", "save", "optimize", "optimization", "waste"]):
        low_usage = [s for s in DEMO_SUBSCRIPTIONS if s["usage_pct"] < 40]
        cards = [
            ResultCard(
                type=CardType.STATS,
                title="💰 Potential Monthly Savings",
                subtitle=f"${TOTAL_SAVINGS_POTENTIAL:.2f}/mo",
                data={"value": f"${TOTAL_SAVINGS_POTENTIAL:.2f}", "label": "by sharing unused seats"},
            )
        ]
        for s in low_usage:
            unused = s["max_seats"] - s["used_seats"]
            savings = unused * (s["cost"] / s["max_seats"] * 0.5)
            cards.append(ResultCard(
                type=CardType.SUBSCRIPTION,
                title=f"{s['logo']} {s['name']}",
                subtitle=f"Only {s['usage_pct']}% used — {unused} unused seats",
                data={**s, "potential_savings": round(savings, 2)},
            ))
        reply = (
            f"I found {len(low_usage)} subscriptions with low usage. "
            f"By sharing {UNUSED_SEATS} unused seats, you could save ~${TOTAL_SAVINGS_POTENTIAL:.2f}/mo. "
            f"Want me to create marketplace listings for these?"
        )
        suggestions = ["Create listings for unused seats", "Find matches for unused seats", "Show all subscriptions"]

    elif any(w in lower for w in ["create listing", "list", "sell", "share", "listing"]):
        reply = (
            "I can create marketplace listings for your unused subscription seats. "
            "Based on your usage analysis, here are the best candidates:\n\n"
            "• 🎵 Spotify — 4 unused seats (~$5.66/mo potential)\n"
            "• 📺 YouTube Premium — 4 unused seats (~$9.20/mo potential)\n"
            "• 🦉 Duolingo — 4 unused seats (~$5.33/mo potential)\n\n"
            "I'll set competitive prices and match with verified sellers nearby. Shall I create these listings?"
        )
        suggestions = ["Yes, create all listings", "Let me customize prices", "Show me the match algorithm"]

    elif any(w in lower for w in ["accept", "confirm", "yes", "go ahead", "do it"]):
        reply = (
            "✅ Done! I've processed that for you. "
            "The changes are reflected in your account. "
            "You'll receive notifications as things progress."
        )
        suggestions = ["Show me my updated overview", "Check notifications", "Find more opportunities"]

    elif any(w in lower for w in ["dashboard", "overview", "summary", "stats", "how am i doing"]):
        cards = [
            ResultCard(type=CardType.STATS, title="Active Subscriptions", subtitle="5", data={"value": "5", "label": "services"}),
            ResultCard(type=CardType.STATS, title="Monthly Cost", subtitle=f"${TOTAL_MONTHLY_COST:.2f}", data={"value": f"${TOTAL_MONTHLY_COST:.2f}"}),
            ResultCard(type=CardType.STATS, title="Potential Savings", subtitle=f"~${TOTAL_SAVINGS_POTENTIAL:.2f}/mo", data={"value": f"~${TOTAL_SAVINGS_POTENTIAL:.2f}"}),
            ResultCard(type=CardType.STATS, title="Trust Score", subtitle="87%", data={"value": "87%", "label": "Gold tier"}),
        ]
        reply = (
            "Here's your Vault overview! You're doing well with a Gold-tier trust score. "
            f"You're spending ${TOTAL_MONTHLY_COST:.2f}/mo across {len(DEMO_SUBSCRIPTIONS)} subscriptions "
            f"but have ~${TOTAL_SAVINGS_POTENTIAL:.2f}/mo in potential savings from unused seats."
        )
        suggestions = ["Show savings opportunities", "Find marketplace matches", "View escrow status"]

    else:
        # Default conversational response
        reply = (
            "I'm Vault Agent — your AI assistant for subscription management. "
            "I can help you with:\n\n"
            "• 📋 **View subscriptions** — See all your active services\n"
            "• 🔍 **Find matches** — Discover marketplace listings\n"
            "• 💰 **Optimize spending** — Find savings from unused seats\n"
            "• 🤝 **Manage matches** — Accept/reject proposals\n"
            "• 💳 **Escrow & payments** — Track transactions\n"
            "• 📊 **Dashboard** — See your overview stats\n\n"
            "What would you like to do?"
        )
        suggestions = [
            "Show my subscriptions",
            "Find marketplace matches",
            "Optimize my spending",
            "View dashboard",
        ]

    return ChatResponse(
        reply=reply,
        cards=cards,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

async def stream_openai_agent(
    message: str,
    conversation_history: list[ChatMessage],
):
    """Stream OpenAI response as SSE events.

    Event types:
      - token:     {"type": "token", "content": "..."}
      - cards:     {"type": "cards", "cards": [...], "suggestions": [...]}
      - done:      {"type": "done"}
      - error:     {"type": "error", "message": "..."}
    """
    import re

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in conversation_history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=settings.AGENT_MAX_TOKENS,
            temperature=settings.AGENT_TEMPERATURE,
            stream=True,
        )

        full_content = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                yield f"data: {json.dumps({'type': 'token', 'content': delta.content})}\n\n"

        # Parse cards from the full completed response
        cards, suggestions = parse_agent_response(full_content)
        yield f"data: {json.dumps({'type': 'cards', 'cards': [c.model_dump() for c in cards], 'suggestions': suggestions})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error("OpenAI streaming failed: {}", e)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


async def stream_demo_agent(
    message: str,
    conversation_history: list[ChatMessage],
):
    """Simulate streaming for the demo agent — types out the response token by token."""
    response = await handle_with_demo_data(message, conversation_history)

    # Stream the reply text in small chunks to simulate typing
    words = response.reply.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        # Small delay to simulate streaming feel
        import asyncio
        await asyncio.sleep(0.02)

    # Send cards and suggestions
    yield f"data: {json.dumps({'type': 'cards', 'cards': [c.model_dump() for c in response.cards], 'suggestions': response.suggestions})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """Main agent chat endpoint — non-streaming fallback."""
    logger.info("Agent chat: {}", request.message[:100])

    if settings.OPENAI_API_KEY:
        try:
            content, cards, suggestions = await call_openai_agent(
                message=request.message,
                conversation_history=request.conversation_history,
            )
            return ChatResponse(reply=content, cards=cards, suggestions=suggestions)
        except Exception as e:
            logger.warning("OpenAI agent failed, falling back to demo: {}", e)
            return await handle_with_demo_data(request.message, request.conversation_history)
    else:
        return await handle_with_demo_data(request.message, request.conversation_history)


@router.post("/agent/chat/stream")
async def agent_chat_stream(request: ChatRequest):
    """Streaming agent chat endpoint — returns SSE stream of tokens, then cards."""
    logger.info("Agent chat (stream): {}", request.message[:100])

    if settings.OPENAI_API_KEY:
        generator = stream_openai_agent(request.message, request.conversation_history)
    else:
        generator = stream_demo_agent(request.message, request.conversation_history)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agent/suggestions")
async def get_suggestions():
    """Get initial suggested actions for the chat interface."""
    return {
        "suggestions": [
            "Show my subscriptions",
            "Find marketplace matches",
            "Optimize my spending",
            "View dashboard",
            "Create a listing",
            "Check escrow status",
        ]
    }
