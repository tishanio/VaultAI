# Railway Environment Variables Configuration

## Production Environment Variables

| Key | Value | Notes |
|-----|-------|-------|
| `APP_NAME` | `Vault` | Application name |
| `APP_VERSION` | `0.1.0` | From package.json |
| `DEBUG` | `false` | Disable debug mode in production |
| `DEMO_MODE` | `false` | Disable demo mode in production |
| `SECRET_KEY` | `[GENERATE: openssl rand -hex 32]` | Generate a secure random key |
| `DATABASE_URL` | `[AUTO-SET by Railway PostgreSQL]` | Railway creates this automatically |
| `REDIS_URL` | `[AUTO-SET by Railway Redis]` | Railway creates this automatically |
| `JWT_PRIVATE_KEY_PATH` | `keys/jwt_private.pem` | Path to private key file |
| `JWT_PUBLIC_KEY_PATH` | `keys/jwt_public.pem` | Path to public key file |
| `STRIPE_SECRET_KEY` | `sk_live_...` | Your Stripe live secret key |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_...` | Your Stripe live publishable key |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Stripe webhook signing secret |
| `STRIPE_CONNECT_CLIENT_ID` | `ca_...` | Stripe Connect client ID |
| `RAZORPAY_KEY_ID` | `[YOUR_KEY_ID]` | From Razorpay dashboard |
| `RAZORPAY_KEY_SECRET` | `[YOUR_SECRET]` | From Razorpay dashboard |
| `RAZORPAY_WEBHOOK_SECRET` | `[YOUR_WEBHOOK_SECRET]` | Razorpay webhook secret |
| `PLAID_CLIENT_ID` | `[YOUR_CLIENT_ID]` | From Plaid dashboard |
| `PLAID_SECRET` | `[YOUR_SECRET]` | From Plaid dashboard |
| `PLAID_ENV` | `production` | Use production for live |
| `ONFIDO_API_TOKEN` | `[YOUR_TOKEN]` | From Onfido dashboard |
| `ONFIDO_MOCK_MODE` | `false` | Use real verification in production |
| `SENDGRID_API_KEY` | `[YOUR_API_KEY]` | For email notifications |
| `TELEGRAM_BOT_TOKEN` | `[YOUR_TOKEN]` | For Telegram alerts |
| `AWS_REGION` | `us-east-1` | AWS region for S3 |
| `AWS_S3_BUCKET` | `vault-production` | S3 bucket name |
| `AWS_ACCESS_KEY_ID` | `[YOUR_KEY]` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | `[YOUR_SECRET]` | AWS credentials |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API key for AI features |
| `OPENAI_MODEL` | `gpt-4o` | Model to use |
| `CORS_ORIGINS` | `["https://yourdomain.com"]` | Your frontend URL |
| `ENVIRONMENT` | `production` | Environment identifier |
| `API_HOST` | `0.0.0.0` | API host binding |
| `API_PORT` | `8001` | API port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Preview Environment (Staging) Variables

Use same values as Production with these differences:

| Key | Value |
|-----|-------|
| `DEBUG` | `true` |
| `DEMO_MODE` | `true` |
| `STRIPE_SECRET_KEY` | `sk_test_...` (use test keys) |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_...` |
| `PLAID_ENV` | `sandbox` |
| `ONFIDO_MOCK_MODE` | `true` |
| `ENVIRONMENT` | `staging` |
| `CORS_ORIGINS` | `["https://staging.yourdomain.com", "http://localhost:3000"]` |

## Setup Instructions

### Step 1: Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Output example: a1b2c3d4e5f6... (copy this value)
```

### Step 2: In Railway Dashboard

1. Go to your project settings
2. Click **"Variables"** section
3. For each variable above:
   - Enter **Key** (left column)
   - Enter **Value** (right column)
   - Select environment: **Production** or **Preview**
   - Click **"Add"**

### Step 3: Auto-Set Variables

**DATABASE_URL** and **REDIS_URL** are automatically set by Railway when you add:
- PostgreSQL service
- Redis service

You don't need to manually set these.

### Step 4: Configure JWT Keys

The JWT keys path references files in the repo. To handle this in Railway:

**Option A: Store keys as environment variables**
```
JWT_PRIVATE_KEY=[PASTE ENTIRE PRIVATE KEY CONTENT]
JWT_PUBLIC_KEY=[PASTE ENTIRE PUBLIC KEY CONTENT]
```

Then update your code to read from env vars instead of files.

**Option B: Mount keys from repository**
Files are already in `keys/jwt_private.pem` and `keys/jwt_public.pem`

### Step 5: Get Your API Keys

You'll need to gather these from third-party platforms:

**Stripe**
- Go to: https://dashboard.stripe.com/apikeys
- Copy: Secret key (sk_test_... or sk_live_...)
- Copy: Publishable key (pk_test_... or pk_live_...)
- Webhook secret: Settings → Webhooks

**Razorpay**
- Go to: https://dashboard.razorpay.com/app/settings/api-keys
- Copy: Key ID and Key Secret

**Plaid**
- Go to: https://dashboard.plaid.com/team/keys
- Copy: Client ID and Secret

**ONFIDO**
- Go to: https://dashboard.onfido.com/settings/api
- Copy: API Token

**Sendgrid**
- Go to: https://app.sendgrid.com/settings/api_keys
- Create and copy: API Key

**OpenAI**
- Go to: https://platform.openai.com/api-keys
- Copy: API Key

**AWS**
- Go to: IAM → Users → Create access key
- Copy: Access Key ID and Secret Access Key

### Step 6: Deploy

After adding all variables:
1. Railway auto-detects changes
2. Redeploys with new environment variables
3. Monitor logs to verify no connection errors

---

## Verification Checklist

- [ ] DATABASE_URL connects to PostgreSQL
- [ ] REDIS_URL connects to Redis
- [ ] API starts without env var errors
- [ ] Stripe webhooks receive events
- [ ] Razorpay payments process
- [ ] JWT authentication works
- [ ] OpenAI API calls succeed
- [ ] Email notifications send

---

## Troubleshooting

**Error: "DATABASE_URL not found"**
→ Add PostgreSQL service to Railway project

**Error: "REDIS_URL not found"**
→ Add Redis service to Railway project

**Error: "Invalid Stripe key"**
→ Verify you're using correct test (sk_test_) or live (sk_live_) key

**Error: "JWT key path not found"**
→ Use Option A above (store keys as env vars)

**Deployment keeps restarting**
→ Check Railway logs for missing required variables

---

## Frontend Configuration

Your React app also needs env vars. In `frontend/dashboard/.env.production`:

```
VITE_API_URL=https://your-railway-app.railway.app
VITE_STRIPE_PUBLIC_KEY=pk_live_...
VITE_RAZORPAY_KEY=your_razorpay_public_key
```

Or configure in Railway as platform variables for the frontend service.
