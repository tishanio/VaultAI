# Vault API Documentation

## Base URL
- **Local:** `http://localhost:8000`
- **Production:** `https://api.vault.app`

All endpoints are prefixed with `/api/v1`.

## Authentication

Vault uses **JWT Bearer tokens** with RS256 signing.

```
Authorization: Bearer <access_token>
```

Tokens expire after 1 hour. Use the `/api/v1/auth/refresh` endpoint to get a new access token.

---

## Auth Endpoints

### POST `/api/v1/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123",
  "display_name": "John Doe",
  "phone": "+1234567890"
}
```

**Response (201):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "uuid",
  "username": "johndoe"
}
```

### POST `/api/v1/auth/login`
Authenticate with email and password.

### POST `/api/v1/auth/refresh`
Exchange refresh token for new access + refresh tokens.

### POST `/api/v1/auth/change-password`
Change current user's password (requires auth).

---

## User Endpoints

### GET `/api/v1/users/me`
Get current user's profile.

### PATCH `/api/v1/users/me`
Update current user's profile.

### GET `/api/v1/users/{user_id}`
Get a public user profile by ID.

---

## Subscription Endpoints

### GET `/api/v1/subscriptions`
List current user's subscriptions.

**Query Parameters:**
- `status` (optional): Filter by status (active, paused, cancelled)

### POST `/api/v1/subscriptions`
Add a new subscription to track.

**Request Body:**
```json
{
  "service_name": "Spotify",
  "tier": "family",
  "monthly_cost": 16.99,
  "max_seats": 6,
  "billing_cycle_day": 15
}
```

**Supported Services:** Spotify, Google One, YouTube Premium, Apple Music, Headspace, Calm, Duolingo, Microsoft 365, Canva

**Blocked Services:** Netflix, Adobe, Hulu, HBO Max, Disney+, Amazon Prime Video, Paramount+

### GET `/api/v1/subscriptions/{id}`
Get a specific subscription.

### DELETE `/api/v1/subscriptions/{id}`
Remove a subscription.

### POST `/api/v1/subscriptions/{id}/usage`
Record usage for a subscription period.

### GET `/api/v1/subscriptions/{id}/analytics`
Get usage analytics and optimization recommendations.

---

## Marketplace Endpoints

### GET `/api/v1/marketplace/listings`
Browse available subscription listings.

**Query Parameters:**
- `service_name`: Filter by service
- `service_category`: Filter by category
- `max_price`: Max price filter
- `min_trust_score`: Min seller trust score
- `latitude`, `longitude`: Location for proximity matching
- `radius_km`: Search radius (default: 25)
- `limit` (default: 20, max: 50)
- `offset` (default: 0)

### POST `/api/v1/marketplace/listings`
Create a new listing for available seats.

### DELETE `/api/v1/marketplace/listings/{id}`
Remove a listing.

---

## Match Endpoints

### GET `/api/v1/matches`
List current user's matches (as buyer or seller).

**Query Parameters:**
- `role`: Filter as 'buyer' or 'seller'
- `status`: Filter by match status

### POST `/api/v1/matches/propose/{listing_id}`
Propose a match for a listing.

### POST `/api/v1/matches/{match_id}/accept`
Accept a proposed match (seller only).

### POST `/api/v1/matches/{match_id}/reject`
Reject a proposed match.

---

## Escrow Endpoints

### POST `/api/v1/escrow/matches/{match_id}/escrow`
Create escrow for an accepted match. Returns Stripe PaymentIntent client_secret.

### POST `/api/v1/escrow/escrows/{escrow_id}/fund`
Fund the escrow (capture payment).

### POST `/api/v1/escrow/escrows/{escrow_id}/release`
Release escrow to seller.

### POST `/api/v1/escrow/escrows/{escrow_id}/refund`
Refund escrow to buyer.

### GET `/api/v1/escrow/escrows/{escrow_id}`
Get escrow details.

### POST `/api/v1/escrow/webhooks/stripe`
Stripe webhook handler.

---

## Compliance Endpoints

### GET `/api/v1/compliance/events`
List compliance events with filters.

### GET `/api/v1/compliance/stats`
Get compliance dashboard statistics.

### GET `/api/v1/compliance/risk-score/{user_id}`
Get risk score for a user.

### POST `/api/v1/compliance/events/{event_id}/resolve`
Resolve a compliance event.

---

## Agent Service Endpoints

### Usage Intelligence (port 8001)
- `GET /api/v1/usage/report/{user_id}` — Usage report
- `POST /api/v1/usage/record` — Record usage
- `POST /api/v1/usage/plaid-sync` — Sync Plaid transactions

### Trust & Verification (port 8002)
- `POST /api/v1/trust/kyc/initiate` — Initiate KYC
- `GET /api/v1/trust/kyc/{user_id}` — KYC status
- `GET /api/v1/trust/reputation/{user_id}` — Reputation score
- `POST /api/v1/trust/reputation/update` — Update reputation
- `GET /api/v1/trust/verify/{user_id}` — Full trust verification
- `POST /api/v1/trust/disputes` — File dispute
- `POST /api/v1/trust/disputes/{id}/resolve` — Resolve dispute

### Market Matching (port 8003)
- `POST /api/v1/matching/search` — Search for matches
- `GET /api/v1/matching/availability/{listing_id}` — Check availability
- `POST /api/v1/matching/pricing/update` — Update dynamic pricing

### Financial Orchestration (port 8004)
- `GET /api/v1/finance/split-preview/{escrow_id}` — Payment split preview
- `GET /api/v1/finance/payouts/{user_id}` — Payout history
- `POST /api/v1/finance/payouts/process` — Process pending payouts
- `GET /api/v1/finance/tax-summary/{user_id}` — Tax summary (1099-K)
- `GET /api/v1/finance/dashboard/{user_id}` — Financial dashboard

### Compliance & Risk (port 8005)
- `GET /api/v1/compliance/tos/check/{service_name}` — ToS compliance check
- `GET /api/v1/compliance/risk/{user_id}` — Risk assessment
- `POST /api/v1/compliance/risk/batch` — Batch risk assessment
- `GET /api/v1/compliance/circuit-breakers` — Circuit breaker status
- `POST /api/v1/compliance/circuit-breakers/{id}/trigger` — Trigger circuit breaker
- `GET /api/v1/compliance/report` — Compliance report
- `POST /api/v1/compliance/audit-log` — Log audit event

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad request / validation error |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable entity (validation error) |
| 503 | Service unavailable |

---

## Rate Limiting

- **Standard endpoints:** 60 requests/minute per user
- **Auth endpoints:** 10 requests/minute per IP
- **Webhook endpoints:** No rate limit

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1699000000
```
