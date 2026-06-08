# Migration Guide — Deploying Huron GenAI on Azure Infrastructure

This document covers every step to deploy the project on Huron's Azure subscription,
from credential collection through production go-live and observability activation.
It mirrors the structure of `MIGRATION_TO_HURON.md` (AWS version) but targets Azure.

> **The Azure Terraform infrastructure is already fully written** in `terraform/azure/`.
> No infrastructure code needs to be created — you only need to configure, apply, and verify.

---

## Overview of What Changes (Personal Dev → Azure Production)

| Item | Current (Personal/AWS) | Target (Azure) |
|------|------------------------|----------------|
| GitHub repo | `bolajil/Huron_GenAI_Knowledge_Assistant` | `HuronOrg/Huron_GenAI_Knowledge_Assistant` |
| Cloud provider | AWS (ECS, RDS, ElastiCache, ECR) | Azure (Container Apps, PostgreSQL Flexible Server, Redis Cache, ACR) |
| Container registry | Amazon ECR | Azure Container Registry (ACR) |
| Container runtime | ECS Fargate | Azure Container Apps |
| Database | RDS PostgreSQL 15 | PostgreSQL Flexible Server 15 |
| Cache | ElastiCache Redis | Azure Cache for Redis (TLS-only) |
| Secrets | AWS Secrets Manager | Azure Key Vault |
| Object storage | S3 | Azure Blob Storage |
| Monitoring | CloudWatch + Grafana | Log Analytics + Application Insights |
| Load balancer | ALB | Container Apps built-in HTTPS ingress |
| SSO | OIDC optional | Azure AD (Entra ID) — native |
| API Keys | Personal OpenAI / Pinecone | Huron enterprise keys |
| Machine | Personal laptop | Huron workstation |

---

## Phase 1 — Prepare on Your Current Machine (Before Handover)

### Step 1.1 — Collect all credentials you need

Create a **secure document (NOT in git)** with:

```
HURON AZURE SUBSCRIPTION ID:     __________________
HURON AZURE TENANT ID:           __________________
HURON AZURE REGION:              __________________   (e.g. East US 2)
HURON GITHUB ORG:                HuronOrg
HURON OPENAI API KEY:            __________________
HURON PINECONE API KEY:          __________________
HURON PINECONE INDEX NAME:       __________________   (default: huron-enterprise-knowledge)
HURON JWT SECRET (32+ chars):    __________________
HURON MCP ENCRYPTION KEY:        __________________
HURON POSTGRES PASSWORD:         __________________
HURON SENTRY DSN (backend):      __________________
HURON SENTRY DSN (frontend):     __________________
HURON LANGCHAIN API KEY:         __________________
AZURE AD TENANT ID (SSO):        __________________
AZURE AD CLIENT ID (SSO):        __________________
AZURE AD CLIENT SECRET (SSO):    __________________
ALERT EMAIL (ops):               __________________
```

