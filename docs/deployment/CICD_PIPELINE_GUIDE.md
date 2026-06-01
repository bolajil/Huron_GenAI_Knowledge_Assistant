# Huron GenAI — CI/CD Pipeline & Deployment Guide

## The Big Picture

```
Your Laptop (local)
      │
      │  git push
      ▼
GitHub (bolajil/Huron_GenAI_Knowledge_Assistant)
      │
      │  GitHub Actions triggers automatically
      ▼
┌─────────────────────────────────────────────────┐
│  CI Workflow (runs on EVERY push, every branch) │
│  1. Backend Unit Tests                          │
│  2. Frontend TypeScript + Lint                  │
│  3. Backend Integration Tests                   │
│  4. Docker Build Smoke Test                     │
└─────────────────┬───────────────────────────────┘
                  │  CI must pass first
                  ▼
     ┌────────────┬────────────┐
     │            │            │
  develop      staging       main
  branch       branch        branch
     │            │            │
     ▼            ▼            ▼
  AWS DEV     AWS STAGING  AWS PROD
  (free tier) (moderate)   (full scale)
```

---

## Part 1: How the Three Pieces Connect

### 1. Your Local Machine
This is where you write code. You have:
- The full project at `VoultMIND_lanre/GenAI Knowledge Assistant Huron/`
- A local backend running on port 8001 (for testing)
- A local frontend running on port 3000 (for testing)
- Git installed — tracks every change you make

### 2. GitHub
GitHub is the central hub. It:
- Stores every version of your code (git history)
- Runs automated checks every time you push (GitHub Actions)
- Controls who can deploy what and when
- Holds secrets and variables that workflows use (AWS keys, ALB URLs, etc.)

### 3. AWS (Amazon Web Services)
AWS is where the app actually runs in the cloud. You have three separate environments:

| Environment | Branch  | AWS Profile  | Purpose |
|-------------|---------|--------------|---------|
| **dev**     | develop | Free tier    | Your sandbox — test features safely |
| **staging** | staging | Moderate     | Mirrors production — catch bugs before users see them |
| **prod**    | main    | Full scale   | Real users, real data |

---

## Part 2: The Git Branch Strategy

```
main ──────────────────────────────────────────────► (production)
  ▲                                                    never push directly
  │ merge when staging looks good
  │
staging ──────────────────────────────────────────► (staging AWS)
  ▲                                                    never push directly
  │ merge when dev looks good
  │
develop ──────────────────────────────────────────► (dev AWS)
  ▲
  │ merge feature branches
  │
feature/my-new-thing ─────────────────────────────► (your daily work)
```

**Rule:** Code always flows LEFT to RIGHT — feature → develop → staging → main.
You never skip a level (never push directly to main).

---

## Part 3: The Two Workflows

### Workflow 1: CI (`.github/workflows/ci.yml`)

**Triggers:** Every push to any branch, every pull request.

**What it does — in order:**

```
Step 1: Backend Unit Tests
  - Sets up Python 3.11
  - pip install -r requirements_production.txt pytest
  - Runs: pytest tests/unit/
  - Uses SQLite (no real database needed)
  - Env: DATABASE_URL="", SQLITE_DB_PATH=/tmp/test.db

Step 2: Frontend TypeScript + Lint  (runs in parallel with Step 1)
  - Sets up Node.js 20
  - npm ci  (installs exact versions from package-lock.json)
  - Runs: tsc --noEmit  (checks types, no output files)
  - Runs: next lint      (checks code quality rules)

Step 3: Backend Integration Tests  (only if Steps 1 AND 2 pass)
  - Spins up a real PostgreSQL container
  - Spins up a real Redis container
  - Starts the actual backend server on port 8004
  - Runs: pytest tests/integration/

Step 4: Docker Build Smoke Test  (only if Steps 1 AND 2 pass)
  - Builds the backend Docker image (does NOT push to ECR)
  - Builds the frontend Docker image (does NOT push to ECR)
  - Just verifies the Dockerfiles are valid and build successfully
```

**Why this order matters:**
Unit tests and frontend checks are fast (< 3 min) and catch 90% of bugs.
Integration tests are slower (need a database) so they run after.
Docker build is slowest so it runs last.

If ANY step fails, the deployment workflows do NOT run.

### Workflow 2: Deploy (`.github/workflows/deploy-dev.yml`)

**Triggers:** Only when you push to the `develop` branch AND CI passes.

