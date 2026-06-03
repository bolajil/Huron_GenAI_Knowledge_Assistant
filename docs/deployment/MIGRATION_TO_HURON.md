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
# Generate a cryptographically secure JWT secret (run once each for dev, staging, prod)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a secure encryption key for MCP (run once each for dev, staging, prod)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a strong database password with a recognisable prefix
python -c "import secrets; print('Huron' + secrets.token_urlsafe(16) + '!')"
```

### Step 1.2 — Export the code from personal GitHub

```bash
# Clone using --mirror so ALL branches, tags and history are included (not just main)
git clone --mirror https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git

# Enter the mirror clone folder — this is a bare repo (no working files, just git data)
cd Huron_GenAI_Knowledge_Assistant.git
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
# Stage the files you just edited
git add .github/workflows/ scripts/

# Save the changes with a descriptive message
git commit -m "chore: update references for Huron infrastructure migration"

# Push develop — CI will run to validate the changes
git push origin develop

# Promote the same changes to main so both branches stay in sync
git checkout main && git merge develop && git push origin main

# Return to develop for normal work
git checkout develop
```

---

## Phase 2 — Set Up Huron's Computer

### Step 2.1 — Install prerequisites on Huron's machine

Run these on the Huron workstation:

```powershell
# Install Git — version control tool to clone and push code
winget install Git.Git

# Install Node.js 20 — required to run the Next.js frontend locally
winget install OpenJS.NodeJS.LTS

# Install Python 3.11 — required to run the FastAPI backend locally
winget install Python.Python.3.11

# Install Docker Desktop — runs containers locally (database, backend, frontend)
winget install Docker.DockerDesktop
# ⚠️ Restart the machine after this before continuing

# Install AWS CLI — lets you run AWS commands from the terminal
winget install Amazon.AWSCLI
# Confirm it installed correctly:
aws --version

# Install Terraform — provisions all AWS infrastructure (VPC, ECS, RDS, etc.)
winget install Hashicorp.Terraform
# Confirm it installed correctly:
terraform -version

# Install GitHub CLI — lets you manage GitHub from the terminal (secrets, workflows)
winget install GitHub.cli
# Confirm it installed correctly:
gh --version
```

### Step 2.2 — Configure AWS CLI with Huron credentials

```bash
# Saves Huron AWS credentials to ~/.aws/credentials so every aws command uses them
aws configure
# AWS Access Key ID:     <Huron AWS access key>
# AWS Secret Access Key: <Huron AWS secret key>
# Default region:        <Huron AWS region>
# Default output format: json

# Test that credentials work — should print Huron's account ID, not personal one
aws sts get-caller-identity
```

### Step 2.3 — Authenticate GitHub CLI

```bash
# Log the GitHub CLI into Huron's GitHub account so gh commands work
gh auth login
# Choose: GitHub.com        ← use github.com, not enterprise
# Choose: HTTPS             ← use HTTPS not SSH
# Choose: Login with a web browser
# Complete browser login with Huron GitHub account
```

---

## Phase 3 — Move Code to Huron GitHub

### Step 3.1 — Create the repo in Huron's GitHub

```bash
# Create a new private repo in Huron's GitHub org (replace HuronOrg with actual org/username)
gh repo create HuronOrg/Huron_GenAI_Knowledge_Assistant \
  --private \
  --description "Huron GenAI Knowledge Assistant"
```

Or manually: GitHub → New Repository → Name: `Huron_GenAI_Knowledge_Assistant` → Private

### Step 3.2 — Push all branches and history

```bash
# Go into the mirror clone folder created in Step 1.2
cd Huron_GenAI_Knowledge_Assistant.git

# Point the remote URL at Huron's new repo instead of the personal one
git remote set-url origin https://github.com/HuronOrg/Huron_GenAI_Knowledge_Assistant.git

# Push everything — all branches, all history, all tags — to Huron's GitHub
git push --mirror
```

### Step 3.3 — Verify branches exist

```bash
# Open the repo in your browser — visually confirm all three branches exist
gh repo view HuronOrg/Huron_GenAI_Knowledge_Assistant --web
```

### Step 3.4 — Create staging branch if missing

```bash
# Clone a normal working copy of the repo
git clone https://github.com/HuronOrg/Huron_GenAI_Knowledge_Assistant.git
cd Huron_GenAI_Knowledge_Assistant

# Create the staging branch locally
git checkout -b staging

