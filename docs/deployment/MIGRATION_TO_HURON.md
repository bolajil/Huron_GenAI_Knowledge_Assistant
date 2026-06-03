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
