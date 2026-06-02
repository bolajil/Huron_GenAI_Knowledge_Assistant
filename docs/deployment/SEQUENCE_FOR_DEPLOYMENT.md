# Huron GenAI — Sequence for Deployment

This document is the single authoritative reference for deploying Huron GenAI
from a fresh machine all the way to production. Follow steps in exact order.

***

## AWS Account Requirements by Environment

> **Important:** The current dev and staging environments run on a personal AWS
> free-tier account with restrictions. When moving to the real Huron AWS account,
> the configuration below must be used. Free-tier accounts cannot support backup
> retention, storage encryption, Multi-AZ, or larger instance types.

### Personal / Free Tier Account (current dev & staging)

| Setting | Value | Reason |
|---------|-------|--------|
| RDS instance | `db.t3.micro` | Only free-tier allowed instance |
| Backup retention | `0` | Free tier blocks any retention > 0 |
| Storage encrypted | `false` | Free tier restriction |
| Multi-AZ | `false` | Free tier restriction |
| ECS CPU/Memory | 256/512 | Minimal to stay within free tier |
| ElastiCache | Basic single node | Free tier |
| SSL/HTTPS | Not configured | No custom domain |

### Huron Enterprise Account (required for real staging & production)

When Huron provides the AWS account, update `staging.tfvars` and `prod.tfvars`
with these production-grade values:

| Setting | Staging | Production | Reason |
|---------|---------|-----------|--------|
| RDS instance | `db.t3.small` | `db.t3.medium` or larger | Handles real query load |
| Backup retention | `7` days | `30` days | Point-in-time recovery |
| Storage encrypted | `true` | `true` | HIPAA/compliance requirement |
| Multi-AZ | `false` | `true` | Zero-downtime failover for prod |
| Deletion protection | `false` | `true` | Prevents accidental data loss |
| ECS Backend CPU/Mem | `512/1024` | `1024/2048` | Production workload capacity |
| ECS Frontend CPU/Mem | `256/512` | `512/1024` | Production workload capacity |
| ElastiCache | `cache.t3.micro` | `cache.t3.small` | Session management at scale |
| SSL/HTTPS | Required | Required | `certificate_arn` from ACM |
| Custom domain | `staging.huron.ai` | `app.huron.ai` | Set in `route53.tf` |
| Blue/Green deploy | `false` | `true` | Zero-downtime prod deployments |

### Changes to make in tfvars when switching to Huron account

**`staging.tfvars` — update these lines:**
```hcl
aws_region   = "<HURON_AWS_REGION>"    # confirm region with Huron IT

use_free_tier = false                   # already false, no change needed

backend_cpu            = 512
backend_memory         = 1024
frontend_cpu           = 256
frontend_memory        = 512

db_instance_class          = "db.t3.small"
db_backup_retention_period = 7          # was 0 on free tier
db_storage_encrypted       = true       # was false on free tier
db_multi_az                = false      # keep false for staging

openai_api_key     = "<HURON_OPENAI_KEY>"     # replace personal key
pinecone_api_key   = "<HURON_PINECONE_KEY>"   # replace personal key
pinecone_index     = "huron-staging"

certificate_arn = "<ACM_CERT_ARN>"      # get from Huron IT
```

**`prod.tfvars` — update these lines:**
```hcl
aws_region   = "<HURON_AWS_REGION>"

use_free_tier = false

backend_cpu            = 1024
backend_memory         = 2048
frontend_cpu           = 512
frontend_memory        = 1024

db_instance_class          = "db.t3.medium"
db_backup_retention_period = 30
db_storage_encrypted       = true
db_multi_az                = true
db_deletion_protection     = true

openai_api_key     = "<HURON_OPENAI_KEY>"
pinecone_api_key   = "<HURON_PINECONE_KEY>"
pinecone_index     = "huron-enterprise-knowledge"

certificate_arn   = "<ACM_CERT_ARN>"
enable_blue_green = true              # enables CodeDeploy Blue/Green

github_repo = "HuronOrg/Huron_GenAI_Knowledge_Assistant"
```

### Information to request from Huron IT before switching accounts

- [ ] Huron AWS Account ID and preferred region
- [ ] IAM user or role for Terraform (needs broad permissions for first apply)
- [ ] ACM SSL certificate ARN for the application domain
- [ ] Approved domain names (staging + production)
- [ ] Huron OpenAI API key (enterprise tier)
- [ ] Huron Pinecone API key and index name
- [ ] VPC CIDR range preferences (default: `10.0.0.0/16`)
- [ ] Confirmation of required AWS services (RDS, ECS, ElastiCache, WAF)
- [ ] Any compliance requirements (HIPAA, SOC2) that affect encryption config