# Push it to GitHub so it exists as a remote branch
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
# Get Huron's AWS account ID — you'll use this to replace the personal one
aws sts get-caller-identity --query Account --output text

# Fill in Huron's values
$huronAccountId = "<HURON_ACCOUNT_ID>"
$region = "<HURON_REGION>"

# List the 3 workflow files that contain hardcoded account IDs
$files = @(
    ".github/workflows/deploy-dev.yml",
    ".github/workflows/deploy-staging.yml",
    ".github/workflows/deploy-prod.yml"
)

# Loop through each file and do a find-and-replace in one go
foreach ($file in $files) {
    (Get-Content $file) `
        -replace "137738968757", $huronAccountId `
        -replace "us-east-1", $region |
    Set-Content $file
}

# Stage the updated workflow files
git add .github/workflows/

# Commit the change
git commit -m "chore: update AWS account ID and region to Huron infrastructure"

# Push to develop — CI will run
git push origin develop

# Sync the same change to main and return to develop
git checkout main; git merge develop; git push origin main; git checkout develop
```

---

## Phase 6 — Deploy Infrastructure on Huron AWS

### Step 6.0 — Verify IAM permissions on Huron AWS account

Before running Terraform, confirm the AWS user has sufficient permissions:

```bash
# Confirm you are logged in as Huron's AWS user (not personal)
aws sts get-caller-identity

# Simulate key actions — any 'implicitDeny' result means you need more permissions
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
# Create the S3 bucket that will store the terraform.tfstate file remotely
aws s3api create-bucket \
  --bucket huron-terraform-state-<HURON_ACCOUNT_ID> \
  --region <HURON_REGION>

# Turn on versioning so you can recover a previous state if something goes wrong
aws s3api put-bucket-versioning \
  --bucket huron-terraform-state-<HURON_ACCOUNT_ID> \
  --versioning-configuration Status=Enabled

# Create a DynamoDB table used as a lock — prevents two people running terraform at the same time
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
# Start a local PostgreSQL database container for development use
# -d         = run in background
# --name     = give it a recognisable name
# -e         = set environment variables (database name, user, password)
# -p 5436    = expose on port 5436 locally (avoids clash with any system postgres on 5432)
docker run -d `
  --name huron-postgres `
  -e POSTGRES_DB=huron `
  -e POSTGRES_USER=huron_user `
  -e POSTGRES_PASSWORD=<NEW_DB_PASSWORD_DEV> `
  -p 5436:5432 `
  postgres:16-alpine

# Confirm the container is running (should show 'Up' in status column)
docker ps --filter "name=huron-postgres"
```

### Step 6.2 — Run Terraform to create AWS infrastructure

```bash
# Enter the Terraform directory
cd terraform/aws

# Download all required Terraform providers (AWS, etc.) — only needed once
terraform init

# Create all AWS infrastructure for dev (VPC, ECS, RDS, ECR, ALB, Secrets Manager…)
# initial_deployment=true sets ECS desired_count=0 so tasks don't start before images exist
# ⚠️  Takes 10-15 minutes — type 'yes' when prompted
terraform apply -var-file environments/dev.tfvars -var="initial_deployment=true"

# Read the outputs — copy these values, you'll need them in the next steps
terraform output alb_dns_name       # → paste as DEV_ALB_URL GitHub variable
terraform output ecr_backend_url    # → paste as DEV_ECR_BACKEND GitHub variable
terraform output ecr_frontend_url   # → paste as DEV_ECR_FRONTEND GitHub variable
terraform output ecs_cluster_name   # → paste as DEV_ECS_CLUSTER GitHub variable
terraform output -raw rds_endpoint  # → use in the DEV_DATABASE_URL secret (sensitive)
```

### Step 6.3b — Request ACM Certificate and get Route 53 Zone ID (staging/prod only)

Required for HTTPS. Skip for dev if using HTTP only.

```bash
# Request an SSL certificate for your domain (covers root + all subdomains with *)
aws acm request-certificate \
  --domain-name "huron.example.com" \
  --subject-alternative-names "*.huron.example.com" \
  --validation-method DNS \
  --region <HURON_REGION>
# → Returns a CertificateArn — save this, you'll need it in staging/prod tfvars

# Get the CNAME records AWS needs you to add to DNS to prove you own the domain
aws acm describe-certificate \
  --certificate-arn <CertificateArn> \
  --query "Certificate.DomainValidationOptions[*].{Domain:DomainName,Name:ResourceRecord.Name,Value:ResourceRecord.Value}" \
  --output table
