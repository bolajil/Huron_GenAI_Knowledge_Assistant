# Migration Guide — Moving Huron GenAI to Huron Infrastructure

This document covers every step to migrate the project from the personal
development machine to Huron's computer, Huron's GitHub, and Huron's AWS account.

---

## Overview of What Changes

| Item | Current (Personal) | Target (Huron) |
|------|-------------------|----------------|
| GitHub repo | `bolajil/Huron_GenAI_Knowledge_Assistant` | `HuronOrg/Huron_GenAI_Knowledge_Assistant` |
| AWS Account | Personal (137738968757) | Huron AWS account |
| AWS Region | us-east-1 | Confirm with Huron IT |
| ECR image URLs | `137738968757.dkr.ecr...` | `<huron-account-id>.dkr.ecr...` |
| API Keys | Personal OpenAI / Pinecone | Huron enterprise keys |
| Machine | Personal laptop | Huron workstation |
| Local DB | Personal Docker container | Huron Docker container |

---

## Phase 1 — Prepare on Your Current Machine (before handover)

### Step 1.1 — Collect all credentials you need to hand over

Create a secure document (NOT in git) with:

```
HURON AWS ACCOUNT ID:         __________________
HURON AWS REGION:             __________________
HURON GITHUB ORG/USERNAME:    __________________
HURON GITHUB REPO NAME:       __________________
HURON OPENAI API KEY:         __________________
HURON PINECONE API KEY:       __________________
HURON PINECONE INDEX NAME:    __________________
NEW DB PASSWORD (dev):        __________________  (generate fresh)
NEW DB PASSWORD (staging):    __________________  (generate fresh)
NEW DB PASSWORD (prod):       __________________  (generate fresh)
NEW JWT SECRET (dev):         __________________  (generate fresh)
NEW JWT SECRET (staging):     __________________  (generate fresh)
NEW JWT SECRET (prod):        __________________  (generate fresh)
NEW MCP KEY (dev):            __________________  (generate fresh)
NEW ROOT PASSWORD:            __________________  (change from HuronRoot2026!)
```

Generate secure random secrets:
```bash
# Generate JWT secrets (run 3 times for dev/staging/prod)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate MCP encryption keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate DB passwords
python -c "import secrets; print('Huron' + secrets.token_urlsafe(16) + '!')"
```

### Step 1.2 — Export the code from personal GitHub

```bash
# On your current machine — clone a clean copy with all branches
git clone --mirror https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git
cd Huron_GenAI_Knowledge_Assistant.git

# This creates a bare repo with ALL branches and history
# You will push this to Huron's GitHub in Phase 3
```

### Step 1.3 — Update all references BEFORE pushing to Huron GitHub

The following files have hardcoded personal account references that must be
updated to Huron's values. Do this on your current machine first:

**Files to update:**

1. `.github/workflows/deploy-dev.yml`
2. `.github/workflows/deploy-staging.yml`
3. `.github/workflows/deploy-prod.yml`

In all three workflow files, replace the AWS account ID and repo reference:
```yaml
# Find (personal account ID):
137738968757.dkr.ecr.us-east-1.amazonaws.com/huron-dev-backend

# Replace with (Huron account ID):
<HURON_AWS_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend
```

4. `scripts/setup-github-secrets.ps1` and `scripts/setup-github-secrets.sh`
```bash
# Find:
REPO="bolajil/Huron_GenAI_Knowledge_Assistant"
# Replace with:
REPO="HuronOrg/Huron_GenAI_Knowledge_Assistant"
```

5. `scripts/post-apply.ps1` and `scripts/post-apply.sh`
```bash
# Same REPO change as above
```

6. `terraform/aws/variables.tf` — confirm default region matches Huron's region

After making these changes:
```bash
git add .github/workflows/ scripts/
git commit -m "chore: update references for Huron infrastructure migration"
git push origin develop
git checkout main && git merge develop && git push origin main
git checkout develop
```

---

## Phase 2 — Set Up Huron's Computer

### Step 2.1 — Install prerequisites on Huron's machine

Run these on the Huron workstation:

```powershell
# 1. Git
winget install Git.Git

# 2. Node.js 20
winget install OpenJS.NodeJS.LTS

# 3. Python 3.11
winget install Python.Python.3.11

# 4. Docker Desktop
winget install Docker.DockerDesktop
# Restart after install

# 5. AWS CLI
winget install Amazon.AWSCLI
# Verify:
aws --version

# 6. Terraform
winget install Hashicorp.Terraform
# Verify:
terraform -version

# 7. GitHub CLI
winget install GitHub.cli
# Verify:
gh --version
```

### Step 2.2 — Configure AWS CLI with Huron credentials

```bash
aws configure
# AWS Access Key ID:     <Huron AWS access key>
# AWS Secret Access Key: <Huron AWS secret key>
# Default region:        <Huron AWS region>
# Default output format: json

# Verify it works:
aws sts get-caller-identity
# Should show Huron's account ID
```

### Step 2.3 — Authenticate GitHub CLI

```bash
gh auth login
# Choose: GitHub.com
# Choose: HTTPS
# Choose: Login with a web browser
# Complete browser login with Huron GitHub account
```

---

## Phase 3 — Move Code to Huron GitHub

### Step 3.1 — Create the repo in Huron's GitHub

```bash
# Create the repo (replace HuronOrg with actual org/username)
gh repo create HuronOrg/Huron_GenAI_Knowledge_Assistant \
  --private \
  --description "Huron GenAI Knowledge Assistant"
```

Or manually: GitHub → New Repository → Name: `Huron_GenAI_Knowledge_Assistant` → Private

### Step 3.2 — Push all branches and history

```bash
# From the mirror clone you made in Step 1.2:
cd Huron_GenAI_Knowledge_Assistant.git

git remote set-url origin https://github.com/HuronOrg/Huron_GenAI_Knowledge_Assistant.git
git push --mirror

# This transfers:
# - All commits and history
# - main branch
# - develop branch
# - staging branch (create if missing)
# - All tags
```

### Step 3.3 — Verify branches exist

```bash
gh repo view HuronOrg/Huron_GenAI_Knowledge_Assistant --web
# Confirm main, develop, staging branches are all present
```

### Step 3.4 — Create staging branch if missing

```bash
git clone https://github.com/HuronOrg/Huron_GenAI_Knowledge_Assistant.git
cd Huron_GenAI_Knowledge_Assistant
git checkout -b staging
git push origin staging
```

---

## Phase 4 — Create Environment Config Files

These files are gitignored and never committed — create them fresh on Huron's machine.

### Step 4.1 — Create terraform/aws/environments/dev.tfvars

```bash
# File: terraform/aws/environments/dev.tfvars
cat > terraform/aws/environments/dev.tfvars << 'EOF'
environment  = "dev"
project_name = "huron"
aws_region   = "<HURON_AWS_REGION>"

use_free_tier = true

backend_cpu            = 256
backend_memory         = 512
backend_desired_count  = 1
frontend_cpu           = 256
frontend_memory        = 512
frontend_desired_count = 1

db_username                = "huron_user"
db_password                = "<NEW_DB_PASSWORD_DEV>"
db_name                    = "huron_dev"
db_allocated_storage       = 20
db_instance_class          = "db.t3.micro"
db_multi_az                = false
db_backup_retention_period = 0
db_skip_final_snapshot     = true
db_storage_encrypted       = false
db_deletion_protection     = false

openai_api_key     = "<HURON_OPENAI_API_KEY>"
pinecone_api_key   = "<HURON_PINECONE_API_KEY>"
pinecone_index     = "<HURON_PINECONE_INDEX>"
jwt_secret         = "<NEW_JWT_SECRET_DEV>"
mcp_encryption_key = "<NEW_MCP_KEY_DEV>"

certificate_arn       = ""
enable_cicd           = false
enable_blue_green     = false
github_repo           = "HuronOrg/Huron_GenAI_Knowledge_Assistant"
github_branch         = "develop"
github_connection_arn = ""
EOF
```

Repeat for `staging.tfvars` and `prod.tfvars` with appropriate values
(staging: `db.t3.small`, `use_free_tier = false`; prod: `db.t3.medium`,
`enable_blue_green = true`, `db_deletion_protection = true`).

### Step 4.2 — Create backend/.env (local development)