---

## The 3-Stage Pipeline

```
LOCAL (test here first)
    │
    │  git push origin develop
    ▼
DEV  (AWS — free tier OK for personal account / full config for Huron account)
    │
    │  git push origin staging
    ▼
STAGING  (AWS — moderate, automated deploy after CI passes)
    │
    │  Manual trigger in GitHub Actions → type "DEPLOY"
    ▼
PROD  (AWS — full scale, Blue/Green via CodeDeploy)
```

**Rule:** Never skip a stage. Test locally → dev → staging → prod.

***

## Prerequisites (one-time installs)

```Shell
# AWS CLI
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
aws configure    # enter your AWS Access Key ID, Secret, region: us-east-1

# Terraform
https://developer.hashicorp.com/terraform/downloads
terraform -version    # should be >= 1.5

# GitHub CLI (gh) — needed for secret/variable setup
https://cli.github.com
gh auth login    # choose GitHub.com → HTTPS → Login with browser

# Docker Desktop
https://www.docker.com/products/docker-desktop
```

***

## Stage 0 — Local Development

### Start local services

```Shell
# Start database container (port 5436)
docker start huron-postgres

# Start backend (from backend/ directory)
cd backend
uvicorn main:app --reload --port 8004

# Start frontend (from frontend/ directory)
cd frontend
npm run dev
# App at http://localhost:3000
```

### What seeds automatically on first run

* Root user: `root` / `HuronRoot2026!`
* 8 departments: HR, Legal, Finance, Clinical, Operations, IT, Marketing, External

### Run tests locally before pushing

```Shell
# Unit tests (no database needed)
pytest tests/unit/ -v

# Integration tests (needs huron-postgres running)
pytest tests/integration/ -v

# Frontend type check + lint
cd frontend && npx tsc --noEmit && npx next lint
```

***

## Stage 1 — First-Time Cloud Setup (run once per environment)

### Step 1 — Create infrastructure

```Shell
cd terraform/aws
terraform init

# For DEV:
terraform apply -var-file environments/dev.tfvars
# For STAGING:
terraform apply -var-file environments/staging.tfvars
# For PROD:
terraform apply -var-file environments/prod.tfvars
```

This creates: VPC, ECS cluster, RDS PostgreSQL, ECR repos, ALB, IAM user, Secrets Manager.

Takes \~10-15 minutes.

### Step 2 — Set GitHub Secrets (AWS credentials)

> **When is this required?**
> - First time setting up a new environment
> - After `terraform destroy` + `terraform apply` on dev or staging (new IAM user created)
> - **Production: NEVER run `terraform destroy` on prod. RDS and all data persist permanently.
>   Only redo this step if you deliberately rotated the IAM key for security reasons.**

#### Windows (PowerShell) — requires gh CLI:

```PowerShell
.\scripts\setup-github-secrets.ps1 -Env dev
```

#### Linux/Mac (Bash) — requires gh CLI:

```Shell
./scripts/setup-github-secrets.sh dev
```

#### Manual (no gh CLI):

```Shell
# 1. Delete any old keys first (max 2 allowed)
aws iam list-access-keys --user-name huron-dev-cicd-user
aws iam delete-access-key --user-name huron-dev-cicd-user --access-key-id <OLD_ID>

# 2. Create ONE fresh key — copy BOTH values immediately
aws iam create-access-key --user-name huron-dev-cicd-user
# Output:
# {
#   "AccessKey": {
#     "AccessKeyId": "AKIAXXXXXXXXXXXXXXXX",       ← copy this
#     "SecretAccessKey": "xxxxxxxxxxxxxxxxxxxx"    ← copy this
#   }
# }
```

Go to: `https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant/settings/secrets/actions`

Add **two separate secrets** — one per entry, raw value only (NO `KEY = VALUE` format):

| Secret Name             | Value                                         |
| ----------------------- | --------------------------------------------- |
| `AWS_ACCESS_KEY_ID`     | Just the key ID (e.g. `AKIAXXXXXXXXXXXXXXXX`) |
| `AWS_SECRET_ACCESS_KEY` | Just the secret key value                     |

