# Vault User Manual

## Getting Started

### Creating an Account
1. Visit `https://vault.app` or open the mobile app
2. Click **Sign Up**
3. Enter your email, username, and password
4. Verify your email address
5. Complete KYC verification (upload ID + selfie)

### Adding Your First Subscription
1. Navigate to **Subscriptions** → **Add Subscription**
2. Select your service (e.g., Spotify Family)
3. Enter your monthly cost and total seats
4. Set your billing cycle day
5. Vault begins tracking your usage automatically

---

## Subscriptions

### Viewing Your Subscriptions
The Subscriptions page shows all your tracked subscriptions with:
- **Service name and logo**
- **Monthly cost**
- **Seat usage** (used/total)
- **Usage percentage** (how much you're actually using)
- **Optimization recommendations**

### Usage Tracking
Vault tracks your usage through:
- **Manual entry** — Log your usage in the app
- **Plaid sync** — Automatically detect usage from bank transactions
- **API integration** — Direct service integrations (when available)

### Understanding Usage Scores
- **< 30% usage** → 🟢 High sharing potential (great savings opportunity)
- **30-60% usage** → 🟡 Moderate (some room to share)
- **> 60% usage** → 🔴 Heavy usage (sharing not recommended)

---

## Marketplace

### Browsing Listings
The Marketplace shows available subscription seats from verified users:
- **Match Score** — AI-calculated compatibility (0-100%)
- **Dynamic Price** — Fair price based on demand/supply
- **Seller Trust** — Reputation score and verification status
- **Distance** — Proximity to you
- **Match Reasons** — Why this is a good match

### Filtering & Sorting
- **Search** by service name or seller
- **Filter** by category (music, storage, streaming, etc.)
- **Sort** by Best Match, Lowest Price, or Nearest

### Creating a Listing
1. Go to **Subscriptions** → select a subscription
2. Click **Create Listing**
3. Set your asking price (or let Vault suggest one)
4. Choose seats available
5. Add a description and preferences
6. Your listing goes live immediately

---

## Matching

### How Matching Works
When you click **Match** on a listing:
1. The Market Matching Agent calculates a multi-factor score
2. The Trust Agent verifies both parties
3. If compatible, a match is proposed
4. The seller can accept or reject
5. Once accepted, escrow is created for payment

### Match Score Factors
| Factor | Weight | Description |
|--------|--------|-------------|
| Trust | 35% | Seller's reputation, KYC status, transaction history |
| Proximity | 25% | Physical distance (less friction for issues) |
| Schedule | 25% | Usage pattern compatibility |
| Price | 15% | Price competitiveness |

### Match Statuses
- **Proposed** — Waiting for seller to accept
- **Accepted** — Both parties agreed, escrow pending
- **Rejected** — Seller declined the match
- **Completed** — Transaction finished successfully
- **Expired** — Match timed out (30 min default)

---

## Payments & Escrow

### How Escrow Works
1. Buyer funds escrow via Stripe (credit card or bank)
2. Funds are held securely until delivery confirmed
3. Seller provides seat access
4. Buyer confirms receipt
5. Funds are released to seller (minus 12% platform fee)

### Payment Flow
```
Buyer pays $5.00
  → Platform fee: $0.60 (12%)
  → Seller receives: $4.40
  → Stripe fee: ~$0.15
```

### Disputes
If there's an issue:
1. Either party can file a dispute
2. Funds are frozen in escrow
3. The Dispute Resolution Agent reviews evidence
4. Resolution is issued (refund or release)
5. Reputation scores are updated

---

## Trust & Reputation

### Building Trust
- **Complete KYC** — Verify your identity (+15% trust bonus)
- **Positive transactions** — Each successful match increases score
- **Fast communication** — Respond quickly to match requests
- **No disputes** — Disputes decrease your score

### Trust Tiers
| Tier | Score | Benefits |
|------|-------|----------|
| Platinum | 90%+ | Priority matching, lowest fees |
| Gold | 75-89% | Standard matching |
| Silver | 60-74% | Standard matching |
| Bronze | < 60% | Limited matching |

### KYC Verification
Required for all users:
1. Upload a government-issued ID
2. Take a selfie
3. Onfido verifies document authenticity
4. Verification is valid for 1 year

---

## Notifications

### Notification Channels
- **Push notifications** — Browser/mobile alerts
- **Email** — Summary digests and important alerts
- **Telegram** — Real-time chat notifications

### Notification Types
- New match proposal
- Match accepted/rejected
- Escrow funded/released
- Usage report ready
- Compliance alerts
- Payout processed

---

## Settings

### Profile
- Update display name, avatar, timezone
- Change password
- Enable two-factor authentication

### Demo Mode
Toggle demo mode to:
- Pre-populate dashboard with realistic mock data
- Test all features without real API connections
- Perfect for presentations and testing

### Privacy
- Export your data (GDPR)
- Delete your account
- Manage notification preferences
- Control location sharing

---

## Troubleshooting

### Common Issues

**"No listings found"**
- Try expanding your search radius
- Check if the service is supported
- Create your own listing to attract matches

**"Match expired"**
- Matches expire after 30 minutes
- Propose a new match quickly
- Ensure your trust score is above the listing's minimum

**"Payment failed"**
- Check your card details with Stripe
- Try a different payment method
- Contact support if issue persists

**"KYC verification pending"**
- Ensure document photos are clear
- Check that all four corners are visible
- Selfie must match the ID photo

### Getting Help
- **In-app chat:** Click the help icon
- **Email:** support@vault.app
- **Status page:** status.vault.app
