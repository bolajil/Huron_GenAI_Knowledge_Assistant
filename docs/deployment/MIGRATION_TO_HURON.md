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

### Step 3.5 — Set up branch protection rules

```bash
# Protect main branch — require PR + CI passing before merge
gh api repos/HuronOrg/Huron_GenAI_Knowledge_Assistant/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci / test","ci / lint"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null

# Protect staging branch
gh api repos/HuronOrg/Huron_GenAI_Knowledge_Assistant/branches/staging/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci / test","ci / lint"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

### Step 3.6 — Day-to-day git push workflow

This is the standard process for pushing changes and triggering deployments.

#### Pushing a feature (dev environment)
```bash
# Start from develop — always branch off the latest dev code
git checkout develop

# Create a new branch just for this feature (keeps develop clean while you work)
git checkout -b feature/my-feature

# Stage all changed files for commit
git add .

# Save the snapshot with a descriptive message ("feat:" = new feature)
git commit -m "feat: describe your change"

# Upload your branch to GitHub — this triggers CI (tests + lint + docker build)
# Does NOT deploy anything yet — just validates the code is healthy
git push origin feature/my-feature

# Switch back to develop so you can merge your finished feature into it
git checkout develop

# Bring your feature's commits into develop
git merge feature/my-feature

# Push develop to GitHub — this triggers Deploy 1 — Dev (AWS)
# Your changes will be live on the dev environment in ~5 minutes
git push origin develop

# Delete the feature branch locally — it's been merged, no longer needed
# (lowercase -d is safe: refuses to delete if branch hasn't been merged)
git branch -d feature/my-feature

# Delete the feature branch on GitHub — keeps the repo tidy
git push origin --delete feature/my-feature
```

#### Promoting dev → staging
```bash
# Switch to the staging branch
git checkout staging

# Pull all the verified dev changes into staging
git merge develop

# Push staging to GitHub — triggers Deploy 2 — Staging (AWS) automatically
# Use this when dev has been tested and is ready for stakeholder/QA review
git push origin staging
```

#### Promoting staging → production
```bash
# Switch to the main branch (represents what is live in production)
git checkout main

# Pull all the staging-verified changes into main
git merge staging

# Push main to GitHub — triggers Deploy 3 — Production (AWS)
# ⚠️  This goes LIVE to real users — only do this after staging sign-off
# A manual approval gate will pause the workflow before deploying
git push origin main
```

#### Keeping all branches in sync after a hotfix on main
```bash
# Start on main and apply your emergency fix there first
git checkout main
# ... make fix, git add ., git commit, git push origin main ...

# Copy the fix down to staging so it doesn't get lost on next promotion
git checkout staging && git merge main && git push origin staging

# Copy the fix down to develop so future features are built on top of it
git checkout develop && git merge main && git push origin develop

# Return to main — back to normal development
git checkout main
```

#### Check CI status before merging
```bash
# See the last 5 CI runs and whether they passed or failed
gh run list --workflow=ci.yml --limit 5