```bash
cat > backend/.env << 'EOF'
# Never commit this file
DATABASE_URL=postgresql://huron_user:<NEW_DB_PASSWORD_DEV>@127.0.0.1:5436/huron
OPENAI_API_KEY=<HURON_OPENAI_API_KEY>
PINECONE_API_KEY=<HURON_PINECONE_API_KEY>
PINECONE_INDEX=<HURON_PINECONE_INDEX>
JWT_SECRET_KEY=<NEW_JWT_SECRET_DEV>
MCP_ENCRYPTION_KEY=<NEW_MCP_KEY_DEV>
SQLITE_DB_PATH=./data/huron.db
VECTOR_BACKEND=pinecone
REDIS_URL=
APP_ENV=dev
EOF
```

### Step 4.3 — Create frontend/.env.local (local development)

```bash
cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://127.0.0.1:8004
EOF
```

---

## Phase 5 — Update Hardcoded AWS Account ID in Workflows

The workflow files currently have the personal AWS account ID `137738968757`.
Update them to Huron's account ID:

```powershell
# Find Huron's account ID first
aws sts get-caller-identity --query Account --output text
# Returns: <HURON_ACCOUNT_ID>

# Replace in all workflow files (PowerShell)
$huronAccountId = "<HURON_ACCOUNT_ID>"
$region = "<HURON_REGION>"

$files = @(
    ".github/workflows/deploy-dev.yml",
    ".github/workflows/deploy-staging.yml",
    ".github/workflows/deploy-prod.yml"
)

foreach ($file in $files) {
    (Get-Content $file) `
        -replace "137738968757", $huronAccountId `
        -replace "us-east-1", $region |
    Set-Content $file
}

git add .github/workflows/
git commit -m "chore: update AWS account ID and region to Huron infrastructure"
git push origin develop
git checkout main; git merge develop; git push origin main; git checkout develop
```

---

## Phase 6 — Deploy Infrastructure on Huron AWS

### Step 6.1 — Start local Docker database

```powershell
# Create the local postgres container for development
docker run -d `
  --name huron-postgres `
  -e POSTGRES_DB=huron `
  -e POSTGRES_USER=huron_user `
  -e POSTGRES_PASSWORD=<NEW_DB_PASSWORD_DEV> `
  -p 5436:5432 `
  postgres:16-alpine

# Verify it runs
docker ps --filter "name=huron-postgres"
```

### Step 6.2 — Run Terraform to create AWS infrastructure

```bash
cd terraform/aws
terraform init

# Deploy DEV first
terraform apply -var-file environments/dev.tfvars
# Type 'yes' when prompted
# Takes 10-15 minutes

# Note the outputs — you will need them:
terraform output alb_dns_name      # → DEV_ALB_URL
terraform output ecr_backend_url   # → DEV_ECR_BACKEND
terraform output ecr_frontend_url  # → DEV_ECR_FRONTEND
terraform output ecs_cluster_name  # → DEV_ECS_CLUSTER
terraform output db_endpoint       # → for DEV_DATABASE_URL secret
```

### Step 6.3 — Set GitHub Secrets

```powershell
# Creates fresh IAM key and sets secrets in Huron GitHub repo
.\scripts\setup-github-secrets.ps1 -Env dev
```

Then manually add the database URL secret:
```
GitHub → Settings → Secrets → Actions → New secret:
  Name:  DEV_DATABASE_URL
  Value: postgresql://huron_user:<password>@<db-endpoint>:5432/huron_dev
```

### Step 6.4 — Set GitHub Variables

```powershell
# Reads terraform outputs and sets variables in Huron GitHub repo
.\scripts\post-apply.ps1 -Env dev
```

### Step 6.5 — Bootstrap first Docker images

```bash
# Authenticate to Huron's ECR
aws ecr get-login-password --region <HURON_REGION> | \
  docker login --username AWS --password-stdin \
  <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com

# Push backend
docker build -f backend/Dockerfile.production \
  -t <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend:latest .
docker push <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend:latest

# Push frontend
docker build -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL=http://<DEV_ALB_URL> \
  -t <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-frontend:latest \
  ./frontend
docker push <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-frontend:latest
```

---

## Phase 7 — First Deploy and Verify

### Step 7.1 — Trigger first automated deploy

```bash
git push origin develop
# GitHub Actions will:
# 1. Run CI (tests + lint + integration + docker build)
# 2. Run DB migrations
# 3. Build + push images to Huron ECR
# 4. Deploy to Huron ECS
# 5. Health check
```

### Step 7.2 — Verify the deployment

