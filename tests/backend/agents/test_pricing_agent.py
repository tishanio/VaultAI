"""Tests for pricing agent — generates subscription pricing conversation messages."""
import pytest
from services.api_gateway.routers.pricing_agent import generate_pricing_messages, SERVICE_PRICING

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Unit tests for generate_pricing_messages
# ---------------------------------------------------------------------------


class TestPricingAgentKnownService:
    """Tests for known services (Spotify, YouTube Premium, etc.)."""

    def test_returns_list_of_dicts(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        assert isinstance(msgs, list)
        assert len(msgs) > 0
        for m in msgs:
            assert "content" in m
            assert "type" in m

    def test_welcome_message_contains_service_name(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        welcome = msgs[0]
        assert welcome["type"] == "pricing_welcome"
        assert "Spotify" in welcome["content"]
        assert "family" in welcome["content"].lower()
        assert "4.50" in welcome["content"]

    def test_welcome_message_contains_proposed_price(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        welcome = msgs[0]
        assert "$4.50" in welcome["content"]

    def test_welcome_message_contains_total_cost(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        welcome = msgs[0]
        assert "$16.99" in welcome["content"]

    def test_welcome_meta_has_match_id(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        meta = msgs[0]["meta"]
        assert meta["match_id"] == "match-1"
        assert meta["proposed_price"] == 4.50

    def test_tier_breakdown_message(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        # Second message should be tier breakdown
        tiers_msg = msgs[1]
        assert tiers_msg["type"] == "pricing_tiers"
        assert "Spotify" in tiers_msg["content"]
        # Should mention individual, duo, family, student tiers
        assert "Individual" in tiers_msg["content"]
        assert "Family" in tiers_msg["content"]
        assert "Student" in tiers_msg["content"]

    def test_tier_breakdown_meta_has_tiers(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        tiers_msg = msgs[1]
        assert "tiers" in tiers_msg["meta"]
        assert "family" in tiers_msg["meta"]["tiers"]
        assert tiers_msg["meta"]["tiers"]["family"]["price"] == 16.99

    def test_billing_info_message(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        billing = msgs[2]
        assert billing["type"] == "billing_info"
        assert "monthly" in billing["content"].lower()
        assert "4.50" in billing["content"]

    def test_billing_info_meta_has_platform_fee(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        billing = msgs[2]
        assert "platform_fee_pct" in billing["meta"]

    def test_promotions_message(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        promos = msgs[3]
        assert promos["type"] == "promotions"
        assert "promotions" in promos["meta"]
        assert len(promos["meta"]["promotions"]) > 0

    def test_payment_prompt_message(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        payment_prompt = msgs[-1]  # Last message
        assert payment_prompt["type"] == "payment_prompt"
        assert "pay now" in payment_prompt["content"].lower()
        assert payment_prompt["meta"]["action"] == "create_escrow"
        assert payment_prompt["meta"]["amount"] == 4.50

    def test_spotify_has_all_expected_tiers(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        tiers = msgs[1]["meta"]["tiers"]
        assert "individual" in tiers
        assert "duo" in tiers
        assert "family" in tiers
        assert "student" in tiers

    def test_youtube_premium_pricing(self):
        msgs = generate_pricing_messages("YouTube Premium", 5.00, 22.99, "family", "match-2")
        assert len(msgs) >= 4
        welcome = msgs[0]
        assert "YouTube Premium" in welcome["content"]
        tiers = msgs[1]["meta"]["tiers"]
        assert "individual" in tiers
        assert tiers["individual"]["price"] == 13.99

    def test_google_one_pricing(self):
        msgs = generate_pricing_messages("Google One", 5.75, 22.99, "family", "match-3")
        tiers = msgs[1]["meta"]["tiers"]
        assert "basic" in tiers
        assert tiers["basic"]["price"] == 1.99

    def test_duolingo_pricing(self):
        msgs = generate_pricing_messages("Duolingo", 2.50, 9.99, "family", "match-4")
        tiers = msgs[1]["meta"]["tiers"]
        assert "super" in tiers
        assert "family" in tiers


class TestPricingAgentUnknownService:
    """Tests for services not in SERVICE_PRICING (fallback behavior)."""

    def test_unknown_service_returns_messages(self):
        msgs = generate_pricing_messages("SomeRandomService", 3.00, 10.00, "basic", "match-5")
        assert isinstance(msgs, list)
        assert len(msgs) >= 2  # At least welcome + payment prompt

    def test_unknown_service_welcome(self):
        msgs = generate_pricing_messages("SomeRandomService", 3.00, 10.00, "basic", "match-5")
        welcome = msgs[0]
        assert "SomeRandomService" in welcome["content"]
        assert "$3.00" in welcome["content"]

    def test_unknown_service_generic_pricing_details(self):
        msgs = generate_pricing_messages("SomeRandomService", 3.00, 10.00, "basic", "match-5")
        # Second message should be generic pricing details (not tiers)
        pricing = msgs[1]
        assert pricing["type"] == "pricing_details"
        assert "$3.00" in pricing["content"]
        assert "basic" in pricing["content"].lower()

    def test_unknown_service_no_tiers_or_billing(self):
        msgs = generate_pricing_messages("SomeRandomService", 3.00, 10.00, "basic", "match-5")
        types = [m["type"] for m in msgs]
        assert "pricing_tiers" not in types
        assert "billing_info" not in types
        assert "promotions" not in types

    def test_unknown_service_has_payment_prompt(self):
        msgs = generate_pricing_messages("SomeRandomService", 3.00, 10.00, "basic", "match-5")
        payment_prompt = msgs[-1]
        assert payment_prompt["type"] == "payment_prompt"


class TestPricingAgentMessageStructure:
    """Tests for message structure consistency."""

    def test_all_messages_have_content_and_type(self):
        for service in ["Spotify", "YouTube Premium", "Google One", "Duolingo"]:
            msgs = generate_pricing_messages(service, 4.50, 16.99, "family", "match-1")
            for m in msgs:
                assert "content" in m, f"Missing 'content' in message for {service}"
                assert "type" in m, f"Missing 'type' in message for {service}"
                assert isinstance(m["content"], str), f"Content not string for {service}"
                assert len(m["content"]) > 0, f"Empty content for {service}"

    def test_all_messages_have_meta(self):
        msgs = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        for m in msgs:
            assert "meta" in m, f"Missing 'meta' in message type {m['type']}"

    def test_payment_prompt_always_last(self):
        for service in ["Spotify", "YouTube Premium", "Duolingo", "UnknownService"]:
            msgs = generate_pricing_messages(service, 4.50, 16.99, "family", "match-1")
            assert msgs[-1]["type"] == "payment_prompt", f"Last message not payment_prompt for {service}"

    def test_message_count_varies_by_service(self):
        """Known services should have more messages than unknown services."""
        known = generate_pricing_messages("Spotify", 4.50, 16.99, "family", "match-1")
        unknown = generate_pricing_messages("UnknownSvc", 4.50, 16.99, "family", "match-1")
        assert len(known) > len(unknown), "Known service should have more messages than unknown"


class TestServicePricingData:
    """Tests for the SERVICE_PRICING data dictionary."""

    def test_all_expected_services_present(self):
        expected = {"Spotify", "YouTube Premium", "Google One", "Apple Music",
                    "Duolingo", "Headspace", "Calm", "Microsoft 365", "Canva", "YouTube Music"}
        assert set(SERVICE_PRICING.keys()) == expected

    def test_all_services_have_tiers(self):
        for name, data in SERVICE_PRICING.items():
            assert "tiers" in data, f"{name} missing 'tiers'"
            assert len(data["tiers"]) > 0, f"{name} has no tiers"

    def test_all_tiers_have_required_fields(self):
        for name, data in SERVICE_PRICING.items():
            for tier_name, tier_data in data["tiers"].items():
                assert "price" in tier_data, f"{name}/{tier_name} missing 'price'"
                assert "seats" in tier_data, f"{name}/{tier_name} missing 'seats'"
                assert "features" in tier_data, f"{name}/{tier_name} missing 'features'"
                assert tier_data["price"] > 0, f"{name}/{tier_name} has invalid price"
                assert tier_data["seats"] > 0, f"{name}/{tier_name} has invalid seats"
                assert len(tier_data["features"]) > 0, f"{name}/{tier_name} has no features"

    def test_all_services_have_billing_note(self):
        for name, data in SERVICE_PRICING.items():
            assert "billing_note" in data, f"{name} missing 'billing_note'"
            assert len(data["billing_note"]) > 0, f"{name} has empty billing_note"

    def test_all_services_have_promotions(self):
        for name, data in SERVICE_PRICING.items():
            assert "promotions" in data, f"{name} missing 'promotions'"
            assert len(data["promotions"]) > 0, f"{name} has no promotions"