# Stream the live logs of the currently running CI job
gh run watch
```

> **Branch → Environment mapping:**
> | Branch | Environment | Workflow triggered |
> |--------|-------------|-------------------|
> | `feature/*`, `fix/*` | — (CI only) | CI |
> | `develop` | Dev | Deploy 1 — Dev (AWS) |
> | `staging` | Staging | Deploy 2 — Staging (AWS) |
> | `main` | Production | Deploy 3 — Production (AWS) |

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

### Step 4.1b — Create terraform/aws/environments/staging.tfvars

```bash
cat > terraform/aws/environments/staging.tfvars << 'EOF'
environment  = "staging"
project_name = "huron"
aws_region   = "<HURON_AWS_REGION>"

use_free_tier = false

backend_cpu            = 512
backend_memory         = 1024
backend_desired_count  = 2
frontend_cpu           = 256
frontend_memory        = 512
frontend_desired_count = 1

db_username                = "huron_user"
db_password                = "<NEW_DB_PASSWORD_STAGING>"
db_name                    = "huron_staging"
db_allocated_storage       = 20
db_instance_class          = "db.t3.small"
db_multi_az                = false
db_backup_retention_period = 3
db_skip_final_snapshot     = true
db_storage_encrypted       = true
db_deletion_protection     = false

openai_api_key     = "<HURON_OPENAI_API_KEY>"
pinecone_api_key   = "<HURON_PINECONE_API_KEY>"
pinecone_index     = "<HURON_PINECONE_INDEX>"
jwt_secret         = "<NEW_JWT_SECRET_STAGING>"
mcp_encryption_key = "<NEW_MCP_KEY_STAGING>"

certificate_arn       = "<ACM_CERT_ARN>"
domain_name           = "staging.huron.example.com"
route53_zone_id       = "<HOSTED_ZONE_ID>"
enable_cicd           = true
enable_blue_green     = true
github_repo           = "HuronOrg/Huron_GenAI_Knowledge_Assistant"
github_branch         = "staging"
github_connection_arn = "<CODESTAR_CONNECTION_ARN>"
EOF
```

### Step 4.1c — Create terraform/aws/environments/prod.tfvars

```bash
cat > terraform/aws/environments/prod.tfvars << 'EOF'
environment  = "prod"
project_name = "huron"
aws_region   = "<HURON_AWS_REGION>"

use_free_tier = false

backend_cpu            = 2048
backend_memory         = 4096
backend_desired_count  = 2
frontend_cpu           = 512
frontend_memory        = 1024
frontend_desired_count = 2

db_username                = "huron_user"
db_password                = "<NEW_DB_PASSWORD_PROD>"
db_name                    = "huron_prod"
db_allocated_storage       = 50
db_instance_class          = "db.t3.medium"
db_multi_az                = true
db_backup_retention_period = 7
db_skip_final_snapshot     = false
db_storage_encrypted       = true
db_deletion_protection     = true

openai_api_key     = "<HURON_OPENAI_API_KEY>"
pinecone_api_key   = "<HURON_PINECONE_API_KEY>"
pinecone_index     = "<HURON_PINECONE_INDEX>"
jwt_secret         = "<NEW_JWT_SECRET_PROD>"
mcp_encryption_key = "<NEW_MCP_KEY_PROD>"

certificate_arn       = "<ACM_CERT_ARN>"
domain_name           = "huron.example.com"
route53_zone_id       = "<HOSTED_ZONE_ID>"
enable_cicd           = true
enable_blue_green     = true
github_repo           = "HuronOrg/Huron_GenAI_Knowledge_Assistant"
github_branch         = "main"
github_connection_arn = "<CODESTAR_CONNECTION_ARN>"
EOF
```

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

### Step 4.4 — Updating secrets after initial deployment

If you need to rotate API keys or passwords after the first `terraform apply`:

```bash
# Update the value in your .tfvars file, then:
terraform apply -var-file environments/dev.tfvars

# Then force ECS to restart and pick up the new secret values:
aws ecs update-service --cluster huron-dev-cluster \
  --service huron-dev-backend --force-new-deployment --region <HURON_REGION>
```

> Secrets stored in AWS Secrets Manager are injected at task startup.
> ECS tasks do **not** automatically restart when a secret value changes —
> you must force a new deployment for the new values to take effect.

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

### Step 6.0 — Verify IAM permissions on Huron AWS account

Before running Terraform, confirm the AWS user has sufficient permissions:

```bash
# Check current identity
aws sts get-caller-identity

# Quick permission test — if any return 'implicitDeny', you need more permissions
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names ec2:DescribeVpcs ecs:CreateCluster ecr:CreateRepository \
    rds:CreateDBInstance iam:CreateRole secretsmanager:CreateSecret \
  --query "EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}"
```

**Minimum required permissions:**
`ec2:*`, `ecs:*`, `ecr:*`, `rds:*`, `elasticache:*`, `iam:*`,
`secretsmanager:*`, `s3:*`, `logs:*`, `wafv2:*`, `elasticloadbalancing:*`,
`autoscaling:*`, `cloudwatch:*`, `route53:*`, `acm:*`

The easiest option for initial setup is `AdministratorAccess` on the Huron AWS
account, scoped down to least-privilege after the initial deployment is verified.

### Step 6.1 — (Recommended) Configure remote Terraform state

If multiple people will run Terraform, use S3 to share state and prevent conflicts:

```bash
# Create S3 bucket for state (one-time setup)
aws s3api create-bucket \
  --bucket huron-terraform-state-<HURON_ACCOUNT_ID> \
  --region <HURON_REGION>

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket huron-terraform-state-<HURON_ACCOUNT_ID> \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name huron-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region <HURON_REGION>
```

Then add a `backend.tf` file in `terraform/aws/`:
```hcl
terraform {
  backend "s3" {
    bucket         = "huron-terraform-state-<HURON_ACCOUNT_ID>"
    key            = "huron/terraform.tfstate"
    region         = "<HURON_REGION>"
    dynamodb_table = "huron-terraform-locks"
    encrypt        = true
  }
}
```

> **Skip this for solo dev deployments.** Only needed if multiple engineers
> will run `terraform apply`.

### Step 6.2 — Start local Docker database

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
# IMPORTANT: First pass — ECS starts at 0 tasks (avoids CannotPullContainerError on first deploy)
terraform apply -var-file environments/dev.tfvars -var="initial_deployment=true"
# Type 'yes' when prompted — takes 10-15 minutes

# Note the outputs — you will need them:
terraform output alb_dns_name      # → DEV_ALB_URL
terraform output ecr_backend_url   # → DEV_ECR_BACKEND
terraform output ecr_frontend_url  # → DEV_ECR_FRONTEND
terraform output ecs_cluster_name  # → DEV_ECS_CLUSTER
terraform output -raw rds_endpoint  # → for DEV_DATABASE_URL secret (sensitive value)
```

### Step 6.3b — Request ACM Certificate and get Route 53 Zone ID (staging/prod only)

Required for HTTPS. Skip for dev if using HTTP only.

```bash
# Request wildcard certificate
aws acm request-certificate \
  --domain-name "huron.example.com" \
  --subject-alternative-names "*.huron.example.com" \
  --validation-method DNS \
  --region <HURON_REGION>
# Returns: CertificateArn — save this value

# Get DNS validation records (needed to prove domain ownership)
aws acm describe-certificate \
  --certificate-arn <CertificateArn> \
  --query "Certificate.DomainValidationOptions[*].{Domain:DomainName,Name:ResourceRecord.Name,Value:ResourceRecord.Value}" \
  --output table
```

Add the returned CNAME records to your DNS registrar (or Route 53 hosted zone).
Certificate status changes from **Pending** → **Issued** within 5–30 minutes.

```bash
# Get your Route 53 hosted zone ID
aws route53 list-hosted-zones \
  --query "HostedZones[*].{Name:Name,Id:Id}" \
  --output table

# Copy the zone ID (format: /hostedzone/ZXXXXXXXXXXXXX — use just ZXXXXXXXXXXXXX)
# Paste into staging.tfvars and prod.tfvars as route53_zone_id
# Paste the certificate ARN as certificate_arn
```

### Step 6.4 — Create AWS CodeStar Connection for GitHub (staging/prod only)

Required if `enable_cicd = true`. This cannot be automated — must be done manually:

1. Go to **AWS Console → CodePipeline → Settings → Connections**
2. Click **Create connection**
3. Select **GitHub** as the provider
4. Name it: `huron-github-connection`
5. Click **Connect to GitHub** → authorize the OAuth prompt
6. Click **Install a new app** → select the Huron GitHub org → grant repo access
7. Click **Connect**
8. Copy the **Connection ARN** — looks like:
   `arn:aws:codestar-connections:us-east-1:<account-id>:connection/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
9. Paste this ARN into `staging.tfvars` and `prod.tfvars` as `github_connection_arn`

> **Note:** The connection must be in **Available** status (not **Pending**) before
> running `terraform apply`. Pending connections will cause the pipeline to fail.

### Step 6.5 — Set GitHub Secrets

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
docker build -f Dockerfile.production \
  -t <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend:latest .
docker push <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend:latest

# Push frontend
docker build -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL=http://<DEV_ALB_URL> \
  -t <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-frontend:latest \
  ./frontend
docker push <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-frontend:latest

# Phase 2 — scale ECS up now that images exist in ECR
terraform apply -var-file environments/dev.tfvars -var="initial_deployment=false"
# Type 'yes' — completes in ~30 seconds
# ECS tasks will start pulling images and become healthy within 2-3 minutes
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

# Migrations run automatically on first container start via Alembic.
# If health shows database errors, check the backend logs:
aws logs tail /ecs/huron-dev/backend --since 10m --region <HURON_REGION>

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

### Step 8.0 — Rollback plan (if Huron deployment fails)

Before cleaning up personal resources, confirm Huron's deployment is fully stable:

- Keep personal AWS infrastructure **running** until all checklist items pass
- Keep personal GitHub repo **un-archived** until handover is complete
- If Huron's deployment fails critically, revert DNS to personal ALB temporarily

Only proceed to Steps 8.1–8.3 after all verification checklist items are checked.

Once Huron infrastructure is verified working:

### Step 9.1 — Archive personal GitHub repo
```bash
# In personal GitHub: Settings → Archive repository
# Or: make it private if you want to keep it as a backup
```

### Step 9.2 — Destroy personal AWS infrastructure
```bash
# ONLY after confirming Huron's deployment is working
cd terraform/aws

# Delete IAM key first to avoid destroy error
aws iam list-access-keys --user-name huron-dev-cicd-user
aws iam delete-access-key --user-name huron-dev-cicd-user --access-key-id <KEY_ID>

# Destroy
terraform apply -destroy -var-file environments/dev.tfvars -auto-approve
```

### Step 9.3 — Remove personal credentials from Huron machine
```bash
# Remove personal AWS profile if it was configured
aws configure --profile personal
# Set all values to 'none' or delete ~/.aws/credentials entry
```

---

## Phase 8.5 — Duo MFA / SSO-Only Login Enforcement

> **Context:** Huron uses Duo Security as the MFA provider inside Azure AD (Entra ID).
> Duo fires automatically when users authenticate via SSO — no Duo SDK integration needed.
> This phase documents the code changes already made and what you need to action
> in your AWS deployment to activate them.

### What Changed in the Code

Two backend files were updated. These changes are already committed and will deploy
automatically via the existing CI/CD pipelines once GitHub Secrets are in place.

#### `backend/core/database.py` — `get_user_by_login`

**Before:**
```python
"SELECT id,username,email,full_name,password_hash,role,department,is_active "
"FROM users WHERE username=?",
```

**After:**
```python
"SELECT id,username,email,full_name,password_hash,role,department,is_active,auth_method "
"FROM users WHERE username=?",
```

`auth_method` is now returned with every login fetch so the enforcement check below
has the value available.

#### `backend/routes/auth.py` — `POST /api/v1/auth/login`

Added environment-gated SSO-only enforcement before the bcrypt check:

```python
_SSO_ENFORCED_ENVS = {"staging", "production", "prod"}
_APP_ENV = os.getenv("APP_ENV", "dev").lower()

# In staging/production: users provisioned via SSO must use the SSO path.
# Local password login is blocked for them — Duo MFA is enforced by Azure AD.
# Root account is exempt for emergency access.
if (
    _APP_ENV in _SSO_ENFORCED_ENVS
    and user.get("auth_method") == "oidc"
    and user["username"] != "root"
):
    write_audit(user["id"], user["username"], "local_login_blocked_sso_required")
    raise HTTPException(
        status_code=403,
        detail="This account uses company SSO. Please sign in with Microsoft.",
    )
```

| `APP_ENV` value | SSO user tries local login | Local-only user | `root` |
|-----------------|---------------------------|-----------------|--------|
| `dev` | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| `staging` | ❌ 403 → must use SSO | ✅ Allowed | ✅ Allowed |
| `production` | ❌ 403 → must use SSO | ✅ Allowed | ✅ Allowed |

---

### Actions Required on AWS

#### Step 8.5.1 — Set `APP_ENV` in AWS Secrets Manager / ECS task definitions

The enforcement only activates when `APP_ENV` is set correctly. Verify each environment:

```bash
# Check current value in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id huron/staging/app-env \
  --query SecretString --output text

# Set for staging
aws secretsmanager put-secret-value \
  --secret-id huron/staging/backend-env \
  --secret-string '{"APP_ENV":"staging"}'

# Set for production
aws secretsmanager put-secret-value \
  --secret-id huron/prod/backend-env \
  --secret-string '{"APP_ENV":"production"}'
```

If `APP_ENV` is injected via ECS task definition directly:

```bash
# Get current task definition
aws ecs describe-task-definition \
  --task-definition huron-staging-backend \
  --query "taskDefinition.containerDefinitions[0].environment"

# Confirm APP_ENV=staging is present
# If missing, add it via the ECS Console or re-apply Terraform
```

#### Step 8.5.2 — Verify the OIDC env vars are set in ECS (staging)

SSO enforcement only blocks users who have `auth_method = 'oidc'` in the DB.
That value is only written when users log in via the OIDC callback endpoint —
which requires the OIDC env vars to be set:

```bash
# Check staging has OIDC vars configured
aws secretsmanager get-secret-value \
  --secret-id huron/staging/backend-env \
  --query SecretString --output text | python -m json.tool | grep OIDC
```

Required variables:
```
OIDC_CLIENT_ID       = <Azure AD app client ID>
OIDC_CLIENT_SECRET   = <Azure AD client secret>
OIDC_AUTHORITY       = https://login.microsoftonline.com/<tenant-id>
OIDC_REDIRECT_URI    = https://<staging-alb-domain>/api/v1/auth/oidc/callback
```

See `OIDC_SSO_SETUP.md` for how to register the app in Azure AD and obtain these values.
Note that `OIDC_REDIRECT_URI` must be updated when the deployment moves from AWS ALB
to Azure Container Apps (the domain will change).

#### Step 8.5.3 — Force ECS redeploy to pick up code changes

After confirming env vars are set, force a new ECS deployment to run the updated code:

```bash
# Staging
aws ecs update-service \
  --cluster huron-staging-cluster \
  --service huron-staging-backend \
  --force-new-deployment \
  --region us-east-1

aws ecs wait services-stable \
  --cluster huron-staging-cluster \
  --services huron-staging-backend \
  --region us-east-1

# Verify code is live
curl -s https://<staging-alb-domain>/health | python -m json.tool
```

#### Step 8.5.4 — Test SSO enforcement on staging

```bash
# 1. Log in via SSO as a real company user
#    Navigate to: https://<staging-alb-domain>/api/v1/auth/oidc/login
#    Complete Duo Push challenge
#    Confirm you land on the dashboard

# 2. Confirm that user's auth_method is now 'oidc' in the DB
#    (Connect to staging DB and run:)
#    SELECT username, email, auth_method FROM users WHERE email = '<your-email>';

# 3. Try to log in with that same user via the local password endpoint
curl -X POST https://<staging-alb-domain>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<your-username>","password":"<your-password>"}'

# Expected response:
# HTTP 403
# {"detail":"This account uses company SSO. Please sign in with Microsoft."}

# 4. Confirm audit log recorded the blocked attempt
#    SELECT * FROM audit_log WHERE action = 'local_login_blocked_sso_required'
#    ORDER BY created_at DESC LIMIT 5;
```

#### Step 8.5.5 — Azure AD Conditional Access (verify Duo fires for this app)

Even on AWS-hosted deployments, the OIDC flow goes through Microsoft Entra ID.
Duo fires inside Microsoft's login page — not at the AWS level.

Confirm Duo is required for the Huron app registration:

1. **Azure Portal → Microsoft Entra ID → Security → Conditional Access → Policies**
2. Find the policy covering the `Huron GenAI Knowledge Assistant` app registration
3. Confirm **Grant: Require multi-factor authentication** is set
4. Confirm **Policy status: On** (not Report-only)

If no policy exists, see `DUO_MFA_INTEGRATION.md` → Section "Azure AD Conditional Access"
for step-by-step instructions to create one.

> **Important:** This verification is required whether you are on AWS or Azure.
> Duo is controlled by Azure AD Conditional Access, not by the cloud hosting platform.

---

### What Does NOT Need to Change on AWS

| Item | Reason |
|------|--------|
| ECS task definition structure | No new containers — same backend image |
| ALB / target groups | No routing changes |
| ECR repositories | Same image names and tags |
| GitHub Actions workflows | Code change deploys automatically via existing pipelines |
| RDS / PostgreSQL schema | `auth_method` column already exists in the `users` table |
| Terraform AWS files | No infrastructure changes required |

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
- [ ] Branch protection rules set on main and staging
- [ ] AWS account ID updated in all workflow files
- [ ] REPO references updated in scripts

### Environment Files (created on Huron machine, never committed)
- [ ] `terraform/aws/environments/dev.tfvars` created with Huron credentials
- [ ] `terraform/aws/environments/staging.tfvars` created
- [ ] `terraform/aws/environments/prod.tfvars` created
- [ ] `backend/.env` created with Huron API keys
- [ ] `frontend/.env.local` created

### Infrastructure
- [ ] IAM permissions verified on Huron AWS account
- [ ] S3 remote state bucket created (if multi-engineer)
- [ ] Local huron-postgres Docker container running
- [ ] `terraform apply -var="initial_deployment=true"` completed for dev
- [ ] Docker images pushed to ECR
- [ ] `terraform apply -var="initial_deployment=false"` run to scale up ECS
- [ ] GitHub Secrets set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DEV_DATABASE_URL)
- [ ] GitHub Variables set (DEV_ALB_URL, DEV_ECR_BACKEND, DEV_ECR_FRONTEND, DEV_ECS_CLUSTER)
- [ ] ACM certificate issued (staging/prod only)
- [ ] CodeStar GitHub connection in **Available** status (staging/prod only)

### Verification
- [ ] CI pipeline passes (all 4 jobs green)
- [ ] Deploy pipeline completes successfully
- [ ] Health check returns `{"status":"healthy"}`
- [ ] Can log in to the app at the ALB URL
- [ ] Departments page shows 8 departments
- [ ] Dashboard shows real data

### Duo MFA / SSO Enforcement (Phase 8.5)
- [ ] `APP_ENV=staging` confirmed on ECS staging task
- [ ] `APP_ENV=production` confirmed on ECS prod task
- [ ] OIDC env vars set in Secrets Manager for staging (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_AUTHORITY`, `OIDC_REDIRECT_URI`)
- [ ] SSO login via `/api/v1/auth/oidc/login` completes with Duo Push on staging
- [ ] `auth_method = 'oidc'` written to DB after first SSO login
- [ ] Local password login for SSO user returns HTTP 403 on staging
- [ ] `local_login_blocked_sso_required` event visible in audit log
- [ ] Azure AD Conditional Access policy status: **On** (not Report-only)
- [ ] Root account local login still works (emergency access confirmed)

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
| `backend/core/database.py` | `auth_method` added to login SELECT | Already committed — auto-deploys |
| `backend/routes/auth.py` | SSO-only enforcement block + `APP_ENV` gate | Already committed — auto-deploys |
| `scripts/setup-github-secrets.*` | REPO reference | Updated in Step 1.3 |
| `scripts/post-apply.*` | REPO reference | Updated in Step 1.3 |

---

## Phase 9 — Observability & Monitoring (Complete Before Production)

All six steps below must be completed before the app goes live. Steps 1–3 activate tools
whose code is already written but not yet configured. Steps 4–6 require code changes.
Complete them in order — each layer builds on the previous one.

| Step | Tool | What it covers | Status |
|------|------|----------------|--------|
| 9.1 | Sentry | Backend + frontend error tracking | Code ready, DSN missing |
| 9.2 | Better Stack | External uptime monitoring + on-call alerts | Not configured |
| 9.3 | CloudWatch SNS | Alert notifications for AWS infra alarms | Terraform gap |
| 9.4 | Deep health check | DB + Pinecone connectivity, not just process alive | Shallow — needs code change |
| 9.5 | Grafana | Unified dashboard for ECS / RDS / ALB metrics | IAM ready, workspace not created |
| 9.6 | LangSmith | Full LLM chain tracing — every RAG call captured | Not implemented |

---

### Step 9.1 — Sentry (Error Tracking)

The Sentry SDK is already integrated in both backend and frontend. The only thing missing
is the DSN values in the environment files. Nothing needs to be installed or coded.

**Why Sentry matters here:** The Huron query pipeline makes 4–5 external calls per request
(embed → Pinecone → LLM → faithfulness check → DB write). Any of them can fail silently
and the user just sees "No results." Without Sentry you are guessing which step broke.
Sentry gives you the exact file, line number, and input values within 30 seconds of failure.

#### 9.1.1 — Create Sentry account and two projects

1. Go to **https://sentry.io** → sign up → create organisation `huron-consulting`.
2. **Create Project → Python → FastAPI** → name it `huron-backend` → copy the DSN.
3. **Create Project → JavaScript → Next.js** → name it `huron-frontend` → copy the DSN.
4. **Settings → Auth Tokens → Create New Token** → scopes: `project:releases` + `org:read`
   → copy the token (shown once only).

#### 9.1.2 — Fill in `backend/.env`

Open `backend/.env` and set:

```
SENTRY_DSN=https://abc123@o000000.ingest.sentry.io/0000000   # backend DSN from step above
APP_ENV=staging                                               # use "staging" here; change to "production" only on prod deploy
```

The backend Sentry integration in `main.py` (lines 44–79) activates automatically as soon
as `SENTRY_DSN` is non-empty. No code change needed. See Step 9.4 — the deep health check
must also be in place before configuring Better Stack monitors in Step 9.2.

#### 9.1.3 — Fill in `frontend/.env.local`

```
NEXT_PUBLIC_SENTRY_DSN=https://xyz789@o000000.ingest.sentry.io/1111111
SENTRY_ORG=huron-consulting
SENTRY_PROJECT=huron-frontend
SENTRY_AUTH_TOKEN=sntrys_your_token_here
```

The frontend Sentry config files (`sentry.client.config.ts`, `sentry.server.config.ts`,
`sentry.edge.config.ts`) and `next.config.js` wrapping are all already written. They
activate automatically when `NEXT_PUBLIC_SENTRY_DSN` is set.

#### 9.1.4 — Install the packages

```bash
# Backend
pip install "sentry-sdk[fastapi]"

# Frontend (from the frontend/ directory)
npm install @sentry/nextjs
```

#### 9.1.5 — Verify

```bash
# Hit the staging backend ALB — replace with your actual staging URL
curl -X POST https://<staging-alb-domain>/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "sentry-test"}'
```

Go to **sentry.io → huron-backend → Issues** and filter by environment `staging`.
You should see the event within 30 seconds. Repeat for the frontend by opening the
staging app URL and checking **huron-frontend → Issues**.

---

### Step 9.2 — Better Stack (Uptime Monitoring)

No code changes required. All configuration is in the Better Stack dashboard.

**Why Better Stack:** Sentry only fires when an error occurs inside the process. If the
ECS task crashes completely, or the ALB becomes unreachable, Sentry never fires because the
process is dead. Better Stack pings `/health` from external locations every 30 seconds —
it catches the cases Sentry misses.

#### 9.2.1 — Create account and monitors

1. Go to **https://betterstack.com** → sign up → open **Uptime** section.
2. **New monitor → HTTP**
   - URL: `https://<staging-alb-domain>/health`  *(use staging URL first — add a second production monitor after prod deploy)*
   - Name: `Huron Backend — Staging`
   - Check frequency: `30 seconds`
   - Expected status: `200`
   - Regions: select **US East** + **EU West** (two regions prevent false alarms from
     single-region network blips)
   - Recovery confirmation: `2 consecutive successes` (prevents flapping incidents)
3. **New monitor → HTTP**
   - URL: `https://<staging-frontend-domain>`
   - Name: `Huron Frontend — Staging`
   - Expected status: `200`
4. **New monitor → HTTP** *(optional but recommended)*
   - URL: `https://api.pinecone.io`
   - Expected status: `401` (Pinecone rejects unauthenticated pings with 401 — this means
     Pinecone is alive and responding. A 5xx or timeout means Pinecone is having an outage
     which would break every query silently.)
   - Name: `Pinecone Reachability`

#### 9.2.2 — Configure alerting

1. Left sidebar → **On-call → Alert policies → New alert policy** → name: `Huron Staging`
2. Add escalations:
   - Immediately → **Email**
   - After 5 minutes → **SMS** (add phone under Team → your profile)
3. On each monitor → **Edit → Alert policy → Huron Staging**.

> After production is deployed, duplicate this policy, rename it `Huron Production`,
> and attach it to the production monitors.

#### 9.2.3 — Add a status page

1. Left sidebar → **Status pages → New status page** → name: `Huron System Status`
2. Add all three monitors.
3. Share the public URL with your team — users can check it themselves instead of messaging you.

---

### Step 9.3 — CloudWatch SNS (Infrastructure Alarm Notifications)

The Terraform config in `terraform/aws/main.tf` already defines 6 CloudWatch alarms
(backend CPU, backend memory, frontend CPU, RDS CPU, RDS connections, RDS storage). The gap
is that **no SNS topic is wired to them** — alarms fire but notify nobody.

#### 9.3.1 — Add SNS topic and subscription to Terraform

Open `terraform/aws/main.tf` and add the following block before the CloudWatch alarms section:

```hcl
# ── SNS topic for CloudWatch alarm notifications ──────────────────────────────
resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
  tags = { Environment = var.environment }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email          # add this variable to variables.tf
}
```

#### 9.3.2 — Add the variable to `variables.tf`

```hcl
variable "alert_email" {
  description = "Email address that receives CloudWatch alarm notifications"
  type        = string
}
```

#### 9.3.3 — Add the variable to each `environments/*.tfvars`

```hcl
alert_email = "ops@huron-vaultmind.ai"    # use the real ops email
```

#### 9.3.4 — Wire SNS to every existing alarm

For each of the 6 `aws_cloudwatch_metric_alarm` blocks in `main.tf`, add:

```hcl
alarm_actions             = [aws_sns_topic.alerts.arn]
ok_actions                = [aws_sns_topic.alerts.arn]
insufficient_data_actions = [aws_sns_topic.alerts.arn]
```

Example for the backend CPU alarm (the same pattern applies to all 6):

```hcl
resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
  alarm_name          = "${local.prefix}-backend-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 120
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Backend CPU above 85%"
  alarm_actions             = [aws_sns_topic.alerts.arn]
  ok_actions                = [aws_sns_topic.alerts.arn]
  insufficient_data_actions = [aws_sns_topic.alerts.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }
}
```

#### 9.3.5 — Apply and confirm subscription

```bash
# Apply to staging first — repeat for prod.tfvars after staging is verified
terraform apply -var-file="environments/staging.tfvars"
```

AWS sends a confirmation email to the address in `alert_email`. **You must click the
confirmation link in that email** or the SNS subscription stays in `PendingConfirmation`
and no alerts are ever sent. Repeat `terraform apply -var-file="environments/prod.tfvars"`
after staging passes all checklist items.

---

### Step 9.4 — Deep Health Check

The current `/health` endpoint returns `{"status":"healthy"}` whether or not the database
or Pinecone are reachable. A process can be alive while being completely unable to serve
requests. This change makes the health check actually verify the critical dependencies.

**Why this matters for Better Stack and the ALB:** The ALB uses `/health` to decide whether
to route traffic to an ECS task. If the task is up but the DB connection is broken, the ALB
currently keeps sending traffic to it. After this change, a broken DB causes `/health` to
return 503, the ALB removes the task from rotation, and ECS replaces it automatically.

#### 9.4.1 — Replace `backend/routes/health.py`

Replace the current contents of `backend/routes/health.py` with:

```python
"""
Deep health check — verifies process, database, and Pinecone connectivity.
Returns 200 only when all critical dependencies are reachable.
Returns 503 with a degraded payload when any dependency is down.
"""
import os
import time
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    checks  = {}
    healthy = True

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        from core.database import db_conn
        t0 = time.time()
        with db_conn() as conn:
            conn.execute("SELECT 1").fetchone()
        checks["database"] = {"status": "ok", "latency_ms": round((time.time() - t0) * 1000)}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        healthy = False

    # ── Pinecone ──────────────────────────────────────────────────────────────
    try:
        from pinecone import Pinecone
        t0  = time.time()
        pc  = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
        pc.list_indexes()
        checks["pinecone"] = {"status": "ok", "latency_ms": round((time.time() - t0) * 1000)}
    except Exception as exc:
        checks["pinecone"] = {"status": "error", "detail": str(exc)}
        healthy = False

    status_code = 200 if healthy else 503
    payload = {
        "status":  "healthy" if healthy else "degraded",
        "service": "huron-genai-backend",
        "version": "4.0.0",
        "checks":  checks,
    }

    from fastapi.responses import JSONResponse
    return JSONResponse(content=payload, status_code=status_code)
```

#### 9.4.2 — Verify locally

```bash
# Test locally first to confirm the code change is correct
curl -s http://localhost:8004/health | python -m json.tool
```

Then verify on staging after deploying:

```bash
curl -s https://<staging-alb-domain>/health | python -m json.tool
```

Expected output when healthy:
```json
{
  "status": "healthy",
  "service": "huron-genai-backend",
  "version": "4.0.0",
  "checks": {
    "database": {"status": "ok", "latency_ms": 2},
    "pinecone":  {"status": "ok", "latency_ms": 45}
  }
}
```

If the database is unreachable, the response code will be `503` and Better Stack will
trigger an alert within 60 seconds. **Do not deploy to production until this returns
200 on staging with both checks `ok`.**

---

### Step 9.5 — Amazon Managed Grafana (Unified Dashboard)

The Terraform IAM role for Grafana already exists (`aws_iam_role.grafana` in `main.tf`).
The `aws_grafana_workspace` resource is commented out because it requires manual enablement
in the AWS Console first.

**Why Grafana:** CloudWatch alarms tell you when a threshold is crossed. Grafana shows you
the full picture — ECS CPU over the last 7 days, RAG query volume per department, RDS
connection pool trends. It is where you go to understand capacity and plan scaling.

#### 9.5.1 — Enable Amazon Managed Grafana in AWS Console

1. AWS Console → **Amazon Grafana** → **Get started**.
2. Select **IAM Identity Center** as the authentication method (compatible with AD).
3. Note the workspace ARN shown after creation — you need it for Step 9.5.2.

#### 9.5.2 — Uncomment the Terraform resource

In `terraform/aws/main.tf`, find the commented-out block and replace it with:

```hcl
resource "aws_grafana_workspace" "main" {
  name                     = "${local.prefix}-grafana"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "SERVICE_MANAGED"
  role_arn                 = aws_iam_role.grafana.arn

  data_sources = [
    "CLOUDWATCH",
    "XRAY",
  ]

  tags = { Environment = var.environment }
}

output "grafana_endpoint" {
  value = aws_grafana_workspace.main.endpoint
}
```

```bash
# Apply to staging first
terraform apply -var-file="environments/staging.tfvars"
```

#### 9.5.3 — Add dashboards

After the workspace is created, import these two standard dashboards from the Grafana
dashboard library using their IDs:

| Dashboard | ID | What it shows |
|-----------|-----|---------------|
| AWS ECS | `550` | ECS CPU, memory, task count |
| AWS RDS | `707` | RDS connections, CPU, storage, IOPS |

In the Grafana workspace: **Dashboards → Import → enter ID → Load → select CloudWatch
as the data source → Import**.

---

### Step 9.6 — LangSmith (Full LLM Chain Tracing)

LangSmith captures every step of the RAG pipeline as a linked trace: embed call →
Pinecone query → retrieved chunks → LLM prompt sent → LLM response received →
faithfulness score. This is the only tool that answers "why did this query give a bad
answer?" with full visibility into what the model actually saw.

**What gets traced in this project:**
- Every `rag.query()` call → embed latency, Pinecone hit count, top scores per department
- Every `openai.chat.completions.create()` call → model used, token count (prompt +
  completion), latency, full prompt text
- Every `_source_guard()` call → faithfulness score, whether it passed
- Every fallback to `_llm_direct()` — so you know when RAG is bypassed

#### 9.6.1 — Create LangSmith account and project

1. Go to **https://smith.langchain.com** → sign up.
2. Create two projects: `huron-genai-staging` and `huron-genai-production`.
3. **Settings → API Keys → Create API Key** → copy the key (one key covers both projects).

#### 9.6.2 — Add environment variables to `backend/.env`

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=ls__your_key_here
LANGCHAIN_PROJECT=huron-genai-staging    # change to huron-genai-production on prod deploy
```

Setting `LANGCHAIN_TRACING_V2=true` activates the LangSmith SDK's auto-patching of
OpenAI calls. **Every `openai.chat.completions.create()` call in the entire backend is
automatically captured** — no code change needed for the LLM calls that already exist.

#### 9.6.3 — Install the package

```bash
pip install langsmith openai
```

#### 9.6.4 — Wrap the RAG query entry point for full trace linking

The auto-patching captures individual LLM calls but does not group them into a single
trace per user request. Add the `@traceable` decorator to the query and chat endpoints
so that the embed call, Pinecone query, and LLM call are all shown as one linked trace
in LangSmith.

Add this to `backend/main.py` in the imports section at the top:

```python
# LangSmith tracing — no-op when LANGCHAIN_TRACING_V2 is not set
try:
    from langsmith import traceable
except ImportError:
    def traceable(*args, **kwargs):      # noqa: E306
        def _wrap(fn):
            return fn
        return _wrap
```

Then wrap the two internal helper functions that do the actual RAG work.
Find `_source_guard` in `main.py` and add the decorator above it:

```python
@traceable(name="source_guard", run_type="chain")
async def _source_guard(query: str, response: str,
                        sources: list, faithfulness_score):
```

And wrap `_llm_direct`:

```python
@traceable(name="llm_direct_fallback", run_type="llm")
async def _llm_direct(messages: list[dict], dept: str, top_k: int = 5) -> dict:
```

#### 9.6.5 — Add metadata tags to traces

LangSmith lets you filter traces by department, user, and model. Add this helper call
inside the `query_endpoint` function in `main.py`, right before `rag.query()` is called:

```python
# Attach LangSmith metadata so traces are filterable by dept and user
try:
    from langsmith import get_current_run_tree
    run = get_current_run_tree()
    if run:
        run.add_metadata({
            "dept":     dept,
            "username": p.get("sub"),
            "role":     p.get("role"),
        })
except Exception:
    pass
```

#### 9.6.6 — Verify traces are appearing

```bash
# Send a test query against staging (must be authenticated)
curl -X POST https://<staging-alb-domain>/api/v1/query \
  -H "Authorization: Bearer <your-staging-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the onboarding policy?"}'
```

Go to **https://smith.langchain.com → huron-genai-staging → Traces**.

Within 10 seconds you should see a trace entry. Click it to confirm it shows:
- The embedding call with latency
- The Pinecone query with number of matches and top score
- The LLM call with prompt tokens, completion tokens, model name, and latency
- The faithfulness score from `_source_guard`
- The department and username as metadata tags

#### 9.6.7 — What to monitor in LangSmith day-to-day

| Metric | Where to find it | What to act on |
|--------|-----------------|----------------|
| P95 LLM latency | Traces → filter by run type `llm` | If >5s, check OpenAI tier limits |
| Prompt token count | Traces → expand LLM run | If >3000 tokens, chunk retrieval is pulling too many chunks |
| Faithfulness score distribution | Traces → filter by `source_guard` | If avg <0.7, documents need re-ingestion or chunking tuned |
| `llm_direct_fallback` frequency | Traces → filter by name | If >5% of queries hit fallback, Pinecone namespace has no documents |
| Error rate by dept | Traces → group by metadata `dept` | Identify which departments have broken retrieval |

---

### Phase 9 — Pre-Production Checklist (Staging)

Complete all items on staging before promoting to production.
After staging passes, re-run the `terraform apply` and env var steps targeting production.

#### Sentry
- [ ] `SENTRY_DSN` set in `backend/.env`
- [ ] `NEXT_PUBLIC_SENTRY_DSN` set in `frontend/.env.local`
- [ ] `SENTRY_AUTH_TOKEN` set in `frontend/.env.local`
- [ ] `APP_ENV=staging` set in staging `backend/.env` (changes to `production` on prod deploy)
- [ ] `sentry-sdk[fastapi]` in `backend/requirements.txt`
- [ ] `@sentry/nextjs` in `frontend/package.json`
- [ ] Test event visible in Sentry dashboard

#### Better Stack
- [ ] Backend `/health` monitor created and showing green
- [ ] Frontend monitor created and showing green
- [ ] Pinecone reachability monitor created
- [ ] Alert policy created with email + SMS escalation
- [ ] Status page created and shared with team

#### CloudWatch SNS
- [ ] `aws_sns_topic.alerts` resource added to `main.tf`
- [ ] `alert_email` variable added to `variables.tf` and all `*.tfvars`
- [ ] All 6 `alarm_actions` wired to SNS topic
- [ ] `terraform apply` completed
- [ ] SNS subscription confirmation email clicked

#### Deep Health Check
- [ ] `backend/routes/health.py` updated with DB + Pinecone checks
- [ ] `/health` returns 503 when DB is intentionally disconnected (local test)
- [ ] `/health` returns 200 with both checks `ok` on staging ALB URL

#### Grafana
- [ ] Amazon Managed Grafana enabled in AWS Console
- [ ] `aws_grafana_workspace` resource uncommented and applied
- [ ] ECS dashboard (ID `550`) imported
- [ ] RDS dashboard (ID `707`) imported
- [ ] At least one team member has Grafana access via AWS SSO

#### LangSmith
- [ ] LangSmith account created, projects `huron-genai-staging` and `huron-genai-production` created
- [ ] `LANGCHAIN_TRACING_V2=true` set in `backend/.env`
- [ ] `LANGCHAIN_API_KEY` set in `backend/.env`
- [ ] `LANGCHAIN_PROJECT=huron-genai-staging` set in staging `backend/.env`
- [ ] `langsmith` package in `backend/requirements.txt`
- [ ] `traceable` import + no-op fallback added to `main.py`
- [ ] `@traceable` decorator added to `_source_guard` and `_llm_direct`
- [ ] Metadata tags (dept, username, role) added in `query_endpoint`
- [ ] Test trace visible in **huron-genai-staging** project with embed + Pinecone + LLM steps linked
- [ ] Faithfulness score visible in trace metadata
- [ ] After prod deploy: `LANGCHAIN_PROJECT` updated to `huron-genai-production` in prod env
