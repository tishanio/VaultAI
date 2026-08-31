# Vault Troubleshooting Guide

## Common Issues & Solutions

### 1. Stripe Webhook Failures

**Symptom:** Webhook events not received in local development.

**Solution:**
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/v1/escrow/webhooks/stripe

# Copy the webhook signing secret (whsec_...) to your .env
```

**If using demo mode:** Webhook verification is bypassed. All payments are simulated.

---

### 2. Plaid Sandbox Errors

**Symptom:** Plaid API returns "invalid credentials" or "sandbox token expired".

**Solution:**
```bash
# Get fresh sandbox credentials from Plaid dashboard
# https://dashboard.plaid.com/team/keys

# Update .env
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_sandbox_secret
PLAID_ENV=sandbox
```

**If Plaid is not configured:** Use demo mode which generates synthetic usage data without Plaid.

---

### 3. Docker Networking Problems

**Symptom:** Services can't connect to each other.

**Solution:**
```bash
# Check if services are running
docker compose ps

# Check logs for connection errors
docker compose logs api-gateway

# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d

# Verify network connectivity
docker compose exec api-gateway ping postgres
docker compose exec api-gateway ping redis
```

---

### 4. Database Connection Errors

**Symptom:** `asyncpg: connection refused` or `FATAL: password authentication failed`

**Solution:**
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Reset database
docker compose down -v
docker compose up -d postgres
sleep 5

# Re-run migrations
cd services/api-gateway
alembic upgrade head

# Seed demo data
curl -X POST http://localhost:8000/api/v1/demo/seed
```

---

### 5. Redis Connection Issues

**Symptom:** `ConnectionRefusedError: [Errno 111] Connection refused` for Redis

**Solution:**
```bash
# Check Redis is running
docker compose ps redis

# Test Redis connection
docker compose exec redis redis-cli ping
# Should return: PONG

# If not running
docker compose up -d redis
```

---

### 6. Frontend Build Errors

**Symptom:** TypeScript compilation errors or missing dependencies.

**Solution:**
```bash
cd frontend/dashboard

# Clean install
rm -rf node_modules
pnpm install

# Check for TypeScript errors
pnpm typecheck

# If Tailwind styles not loading
pnpm build
```

---

### 7. Port Conflicts

**Symptom:** `Error: listen EADDRINUSE: address already in use :::8000`

**Solution:**
```bash
# Find process using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn main:app --reload --port 8001
```

---

### 8. JWT Token Errors

**Symptom:** `401 Unauthorized` on authenticated endpoints.

**Solution:**
```bash
# Ensure JWT keys exist
ls keys/

# If missing, delete and restart (keys auto-generate)
rm -rf keys/
# Restart any service — keys will be regenerated

# Test token creation
python -c "from vault.security import create_access_token, decode_token; t = create_access_token('test'); print(decode_token(t))"
```

---

### 9. Alembic Migration Conflicts

**Symptom:** `alembic.util.exc.CommandError: Can't locate revision identified by 'xxx'`

**Solution:**
```bash
# Check current revision
alembic current

# Stamp to latest (if DB is already correct)
alembic stamp head

# Or reset completely
alembic downgrade base
alembic upgrade head
```

---

### 10. Demo Mode Not Working

**Symptom:** Dashboard shows no data or API returns empty responses.

**Solution:**
```bash
# 1. Toggle demo mode in sidebar or via API
curl -X POST http://localhost:8000/api/v1/demo/toggle

# 2. Seed demo data
curl -X POST http://localhost:8000/api/v1/demo/seed

# 3. Verify demo mode is on
curl http://localhost:8000/health
# Should show DEMO_MODE in response
```

---

## Performance Optimization

### Target Benchmarks
- API p95 latency: < 200ms
- Database query p95: < 50ms
- Concurrent users: 100+

### Optimization Tips
1. **Enable connection pooling:** Ensure `pool_size` is configured in database settings
2. **Use Redis caching:** Cache frequently accessed data (listings, user profiles)
3. **Lazy loading:** Don't fetch all data upfront
4. **Index optimization:** Check `EXPLAIN ANALYZE` on slow queries

---

## Getting Help

If issues persist:
1. Check logs: `docker compose logs -f`
2. Run health checks: `make health`
3. Review the API docs: `http://localhost:8000/docs` (in debug mode)
4. Check GitHub Issues for known problems
