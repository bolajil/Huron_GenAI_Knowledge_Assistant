# Phase 1 — AWS Foundation

**Goal:** Stand up the full AWS infrastructure using Terraform, push Docker images to ECR, and have both frontend and backend running healthy on ECS Fargate behind an ALB.

**Status:** ✅ Complete — confirmed healthy 2026-05-31
**Time taken:** ~90 minutes (dominated by RDS provisioning + iterative IAM/SG fixes)

---

## What Was Deployed

| Resource | Details | Status |
|----------|---------|--------|
| VPC | 3-tier: public / private / database subnets across 2 AZs (`us-east-1a/b`) | ✅ |
| Internet Gateway + NAT | Public egress for private subnets | ✅ |
| VPC Endpoints (Interface) | ECR API, ECR DKR, Secrets Manager, CloudWatch Logs — each with dedicated endpoint SG | ✅ |
| VPC Endpoint (Gateway) | S3 | ✅ |
| RDS PostgreSQL 15.12 | Single-AZ `db.t3.micro`, encrypted at rest, private subnet | ✅ |
| ElastiCache Redis | Single-node, private subnet, TLS only | ✅ |
| ECR | `huron-dev-backend`, `huron-dev-frontend` repositories with lifecycle policies | ✅ |
| Secrets Manager | All API keys, JWT secret, DB password stored in one secret | ✅ |
| S3 | `huron-dev-documents-z3xm96` — SSE + versioning enabled | ✅ |
| ALB | HTTP listener on port 80, path-based routing (`/api/*` → backend, `/` → frontend) | ✅ |
| HTTPS listener | Conditional — created only when `certificate_arn` is set in tfvars | ✅ |
| WAF v2 | OWASP managed rules + rate limiting (2000 req/5 min per IP), associated to ALB | ✅ |
| ECS Cluster | `huron-dev-cluster` (Fargate) | ✅ |
| ECS Services | `huron-dev-backend` (port 8004) + `huron-dev-frontend` (port 3000) | ✅ |
| IAM Roles | `ecs-execution-role` (image pull + secret injection) + `ecs-task-role` (S3 + logs) | ✅ |
| CloudWatch | Log groups `/ecs/huron-dev/backend` + `/ecs/huron-dev/frontend`, CPU alarms | ✅ |
| Auto-scaling | Backend: 1–10 tasks, CPU target 70% | ✅ |

**Live URLs (dev):**
- Frontend: `http://huron-dev-alb-1576743853.us-east-1.elb.amazonaws.com`
- API: `http://huron-dev-alb-1576743853.us-east-1.elb.amazonaws.com/api`
- Swagger: `http://huron-dev-alb-1576743853.us-east-1.elb.amazonaws.com/docs`

---

## Prerequisites

- AWS account with admin IAM permissions (Account: `137738968757`, Region: `us-east-1`)
- Terraform 1.14.5+: `terraform --version`
- AWS CLI 2.33.19+: `aws sts get-caller-identity`
- Docker Desktop running

---

## Steps to Reproduce

### 1. Fill in `terraform/aws/terraform.tfvars`

```hcl
aws_region   = "us-east-1"
environment  = "dev"
project_name = "huron"

openai_api_key   = "sk-proj-..."
pinecone_api_key = "pcsk_..."
pinecone_index   = "huron-enterprise-knowledge"

jwt_secret         = "<minimum 32 chars>"
mcp_encryption_key = "<minimum 32 chars>"

db_username          = "huron_admin"
db_password          = "<minimum 16 chars>"
db_name              = "huron_db"
db_instance_class    = "db.t3.micro"   # free-tier; use db.t3.medium on paid account
db_allocated_storage = 20
db_multi_az          = false

backend_cpu            = 2048
backend_memory         = 4096
frontend_cpu           = 512
frontend_memory        = 1024
backend_desired_count  = 1
frontend_desired_count = 1

domain_name     = ""   # leave blank to use ALB DNS
certificate_arn = ""   # leave blank for HTTP-only dev

oidc_client_id     = ""
oidc_client_secret = ""
oidc_authority     = ""
oidc_redirect_uri  = ""

sentry_dsn  = ""
posthog_key = ""

grafana_workspace_name      = "huron-observability"
grafana_account_access_type = "CURRENT_ACCOUNT"
```

### 2. Initialise and apply

```bash
cd terraform/aws
terraform init
terraform validate
terraform plan -out=plan.tfplan
# Review: expect ~67 resources to add
terraform apply plan.tfplan
```

### 3. Push Docker images to ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend

# Build and push backend (from project root)
docker build -t 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend:latest \
  -f backend/Dockerfile.production .
docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend:latest

# Build and push frontend (bake ALB URL at build time)
docker build -t 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend:latest \
  -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL="http://huron-dev-alb-1576743853.us-east-1.elb.amazonaws.com" \
  --build-arg BACKEND_URL="http://huron-dev-alb-1576743853.us-east-1.elb.amazonaws.com" \
  ./frontend
docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend:latest
```

### 4. Trigger ECS deployments

```bash
aws ecs update-service --cluster huron-dev-cluster \
  --service huron-dev-backend --force-new-deployment --region us-east-1