# → Add those CNAME records in your DNS registrar — cert status changes to 'Issued' in 5-30 min
```

Add the returned CNAME records to your DNS registrar (or Route 53 hosted zone).
Certificate status changes from **Pending** → **Issued** within 5–30 minutes.

```bash
# List all Route 53 hosted zones — find the one matching your domain
aws route53 list-hosted-zones \
  --query "HostedZones[*].{Name:Name,Id:Id}" \
  --output table
# → Copy the zone ID (strip the /hostedzone/ prefix, keep just ZXXXXXXXXXXXXX)
# → Paste it as route53_zone_id in staging.tfvars and prod.tfvars
# → Paste the certificate ARN as certificate_arn in both files
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
# Runs the setup script which creates a new IAM access key and stores it
# as AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the GitHub repo secrets
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
# Reads the terraform outputs (ALB URL, ECR URLs, cluster name) and saves them
# as GitHub Actions variables so the deploy workflow knows where to deploy to
.\scripts\post-apply.ps1 -Env dev
```

### Step 6.5 — Bootstrap first Docker images

```bash
# Log Docker into AWS ECR — gets a temporary password and passes it straight to docker login
aws ecr get-login-password --region <HURON_REGION> | \
  docker login --username AWS --password-stdin \
  <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com

# Build the backend Docker image using the production Dockerfile
docker build -f Dockerfile.production \
  -t <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend:latest .

# Upload (push) the backend image to ECR so ECS can pull it
docker push <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-backend:latest

# Build the frontend image — bake the ALB URL in so the browser knows where the API is
docker build -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL=http://<DEV_ALB_URL> \
  -t <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-frontend:latest \
  ./frontend

# Upload the frontend image to ECR
docker push <HURON_ACCOUNT_ID>.dkr.ecr.<HURON_REGION>.amazonaws.com/huron-dev-frontend:latest

# Now images exist in ECR — tell Terraform to scale ECS back up to normal task count
# ⚠️  Type 'yes' — completes in ~30 seconds, ECS tasks become healthy within 2-3 minutes
terraform apply -var-file environments/dev.tfvars -var="initial_deployment=false"
```

---

## Phase 7 — First Deploy and Verify

### Step 7.1 — Trigger first automated deploy

```bash
# Push to develop — this kicks off the full automated pipeline:
# 1. CI runs (unit tests, TypeScript lint, integration tests, docker build smoke test)
# 2. DB migrations run against the RDS database
# 3. Docker images are built and pushed to Huron's ECR
# 4. ECS services are updated with the new images
# 5. Health check confirms the app is responding
git push origin develop
```

### Step 7.2 — Verify the deployment

```bash
# Hit the health endpoint — confirms backend is running and connected to the database
curl http://<DEV_ALB_URL>/health
# Expected response: {"status":"healthy","db":{"status":"ok","backend":"postgresql"},...}

# If health shows database errors, stream the last 10 minutes of backend container logs
aws logs tail /ecs/huron-dev/backend --since 10m --region <HURON_REGION>

# Open the frontend in a browser and log in
# URL:   http://<DEV_ALB_URL>
# Login: root / <NEW_ROOT_PASSWORD>
```

### Step 7.3 — Change root password

Once logged in, immediately change the root password from the default.
Or via the backend:
```bash
# Open a direct SQL connection to the RDS database
psql postgresql://huron_user:<password>@<db-endpoint>:5432/huron_dev

# Generate a bcrypt hash of your chosen new password (bcrypt is what the app expects)
python -c "import bcrypt; print(bcrypt.hashpw(b'<NEW_PASSWORD>', bcrypt.gensalt()).decode())"

# Paste the hash into this SQL command and run it inside psql:
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
# ⚠️  ONLY run this after Huron's deployment is fully verified and stable
cd terraform/aws

# List IAM access keys for the CI user — you need the key ID to delete it first
aws iam list-access-keys --user-name huron-dev-cicd-user

# Delete the IAM key — Terraform destroy fails if active keys exist
aws iam delete-access-key --user-name huron-dev-cicd-user --access-key-id <KEY_ID>

# Destroy all personal AWS infrastructure — this is irreversible
terraform apply -destroy -var-file environments/dev.tfvars -auto-approve
```

### Step 8.3 — Remove personal credentials from Huron machine
```bash
# Re-run aws configure for the personal profile and blank out all values
# Or open ~/.aws/credentials in a text editor and delete the [personal] section
aws configure --profile personal
# Set all values to 'none' to remove personal credentials from this machine
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