**What it does:**

```
Step 1: Configure AWS credentials
  - Uses secrets.AWS_ACCESS_KEY_ID and secrets.AWS_SECRET_ACCESS_KEY
  - These are the GitHub Secrets you set up with setup-github-secrets.sh

Step 2: Log in to ECR (Elastic Container Registry)
  - ECR is AWS's private Docker image storage
  - Like Docker Hub, but inside your AWS account

Step 3: Build & Push Backend Image
  - docker build -f backend/Dockerfile.production
  - docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend:latest

Step 4: Build & Push Frontend Image
  - docker build -f frontend/Dockerfile.production
  - docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend:latest

Step 5: Deploy to ECS (Elastic Container Service)
  - aws ecs update-service --force-new-deployment
  - ECS pulls the new images from ECR and replaces running containers
  - Old containers shut down, new containers start up
  - ALB (load balancer) routes traffic to new containers once healthy

Step 6: Health Check
  - curl http://${{ vars.DEV_ALB_URL }}/health
  - Waits until the new backend responds with {"status": "healthy"}
```

---

## Part 4: The Infrastructure (What Terraform Built)

Terraform created all the AWS resources. You don't manage these manually:

```
Internet
    │
    ▼
ALB (Application Load Balancer)
    │  huron-dev-alb-XXXXXXX.us-east-1.elb.amazonaws.com
    │
    ├──/api/* ──► ECS Task: Backend (FastAPI, port 8000)
    │                │
    │                ├── RDS PostgreSQL (huron_dev database)
    │                ├── Secrets Manager (API keys)
    │                └── Pinecone (external vector DB)
    │
    └──/* ──────► ECS Task: Frontend (Next.js, port 3000)
```

**Key AWS services:**
- **ECS (Elastic Container Service)** — runs your Docker containers
- **ECR (Elastic Container Registry)** — stores your Docker images
- **RDS** — managed PostgreSQL database
- **ALB** — load balancer, the public URL
- **Secrets Manager** — stores API keys securely (not in code)
- **VPC** — private network, containers can't be accessed directly

---

## Part 5: How Variables and Secrets Work

### GitHub Secrets (sensitive — encrypted, never visible)
Set via: `./scripts/setup-github-secrets.sh dev`

| Secret | What it is |
|--------|-----------|
| `AWS_ACCESS_KEY_ID` | IAM user key to deploy to AWS |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret |

### GitHub Variables (non-sensitive — visible in logs)
Set via: `./scripts/post-apply.sh dev` after each `terraform apply`

| Variable | What it is | Example |
|----------|-----------|---------|
| `DEV_ALB_URL` | Dev load balancer URL | `huron-dev-alb-XXXX.us-east-1.elb.amazonaws.com` |
| `DEV_ECR_BACKEND` | Dev backend image URL | `137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend` |
| `DEV_ECR_FRONTEND` | Dev frontend image URL | `137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend` |
| `DEV_ECS_CLUSTER` | Dev ECS cluster name | `huron-dev-cluster` |
| `STAGING_ALB_URL` | Staging load balancer URL | (set after staging terraform apply) |
| `PROD_URL` | Production URL | (set after prod terraform apply) |

### Terraform tfvars (local only — NEVER committed to git)
Files: `terraform/aws/environments/dev.tfvars`, `staging.tfvars`, `prod.tfvars`

These contain the real database passwords, API keys, and config for each environment.
They are in `.gitignore` — they never go to GitHub.
Terraform reads them when you run `terraform apply`.
The values get stored in AWS Secrets Manager, not in the deployed code.

---

## Part 6: The Daily Workflow

### Working on a new feature

```bash
# 1. Create a feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# 2. Write code, run locally to test
cd backend && python main.py          # backend on port 8001
cd frontend && npm run dev            # frontend on port 3000

# 3. Commit your work
git add src/...
git commit -m "feat: add my new feature"

# 4. Push to GitHub
git push origin feature/my-new-feature

# CI runs automatically — checks your code
# If CI passes, you can open a Pull Request to develop
```

### Deploying to DEV

```bash
# Merge your feature into develop
git checkout develop
git merge feature/my-new-feature
git push origin develop

# GitHub Actions automatically:
# 1. Runs CI (tests + lint + docker build)
# 2. If CI passes: builds Docker images, pushes to ECR, deploys to ECS
# 3. Health checks the ALB URL

# Your change is live at:
# http://huron-dev-alb-XXXX.us-east-1.elb.amazonaws.com
```

