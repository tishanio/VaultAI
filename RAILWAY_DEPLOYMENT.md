# Railway Deployment Guide

## Prerequisites
- GitHub account with access to tishanio/VaultAI
- Railway account (sign up at https://railway.app)
- Stripe and Razorpay API keys

## Deployment Steps

### 1. Create Railway Project
1. Go to **https://railway.app**
2. Sign in with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Authorize Railway to access your GitHub
6. Search and select **tishanio/VaultAI**

### 2. Configure Services

#### PostgreSQL Database
1. Click **"Add"** in Railway dashboard
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically provision and set `DATABASE_URL`

#### Redis Cache
1. Click **"Add"** again
2. Select **"Database"** → **"Redis"**
3. Railway will automatically set `REDIS_URL`

#### Backend API (Python)
1. The repo will auto-detect and create service
2. Set **Start Command**: `python services/api_gateway/main.py`
3. Set **Port**: `8001`

### 3. Environment Variables

Copy the following to Railway's environment section:

**Database & Cache** (auto-set by Railway):
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

**Payment Gateways** (add these manually):
```
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
```

**API Configuration**:
```
API_HOST=0.0.0.0
API_PORT=8001
ENVIRONMENT=production
SECRET_KEY=generate_a_random_string
JWT_SECRET=generate_another_random_string
```

**Frontend URLs**:
```
VITE_API_URL=https://vaultai-production.railway.app
VITE_STRIPE_PUBLIC_KEY=pk_live_...
VITE_RAZORPAY_KEY=your_public_key
```

### 4. Configure Domains

1. In Railway dashboard, go to your backend service
2. Click **"Settings"** → **"Domain"**
3. Enable domain - Railway will assign: `vaultai-production.railway.app`
4. Copy this URL to `VITE_API_URL` in frontend

### 5. Deploy

1. Railway automatically deploys when you push to GitHub
2. Monitor deployment in Railway dashboard
3. Check logs for any errors

### 6. Database Migrations

After first deployment:
```bash
# SSH into Railway container and run:
alembic upgrade head
```

Or set this in the start command:
```
alembic upgrade head && python services/api_gateway/main.py
```

## Verification

- Backend API: `https://vaultai-production.railway.app/health`
- Check Redis connection in logs
- Monitor database in Railway PostgreSQL dashboard

## Troubleshooting

**"Database connection failed"**
- Verify `DATABASE_URL` is set correctly
- Check PostgreSQL service is running in Railway

**"Redis connection refused"**
- Verify `REDIS_URL` is set
- Ensure Redis service is added to project

**"Missing environment variables"**
- All vars from `.env.example` must be set in Railway
- Restart deployment after adding variables

## Next Steps

- Set up GitHub Actions for automated testing before deployment
- Configure monitoring with Railway's built-in logs
- Set up error tracking (Sentry integration available)
- Configure custom domain instead of Railway domain