```bash
# Check backend health
curl http://<DEV_ALB_URL>/health

# Expected:
# {"status":"healthy","db":{"status":"ok","backend":"postgresql"},...}

# Open frontend in browser
# http://<DEV_ALB_URL>
# Login: root / <NEW_ROOT_PASSWORD>
```

### Step 7.3 — Change root password

Once logged in, immediately change the root password from the default.
Or via the backend:
```bash
# Connect to the RDS database directly
psql postgresql://huron_user:<password>@<db-endpoint>:5432/huron_dev

# Update root password (use bcrypt hash)
python -c "import bcrypt; print(bcrypt.hashpw(b'<NEW_PASSWORD>', bcrypt.gensalt()).decode())"
# Then in psql:
UPDATE users SET password_hash='<hash>' WHERE username='root';
```

---

## Phase 8 — Clean Up Personal Resources

Once Huron infrastructure is verified working:

### Step 8.1 — Archive personal GitHub repo
```bash
# In personal GitHub: Settings → Archive repository
# Or: make it private if you want to keep it as a backup
```

### Step 8.2 — Destroy personal AWS infrastructure
```bash
# ONLY after confirming Huron's deployment is working
cd terraform/aws

# Delete IAM key first to avoid destroy error
aws iam list-access-keys --user-name huron-dev-cicd-user
aws iam delete-access-key --user-name huron-dev-cicd-user --access-key-id <KEY_ID>

# Destroy
terraform apply -destroy -var-file environments/dev.tfvars -auto-approve
```

### Step 8.3 — Remove personal credentials from Huron machine
```bash
# Remove personal AWS profile if it was configured
aws configure --profile personal
# Set all values to 'none' or delete ~/.aws/credentials entry
```

---

## Migration Checklist

Use this to track progress:

### Preparation (on personal machine)
- [ ] Collected all Huron credentials and generated new secrets
- [ ] Updated REPO references in scripts to Huron GitHub
- [ ] Pushed final changes to personal GitHub
- [ ] Created mirror clone of the repo

### Huron Machine Setup
- [ ] Git installed and configured
- [ ] Node.js 20 installed
- [ ] Python 3.11 installed
- [ ] Docker Desktop installed and running
- [ ] AWS CLI installed and configured with Huron credentials
- [ ] Terraform installed
- [ ] GitHub CLI installed and logged into Huron GitHub

### Code Migration
- [ ] New repo created in Huron GitHub
- [ ] All branches pushed (main, develop, staging)
- [ ] AWS account ID updated in all workflow files
- [ ] REPO references updated in scripts

### Environment Files (created on Huron machine, never committed)
- [ ] `terraform/aws/environments/dev.tfvars` created with Huron credentials
- [ ] `terraform/aws/environments/staging.tfvars` created
- [ ] `terraform/aws/environments/prod.tfvars` created
- [ ] `backend/.env` created with Huron API keys
- [ ] `frontend/.env.local` created

### Infrastructure
- [ ] Local huron-postgres Docker container running
- [ ] `terraform apply` completed for dev
- [ ] GitHub Secrets set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DEV_DATABASE_URL)
- [ ] GitHub Variables set (DEV_ALB_URL, DEV_ECR_BACKEND, DEV_ECR_FRONTEND, DEV_ECS_CLUSTER)
- [ ] First Docker images bootstrapped to ECR

### Verification
- [ ] CI pipeline passes (all 4 jobs green)
- [ ] Deploy pipeline completes successfully
- [ ] Health check returns `{"status":"healthy"}`
- [ ] Can log in to the app at the ALB URL
- [ ] Departments page shows 8 departments
- [ ] Dashboard shows real data

### Cleanup
- [ ] Personal GitHub repo archived
- [ ] Personal AWS infrastructure destroyed
- [ ] Personal credentials removed from Huron machine

---

## Summary of Files That Change Per Environment

| File | What changes | When |
|------|-------------|------|
| `terraform/aws/environments/*.tfvars` | All Huron-specific values | Created fresh on Huron machine |
| `backend/.env` | API keys, DB URL, secrets | Created fresh on Huron machine |
| `frontend/.env.local` | Backend API URL | Created fresh on Huron machine |
| `.github/workflows/*.yml` | AWS account ID, region | Updated in Step 1.3 + Phase 5 |
| `scripts/setup-github-secrets.*` | REPO reference | Updated in Step 1.3 |
| `scripts/post-apply.*` | REPO reference | Updated in Step 1.3 |