### Promoting to STAGING

```bash
# When dev is stable and you're ready to test in staging
git checkout staging
git merge develop
git push origin staging

# GitHub Actions (deploy-staging.yml) automatically deploys to staging AWS
# staging has its own RDS, ECR, ECS, ALB — completely separate from dev
```

### Releasing to PRODUCTION

```bash
# When staging is verified and approved
git checkout main
git merge staging
git push origin main

# GitHub Actions (deploy-prod.yml) automatically deploys to production
# Has environment protection gate — requires manual approval in GitHub UI
```

---

## Part 7: First-Time Setup Steps (One-time per environment)

### Step 1: Terraform — Create AWS Infrastructure
```bash
cd terraform/aws
terraform init
terraform apply -var-file=environments/dev.tfvars
# Creates: VPC, ECS, RDS, ECR, ALB, IAM, Secrets Manager
```

### Step 2: IAM + GitHub Secrets
```bash
./scripts/setup-github-secrets.sh dev
# Creates IAM access key for CI/CD user
# Sets AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in GitHub
```

### Step 3: GitHub Variables
```bash
./scripts/post-apply.sh dev
# Reads terraform outputs (ALB URL, ECR URLs, cluster name)
# Sets DEV_ALB_URL, DEV_ECR_BACKEND, etc. in GitHub Variables
```

### Step 4: First Image Push (bootstrap)
```bash
# Terraform creates empty ECR repos — you need to push an initial image
# before ECS can start containers
aws ecr get-login-password --region us-east-1 | docker login ...
docker build -f backend/Dockerfile.production -t huron-dev-backend .
docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend:latest
# Repeat for frontend
```

### Step 5: Every deploy after that
```bash
# Just push code to develop — GitHub Actions handles everything
git push origin develop
```

---

## Part 8: Troubleshooting Common Problems

| Problem | Cause | Fix |
|---------|-------|-----|
| CI fails: `pytest: command not found` | pytest not installed | `pip install -r requirements_production.txt pytest` in ci.yml |
| CI fails: `npm ci` error | package-lock.json not in git | Add `!frontend/package-lock.json` to .gitignore and commit it |
| CI fails: `next lint` hangs | No .eslintrc.json exists | Create `frontend/.eslintrc.json` |
| Deploy fails: `CannotPullContainerError` | Image not in ECR | Push image manually (bootstrap step) or let CI push it |
| Deploy fails: ECS circuit breaker | Previous deployment failed | `aws ecs update-service --force-new-deployment` |
| ALB returns 503 | ECS containers still starting | Wait 2-3 minutes for health checks to pass |
| Terraform destroy fails: ECR not empty | Images in ECR | Add `force_delete = true` to ECR resource in main.tf |
| Terraform destroy fails: ALB protection | Deletion protection on | Set `enable_deletion_protection = false` in main.tf |
| Secrets Manager "scheduled for deletion" | Previous secret pending delete | Add `recovery_window_in_days = 0` in main.tf |

---

## Part 9: File Map — What Does What

```
.github/
  workflows/
    ci.yml              ← Runs tests + lint on EVERY push
    deploy-dev.yml      ← Deploys to AWS DEV when develop branch is pushed
    deploy-staging.yml  ← Deploys to AWS STAGING when staging branch is pushed
    deploy-prod.yml     ← Deploys to AWS PROD when main branch is pushed

terraform/
  aws/
    main.tf             ← All AWS resources (ECS, RDS, ECR, ALB, VPC)
    variables.tf        ← Variable declarations (what inputs the config accepts)
    outputs.tf          ← Outputs (ALB URL, ECR URLs) after terraform apply
    environments/
      dev.tfvars         ← Dev config (free tier, dev API keys) — NEVER commit
      staging.tfvars     ← Staging config — NEVER commit
      prod.tfvars        ← Prod config — NEVER commit

scripts/
  setup-github-secrets.sh   ← Run once: creates IAM key, sets GitHub secrets
  post-apply.sh             ← Run after each terraform apply: syncs URLs to GitHub

tests/
  unit/           ← Fast tests, no database (runs in CI Step 1)
  integration/    ← Tests with real PostgreSQL (runs in CI Step 3)

frontend/
  .eslintrc.json          ← ESLint rules (next/core-web-vitals)
  package-lock.json       ← Exact dependency versions (committed so CI is reproducible)
```
