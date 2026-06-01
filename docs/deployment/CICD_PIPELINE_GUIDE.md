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
                  │  CI must PASS first
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
Where you write and test code:
- Full project at `VoultMIND_lanre/GenAI Knowledge Assistant Huron/`
- Local backend on port 8001, local frontend on port 3000
- Git tracks every change

### 2. GitHub
The central hub:
- Stores all code versions
- Runs automated CI checks on every push
- Holds **Secrets** (AWS keys) and **Variables** (ALB URLs) for workflows
- Gates deployments — deploy only runs when CI passes

### 3. AWS (Amazon Web Services)
Where the app runs in the cloud. Three completely separate environments:

| Environment | Branch  | Instance Size | Purpose |
|-------------|---------|---------------|---------|
| **dev**     | develop | Free tier     | Safe sandbox for new features |
| **staging** | staging | Moderate      | Mirror of prod — catch bugs before users |
| **prod**    | main    | Full scale    | Real users, real data |

---

## Part 2: The Git Branch Strategy

```
main ──────────────────────────────────────► (production — never push directly)
  ▲
  │ merge when staging is verified
staging ───────────────────────────────────► (staging AWS)
  ▲
  │ merge when dev is stable
develop ───────────────────────────────────► (dev AWS)
  ▲
  │ merge feature branches
feature/my-feature ────────────────────────► (your daily work)
```

**Rule:** Code always flows feature → develop → staging → main. Never skip a level.

---

## Part 3: The Workflows Explained

### CI (`.github/workflows/ci.yml`)
Triggers on every push to any branch.

```
Step 1 (parallel): Backend Unit Tests + Frontend TypeScript & Lint
  Backend:  pip install requirements + pytest → pytest tests/unit/
  Frontend: npm ci → tsc --noEmit → next lint

Step 2 (after Step 1 passes): Backend Integration Tests
  Spins up PostgreSQL + Redis containers
  Starts backend on port 8004 (BACKEND_URL env var)
  Runs: pytest tests/integration/

Step 3 (after Step 1 passes): Docker Build Smoke Test
  Builds backend + frontend Docker images
  Does NOT push — just verifies Dockerfiles are valid
```

### Deploy Dev (`.github/workflows/deploy-dev.yml`)
Triggers only when CI passes on the `develop` branch.

```
Step 1 (parallel): Build & Push Backend + Build & Push Frontend
  - Authenticates to AWS using GitHub Secrets
  - Logs into ECR (AWS private Docker registry)
  - docker build → docker push to ECR with commit SHA tag

Step 2 (after both builds): Deploy to ECS Dev
  - aws ecs update-service --force-new-deployment
  - Waits for containers to become healthy (5-10 min)
  - Health check: curl ALB_URL/health → must return {"status":"healthy"}
```

### Deploy Staging / Prod
Same structure as Deploy Dev, but triggered on `staging`/`main` branches.

---

## Part 4: One-Time Setup Per Environment

### Step 1 — Create AWS Infrastructure
```bash
cd terraform/aws
terraform init
terraform apply -var-file environments/dev.tfvars
# Creates: VPC, ECS cluster, RDS, ECR repos, ALB, IAM user, Secrets Manager
```

### Step 2 — Set GitHub Secrets (AWS credentials)

**Windows (PowerShell) — requires `gh` CLI:**
```powershell
.\scripts\setup-github-secrets.ps1 -Env dev
```

**Linux/Mac (Bash) — requires `gh` CLI:**
```bash
./scripts/setup-github-secrets.sh dev
```

**Manual (no `gh` CLI needed):**
```bash
# 1. Create fresh IAM access key (deletes old ones first if needed)
aws iam list-access-keys --user-name huron-dev-cicd-user   # check existing
aws iam delete-access-key --user-name huron-dev-cicd-user --access-key-id <OLD_ID>
aws iam create-access-key --user-name huron-dev-cicd-user
# Copy BOTH AccessKeyId and SecretAccessKey from the output

# 2. Go to: github.com/<repo>/settings/secrets/actions
# Add TWO separate secrets — one per entry, raw value only:
#   AWS_ACCESS_KEY_ID     → just the key ID (e.g. AKIASAEPB3223OURDIVY)
#   AWS_SECRET_ACCESS_KEY → just the secret (e.g. ClLwY2bOpwg...)
```