To generate secrets locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Run twice — once for JWT_SECRET, once for MCP_ENCRYPTION_KEY
```

### Step 1.2 — Update GitHub repo references

In `.github/workflows/*.yml`, update the repo reference from personal to Huron org:

```bash
# On your current machine, find all personal repo references
grep -r "bolajil" .github/
```

Change every occurrence of `bolajil/Huron_GenAI_Knowledge_Assistant` to
`HuronOrg/Huron_GenAI_Knowledge_Assistant`.

### Step 1.3 — Add `.gitignore` protection for secret files

Confirm these lines exist in `.gitignore` (they should already be there):

```
terraform/azure/terraform.tfvars
terraform/azure/environments/
backend/.env
frontend/.env.local
*.tfvars
*.tfstate
*.tfstate.backup
deployment_outputs.txt
```

---

## Phase 2 — Set Up Huron Machine

### Step 2.1 — Install required tools

```bash
# Azure CLI (Windows)
winget install Microsoft.AzureCLI

# Azure CLI (macOS)
brew install azure-cli

# Verify
az --version          # must be 2.50+

# Terraform (Windows)
winget install HashiCorp.Terraform

# Terraform (macOS)
brew install terraform

# Verify
terraform --version   # must be 1.6+

# Docker Desktop
# Download from https://docs.docker.com/get-docker/
docker --version

# Git
git --version

# Python 3.11+
python --version

# Node.js 18+
node --version
```

### Step 2.2 — Log in to Azure

```bash
# Log in to Huron's Azure tenant
az login --tenant <huron-tenant-id>

# Confirm correct subscription
az account list --output table
az account set --subscription "<huron-subscription-id>"

# Verify
az account show --query "{name:name, id:id, tenantId:tenantId}"
```

### Step 2.3 — Register required Azure resource providers

These need to be registered once per subscription. Some may already be registered:

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Cache
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.Insights

# Check registration (repeat for each)
az provider show -n Microsoft.App --query "registrationState"
# Expected: "Registered"
```

### Step 2.4 — Clone the repository

```bash
git clone https://github.com/HuronOrg/Huron_GenAI_Knowledge_Assistant.git
cd "Huron_GenAI_Knowledge_Assistant"

# Confirm you are on the correct branch
git branch        # should show main or develop
git log --oneline -5
```

---

## Phase 3 — Create Terraform State Backend (Do This First)

Before running `terraform apply`, create the Azure Blob Storage container that will
store the Terraform state file. This ensures state is shared across the team and not
lost if your local machine changes.

### Step 3.1 — Create the state storage account manually

```bash
# Variables
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
STATE_RG="huron-tfstate-rg"
STATE_SA="hurontfstate"          # must be globally unique, lowercase, 3-24 chars
STATE_CONTAINER="tfstate"
LOCATION="eastus2"               # use Huron's region

# Create resource group for state
az group create --name $STATE_RG --location $LOCATION

# Create storage account
az storage account create \
  --name $STATE_SA \
  --resource-group $STATE_RG \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2

# Create blob container
az storage container create \
  --name $STATE_CONTAINER \
  --account-name $STATE_SA

echo "State backend ready: $STATE_SA/$STATE_CONTAINER"
```

### Step 3.2 — Uncomment the backend block in `terraform/azure/providers.tf`

Open `terraform/azure/providers.tf` and uncomment the backend block:

```hcl
backend "azurerm" {
  resource_group_name  = "huron-tfstate-rg"
  storage_account_name = "hurontfstate"      # must match what you created above
  container_name       = "tfstate"
  key                  = "huron.terraform.tfstate"
}
```

---

## Phase 4 — Configure Terraform Variables

### Step 4.1 — Create environment-specific tfvars files

Create the directory and files (never commit these):

```bash
mkdir -p terraform/azure/environments
```

**`terraform/azure/environments/dev.tfvars`**

```hcl
location                = "East US 2"
environment             = "dev"
project_name            = "huron"

openai_api_key          = "sk-..."
pinecone_api_key        = "pcsk_..."
pinecone_index          = "huron-enterprise-knowledge"
jwt_secret              = "<32-char-secret>"
mcp_encryption_key      = "<32-char-secret>"

postgres_admin_user     = "huron_admin"
postgres_admin_password = "<strong-password>"
postgres_db_name        = "huron_db"
postgres_sku            = "B_Standard_B1ms"       # ~$12/mo — dev only
postgres_storage_mb     = 32768

backend_cpu             = 0.5
backend_memory          = "1Gi"
frontend_cpu            = 0.25
frontend_memory         = "0.5Gi"
backend_min_replicas    = 1
backend_max_replicas    = 3
jwt_expiration_hours    = 24
```

**`terraform/azure/environments/staging.tfvars`**

```hcl
location                = "East US 2"
environment             = "staging"
project_name            = "huron"

openai_api_key          = "sk-..."
pinecone_api_key        = "pcsk_..."
pinecone_index          = "huron-enterprise-knowledge"
jwt_secret              = "<32-char-secret>"
mcp_encryption_key      = "<32-char-secret>"

postgres_admin_user     = "huron_admin"
postgres_admin_password = "<strong-password>"
postgres_db_name        = "huron_db"
postgres_sku            = "GP_Standard_D2ds_v4"   # ~$70/mo
postgres_storage_mb     = 32768

backend_cpu             = 1.0
backend_memory          = "2Gi"
frontend_cpu            = 0.5
frontend_memory         = "1Gi"
backend_min_replicas    = 1
backend_max_replicas    = 5
jwt_expiration_hours    = 12
```

**`terraform/azure/environments/prod.tfvars`**

```hcl
location                = "East US 2"
environment             = "prod"
project_name            = "huron"

openai_api_key          = "sk-..."
pinecone_api_key        = "pcsk_..."
pinecone_index          = "huron-enterprise-knowledge"
jwt_secret              = "<32-char-secret>"
mcp_encryption_key      = "<32-char-secret>"

postgres_admin_user     = "huron_admin"
postgres_admin_password = "<strong-password>"
postgres_db_name        = "huron_db"
postgres_sku            = "GP_Standard_D4ds_v4"   # ~$140/mo — production
postgres_storage_mb     = 65536

backend_cpu             = 2.0
backend_memory          = "4Gi"
frontend_cpu            = 1.0
frontend_memory         = "2Gi"
backend_min_replicas    = 2
backend_max_replicas    = 10
jwt_expiration_hours    = 8
```

### Step 4.2 — Create `backend/.env` on the Huron machine

```bash
# backend/.env — NEVER commit this file
DATABASE_URL=postgresql://huron_admin:<password>@<postgres-fqdn>:5432/huron_db?sslmode=require
REDIS_URL=rediss://:<redis-key>@<redis-hostname>:6380
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX=huron-enterprise-knowledge
JWT_SECRET=<32-char-secret>
MCP_ENCRYPTION_KEY=<32-char-secret>
APP_ENV=staging

# Sentry (fill after Step 10.1)
SENTRY_DSN=

# LangSmith (fill after Step 10.6)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=huron-genai-staging

# Azure AD SSO (fill after Phase 7)
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
OIDC_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
OIDC_REDIRECT_URI=https://<backend-fqdn>/api/v1/auth/oidc/callback
```

### Step 4.3 — Create `frontend/.env.local` on the Huron machine

```bash
# frontend/.env.local — NEVER commit this file
NEXT_PUBLIC_API_URL=https://<backend-fqdn>

# Sentry frontend (fill after Step 10.1)
NEXT_PUBLIC_SENTRY_DSN=
SENTRY_ORG=huron-consulting
SENTRY_PROJECT=huron-frontend
SENTRY_AUTH_TOKEN=

# PostHog analytics (optional)
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

---

## Phase 5 — Deploy Infrastructure (Staging First)

### Step 5.1 — Initialise Terraform

```bash
cd terraform/azure

terraform init
# Expected: "Terraform has been successfully initialized!"
# If using remote state backend, it will prompt for Azure auth — already logged in.

terraform validate
# Expected: "Success! The configuration is valid."
```

### Step 5.2 — Plan and apply for staging

```bash
terraform plan -var-file="environments/staging.tfvars" -out=staging.tfplan

# Review the plan — expect approximately 25 resources:
# - azurerm_resource_group
# - azurerm_virtual_network + 3 subnets
# - azurerm_container_registry
# - azurerm_log_analytics_workspace
# - azurerm_application_insights
# - azurerm_container_app_environment
# - azurerm_private_dns_zone + link
# - azurerm_postgresql_flexible_server + database + ssl config
# - azurerm_redis_cache
# - azurerm_key_vault + 5 secrets
# - azurerm_storage_account + container
# - azurerm_user_assigned_identity
# - azurerm_key_vault_access_policy
# - azurerm_role_assignment
# - azurerm_container_app (backend + frontend)

terraform apply staging.tfplan
# Takes 10-15 minutes
# PostgreSQL: ~6-8 min
# Redis: ~5-7 min
# Container Apps Environment: ~3-5 min
```

### Step 5.3 — Save the outputs

```bash
terraform output > ../../deployment_outputs_staging.txt
cat deployment_outputs_staging.txt

# Key values you will need:
terraform output -raw frontend_url
terraform output -raw backend_url
terraform output -raw acr_login_server
terraform output -raw resource_group_name
terraform output -raw postgres_fqdn
terraform output -raw redis_hostname
terraform output -raw key_vault_uri
```

---

## Phase 6 — Build and Push Docker Images

### Step 6.1 — Set variables from Terraform outputs

```bash
cd terraform/azure

ACR_SERVER=$(terraform output -raw acr_login_server)
BACKEND_URL=$(terraform output -raw backend_url)
RG_NAME=$(terraform output -raw resource_group_name)

echo "ACR: $ACR_SERVER"
echo "Backend URL: $BACKEND_URL"
echo "Resource Group: $RG_NAME"
```

### Step 6.2 — Authenticate with ACR

```bash
az acr login --name $(echo $ACR_SERVER | cut -d. -f1)
# Expected: Login Succeeded
```

### Step 6.3 — Build and push the backend image

```bash
# From the project root
cd ../..

docker build \
  -f backend/Dockerfile.production \
  -t $ACR_SERVER/huron-backend:latest \
  -t $ACR_SERVER/huron-backend:$(git rev-parse --short HEAD) \
  .

docker push $ACR_SERVER/huron-backend:latest
docker push $ACR_SERVER/huron-backend:$(git rev-parse --short HEAD)

echo "Backend image pushed"
```

### Step 6.4 — Build and push the frontend image

The frontend bakes the backend URL in at build time via a build arg:

```bash
docker build \
  -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  --build-arg BACKEND_URL="$BACKEND_URL" \
  -t $ACR_SERVER/huron-frontend:latest \
  -t $ACR_SERVER/huron-frontend:$(git rev-parse --short HEAD) \
  ./frontend

docker push $ACR_SERVER/huron-frontend:latest
docker push $ACR_SERVER/huron-frontend:$(git rev-parse --short HEAD)

echo "Frontend image pushed"
```

### Step 6.5 — Update Container Apps to pull the new images

```bash
cd terraform/azure

az containerapp update \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-backend:latest

az containerapp update \
  --name huron-staging-frontend \
  --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-frontend:latest

echo "Container Apps updating — takes 2-3 minutes"

# Watch status
az containerapp revision list \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --output table
```

---

## Phase 7 — Set Up Azure AD SSO (Entra ID)

Azure AD SSO is built into the backend (`main.py`) and activates when the OIDC env
vars are set. This step registers the app in your Azure tenant.

### Step 7.1 — Register the app in Microsoft Entra ID

1. **Azure Portal → Microsoft Entra ID → App registrations → New registration**
2. Fill in:
   - **Name:** `Huron GenAI Knowledge Assistant`
   - **Supported account types:** Accounts in this organizational directory only
   - **Redirect URI:** Web → `https://<staging-backend-fqdn>/api/v1/auth/oidc/callback`
3. Click **Register**
4. Copy:
   - **Application (client) ID** → `OIDC_CLIENT_ID`
   - **Directory (tenant) ID** → used in `OIDC_AUTHORITY`

### Step 7.2 — Create a client secret

1. **Certificates & secrets → New client secret**
2. Description: `huron-backend-staging`, Expires: 24 months
3. Copy the **Value** immediately (shown once only) → `OIDC_CLIENT_SECRET`

### Step 7.3 — Configure API permissions

1. **API permissions → Add a permission → Microsoft Graph → Delegated**
2. Add: `openid`, `profile`, `email`, `User.Read`, `GroupMember.Read.All`
3. Click **Grant admin consent for [your org]**

### Step 7.4 — Add groups claim to the ID token

1. In the app registration → **Token configuration → Add groups claim**
2. Select: **Security groups**
3. Include in **ID token**: **Group ID**

### Step 7.5 — Get AD group Object IDs and map them to Huron roles

```bash
# List all AD groups (filter to relevant ones)
az ad group list --filter "startswith(displayName, 'Huron')" \
  --query "[].{Name:displayName, ID:id}" \
  --output table
```

Once you have the Object IDs, log in to the Huron app as `root` and run the mappings
via the API (or insert them into the DB directly):

```sql
INSERT INTO oidc_role_mappings (ad_group, huron_role, dept_code) VALUES
  ('<Huron-KM-Root-ObjectId>',       'root',       NULL),
  ('<Huron-KM-Admins-ObjectId>',     'dept_admin', NULL),
  ('<Huron-KM-PowerUsers-ObjectId>', 'power_user', NULL),
  ('<Huron-KM-Users-ObjectId>',      'user',       NULL),
  ('<Huron-HR-ObjectId>',            'user',       'hr'),
  ('<Huron-Finance-ObjectId>',       'user',       'finance'),
  ('<Huron-Legal-ObjectId>',         'user',       'legal'),
  ('<Huron-Clinical-ObjectId>',      'user',       'clinical');
```

### Step 7.6 — Set OIDC env vars in Container Apps

```bash
cd terraform/azure

az containerapp update \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --set-env-vars \
    OIDC_CLIENT_ID="<your-client-id>" \
    OIDC_CLIENT_SECRET="<your-client-secret>" \
    OIDC_AUTHORITY="https://login.microsoftonline.com/<tenant-id>" \
    OIDC_REDIRECT_URI="https://<staging-backend-fqdn>/api/v1/auth/oidc/callback"
```

### Step 7.7 — Verify SSO

Open a browser and navigate to:
`https://<staging-backend-fqdn>/api/v1/auth/oidc/login`

You should be redirected to the Microsoft login page. After signing in with an AD
account, you should land on `https://<staging-frontend-fqdn>/auth/sso-complete`.

---

## Phase 8 — Set Up GitHub Actions CI/CD for Azure

### Step 8.1 — Create a Service Principal for GitHub Actions

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RG_NAME=$(cd terraform/azure && terraform output -raw resource_group_name)

az ad sp create-for-rbac \
  --name "huron-github-actions" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME \
  --sdk-auth

# This outputs a JSON block — save the entire JSON as a GitHub Secret
```

### Step 8.2 — Grant ACR push access to the Service Principal

```bash
SP_APP_ID=$(az ad sp list --display-name "huron-github-actions" --query "[0].appId" -o tsv)
ACR_ID=$(az acr show --name $(cd terraform/azure && terraform output -raw acr_login_server | cut -d. -f1) --query id -o tsv)

az role assignment create \
  --assignee $SP_APP_ID \
  --role AcrPush \
  --scope $ACR_ID
```

### Step 8.4 — GitHub Actions workflow files (already created)

Three workflow files have been created in `.github/workflows/`:

| File | Trigger | Target |
|------|---------|--------|
| `deploy-azure-dev.yml` | Push to `develop` (after CI passes) | `huron-dev-*` Container Apps |
| `deploy-azure-staging.yml` | Push to `staging` (after CI passes) | `huron-staging-*` Container Apps, requires `staging` environment approval |
| `deploy-azure-prod.yml` | Manual only — must type `DEPLOY` to confirm | `huron-prod-*` Container Apps, Blue/Green with canary traffic splitting, requires `production` environment approval |

**Production workflow behaviour:**
1. Builds and pushes image tagged `prod-<sha>`
2. Deploys new revision with **0% traffic** (old revision stays live — blue)
3. Shifts **10% canary traffic** to new revision
4. Runs health check during canary period
5. Holds for the selected canary duration (5 / 10 / 15 minutes, or skip)
6. If healthy → shifts **100%** to new revision (green cutover)
7. Old revision deactivated automatically

**Rollback:** Re-run `deploy-azure-prod.yml` via `workflow_dispatch` pointing to the previous commit SHA — Container Apps keeps all revisions available.

### Step 8.5 — Add GitHub Secrets and Variables

In GitHub → Repository → **Settings → Secrets and Variables → Actions**, add:

**Secrets** (sensitive — never visible after saving):

```
AZURE_CREDENTIALS_DEV       → Service Principal JSON for dev (from Step 8.1)
AZURE_CREDENTIALS_STAGING   → Service Principal JSON for staging
AZURE_CREDENTIALS_PROD      → Service Principal JSON for prod (separate SP recommended)
AZURE_DEV_DATABASE_URL      → postgresql://huron_admin:<pw>@<dev-postgres-fqdn>:5432/huron_db?sslmode=require
AZURE_STAGING_DATABASE_URL  → postgresql://huron_admin:<pw>@<staging-postgres-fqdn>:5432/huron_db?sslmode=require
```

**Variables** (non-sensitive — visible in logs):

```
AZURE_ACR_SERVER              → huronacr<suffix>.azurecr.io   (same ACR for all envs)
AZURE_DEV_RESOURCE_GROUP      → huron-dev-rg
AZURE_STAGING_RESOURCE_GROUP  → huron-staging-rg
AZURE_PROD_RESOURCE_GROUP     → huron-prod-rg
AZURE_DEV_BACKEND_URL         → https://<dev-backend-fqdn>
AZURE_STAGING_BACKEND_URL     → https://<staging-backend-fqdn>
AZURE_PROD_BACKEND_URL        → https://<prod-backend-fqdn>
```

### Step 8.6 — Configure GitHub Environments with protection rules

In GitHub → Repository → **Settings → Environments**:

**`staging` environment:**
- Required reviewers: 0 (auto-deploy on branch push)
- No wait timer needed

**`production` environment:**
- Required reviewers: add at least 1 reviewer (e.g. tech lead)
- Wait timer: 5 minutes (gives time to cancel)
- Allowed branches: `main` only

---

## Phase 9 — Verify Staging Deployment

### Step 9.1 — Health check

```bash
BACKEND_URL=$(cd terraform/azure && terraform output -raw backend_url)

curl -s $BACKEND_URL/health | python -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "service": "huron-genai-backend",
#   "version": "4.0.0",
#   "checks": {
#     "database": {"status": "ok", "latency_ms": ...},
#     "pinecone":  {"status": "ok", "latency_ms": ...}
#   }
# }
```

### Step 9.2 — Check Container App revisions

```bash
RG_NAME=$(cd terraform/azure && terraform output -raw resource_group_name)

az containerapp revision list \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --output table

# Expected: latest revision shows Active: True, Traffic: 100
```

### Step 9.3 — Check application logs

```bash
# Live log stream (Ctrl+C to stop)
az containerapp logs show \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --follow

# Last 100 lines
az containerapp logs show \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --tail 100
```

### Step 9.4 — Staging verification checklist

- [ ] `terraform apply` exits 0 with no errors
- [ ] Resource group `huron-staging-rg` visible in Azure Portal
- [ ] PostgreSQL Flexible Server status: `Ready`
- [ ] Azure Cache for Redis status: `Running`
- [ ] ACR repositories contain `huron-backend` and `huron-frontend` images
- [ ] Container App `huron-staging-backend` latest revision: `Running`
- [ ] Container App `huron-staging-frontend` latest revision: `Running`
- [ ] `/health` returns `{"status":"healthy"}` with database and pinecone `ok`
- [ ] Can log in at the frontend URL (username: `root`, password: `HuronRoot2026!`)
- [ ] **Change the root password immediately after first login**
- [ ] Departments page shows 9 departments (including `company`)
- [ ] Dashboard shows real data
- [ ] Azure AD SSO login redirects correctly to Microsoft
- [ ] After SSO login, user is auto-provisioned with correct role

---

## Phase 9.5 — Duo MFA / SSO-Only Login Enforcement

> **Context:** Huron uses Duo Security as the MFA provider inside Azure AD (Entra ID).
> Duo Push fires on the user's phone automatically during the Microsoft login page flow —
> before Microsoft issues the OIDC token. No Duo SDK integration is needed in the app.
> This phase documents the code changes already made and the Azure-specific actions
> required to activate and verify them.

### What Changed in the Code

These changes are already committed. They deploy automatically when the GitHub Actions
pipeline runs after merge to `staging` or `main`.

#### Change 1 — `backend/core/database.py`

`auth_method` added to `get_user_by_login` SELECT:

```python
# Before
"SELECT id,username,email,full_name,password_hash,role,department,is_active "

# After
"SELECT id,username,email,full_name,password_hash,role,department,is_active,auth_method "
```

Without this, the enforcement check had no value to read.

#### Change 2 — `backend/routes/auth.py`

Environment-gated block inserted at the top of `POST /api/v1/auth/login`,
**before** the bcrypt password check:

```python
_SSO_ENFORCED_ENVS = {"staging", "production", "prod"}
_APP_ENV = os.getenv("APP_ENV", "dev").lower()

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

**Behaviour per environment:**

| `APP_ENV` | SSO user tries local login | Local-only user | `root` |
|-----------|---------------------------|-----------------|--------|
| `dev` | ✅ Allowed (dev convenience) | ✅ Allowed | ✅ Allowed |
| `staging` | ❌ 403 — redirected to SSO | ✅ Allowed | ✅ Allowed |
| `production` | ❌ 403 — redirected to SSO | ✅ Allowed | ✅ Allowed |

---

### Actions Required on Azure

#### Step 9.5.1 — Confirm `APP_ENV` is set correctly in Container Apps

The enforcement only fires when `APP_ENV` is `staging` or `production`.
Terraform sets this automatically via the `environment` variable in your `tfvars` file,
but verify it is correct on the running container:

```bash
RG_NAME=$(cd terraform/azure && terraform output -raw resource_group_name)

# Check current env vars on the backend Container App
az containerapp show \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --query "properties.template.containers[0].env[?name=='APP_ENV']"

# Expected output:
# [{"name": "APP_ENV", "value": "staging"}]

# If missing or wrong, set it:
az containerapp update \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --set-env-vars APP_ENV=staging
```

Repeat for production replacing `staging` with `prod` and `huron-prod-backend`.

#### Step 9.5.2 — Confirm OIDC env vars are set in the Container App

The SSO block only triggers for users with `auth_method = 'oidc'` — that value is
written during the OIDC callback, which requires these four env vars to be set:

```bash
# Verify all OIDC vars are present on staging backend
az containerapp show \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --query "properties.template.containers[0].env[?starts_with(name,'OIDC')]"
```

Required variables (from Phase 7 of this guide):

```
OIDC_CLIENT_ID       = <Azure AD application client ID>
OIDC_CLIENT_SECRET   = <Azure AD client secret value>
OIDC_AUTHORITY       = https://login.microsoftonline.com/<tenant-id>
OIDC_REDIRECT_URI    = https://<staging-backend-fqdn>/api/v1/auth/oidc/callback
```

> **Note — `OIDC_REDIRECT_URI` must be updated when moving from AWS to Azure.**
> The domain changes from the AWS ALB hostname to the Azure Container Apps FQDN.
> Update the redirect URI in both:
> 1. The env var on the Container App (above)
> 2. The Azure AD app registration → Authentication → Redirect URIs

#### Step 9.5.3 — Verify Conditional Access policy targets this app

Duo fires inside Microsoft's login page via Azure AD Conditional Access.
This is cloud-agnostic — it works the same whether the app is hosted on AWS or Azure.

1. **Azure Portal → Microsoft Entra ID → Security → Conditional Access → Policies**
2. Find the policy covering the `Huron GenAI Knowledge Assistant` app registration
3. Confirm **Grant: Require multi-factor authentication**
4. Confirm **Policy status: On** — not Report-only

If no such policy exists, see `DUO_MFA_INTEGRATION.md` → "Azure AD Conditional Access"
for step-by-step creation instructions.

#### Step 9.5.4 — Test SSO enforcement end-to-end on staging

```bash
BACKEND_URL=$(cd terraform/azure && terraform output -raw backend_url)
FRONTEND_URL=$(cd terraform/azure && terraform output -raw frontend_url)

# ── Step 1: Login via SSO (open in browser) ──────────────────────────────────
echo "SSO login URL: $BACKEND_URL/api/v1/auth/oidc/login"
# Open in browser → Microsoft login page appears
# Duo Push fires on your phone → tap Approve
# You land on $FRONTEND_URL/auth/sso-complete → redirected to dashboard

# ── Step 2: Confirm auth_method = 'oidc' was written (query the DB) ──────────
# Connect to staging PostgreSQL and run:
# SELECT username, email, auth_method FROM users WHERE email = '<your-company-email>';
# Expected: auth_method = oidc

# ── Step 3: Try to use that same account via local password login ─────────────
curl -s -X POST $BACKEND_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<your-username>","password":"<any-password>"}' | python -m json.tool

# Expected:
# HTTP 403
# {"detail": "This account uses company SSO. Please sign in with Microsoft."}

# ── Step 4: Confirm audit log entry ──────────────────────────────────────────
# SELECT action, username, created_at
# FROM audit_log
# WHERE action = 'local_login_blocked_sso_required'
# ORDER BY created_at DESC LIMIT 5;
```

#### Step 9.5.5 — Update the OIDC redirect URI in the Azure AD app registration

When you move from AWS (ALB domain) to Azure (Container Apps FQDN), the callback
URL changes. Both environments can be registered simultaneously as redirect URIs
during the transition period:

1. **Azure Portal → Microsoft Entra ID → App registrations →
   Huron GenAI Knowledge Assistant → Authentication**
2. Under **Redirect URIs**, confirm both are present:
   ```
   https://<aws-staging-alb-domain>/api/v1/auth/oidc/callback    ← AWS (remove after cutover)
   https://<azure-staging-backend-fqdn>/api/v1/auth/oidc/callback ← Azure (add now)
   ```
3. Save
4. After full Azure cutover, remove the AWS URI

---

### What Does NOT Need to Change for Azure Specifically

| Item | Reason |
|------|--------|
| Terraform `terraform/azure/main.tf` | No infrastructure changes — code-only fix |
| Container Apps environment definition | `APP_ENV` injected from `tfvars` `environment` variable |
| Azure Key Vault secrets | No new secrets — uses existing OIDC secrets from Phase 7 |
| ACR images | Same Docker image — the logic is in Python, not the Dockerfile |
| GitHub Actions workflows | Deploy pipelines pick up the committed code change automatically |
| PostgreSQL schema | `auth_method` column already exists in the `users` table migration |

---

## Phase 10 — Observability & Monitoring (Staging First, Then Production)

All items must pass on staging before deploying to production.
Azure has Application Insights built in — this phase activates it and adds the
remaining tools from the observability stack.

### Step 10.1 — Sentry (Error Tracking)

The Sentry SDK is already integrated in both backend and frontend. The code is
written — only the DSN env vars are missing.

**Create Sentry projects:**
1. Go to **https://sentry.io** → sign up → create organisation `huron-consulting`
2. **Create Project → Python → FastAPI** → name: `huron-backend` → copy DSN
3. **Create Project → JavaScript → Next.js** → name: `huron-frontend` → copy DSN
4. **Settings → Auth Tokens → Create New Token** → scopes: `project:releases` + `org:read`

**Set env vars in Container App:**

```bash
az containerapp update \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --set-env-vars \
    SENTRY_DSN="https://abc123@o000000.ingest.sentry.io/0000000" \
    APP_ENV="staging"
```

Set `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_AUTH_TOKEN`
in `frontend/.env.local` and rebuild the frontend image (Step 6.3–6.5).

**Install packages** (already in requirements if using pip):

```bash
pip install "sentry-sdk[fastapi]"    # backend
npm install @sentry/nextjs           # frontend
```

**Verify:** Send a test request then check **sentry.io → huron-backend → Issues**,
filtering by environment `staging`. Event should appear within 30 seconds.

### Step 10.2 — Application Insights (Built-in Azure Monitoring)

Application Insights is already provisioned by Terraform and the connection string is
already injected into the backend Container App via `APPLICATIONINSIGHTS_CONNECTION_STRING`.

**Install the SDK:**

```bash
pip install opencensus-ext-azure    # or: pip install azure-monitor-opentelemetry
```

**View logs and metrics:**

1. Azure Portal → Resource Group `huron-staging-rg` → `huron-staging-appinsights`
2. **Live Metrics** — real-time request rate, failure rate, response time
3. **Failures** — exceptions grouped by type
4. **Performance** — P50/P95/P99 response times per endpoint
5. **Logs → Traces** — structured log output from the backend

**Useful KQL queries in Log Analytics:**

```kql
// All backend errors in the last hour
ContainerAppConsoleLogs_CL
| where ContainerName_s == "backend"
| where Log_s contains "ERROR"
| project TimeGenerated, Log_s
| order by TimeGenerated desc

// Request latency by endpoint
requests
| summarize avg(duration), percentile(duration, 95) by name
| order by avg_duration desc
```

### Step 10.3 — Better Stack (External Uptime Monitoring)

No code changes required. All configuration is in the Better Stack dashboard.

1. Go to **https://betterstack.com** → sign up → open **Uptime** section
2. **New monitor → HTTP**
   - URL: `https://<staging-backend-fqdn>/health`
   - Name: `Huron Backend — Staging`
   - Check frequency: `30 seconds`
   - Expected status: `200`
   - Regions: **US East** + **EU West**
   - Recovery confirmation: `2 consecutive successes`
3. **New monitor → HTTP**
   - URL: `https://<staging-frontend-fqdn>`
   - Name: `Huron Frontend — Staging`
   - Expected status: `200`
4. **New monitor → HTTP**
   - URL: `https://api.pinecone.io`
   - Name: `Pinecone Reachability`
   - Expected status: `401`

**Configure alerting:**
1. **On-call → Alert policies → New alert policy** → name: `Huron Staging`
2. Escalations: Email immediately → SMS after 5 minutes
3. Attach policy to each monitor

> After production deploy, duplicate the policy as `Huron Production` and create
> matching production monitors.

### Step 10.4 — Azure Monitor Alerts (equivalent to CloudWatch SNS)

```bash
# Create an action group for email alerts
az monitor action-group create \
  --name "huron-ops-alerts" \
  --resource-group $RG_NAME \
  --short-name "huron-ops" \
  --action email ops-email ops@huron-vaultmind.ai

# Get the action group ID
ACTION_GROUP_ID=$(az monitor action-group show \
  --name "huron-ops-alerts" \
  --resource-group $RG_NAME \
  --query id -o tsv)

# Alert: backend Container App has 0 running replicas
az monitor metrics alert create \
  --name "huron-staging-backend-down" \
  --resource-group $RG_NAME \
  --scopes $(az containerapp show \
    --name huron-staging-backend \
    --resource-group $RG_NAME --query id -o tsv) \
  --condition "avg Replicas < 1" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 0 \
  --action $ACTION_GROUP_ID \
  --description "Backend has no running replicas"

# Alert: PostgreSQL CPU above 80%
az monitor metrics alert create \
  --name "huron-staging-postgres-cpu-high" \
  --resource-group $RG_NAME \
  --scopes $(az postgres flexible-server show \
    --name huron-staging-postgres-* \
    --resource-group $RG_NAME --query id -o tsv) \
  --condition "avg cpu_percent > 80" \
  --window-size 10m \
  --evaluation-frequency 5m \
  --severity 2 \
  --action $ACTION_GROUP_ID
```

### Step 10.5 — Deep Health Check

Replace the shallow `/health` endpoint with one that checks DB and Pinecone.
See `MIGRATION_TO_HURON.md` Step 9.4 for the full replacement code for
`backend/routes/health.py`. After updating, rebuild and push the backend image
(Phase 6, Steps 6.3 and 6.5).

**Verify:**

```bash
curl -s https://<staging-backend-fqdn>/health | python -m json.tool

# Expected when healthy:
# {
#   "status": "healthy",
#   "checks": {
#     "database": {"status": "ok", "latency_ms": 3},
#     "pinecone":  {"status": "ok", "latency_ms": 45}
#   }
# }
```

**Do not deploy to production until this returns 200 on staging.**

### Step 10.6 — LangSmith (Full LLM Chain Tracing)

LangSmith captures every step of the RAG pipeline: embed → Pinecone → LLM →
faithfulness score. This is the only tool that tells you exactly why a query
returned a bad answer.

**Create LangSmith account:**
1. Go to **https://smith.langchain.com** → sign up
2. Create projects: `huron-genai-staging` and `huron-genai-production`
3. **Settings → API Keys → Create API Key** → copy the key

**Set env vars in Container App:**

```bash
az containerapp update \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --set-env-vars \
    LANGCHAIN_TRACING_V2="true" \
    LANGCHAIN_ENDPOINT="https://api.smith.langchain.com" \
    LANGCHAIN_API_KEY="ls__your_key_here" \
    LANGCHAIN_PROJECT="huron-genai-staging"
```

**Install package:**

```bash
pip install langsmith
```

**Add `@traceable` decorators to `backend/main.py`** — see `MIGRATION_TO_HURON.md`
Steps 9.6.4 and 9.6.5 for the exact code changes.

**Verify:** Send a query to staging then open
**https://smith.langchain.com → huron-genai-staging → Traces**. Within 10 seconds
you should see a linked trace with embed + Pinecone + LLM steps.

---

## Phase 11 — Deploy to Production

Only proceed once every item in the Phase 9 and Phase 10 staging checklists is checked.

### Step 11.1 — Apply Terraform to production

```bash
cd terraform/azure

terraform plan -var-file="environments/prod.tfvars" -out=prod.tfplan
terraform apply prod.tfplan

terraform output > ../../deployment_outputs_prod.txt
```

### Step 11.2 — Build and push production-tagged images

```bash
ACR_SERVER=$(terraform output -raw acr_login_server)
BACKEND_URL=$(terraform output -raw backend_url)
RG_NAME=$(terraform output -raw resource_group_name)

az acr login --name $(echo $ACR_SERVER | cut -d. -f1)

docker build -f backend/Dockerfile.production \
  -t $ACR_SERVER/huron-backend:prod-$(git rev-parse --short HEAD) \
  .
docker push $ACR_SERVER/huron-backend:prod-$(git rev-parse --short HEAD)

docker build -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  -t $ACR_SERVER/huron-frontend:prod-$(git rev-parse --short HEAD) \
  ./frontend
docker push $ACR_SERVER/huron-frontend:prod-$(git rev-parse --short HEAD)
```

### Step 11.3 — Update production Container Apps

```bash
az containerapp update \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-backend:prod-$(git rev-parse --short HEAD)

az containerapp update \
  --name huron-prod-frontend \
  --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-frontend:prod-$(git rev-parse --short HEAD)
```

### Step 11.4 — Update observability env vars to production values

```bash
az containerapp update \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --set-env-vars \
    APP_ENV="production" \
    SENTRY_DSN="<production-sentry-dsn>" \
    LANGCHAIN_PROJECT="huron-genai-production" \
    OIDC_REDIRECT_URI="https://<prod-backend-fqdn>/api/v1/auth/oidc/callback"
```

### Step 11.5 — Enable remote Terraform state for prod (if not already done)

The state backend in `providers.tf` uses a single key. For multi-environment isolation,
use separate keys per environment:

```hcl
# For prod, use key = "huron-prod.terraform.tfstate"
# For staging, use key = "huron-staging.terraform.tfstate"
```

---

## Phase 12 — Production Verification

```bash
PROD_BACKEND=$(cd terraform/azure && terraform output -raw backend_url)

# Health check
curl -s $PROD_BACKEND/health | python -m json.tool

# API docs
echo "Swagger UI: $PROD_BACKEND/docs"

# Check revision status
az containerapp revision list \
  --name huron-prod-backend \
  --resource-group $(cd terraform/azure && terraform output -raw resource_group_name) \
  --output table
```

---

## Phase 13 — Clean Up Personal Resources

Only proceed after all production verification items are green.

```bash
# Archive personal GitHub repo (do this in GitHub UI)
# Settings → Danger Zone → Archive this repository

# Destroy personal AWS infrastructure (if applicable)
# cd terraform/aws
# terraform destroy

# Remove personal Azure resources if any test deployments were made
# cd terraform/azure
# terraform workspace select dev
# terraform destroy -var-file="environments/dev.tfvars"
```

---

## Summary of Files That Change Per Environment

| File | What changes | When |
|------|-------------|------|
| `terraform/azure/environments/*.tfvars` | All Azure-specific values | Created fresh on Huron machine |
| `backend/.env` | API keys, DB URL, secrets | Created fresh on Huron machine |
| `frontend/.env.local` | Backend API URL, Sentry keys | Created fresh on Huron machine |
| `terraform/azure/providers.tf` | Remote state backend (uncomment) | Once, before first `terraform init` |
| `.github/workflows/deploy-azure-*.yml` | ACR server, resource group names, env vars | After Step 8.4 |
| `backend/core/database.py` | `auth_method` added to login SELECT | Already committed — auto-deploys |
| `backend/routes/auth.py` | SSO-only enforcement block + `APP_ENV` gate | Already committed — auto-deploys |

---

## Duo MFA Deployment Checklist (Phase 9.5)

Complete this after Phase 9 staging verification and before Phase 10 observability.

- [ ] `APP_ENV=staging` confirmed on `huron-staging-backend` Container App
- [ ] `APP_ENV=prod` confirmed on `huron-prod-backend` Container App
- [ ] OIDC env vars confirmed on staging Container App (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_AUTHORITY`, `OIDC_REDIRECT_URI`)
- [ ] `OIDC_REDIRECT_URI` updated to Azure Container Apps FQDN (not AWS ALB domain)
- [ ] Azure AD app registration has **both** AWS and Azure redirect URIs during transition
- [ ] SSO login via `/api/v1/auth/oidc/login` completes — Duo Push fires on phone
- [ ] `auth_method = 'oidc'` written to staging DB after first SSO login
- [ ] Local password login for SSO user returns **HTTP 403** on staging
- [ ] `local_login_blocked_sso_required` event visible in `audit_log` table
- [ ] Azure AD Conditional Access policy status: **On** (not Report-only)
- [ ] Root account local login still works (emergency access verified)
- [ ] After full Azure cutover — AWS redirect URI removed from app registration

---

## Azure vs AWS — Operational Differences

| Task | AWS command | Azure command |
|------|-------------|---------------|
| View logs | `aws ecs execute-command ...` | `az containerapp logs show --follow` |
| Restart service | Redeploy ECS task | `az containerapp revision restart` |
| Scale replicas | Update ECS service desired count | `az containerapp update --min-replicas` |
| View metrics | CloudWatch Console | Azure Portal → Application Insights |
| Rotate a secret | AWS Secrets Manager | `az keyvault secret set --vault-name ... --name ... --value ...` |
| Push a new image | `docker push <ecr-url>/<image>` | `docker push <acr-server>/<image>` then `az containerapp update` |
| Check DB | RDS Console | Azure Portal → PostgreSQL Flexible Server |

---

## Cost Estimates

### Staging

| Resource | Monthly estimate |
|----------|-----------------|
| PostgreSQL Flexible Server `GP_Standard_D2ds_v4` | ~$70 |
| Container Apps (backend + frontend, low traffic) | ~$15–25 |
| Azure Cache for Redis Standard C1 | ~$25 |
| Azure Container Registry Standard | ~$5 |
| Log Analytics (30-day retention) | ~$5–10 |
| Storage Account | ~$1 |
| Key Vault | ~$0 (free tier) |
| Application Insights | ~$5 |
| **Staging total** | **~$126–141/month** |

### Production

| Resource | Monthly estimate |
|----------|-----------------|
| PostgreSQL Flexible Server `GP_Standard_D4ds_v4` | ~$140 |
| Container Apps (2–10 replicas, normal traffic) | ~$50–100 |
| Azure Cache for Redis Standard C1 | ~$45–55 |
| Azure Container Registry Standard | ~$5 |
| Log Analytics | ~$10–20 |
| Storage Account | ~$2–5 |
| Key Vault | ~$1–3 |
| Application Insights | ~$10–20 |
| **Production total** | **~$263–348/month** |

---

## Troubleshooting

### Container App not starting

```bash
# Check revision status
az containerapp revision list \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --output table

# Check for errors in startup logs
az containerapp logs show \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --tail 100

# Common causes:
# - Image pull error     → re-run az acr login and docker push
# - Health probe failing → verify /health endpoint responds before probe fires
# - Secret not found     → verify Key Vault access policy for managed identity
# - DB connection refused → PostgreSQL subnet delegation or private DNS misconfigured
```

### Database connection refused

```bash
# Verify PostgreSQL FQDN
POSTGRES_FQDN=$(cd terraform/azure && terraform output -raw postgres_fqdn)
echo $POSTGRES_FQDN

# Check firewall / VNet integration
az postgres flexible-server show \
  --name huron-staging-postgres-* \
  --resource-group $RG_NAME \
  --query "network"

# Private DNS zone must be linked to VNet
az network private-dns zone list \
  --resource-group $RG_NAME \
  --output table
```

### Redis connection refused

The Redis URL must use `rediss://` (TLS, port 6380) — not `redis://` (port 6379):

```bash
REDIS_HOST=$(cd terraform/azure && terraform output -raw redis_hostname)
echo "Redis: $REDIS_HOST:6380"

# Test connectivity from inside the container
az containerapp exec \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --command "/bin/sh -c 'nc -zv $REDIS_HOST 6380'"
```

### Key Vault access denied

```bash
# Verify managed identity has access policy
az keyvault show \
  --name $(cd terraform/azure && terraform output -raw key_vault_uri | sed 's|https://||' | sed 's|.vault.azure.net/||') \
  --query "properties.accessPolicies"
```

### Terraform state conflict

If two people run `terraform apply` simultaneously, the state lock will block one:

```bash
# List existing state locks
az storage blob lease show \
  --account-name hurontfstate \
  --container-name tfstate \
  --name huron.terraform.tfstate

# Force-break a lock (only if the other process is dead)
terraform force-unlock <lock-id>
```

---

## Quick Reference Commands

```bash
# ── Variables (set once per session) ─────────────────────────────────────────
RG_NAME=$(cd terraform/azure && terraform output -raw resource_group_name)
ACR_SERVER=$(cd terraform/azure && terraform output -raw acr_login_server)
BACKEND_URL=$(cd terraform/azure && terraform output -raw backend_url)
FRONTEND_URL=$(cd terraform/azure && terraform output -raw frontend_url)

# ── Health ────────────────────────────────────────────────────────────────────
curl -s $BACKEND_URL/health | python -m json.tool

# ── Logs ─────────────────────────────────────────────────────────────────────
az containerapp logs show --name huron-staging-backend --resource-group $RG_NAME --follow

# ── Restart ───────────────────────────────────────────────────────────────────
az containerapp revision restart \
  --name huron-staging-backend \
  --resource-group $RG_NAME \
  --revision $(az containerapp revision list \
    --name huron-staging-backend --resource-group $RG_NAME \
    --query "[0].name" -o tsv)

# ── Scale ─────────────────────────────────────────────────────────────────────
az containerapp update --name huron-staging-backend --resource-group $RG_NAME \
  --min-replicas 2 --max-replicas 10

# ── List all resources ────────────────────────────────────────────────────────
az resource list --resource-group $RG_NAME --output table

# ── Rotate a secret ───────────────────────────────────────────────────────────
KV_NAME=$(cd terraform/azure && terraform output -raw key_vault_uri | sed 's|https://||' | sed 's|.vault.azure.net/||')
az keyvault secret set --vault-name $KV_NAME --name "openai-api-key" --value "sk-new-key"

# ── Push new backend image ────────────────────────────────────────────────────
az acr login --name $(echo $ACR_SERVER | cut -d. -f1)
docker build -f backend/Dockerfile.production -t $ACR_SERVER/huron-backend:latest .
docker push $ACR_SERVER/huron-backend:latest
az containerapp update --name huron-staging-backend --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-backend:latest

# ── Destroy (danger) ──────────────────────────────────────────────────────────
# cd terraform/azure
# terraform destroy -var-file="environments/staging.tfvars"
```

---

*Last updated: 2026-06-08*