> **CRITICAL:** Both values must come from the same `create-access-key` output.
> Mixing values from different calls = "security token invalid" error.
>
> **NOTE:** These secrets are shared across all environments (dev/staging/prod).
> The same IAM user deploys to all three. You only set them once — not once per environment.
> Only redo if you ran `terraform destroy` on dev/staging (which recreates the IAM user)
> or if you explicitly rotated the key for security.

Also add the database URL as a secret — **only needed after terraform apply (new RDS created)**:

```Shell
# Get the RDS endpoint
terraform output db_endpoint
```

| Secret Name        | Value                                                               |
| ------------------ | ------------------------------------------------------------------- |
| `DEV_DATABASE_URL` | `postgresql://huron_user:<password>@<rds-endpoint>:5432/huron_dev` |

> **Production note:** `PROD_DATABASE_URL` is set once when prod is first deployed and never
> changes unless you migrate to a new RDS instance. Do NOT destroy prod RDS — all user data,
> query history, and documents would be permanently lost.

### Step 3 — Set GitHub Variables (non-sensitive config)

#### Windows (PowerShell):

```PowerShell
.\scripts\post-apply.ps1 -Env dev
```

#### Linux/Mac (Bash):

```Shell
./scripts/post-apply.sh dev
```

#### Manual (no gh CLI):

```Shell
# Get values from terraform
cd terraform/aws
terraform output alb_dns_name      # → DEV_ALB_URL value
terraform output ecr_backend_url   # → DEV_ECR_BACKEND value
terraform output ecr_frontend_url  # → DEV_ECR_FRONTEND value
terraform output ecs_cluster_name  # → DEV_ECS_CLUSTER value
```

Go to: `https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant/settings/variables/actions`

Add these variables (one per entry):

| Variable Name      | Value                                                             |
| ------------------ | ----------------------------------------------------------------- |
| `DEV_ALB_URL`      | `http://huron-dev-alb-XXXX.us-east-1.elb.amazonaws.com`           |
| `DEV_ECR_BACKEND`  | `137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend`  |
| `DEV_ECR_FRONTEND` | `137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend` |
| `DEV_ECS_CLUSTER`  | `huron-dev-cluster`                                               |

Repeat for staging with `STAGING_` prefix, and prod with `PROD_URL`.

### Step 4 — Bootstrap first Docker images

ECR repos start empty. ECS cannot start without images. Push once manually:

```Shell
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  137738968757.dkr.ecr.us-east-1.amazonaws.com

# Backend
docker build -f backend/Dockerfile.production \
  -t 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend:latest .
docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend:latest

# Frontend
docker build -f frontend/Dockerfile.production \
  -t 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=http://<DEV_ALB_URL> ./frontend
docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend:latest
```

After this bootstrap, all future deployments are fully automated.

***

## Stage 2 — Daily Deployment Flow

### Deploy to DEV (automatic)

```Shell
git checkout develop
git pull origin develop
# ... make changes, test locally ...
git add .
git commit -m "feat: your change"
git push origin develop

# GitHub Actions automatically:
# 1. CI: unit tests + lint + integration tests + docker build (~17 min)
# 2. DB migrations run (if any new .sql files in backend/migrations/versions/)
# 3. Build + push Docker images to ECR
# 4. ECS force redeploy
# 5. Health check at DEV_ALB_URL/health
```

### Promote to STAGING (when DEV is stable)

```Shell
git checkout staging
git merge develop
git push origin staging
# Same automated sequence runs against staging infrastructure
```

### Deploy to PRODUCTION (manual gate)

```Shell
git checkout main
git merge staging
git push origin main
# CI runs automatically on main
# NO automatic deploy — must trigger manually:

# Go to: GitHub Actions → Deploy — Production (AWS) → Run workflow
# Select traffic strategy (default: Canary 10% for 5 min)
# Type: DEPLOY
# Click: Run workflow
```

***

## Stage 3 — Blue/Green Production Deployment

Production uses AWS CodeDeploy for zero-downtime Blue/Green deployment.

### Traffic shifting options (choose at deploy time):

| Strategy                          | Traffic shift         | Use when                      |
| --------------------------------- | --------------------- | ----------------------------- |
| `ECSCanary10Percent5Minutes`      | 10% for 5 min → 100%  | **Default — normal releases** |
| `ECSCanary10Percent15Minutes`     | 10% for 15 min → 100% | High-risk, more monitoring    |
| `ECSLinear10PercentEvery1Minutes` | +10% every minute     | Want gradual visibility       |
| `ECSLinear10PercentEvery3Minutes` | +10% every 3 min      | Maximum caution               |
| `ECSAllAtOnce`                    | Instant 100%          | Hotfixes only                 |

