# Vault Deployment Guide

## Overview

Vault deploys to AWS using ECS Fargate for compute, RDS PostgreSQL for data, ElastiCache Redis for caching, and S3 for file storage. Infrastructure is managed via Terraform.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform 1.6+
- Docker 24+
- Node.js 18+
- Python 3.11+
- pnpm 8+

## Local Development

### 1. Clone and setup
```bash
git clone https://github.com/your-org/vault.git
cd vault
cp .env.example .env
```

### 2. Start infrastructure
```bash
docker compose up -d postgres redis minio
```

### 3. Initialize database
```bash
cd services/api-gateway
pip install -r requirements.txt
alembic upgrade head
```

### 4. Seed demo data
```bash
curl -X POST http://localhost:8000/api/v1/demo/seed
```

### 5. Start services
```bash
# Option A: Docker Compose (all services)
docker compose up

# Option B: Individual terminals
cd services/api-gateway && uvicorn main:app --reload --port 8000
cd services/usage-intelligence && uvicorn main:app --reload --port 8001
cd services/trust-verification && uvicorn main:app --reload --port 8002
cd services/market-matching && uvicorn main:app --reload --port 8003
cd services/financial-orchestration && uvicorn main:app --reload --port 8004
cd services/compliance-risk && uvicorn main:app --reload --port 8005
```

### 6. Start frontend
```bash
cd frontend/dashboard
pnpm install
pnpm dev
```

## Staging Deployment

### 1. Initialize Terraform
```bash
cd infrastructure/terraform
terraform init
terraform workspace new staging
```

### 2. Plan and apply
```bash
terraform plan -var-file="staging.tfvars" -out=tfplan
terraform apply tfplan
```

### 3. Build and push Docker images
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

for service in api-gateway usage-intelligence trust-verification market-matching financial-orchestration compliance-risk; do
  docker build -t vault-$service:latest .
  docker tag vault-$service:latest <account>.dkr.ecr.us-east-1.amazonaws.com/vault-$service:latest
  docker push <account>.dkr.ecr.us-east-1.amazonaws.com/vault-$service:latest
done
```

### 4. Run migrations
```bash
aws ecs run-task \
  --cluster vault-staging \
  --task-definition vault-migrate \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

### 5. Deploy services
```bash
for service in api-gateway usage-intelligence trust-verification market-matching financial-orchestration compliance-risk; do
  aws ecs update-service \
    --cluster vault-staging \
    --service $service \
    --force-new-deployment
done
```

## Production Deployment

Same as staging, but:
- Use `production` workspace
- RDS Multi-AZ is enabled
- ElastiCache has 3 nodes
- CloudFront CDN is configured
- WAF is enabled
- Monitoring alerts are active

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `STRIPE_SECRET_KEY` | Stripe API key | Required |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | Required |
| `JWT_PRIVATE_KEY_PATH` | Path to RSA private key | `keys/jwt_private.pem` |
| `ENCRYPTION_KEY` | AES-256 key (base64) | Required in production |
| `DEMO_MODE` | Enable demo mode | `false` |

## Monitoring

- **Prometheus:** Metrics scraping at `/metrics`
- **Grafana:** Dashboard at `:3001`
- **CloudWatch:** AWS metrics and logs
- **Structured Logging:** JSON format via Loguru

## SSL/TLS

Production uses ACM certificates with CloudFront:
```bash
aws acm request-certificate --domain-name api.vault.app --validation-method DNS
```

## Backup & Recovery

- RDS automated backups: 7-day retention
- S3 versioning enabled
- ElastiCache daily snapshots
- Runbook in `docs/runbook.md`
