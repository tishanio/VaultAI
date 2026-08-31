# Vercel Deployment Guide

## Overview

VaultAI can be deployed on Vercel in two ways:

1. **Frontend only** (React dashboard) - ✅ Recommended for fastest setup
2. **Full stack** (Frontend + Backend API) - Advanced, requires serverless Python

---

## Option 1: Deploy Frontend to Vercel (Recommended)

### Prerequisites
- Vercel account (sign up at https://vercel.com)
- GitHub account with access to `tishanio/VaultAI`

### Steps

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com/dashboard
   - Click: **"Add New"** → **"Project"**

2. **Import Git Repository**
   - Select: **GitHub**
   - Authorize Vercel to access your repos
   - Search and select: **tishanio/VaultAI**

3. **Configure Project Settings**
   - **Framework Preset:** React
   - **Root Directory:** `frontend/dashboard`
   - **Build Command:** `npm run build` (or use default)
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

4. **Add Environment Variables**
   - Click: **"Environment Variables"**
   - Add the following:
   
   ```
   VITE_API_URL=https://your-backend-api.railway.app
   VITE_STRIPE_PUBLIC_KEY=pk_test_...
   VITE_RAZORPAY_KEY=your_razorpay_public_key
   ```

5. **Deploy**
   - Click: **"Deploy"**
   - Vercel builds and deploys your frontend
   - Gets a live URL: `https://vaultai.vercel.app`

### Result
✅ Frontend deployed and auto-updates on every GitHub push

---

## Option 2: Deploy Backend API to Vercel

### Prerequisites
- Vercel CLI installed: `npm install -g vercel`
- Backend running on serverless Python

### Configuration Files

**Root-level `vercel.json`** (already created):
```json
{
  "builds": [
    {
      "src": "services/api_gateway/main.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb",
        "runtime": "python3.11"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "services/api_gateway/main.py"
    }
  ]
}
```

### Create Python Requirements File

Ensure `services/api_gateway/requirements.txt` exists with all dependencies:

```bash
pip install -r services/api_gateway/requirements.txt
```

### Deployment Steps

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Authenticate**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   cd c:\projects\VVault\vault
   vercel --prod
   ```

4. **Configure Environment Variables in Vercel Dashboard**
   - After first deployment, go to project settings
   - Click: **"Environment Variables"**
   - Add all required variables from `.env.example`

5. **Add Database & Redis**
   - ⚠️ **Issue:** Vercel serverless can't easily connect to external databases
   - **Solution:** Use Railway for database + Redis (as recommended earlier)

### Configuration

Update `vercel.json` with environment variables:

```json
"env": {
  "DATABASE_URL": "@database_url",
  "REDIS_URL": "@redis_url",
  "STRIPE_SECRET_KEY": "@stripe_secret_key",
  "RAZORPAY_KEY_ID": "@razorpay_key_id",
  "OPENAI_API_KEY": "@openai_api_key"
}
```

Then set in Vercel dashboard secrets.

---

## Recommended Hybrid Approach ✅

**Best Practice: Use Vercel + Railway**

| Component | Platform | Reason |
|-----------|----------|--------|
| Frontend React App | **Vercel** | Optimized for static sites + edge functions |
| Backend API | **Railway** | Better for long-running Python services |
| Database | **Railway PostgreSQL** | Simple, integrated, scalable |
| Cache | **Railway Redis** | Simple, integrated |

This gives you:
- ✅ Fast frontend CDN on Vercel
- ✅ Reliable backend services on Railway
- ✅ Simple database management
- ✅ Automatic scaling for both

---

## Frontend Deployment on Vercel (Step-by-Step)

### 1. Go to Vercel
```
https://vercel.com/dashboard
```

### 2. Click "Add New Project"

### 3. Import Repository
- Select GitHub integration
- Choose `tishanio/VaultAI`

### 4. Configure
```
Root Directory: frontend/dashboard
Build Command: npm run build
Output Directory: dist
Install Command: npm install
```

### 5. Add Env Vars
```
VITE_API_URL = https://your-railway-app.railway.app
VITE_STRIPE_PUBLIC_KEY = pk_test_xxx
VITE_RAZORPAY_KEY = xxx
```

### 6. Deploy
Click "Deploy" button

### 7. Monitor
- Vercel shows build logs in real-time
- Get live URL when complete
- Auto-deploys on GitHub push

---

## Backend Deployment on Vercel (Advanced)

### Prerequisites
```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login
```

### Deploy Command
```bash
cd c:\projects\VVault\vault
vercel --prod
```

### Issues to Watch For

**Issue 1: Lambda Timeout**
- Vercel functions timeout after 60 seconds
- **Solution:** Use Railway for long-running tasks

**Issue 2: Database Connection**
- Vercel serverless can't maintain persistent connections
- **Solution:** Use Railway PostgreSQL + connection pooling

**Issue 3: File System**
- Serverless has ephemeral file system
- **Solution:** Store files in S3, keys in env vars

**Issue 4: Python Version**
- Ensure `runtime: "python3.11"` in `vercel.json`
- Verify `services/api_gateway/requirements.txt` exists

---

## Environment Variables Reference

### For Frontend (Vercel)
```
VITE_API_URL=https://api.vault.app
VITE_STRIPE_PUBLIC_KEY=pk_test_...
VITE_RAZORPAY_KEY=...
```

### For Backend (Vercel or Railway)
```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
STRIPE_SECRET_KEY=sk_live_...
RAZORPAY_KEY_ID=...
SECRET_KEY=[generated]
ENVIRONMENT=production
```

---

## Verification Checklist

- [ ] Frontend builds successfully on Vercel
- [ ] Frontend has live URL
- [ ] Environment variables set in Vercel
- [ ] Frontend loads without CORS errors
- [ ] API calls reach backend
- [ ] Stripe webhooks configured
- [ ] Database migrations ran
- [ ] Redis cache working

---

## Troubleshooting

### "Build failed"
- Check Vercel logs for error message
- Verify `package.json` exists in `frontend/dashboard/`
- Ensure `vite.config.ts` is correct

### "Cannot find module"
- Run `npm install` locally
- Verify all dependencies in `package.json`

### "CORS error when calling API"
- Add frontend URL to CORS_ORIGINS in backend
- Verify `VITE_API_URL` is correct

### "Database connection failed"
- Verify `DATABASE_URL` is set
- Test connection locally first
- Check PostgreSQL is running

### "Port already in use"
- Vercel auto-assigns ports
- Don't hardcode port in code
- Use environment variable: `process.env.PORT || 8001`

---

## Next Steps

1. **Deploy Frontend First** (takes ~2 minutes)
   - Easier, faster, immediate feedback

2. **Then Deploy Backend** (optional, advanced)
   - If you want full stack on Vercel
   - Or stick with Railway for backend

3. **Configure CI/CD**
   - Vercel auto-deploys on git push
   - Add tests in GitHub Actions

4. **Monitor in Production**
   - Vercel Analytics for performance
   - Error tracking with Sentry
   - Logs available in Vercel dashboard

---

## Quick Links

- **Vercel Dashboard:** https://vercel.com/dashboard
- **Vercel Python Runtime:** https://vercel.com/docs/runtimes/python
- **Vercel Environment Variables:** https://vercel.com/docs/concepts/projects/environment-variables
- **Vercel Deployment:** https://vercel.com/docs/concepts/deployments/overview