### How to roll back production instantly

```
AWS Console → CodeDeploy → Deployments → your deployment → Stop and rollback
```

Traffic returns 100% to Blue (old version) in seconds.

***

## Stage 4 — Database Migrations

All schema changes go through versioned migration files.

### Adding a new migration

```Shell
# Create a new numbered SQL file
# File: backend/migrations/versions/002_your_change.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';
```

### How migrations run

* **Locally:** `cd backend && python -m migrations.runner`
* **On CI/CD:** Runs automatically before ECS deploy in `deploy-dev.yml`
* **Idempotent:** `schema_migrations` table tracks what's been applied — never runs twice

### Seed dev/staging data

```Shell
# After terraform apply + migrations:
cd backend
DATABASE_URL="postgresql://..." APP_ENV=dev python -m migrations.seed_dev

# Creates: hr_admin, legal_user, it_engineer test users + sample queries
# NEVER runs on prod (blocked by APP_ENV check)
```

***

## Stage 5 — Cost Management

### Save data before destroying infrastructure

```PowerShell
# Windows
.\scripts\db-snapshot.ps1 -Env dev    # takes RDS snapshot (~5-10 min)
```

### Destroy infrastructure (stops all AWS charges)

```Shell
cd terraform/aws
terraform apply -destroy -var-file environments/dev.tfvars -auto-approve

# IMPORTANT: Delete IAM access keys first or destroy will fail
aws iam list-access-keys --user-name huron-dev-cicd-user
aws iam delete-access-key --user-name huron-dev-cicd-user --access-key-id <KEY_ID>
```

### Resume next session

```Shell
cd terraform/aws
terraform apply -var-file environments/dev.tfvars     # recreates everything

.\scripts\post-apply.ps1 -Env dev     # updates DEV_ALB_URL in GitHub Variables
.\scripts\setup-github-secrets.ps1 -Env dev   # new IAM key → GitHub Secrets

git push origin develop    # triggers automated deploy
```

> **NOTE:** The ALB URL changes on every `terraform apply`.
> Always run `post-apply` to update `DEV_ALB_URL` in GitHub Variables.

***

## Quick Reference — GitHub Settings URLs

| What      | URL                                                                             |
| --------- | ------------------------------------------------------------------------------- |
| Secrets   | `github.com/bolajil/Huron_GenAI_Knowledge_Assistant/settings/secrets/actions`   |
| Variables | `github.com/bolajil/Huron_GenAI_Knowledge_Assistant/settings/variables/actions` |
| Actions   | `github.com/bolajil/Huron_GenAI_Knowledge_Assistant/actions`                    |

## Quick Reference — AWS Console URLs

| What             | URL                                                          |
| ---------------- | ------------------------------------------------------------ |
| ECS Clusters     | `console.aws.amazon.com/ecs/v2/clusters`                     |
| RDS Databases    | `console.aws.amazon.com/rds/home?region=us-east-1#databases` |
| ECR Repositories | `console.aws.amazon.com/ecr/repositories`                    |
| CodeDeploy       | `console.aws.amazon.com/codesuite/codedeploy/deployments`    |
| Secrets Manager  | `console.aws.amazon.com/secretsmanager/listsecrets`          |

***

## Troubleshooting Quick Reference

| Error                             | Cause                                  | Fix                                                                                    |
| --------------------------------- | -------------------------------------- | -------------------------------------------------------------------------------------- |
| `Could not load credentials`      | GitHub Secrets not set                 | Add `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`                                      |
| `security token is invalid`       | Key ID and secret are mismatched pairs | Delete all keys, run `create-access-key` once, use both values from that single output |
| Secrets entered as `KEY = VALUE`  | Both values in one box                 | Each secret needs its own entry — name in Name field, raw value only in Value field    |
| `Connection refused` on port 5436 | Using `localhost` (IPv6) on Windows    | Change `DATABASE_URL` to use `127.0.0.1` not `localhost`                               |
| ALB 503 after deploy              | ECS containers still starting          | Wait 2-3 min for health checks                                                         |
| Terraform destroy fails: IAM user | Active access key still exists         | Delete key first: `aws iam delete-access-key ...`                                      |
| New ALB URL after terraform apply | ALB gets new DNS each time             | Run `post-apply.ps1` to update `DEV_ALB_URL` variable                                  |
| Deploy skipped / not triggered    | Workflow gated on CI                   | CI must pass first; or use `workflow_dispatch` to trigger manually                     |