> **IMPORTANT:** The key ID and secret MUST come from the same `create-access-key`
> call. Mixing an ID from one call with a secret from another = "invalid security token".

### Step 3 — Set GitHub Variables (ALB URL etc.)

**Windows (PowerShell) — requires `gh` CLI:**
```powershell
.\scripts\post-apply.ps1 -Env dev
```

**Linux/Mac (Bash) — requires `gh` CLI:**
```bash
./scripts/post-apply.sh dev
```

**Manual (no `gh` CLI needed):**
```bash
# Get values from terraform outputs
cd terraform/aws
terraform output alb_dns_name
terraform output ecr_backend_url
terraform output ecr_frontend_url
terraform output ecs_cluster_name

# Go to: github.com/<repo>/settings/variables/actions
# Add these variables (one per entry):
#   DEV_ALB_URL      → http://huron-dev-alb-XXXX.us-east-1.elb.amazonaws.com
#   DEV_ECR_BACKEND  → 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend
#   DEV_ECR_FRONTEND → 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend
#   DEV_ECS_CLUSTER  → huron-dev-cluster
```

> **NOTE:** Secrets and Variables are DIFFERENT tabs in GitHub Settings.
> Secrets = sensitive (encrypted, never visible). Variables = non-sensitive (visible in logs).

### Step 4 — First Image Bootstrap
ECR repos start empty. ECS can't start containers without images.
After `terraform apply`, push the first images manually once:

```bash
# Authenticate
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
  ./frontend
docker push 137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-frontend:latest
```

After this bootstrap, all future deployments are automatic via GitHub Actions.

---

## Part 5: Daily Development Workflow

```bash
# 1. Start from develop, create a feature branch
git checkout develop && git pull origin develop
git checkout -b feature/my-feature

# 2. Write code, test locally
cd backend && python main.py        # port 8001
cd frontend && npm run dev          # port 3000

# 3. Commit and push
git add .
git commit -m "feat: my new feature"
git push origin feature/my-feature
# CI runs on your branch — check for green before merging

# 4. Merge to develop → deploys to DEV
git checkout develop
git merge feature/my-feature
git push origin develop
# CI → passes → Deploy Dev runs → app live at ALB URL

# 5. Promote to STAGING when dev is stable
git checkout staging
git merge develop
git push origin staging
# CI → passes → Deploy Staging runs

# 6. Release to PRODUCTION when staging is verified
git checkout main
git merge staging
git push origin main
# CI → passes → Deploy Prod runs (requires manual approval gate)
```

---

## Part 6: Cost Management — Start/Stop Infrastructure

### Destroy (stop all AWS charges)
```bash
cd terraform/aws
terraform destroy -var-file environments/dev.tfvars
# Type 'yes' when prompted
# Destroys: ECS tasks, RDS, ALB, ECR, VPC — stops all charges
```

### Re-create (resume work next session)
```bash
cd terraform/aws
terraform apply -var-file environments/dev.tfvars
# Re-creates everything from scratch in ~10 minutes

# Then run post-apply to update GitHub Variables with new ALB URL
.\scripts\post-apply.ps1 -Env dev   # Windows
./scripts/post-apply.sh dev          # Linux/Mac

# The first deploy after re-creation needs the bootstrap push OR
# just push any commit to develop — GitHub Actions will rebuild and push images
```

> **NOTE:** The ALB URL changes every time you run `terraform apply`.
> Always run `post-apply` after to update the `DEV_ALB_URL` GitHub Variable.

---

## Part 7: Secrets vs Variables — What Goes Where

