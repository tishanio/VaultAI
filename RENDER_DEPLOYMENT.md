# Render Full-Stack Deployment Guide

## Overview

Deploy the entire VaultAI stack on Render with a single configuration file:
- **Frontend:** React app (Node.js)
- **Backend:** Python FastAPI
- **Database:** PostgreSQL
- **Cache:** Redis

---

## Prerequisites

1. **Render Account** (https://render.com)
   - Sign up with GitHub
   - Free tier available for testing

2. **GitHub Repository**
   - Already have `tishanio/VaultAI`
   - Render reads from main branch

3. **API Keys** (gather before deploying)
   - Stripe: secret + webhook keys
   - Razorpay: key ID + secret + webhook
   - OpenAI: API key
   - AWS (optional): S3 access

---

## Quick Deploy (5 Minutes)

### Step 1: Go to Render Dashboard

```
https://render.com/dashboard
```

### Step 2: Connect GitHub Repository

1. Click **"New +"** → **"Blueprint"**
2. **Select Repository:** `tishanio/VaultAI`
3. Click **"Connect"**

### Step 3: Configure Blueprint

Render auto-detects `render.yaml` in your repo

1. **Name your blueprint:** `VaultAI Production`
2. **Review services:**
   - ✅ vault-postgres (Database)
   - ✅ vault-redis (Cache)
   - ✅ vault-api (Backend)
   - ✅ vault-frontend (Frontend)

### Step 4: Set Environment Variables

Before deploying, set these required variables:

**Payment Gateways:**
```
STRIPE_SECRET_KEY = sk_live_...
STRIPE_WEBHOOK_SECRET = whsec_...
RAZORPAY_KEY_ID = your_key_id
RAZORPAY_KEY_SECRET = your_secret
RAZORPAY_WEBHOOK_SECRET = your_webhook_secret
```

**AI/Services:**
```
OPENAI_API_KEY = sk-...
SECRET_KEY = [Generate: openssl rand -hex 32]
```

**Optional (if using S3):**
```
AWS_REGION = us-east-1
AWS_S3_BUCKET = vault-assets
AWS_ACCESS_KEY_ID = your_key
AWS_SECRET_ACCESS_KEY = your_secret
```

### Step 5: Deploy

1. Click **"Deploy Blueprint"**
2. Render provisions all services automatically:
   - Creates PostgreSQL database
   - Creates Redis instance
   - Builds and deploys backend
   - Builds and deploys frontend
3. Monitor deployment progress in dashboard

### Step 6: Verify Deployment

- **Frontend URL:** `https://vault-frontend.onrender.com`
- **Backend URL:** `https://vault-api.onrender.com`
- **API Health:** `https://vault-api.onrender.com/health`

---

## Understanding `render.yaml`

### PostgreSQL Service
```yaml
- type: pserv
  name: vault-postgres
  plan: starter
  dbName: vault_db
  user: vault_user
```
- Creates managed PostgreSQL database
- Auto-generates `DATABASE_URL`
- Starter plan: 256 MB RAM, free tier eligible

### Redis Service
```yaml
- type: pserv
  name: vault-redis
  plan: starter
```
- Creates managed Redis cache
- Auto-generates connection string
- Starter plan: free tier eligible

### Backend API Service
```yaml
- type: web
  name: vault-api
  runtime: python
  buildCommand: |
    pip install -r services/api_gateway/requirements.txt
    alembic upgrade head
  startCommand: python services/api_gateway/main.py
```
- Runs Python FastAPI
- Installs dependencies from `requirements.txt`
- Runs database migrations on each deploy
- Restarts on code changes

### Frontend Service
```yaml
- type: web
  name: vault-frontend
  runtime: node
  rootDir: frontend/dashboard
  buildCommand: npm run build
  startCommand: npm run preview
```
- Builds React app
- Serves from `dist/` directory
- Auto-updates on git push

---

## Environment Variables Setup

### Auto-Set (Don't Edit)

These are automatically populated by Render:

```
DATABASE_URL       ← PostgreSQL connection string
REDIS_URL          ← Redis connection string
VITE_API_URL       ← Backend URL (frontend auto-linked)
```

### Required (Must Set in Dashboard)

**Payment Processing:**
| Variable | Source | Get From |
|----------|--------|----------|
| `STRIPE_SECRET_KEY` | Stripe | https://dashboard.stripe.com/apikeys |
| `STRIPE_WEBHOOK_SECRET` | Stripe | Settings → Webhooks |
| `RAZORPAY_KEY_ID` | Razorpay | https://dashboard.razorpay.com/settings/api-keys |
| `RAZORPAY_KEY_SECRET` | Razorpay | Same page |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay | Webhooks section |

**Security & AI:**
| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Run: `openssl rand -hex 32` and paste result |
| `OPENAI_API_KEY` | From https://platform.openai.com/api-keys |

**Optional (AWS S3):**
| Variable | Value |
|----------|-------|
| `AWS_REGION` | `us-east-1` |
| `AWS_S3_BUCKET` | `vault-production` |
| `AWS_ACCESS_KEY_ID` | From AWS IAM |
| `AWS_SECRET_ACCESS_KEY` | From AWS IAM |

---

## Deployment Steps in Render Dashboard

### 1. Navigate to Blueprint

```
Render Dashboard → New + → Blueprint
```

### 2. Connect GitHub

- Select GitHub integration
- Authorize Render
- Search: `tishanio/VaultAI`
- Click to connect

### 3. Review Services

```
✅ vault-postgres     (PostgreSQL Database)
✅ vault-redis        (Redis Cache)
✅ vault-api          (Backend API)
✅ vault-frontend     (React App)
```

### 4. Set Environment Variables

In the deployment form:

```
Name                          Value
─────────────────────────────────────────────────────
STRIPE_SECRET_KEY             sk_live_xxxxx
STRIPE_WEBHOOK_SECRET         whsec_xxxxx
RAZORPAY_KEY_ID               rzp_xxxxx
RAZORPAY_KEY_SECRET           xxxxx
SECRET_KEY                    [Generated value]
OPENAI_API_KEY                sk-xxxxx
CORS_ORIGINS                  ["https://vault-frontend.onrender.com"]
```

### 5. Click "Deploy Blueprint"

Render orchestrates:
1. PostgreSQL provisioning (30 sec)
2. Redis provisioning (30 sec)
3. Backend build (2-3 min)
4. Frontend build (2-3 min)
5. Services start and link (1 min)

**Total: ~8-10 minutes**

---

## Post-Deployment Configuration

### 1. Get Your URLs

After deployment completes:
- **Frontend:** `https://vault-frontend.onrender.com`
- **Backend:** `https://vault-api.onrender.com`

### 2. Configure Webhooks

**Stripe:**
1. Go: https://dashboard.stripe.com/webhooks
2. Click: "Add endpoint"
3. URL: `https://vault-api.onrender.com/webhooks/stripe`
4. Events: payment_intent.succeeded, charge.refunded
5. Copy webhook signing secret
6. Paste as `STRIPE_WEBHOOK_SECRET` in Render

**Razorpay:**
1. Go: https://dashboard.razorpay.com/settings/webhooks
2. Add webhook:
   - URL: `https://vault-api.onrender.com/webhooks/razorpay`
   - Events: payment.authorized, payment.failed
3. Copy webhook secret
4. Paste as `RAZORPAY_WEBHOOK_SECRET` in Render

### 3. Update Frontend API URL

Frontend auto-links to backend via `VITE_API_URL` env var. Verify:
- API calls use correct endpoint
- No CORS errors in browser console

### 4. Test API Connection

```bash
curl https://vault-api.onrender.com/health
```

Should return: `{"status": "ok"}`

---

## Scaling & Monitoring

### View Logs
```
Dashboard → Service → Logs
```

### Monitor Performance
```
Dashboard → Service → Metrics
```

### Adjust Plan
```
Settings → Instance Type
- Starter: Free, with sleep mode
- Professional: $7/month, no sleep
- Standard: $12/month+
```

### Auto-Deploy
- Render auto-redeploys on git push to `main`
- No manual deployment needed
- Monitor in "Deployments" tab

---

## Troubleshooting

### "Build failed"
1. Check logs: Dashboard → Service → Logs
2. Verify `requirements.txt` exists for Python
3. Verify `package.json` exists in `frontend/dashboard/`
4. Check syntax errors in code

### "Database connection failed"
1. Verify `DATABASE_URL` is set
2. Run migrations manually if needed
3. Check PostgreSQL service status

### "Redis connection refused"
1. Verify `REDIS_URL` is set
2. Check Redis service is running
3. Restart Redis service if needed

### "Frontend shows blank page"
1. Check frontend logs
2. Verify `VITE_API_URL` is correct
3. Look for CORS errors in browser console

### "API 502 Bad Gateway"
1. Check backend logs
2. Verify all env vars are set
3. Check database migrations ran
4. Restart backend service

### "Stripe webhooks not working"
1. Verify webhook URL is correct
2. Check webhook signing secret matches
3. Monitor webhook deliveries in Stripe dashboard

---

## Cost Estimate

| Service | Plan | Cost |
|---------|------|------|
| PostgreSQL | Starter | Free (with usage limits) |
| Redis | Starter | Free (with usage limits) |
| Backend API | Professional | $7/month (recommended for production) |
| Frontend | Starter | Free |
| **Total** | | **~$7/month** |

*Starter services sleep after 15 min inactivity (free tier)*
*Professional services run 24/7 (production ready)*

---

## Next Steps

1. **Gather API keys** (Stripe, Razorpay, OpenAI)
2. **Go to Render:** https://render.com/dashboard
3. **Deploy blueprint** (click "New +" → "Blueprint")
4. **Set environment variables**
5. **Monitor deployment** in dashboard
6. **Configure webhooks** in payment providers
7. **Test** API and frontend
8. **Monitor logs** for any errors

---

## Production Checklist

- [ ] All API keys configured
- [ ] Frontend loads without errors
- [ ] API responds to health check
- [ ] Database migrations ran successfully
- [ ] Redis cache working
- [ ] Stripe webhooks receiving events
- [ ] Razorpay webhooks receiving events
- [ ] Email notifications working
- [ ] Error logging configured
- [ ] Performance monitoring enabled
- [ ] Database backups enabled
- [ ] Auto-redeploy on git push verified

---

## Quick Links

- **Render Dashboard:** https://render.com/dashboard
- **Render Docs:** https://render.com/docs
- **Render YAML Reference:** https://render.com/docs/infrastructure-as-code
- **GitHub Integration:** https://render.com/docs/github
- **Environment Variables:** https://render.com/docs/environment-variables
