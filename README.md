# Vault — AI-Powered Peer-to-Peer Subscription Liquidity Platform

> Unlock the value trapped in underused subscriptions. Vault matches people with complementary usage patterns to share subscriptions safely, securely, and compliantly.

## 📊 The Problem

- **$252/year** wasted on average per household on underutilized subscriptions
- **47%** of Netflix subscribers watch less than 5 hours/month
- **62%** of people pay for full-tier plans that share with strangers anyway
- **$48B** total addressable market in subscription waste globally

## 🏗 Architecture Overview

Vault uses a **five-agent microservices architecture** with event-driven communication:

```
┌─────────────────────────────────────────────────────────────────┐
│                        VAULT PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    Usage      │  │    Trust &   │  │     Market           │  │
│  │  Intelligence │  │ Verification │  │    Matching          │  │
│  │    Agent      │  │    Agent     │  │     Agent            │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           │                                     │
│                    ┌──────┴───────┐                             │
│                    │   Event Bus  │  (Redis Streams / Kafka)    │
│                    └──────┬───────┘                             │
│                           │                                     │
│         ┌─────────────────┼──────────────────────┐              │
│         │                 │                      │              │
│  ┌──────┴───────┐  ┌──────┴───────┐             │              │
│  │  Financial   │  │  Compliance  │             │              │
│  │Orchestration │  │    & Risk    │             │              │
│  │    Agent     │  │    Agent     │             │              │
│  └──────────────┘  └──────────────┘             │              │
│                                                  │              │
├──────────────────────────────────────────────────┤              │
│  PostgreSQL  │  Redis  │  S3  │  Stripe  │ Plaid │              │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker 24+ & Docker Compose v2
- Python 3.11+
- Node.js 18+
- pnpm or npm

### 1. Clone and setup
```bash
git clone https://github.com/your-org/vault.git
cd vault

# Copy environment template
cp .env.example .env
```

### 2. Start infrastructure
```bash
docker compose up -d postgres redis minio
```

### 3. Start backend services
```bash
# API Gateway
cd services/api-gateway
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Each agent service (in separate terminals or docker compose)
cd services/usage-intelligence
pip install -r requirements.txt
celery -A worker worker -l info &
uvicorn main:app --reload --port 8001
```

### 4. Start frontend
```bash
cd frontend/dashboard
pnpm install
pnpm dev
```

### 5. Start mobile (optional)
```bash
cd mobile/vault-app
pnpm install
pnpm start
```

### 6. Demo mode
```bash
# Toggle demo mode in the frontend dashboard
# Navigate to Settings → Enable Demo Mode
# This pre-populates all data with realistic mock data
```

## 🧪 Testing

```bash
# Backend tests
cd services/api-gateway && pytest --cov=. --cov-report=html

# Frontend tests
cd frontend/dashboard && pnpm test

# Load tests
cd tests/load && k6 run --vus 10 --duration 30s scenario.js

# Full test suite
make test
```

## 📦 Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Central REST API, auth, routing |
| Usage Intelligence | 8001 | Subscription usage tracking & analytics |
| Trust & Verification | 8002 | KYC, escrow, reputation scoring |
| Market Matching | 8003 | Dynamic pricing, match discovery |
| Financial Orchestration | 8004 | Payment splitting, payouts, tax forms |
| Compliance & Risk | 8005 | ToS monitoring, risk scoring, circuit breakers |
| Frontend Dashboard | 3000 | React admin/user dashboard |
| Mobile App | 19006 | React Native Expo dev server |

## 🔒 Security

- OAuth 2.0 + JWT with RS256 signing
- AES-256-GCM credential encryption at rest
- TLS 1.3 for all communications
- OWASP Top 10 hardening
- PCI DSS compliant payment handling via Stripe
- GDPR/CCPA data handling with right to deletion
- Row-level security in PostgreSQL

## 📄 Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Security Audit Checklist](docs/security-audit.md)
- [User Manual](docs/user-manual.md)
- [Hackathon Demo Script](docs/demo-script.md)
- [Pitch Deck Outline](docs/pitch-deck.md)

## 📜 License

MIT License — Vault 2024