| Type | Tab in GitHub | Visible in logs | Examples |
|------|--------------|-----------------|---------|
| **Secret** | Secrets | Never (shown as `***`) | AWS keys, API keys, passwords |
| **Variable** | Variables | Yes | ALB URL, ECR URL, cluster name |

**Current secrets required:**
- `AWS_ACCESS_KEY_ID` — IAM key to deploy to AWS
- `AWS_SECRET_ACCESS_KEY` — must match the key ID exactly

**Current variables required:**
- `DEV_ALB_URL` — dev load balancer URL (changes on each terraform apply)
- `STAGING_ALB_URL` — (set after staging terraform apply)
- `PROD_URL` — (set after prod terraform apply)

---

## Part 8: Troubleshooting Reference

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Deploy fails in 10-15s: "Could not load credentials" | Secrets not set in GitHub | Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to GitHub Secrets |
| Deploy fails: "security token is invalid" | Key ID and secret are mismatched pairs | Delete all keys, run `create-access-key` once, use both values from that single output |
| Deploy fails: "security token is invalid" (again) | Entered value as `KEY = VALUE` in one box | Each secret needs its own entry — name in the Name field, raw value only in the Value field |
| CI fails: `pytest: command not found` | pytest missing from install step | `pip install -r requirements_production.txt pytest` |
| CI fails: `npm ci` error | `package-lock.json` gitignored | Add `!frontend/package-lock.json` to `.gitignore` and commit the file |
| CI fails: `next lint` hangs with prompt | No `.eslintrc.json` | Create `frontend/.eslintrc.json` with `{"extends": "next/core-web-vitals"}` |
| CI fails: React Hook called conditionally | `useEffect` after early `return` | Move all hooks to top of component, before any `return` |
| Integration tests fail: Connection refused | `BASE_URL` hardcoded to wrong port | Use `os.getenv("BACKEND_URL", "http://localhost:8004")` |
| Deploy and CI run simultaneously | `on: push` trigger on deploy workflow | Use `on: workflow_run` so deploy only starts after CI passes |
| ALB returns 503 | ECS containers still starting | Wait 2-3 min — containers need time to pass health checks |
| Terraform destroy fails: ECR not empty | Images in ECR repos | `force_delete = true` on ECR resource in `main.tf` |
| Terraform destroy fails: ALB deletion protection | Protection enabled | `enable_deletion_protection = false` in `main.tf` |
| New ALB URL after terraform apply | ALB recreated with new DNS | Run `post-apply.sh/ps1` to update `DEV_ALB_URL` GitHub Variable |

---

## Part 9: File Map

```
.github/
  workflows/
    ci.yml                ← Tests every push (all branches)
    deploy-dev.yml        ← Deploys to DEV after CI passes on develop
    deploy-staging.yml    ← Deploys to STAGING after CI passes on staging
    deploy-prod.yml       ← Deploys to PROD after CI passes on main

terraform/
  aws/
    main.tf               ← All AWS resources
    variables.tf          ← Input variable declarations
    outputs.tf            ← Outputs (ALB URL, ECR URLs)
    environments/
      dev.tfvars          ← Dev config — NEVER commit (in .gitignore)
      staging.tfvars      ← Staging config — NEVER commit
      prod.tfvars         ← Prod config — NEVER commit

scripts/
  setup-github-secrets.sh    ← Bash: create IAM key + set GitHub Secrets
  setup-github-secrets.ps1   ← PowerShell: same (Windows)
  post-apply.sh              ← Bash: sync terraform outputs → GitHub Variables
  post-apply.ps1             ← PowerShell: same (Windows)

tests/
  unit/           ← Fast tests, SQLite, no server needed (CI Step 1)
  integration/    ← Tests against running backend + real PostgreSQL (CI Step 3)

frontend/
  .eslintrc.json        ← ESLint config (required for next lint in CI)
  package-lock.json     ← Committed so CI can run npm ci reproducibly
```