aws ecs update-service --cluster huron-dev-cluster \
  --service huron-dev-frontend --force-new-deployment --region us-east-1

# Wait for both to stabilise (~3-5 min)
aws ecs wait services-stable \
  --cluster huron-dev-cluster \
  --services huron-dev-backend huron-dev-frontend \
  --region us-east-1
```

### 5. Load real secrets into Secrets Manager

ECS injects secrets at task startup from Secrets Manager. After `terraform apply` the secret
contains placeholder values — update with real keys:

```bash
aws secretsmanager put-secret-value \
  --secret-id "arn:aws:secretsmanager:us-east-1:137738968757:secret:huron-dev/app-secrets-f9zHY6" \
  --region us-east-1 \
  --secret-string '{
    "DB_PASSWORD":"<your-db-password>",
    "JWT_SECRET":"<your-32-char-jwt-secret>",
    "OPENAI_API_KEY":"<your-openai-key>",
    "PINECONE_API_KEY":"<your-pinecone-key>",
    "PINECONE_INDEX":"huron-enterprise-knowledge"
  }'

# Force redeploy so ECS picks up new secrets
aws ecs update-service --cluster huron-dev-cluster \
  --service huron-dev-backend --force-new-deployment --region us-east-1
```

### 6. Validate

```bash
curl http://huron-dev-alb-1576743853.us-east-1.elb.amazonaws.com/health
```

Expected response (all green):
```json
{
  "version": "4.0.0",
  "db":      { "status": "ok", "backend": "postgresql" },
  "redis":   { "status": "ok" },
  "pinecone":{ "status": "ok" },
  "status":  "healthy"
}
```

---

## Bugs Found and Fixed During Deployment

These bugs are already corrected in the current `terraform/aws/main.tf`. Documented here so
future deployments to new accounts know what to watch for.

| # | Error | Root Cause | Fix Applied |
|---|-------|-----------|------------|
| 1 | `FreeTierRestrictionError` on RDS backup retention | `backup_retention_period = 7` not allowed on AWS free-tier accounts | Set to `0` (no automated backups for dev); also set `deletion_protection = false` |
| 2 | `FreeTierRestrictionError` on RDS instance size | `db.t3.medium` not available on free-tier | Changed to `db.t3.micro` in tfvars |
| 3 | `InvalidParameterCombination` on postgres version | PostgreSQL `15.4` removed from RDS catalogue | Updated to `15.12` (latest stable available) |
| 4 | `ValidationError` on HTTPS listener | `certificate_arn` is empty in dev; can't create HTTPS listener without cert | Made listener conditional: `count = var.certificate_arn != "" ? 1 : 0`; HTTP listener now forwards directly |
| 5 | WAF `ValidationException` on description | Em-dash `—` rejected by AWS regex `[\w+=:#@/\-,\.]` | Replaced with ASCII hyphen `-` |
| 6 | Grafana `SubscriptionRequiredException` | Amazon Managed Grafana requires the service to be activated in the AWS Console first | Commented out `aws_grafana_workspace` resource; IAM role kept for easy re-enable |
| 7 | ECS tasks stuck `ResourceInitializationError` (timeout) | VPC interface endpoints used the backend task SG, which only allows inbound port 8004 — not HTTPS 443 from tasks | Created dedicated `aws_security_group.vpc_endpoints` allowing inbound 443 from both backend and frontend SGs |
| 8 | ECS tasks `AccessDeniedException` on Secrets Manager | `secretsmanager:GetSecretValue` was on the task role, not the execution role — ECS uses the execution role to pull secrets before container starts | Added `aws_iam_role_policy.ecs_execution_secrets` inline policy to the execution role |

---

## Re-enabling Grafana (when ready)

1. In AWS Console → Amazon Grafana → **Get started** (one-time account activation)
2. Uncomment the `aws_grafana_workspace` resource block in `terraform/aws/main.tf`
3. Run `terraform apply`

---

## Cost Notes (Dev — free-tier account)

| Resource | Monthly estimate |
|----------|-----------------|
| RDS `db.t3.micro` (single-AZ) | ~$0 (free tier 750h/mo) |
| ElastiCache `cache.t3.micro` | ~$12 |
| ALB | ~$16 |
| NAT Gateway | ~$32 + data transfer |
| VPC Interface Endpoints (4) | ~$28 |
| ECS Fargate (1 task each) | ~$15 |
| **Subtotal (dev, free-tier RDS)** | **~$103–120/month** |

Upgrade to paid account → swap `db.t3.micro` → `db.t3.medium` for ~$30/mo increase and enable Multi-AZ for prod.

---

## Validation Checklist

- [x] `terraform apply` exits 0 — 67 resources created
- [x] RDS instance status: `available`
- [x] ElastiCache cluster status: `available`
- [x] ECR repositories exist with images pushed
- [x] WAF associated to ALB
- [x] ECS backend service: running=1, stable
- [x] ECS frontend service: running=1, stable
- [x] `/health` returns `{ "status": "healthy" }` with PostgreSQL + Redis + Pinecone all green
- [ ] Custom domain + HTTPS certificate (Phase 2)
- [ ] Grafana workspace (requires account activation)
