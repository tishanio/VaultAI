# Render Environment Variables Quick Reference

## Copy-Paste Template for Render Dashboard

Use this as a checklist when setting environment variables in Render's dashboard.

---

## Auto-Set by Render (DON'T ENTER)

These are automatically created:
- ✅ `DATABASE_URL` ← PostgreSQL service
- ✅ `REDIS_URL` ← Redis service  
- ✅ `VITE_API_URL` ← Backend service URL (for frontend)

---

## Required: Payment Processing

**Stripe** (get from https://dashboard.stripe.com/apikeys)

```
STRIPE_SECRET_KEY = sk_live_...
STRIPE_WEBHOOK_SECRET = whsec_...
STRIPE_PUBLISHABLE_KEY = pk_live_...
```

**Razorpay** (get from https://dashboard.razorpay.com/app/settings/api-keys)

```
RAZORPAY_KEY_ID = rzp_live_...
RAZORPAY_KEY_SECRET = ...
RAZORPAY_WEBHOOK_SECRET = ...
```

---

## Required: Security & AI

**Generate new secure keys:**

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Copy output and paste as STRIPE_WEBHOOK_SECRET value
```

```
SECRET_KEY = [paste the generated value]
OPENAI_API_KEY = sk-... (from https://platform.openai.com/api-keys)
JWT_PRIVATE_KEY_PATH = keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH = keys/jwt_public.pem
```

---

## Optional: AWS S3

If using S3 for file storage (https://console.aws.amazon.com/iam/):

```
AWS_REGION = us-east-1
AWS_S3_BUCKET = vault-production
AWS_ACCESS_KEY_ID = AKIA...
AWS_SECRET_ACCESS_KEY = ...
```

---

## Optional: Email & Notifications

```
SENDGRID_API_KEY = SG... (from https://app.sendgrid.com/settings/api_keys)
TELEGRAM_BOT_TOKEN = ... (from Telegram BotFather)
```

---

## Application Configuration

```
ENVIRONMENT = production
APP_NAME = Vault
APP_VERSION = 0.1.0
DEBUG = false
DEMO_MODE = false
LOG_LEVEL = INFO
API_HOST = 0.0.0.0
API_PORT = 8001
```

---

## CORS Configuration

```
CORS_ORIGINS = ["https://vault-frontend.onrender.com"]
```

---

## Other Services (if using)

**Plaid** (for bank account linking):
```
PLAID_CLIENT_ID = ...
PLAID_SECRET = ...
PLAID_ENV = production
```

**Onfido** (for KYC verification):
```
ONFIDO_API_TOKEN = ...
ONFIDO_MOCK_MODE = false
```

---

## Step-by-Step Entry

1. Go to **Render Dashboard**
2. Click your **VaultAI Blueprint** deployment
3. Click **"Environment"** section
4. For each variable:
   - Click **"Add Variable"**
   - Paste **Key** name (left side)
   - Paste **Value** (right side)
   - Click **"Save"**
5. Render auto-redeploys

---

## Example Entry

**Key:** `STRIPE_SECRET_KEY`  
**Value:** `sk_live_[your-actual-stripe-key]`

**Key:** `RAZORPAY_KEY_ID`  
**Value:** `rzp_live_[your-actual-razorpay-key-id]`

---

## Production Checklist

Copy and fill in as you gather each key:

```
□ STRIPE_SECRET_KEY = ________________
□ STRIPE_WEBHOOK_SECRET = ________________
□ RAZORPAY_KEY_ID = ________________
□ RAZORPAY_KEY_SECRET = ________________
□ RAZORPAY_WEBHOOK_SECRET = ________________
□ SECRET_KEY = ________________ (run: openssl rand -hex 32)
□ OPENAI_API_KEY = ________________
□ SENDGRID_API_KEY = ________________ (optional)
□ AWS_ACCESS_KEY_ID = ________________ (optional)
□ AWS_SECRET_ACCESS_KEY = ________________ (optional)
```

---

## Verification After Deployment

1. **Check Logs**
   ```
   Dashboard → Service → Logs
   ```
   Should see no error messages about missing env vars

2. **Test API**
   ```
   curl https://vault-api.onrender.com/health
   ```
   Should return: `{"status": "ok"}`

3. **Test Frontend**
   ```
   https://vault-frontend.onrender.com
   ```
   Should load without errors

4. **Test Database Connection**
   Check logs for any "connection failed" errors

5. **Test Redis Cache**
   Check logs for cache operation messages

---

## Support

- **Render Docs:** https://render.com/docs
- **Environment Variables:** https://render.com/docs/environment-variables
- **Troubleshooting:** https://render.com/docs/troubleshooting
