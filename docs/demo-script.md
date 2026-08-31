# Vault Hackathon Demo Script

## Pre-Demo Setup (5 minutes before)

```bash
# 1. Start all services
docker compose up -d

# 2. Seed demo data
curl -X POST http://localhost:8000/api/v1/demo/seed

# 3. Open dashboard
open http://localhost:3000

# 4. Enable demo mode (if not already)
# Click "Demo Mode ON" in sidebar

# 5. Verify services are running
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

---

## Demo Flow (10 minutes)

### Slide 1-2: Problem & Solution (2 min)

**Narration:**
> "Americans waste $252 per year on average on underutilized subscriptions. 47% of Netflix subscribers watch less than 5 hours per month. Meanwhile, 62% of people already share accounts informally — with strangers on Reddit. That's risky, unprotected, and violates ToS.
>
> Vault is the AI-powered platform that makes subscription sharing safe, legal, and profitable. We use a 5-agent AI system to match users, verify trust, manage payments in escrow, and ensure compliance."

**Show:** Problem stats slide → Vault logo → Architecture overview

---

### Slide 3: Live Demo — Dashboard (2 min)

**Actions:**
1. Open `http://localhost:3000`
2. Show the Dashboard with demo data populated
3. Point out:
   - **5 active subscriptions** tracked
   - **$27.50/month savings** already achieved
   - **Weekly usage chart** showing optimization opportunities
   - **Trust score** at 87% (Gold tier)

**Narration:**
> "Here's the Vault dashboard. We're tracking 5 subscriptions across music, cloud storage, streaming, wellness, and education. The Usage Intelligence Agent analyzes patterns and shows I could save $27.50/month by sharing unused seats."

**API Demo:**
```bash
# Show the usage report
curl -s http://localhost:8001/api/v1/usage/report/demo-user-1 | python -m json.tool
```

---

### Slide 4: Live Demo — Marketplace (2 min)

**Actions:**
1. Navigate to Marketplace
2. Show filtered listings with match scores
3. Click "Match" on a Spotify listing
4. Show the match animation and score breakdown

**Narration:**
> "The Market Matching Agent uses multi-factor scoring: trust (35%), proximity (25%), schedule compatibility (25%), and price (15%). Watch — I'll match with Alex Chen's Spotify Family seat. Score: 84%, based on his 92% trust rating, 2.3km proximity, and compatible late-evening usage schedule."

**API Demo:**
```bash
# Show the matching search
curl -s -X POST http://localhost:8003/api/v1/matching/search \
  -H "Content-Type: application/json" \
  -d '{"buyer_id": "demo-user-1", "buyer_latitude": 37.7749, "buyer_longitude": -122.4194}' | python -m json.tool
```

---

### Slide 5: Live Demo — Trust & Escrow (2 min)

**Actions:**
1. Navigate to Matches
2. Show the accepted match with Alex Chen
3. Click to view escrow details
4. Show the payment flow (Stripe test mode)

**Narration:**
> "Trust is everything. The Trust & Verification Agent runs KYC via Onfido, calculates reputation from 4 dimensions (reliability, communication, payment history, dispute rate), and holds funds in Stripe Connect escrow. The seller only gets paid when the buyer confirms delivery."

**API Demo:**
```bash
# Show trust verification
curl -s http://localhost:8002/api/v1/trust/verify/demo-user-1 | python -m json.tool

# Show escrow split preview
curl -s http://localhost:8004/api/v1/finance/split-preview/esc-1 | python -m json.tool
```

---

### Slide 6: Live Demo — Compliance (1 min)

**Actions:**
1. Show blocked services list
2. Show circuit breaker status
3. Show risk score for a user

**Narration:**
> "The Compliance & Risk Agent is always watching. It blocks ToS-violating services like Netflix and Adobe, monitors for suspicious activity, and can activate circuit breakers to freeze accounts. Every transaction is risk-scored in real-time."

**API Demo:**
```bash
# Show ToS check — blocked service
curl -s http://localhost:8005/api/v1/compliance/tos/check/Netflix | python -m json.tool

# Show ToS check — allowed service
curl -s http://localhost:8005/api/v1/compliance/tos/check/Spotify | python -m json.tool

# Show circuit breakers
curl -s http://localhost:8005/api/v1/compliance/circuit-breakers | python -m json.tool
```

---

### Slide 7-8: Technical Innovation (1 min)

**Show:** Architecture diagram

**Narration:**
> "Under the hood, Vault runs 5 microservices communicating via Redis Streams. Each agent is independently scalable:
> - **Usage Intelligence** — Plaid transaction scanning + usage analytics
> - **Trust & Verification** — Onfido KYC + reputation scoring
> - **Market Matching** — Dynamic pricing + multi-factor matching
> - **Financial Orchestration** — Stripe Connect escrow + automated payouts
> - **Compliance & Risk** — ToS monitoring + circuit breakers
>
> All in Python/FastAPI with SQLAlchemy, React/TypeScript dashboard, and React Native mobile app."

---

### Slide 9: Market Opportunity (30 sec)

**Show:** Market size slide

**Narration:**
> "The subscription economy is $252B globally. With 47% waste, that's $118B in addressable market. Vault takes 12% of each transaction — if we capture just 0.1% of the US market, that's $35M ARR."

---

### Slide 10: Roadmap & Ask (30 sec)

**Show:** Roadmap slide

**Narration:**
> "Our roadmap:
> - **Q1:** Launch in SF Bay Area with Spotify + Google One
> - **Q2:** Add 10 more services, expand to NYC and LA
> - **Q3:** Enterprise tier for teams
> - **Q4:** International expansion
>
> We're looking for $500K seed to build the full team. Thank you!"

---

## Post-Demo: Q&A Preparation

### Common Questions & Answers

**Q: How do you handle if a user stops paying?**
> "The escrow is pre-funded monthly. If payment fails, the circuit breaker activates, the match is paused, and the buyer is notified. The seller's reputation is updated after resolution."

**Q: What about Netflix's ToS?**
> "We explicitly block Netflix and other services that prohibit sharing. We only support family-plan-compliant services like Spotify and Google One."

**Q: How is this different from just sharing a password?**
> "Three key differences: (1) Escrow-protected payments — no trust required, (2) Usage optimization — we match based on complementary schedules, (3) Compliance — we ensure ToS adherence."

**Q: What's your unit economics?**
> "12% platform fee. Stripe takes ~3%. Net margin ~9% per transaction. Average transaction is $5/month. CAC is near-zero through organic matching."
