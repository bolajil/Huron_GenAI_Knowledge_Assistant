# Azure Deployment Guide — CLI Step-by-Step

> **Huron GenAI Knowledge Assistant**  
> Container Apps · PostgreSQL Flexible Server · Azure Cache for Redis · Key Vault

---

## Prerequisites

### Required Tools
```bash
# Install Azure CLI
# Windows (PowerShell as Admin)
winget install Microsoft.AzureCLI

# macOS
brew install azure-cli

# Verify installation
az --version
# azure-cli 2.x.x

# Install Terraform
# Windows (Chocolatey)
choco install terraform

# macOS
brew install terraform

# Verify
terraform --version

# Install Docker
# https://docs.docker.com/get-docker/
docker --version
```

### Azure Account Setup
```bash
# Login to Azure
az login

# If you have multiple subscriptions, set the active one
az account list --output table
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify
az account show --query "{Name:name, ID:id, IsDefault:isDefault}"

# Register required providers (if not already)
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Cache
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.OperationalInsights

# Check registration status
az provider show -n Microsoft.App --query "registrationState"
```

### Required API Keys
- **OpenAI API Key** — `sk-...` (GPT-4o + embeddings)
- **Pinecone API Key** — `pcsk_...`
- **JWT Secret** — Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **Database Password** — Strong password for PostgreSQL

---

## Step 1: Clone & Configure

```bash
# Clone repository
git clone https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git
cd Huron_GenAI_Knowledge_Assistant

# Navigate to Terraform Azure directory
cd terraform/azure
```

---

## Step 2: Create Variables File

```bash
# Create terraform.tfvars (NEVER commit this file)
cat > terraform.tfvars << 'EOF'
# ── Required ──────────────────────────────────────────────────────────────────
subscription_id = "YOUR_AZURE_SUBSCRIPTION_ID"
location        = "eastus"
environment     = "prod"
project_name    = "huron"

# ── API Keys ──────────────────────────────────────────────────────────────────
openai_api_key     = "sk-YOUR_OPENAI_API_KEY"
pinecone_api_key   = "pcsk_YOUR_PINECONE_API_KEY"
jwt_secret         = "YOUR_GENERATED_JWT_SECRET_MIN_32_CHARS"
mcp_encryption_key = "YOUR_MCP_ENCRYPTION_KEY"

# ── Database ──────────────────────────────────────────────────────────────────
db_username = "huron_admin"
db_password = "YourStrongDBPassword123!"

# ── Container Resources ───────────────────────────────────────────────────────
backend_cpu    = 2.0   # vCPU cores
backend_memory = "4Gi"
frontend_cpu   = 0.5
frontend_memory = "1Gi"

# ── Scaling ───────────────────────────────────────────────────────────────────
backend_min_replicas  = 1
backend_max_replicas  = 5
frontend_min_replicas = 1
frontend_max_replicas = 3

# ── Optional ──────────────────────────────────────────────────────────────────
# custom_domain = "huron.example.com"
# sentry_dsn    = "https://xxx@xxx.ingest.sentry.io/xxx"
EOF

echo "✅ Created terraform.tfvars"
```

---

## Step 3: Initialize Terraform

```bash
# Initialize Terraform with Azure provider
terraform init

# Expected output:
# Terraform has been successfully initialized!
```

---

## Step 4: Review Deployment Plan

```bash
# Preview what will be created
terraform plan -out=tfplan

# Resources created:
# - Resource Group
# - Virtual Network with 3 subnets
# - Azure Container Registry (ACR)
# - Container Apps Environment
# - Container Apps (backend + frontend)
# - PostgreSQL Flexible Server
# - Azure Cache for Redis
# - Azure Key Vault
# - Log Analytics Workspace
# - Application Insights

# Estimated cost: ~$150-300/month
```

---

## Step 5: Deploy Infrastructure

```bash
# Apply the plan
terraform apply tfplan

# This takes 10-15 minutes
# - PostgreSQL: ~6-8 min
# - Redis: ~5-7 min
# - Container Apps Environment: ~3-5 min

# Save the outputs
terraform output > deployment_outputs.txt
```

---

## Step 6: Build & Push Docker Images

```bash
# Login to Azure Container Registry
az acr login --name $(terraform output -raw acr_login_server | cut -d'.' -f1)

# Navigate to project root
cd ../..

# Build backend image
docker build -f Dockerfile.production -t huron-backend:latest .

# Tag for ACR
ACR_SERVER=$(cd terraform/azure && terraform output -raw acr_login_server)
docker tag huron-backend:latest $ACR_SERVER/huron-backend:latest

# Push backend
docker push $ACR_SERVER/huron-backend:latest

echo "✅ Backend image pushed"

# Build frontend image
cd frontend
BACKEND_URL=$(cd ../terraform/azure && terraform output -raw backend_url)
docker build -f Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  -t huron-frontend:latest .

# Tag for ACR
docker tag huron-frontend:latest $ACR_SERVER/huron-frontend:latest

# Push frontend
docker push $ACR_SERVER/huron-frontend:latest

echo "✅ Frontend image pushed"
cd ..
```

---

## Step 7: Update Container Apps with Images

```bash
cd terraform/azure

# Get resource names
RG_NAME=$(terraform output -raw resource_group_name)
ACR_SERVER=$(terraform output -raw acr_login_server)

# Update backend container app
az containerapp update \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-backend:latest

# Update frontend container app
az containerapp update \
  --name huron-prod-frontend \
  --resource-group $RG_NAME \
  --image $ACR_SERVER/huron-frontend:latest

echo "⏳ Container Apps updating... (2-3 minutes)"
```

---

## Step 8: Verify Deployment

```bash
# Check backend revision status
az containerapp revision list \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --output table

# Test health endpoint
BACKEND_FQDN=$(terraform output -raw backend_url)
curl -f "$BACKEND_FQDN/health"
# Expected: {"status":"healthy","service":"huron-genai-backend","version":"4.0.0"}

# Get application URLs
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  🚀 DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Frontend:  $(terraform output -raw frontend_url)"
echo "  API Docs:  $(terraform output -raw api_docs_url)"
echo "  Backend:   $(terraform output -raw backend_url)"
echo ""
echo "  Default Login:"
echo "    Username: root"
echo "    Password: HuronRoot2026!"
echo ""
echo "  ⚠️  CHANGE THE ROOT PASSWORD IMMEDIATELY!"
echo "═══════════════════════════════════════════════════════════════"
```

---

## Step 9: Add Secrets to Key Vault

```bash
# Get Key Vault name
KV_URI=$(terraform output -raw key_vault_uri)
KV_NAME=$(echo $KV_URI | sed 's|https://||' | sed 's|.vault.azure.net/||')

# Store secrets (already done by Terraform, but useful for updates)
az keyvault secret set --vault-name $KV_NAME --name "openai-api-key" --value "sk-YOUR_KEY"
az keyvault secret set --vault-name $KV_NAME --name "pinecone-api-key" --value "pcsk_YOUR_KEY"
az keyvault secret set --vault-name $KV_NAME --name "jwt-secret" --value "YOUR_JWT_SECRET"
```

---

## Step 10: Set Up Pinecone Index (First Time Only)

```python
# Run this Python script once
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="YOUR_PINECONE_API_KEY")
pc.create_index(
    name="huron-enterprise-knowledge",
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(cloud="azure", region="eastus"),
)
print("✅ Pinecone index created")
```

---

## Monitoring & Logs

```bash
# View backend logs (real-time)
az containerapp logs show \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --follow

# View frontend logs
az containerapp logs show \
  --name huron-prod-frontend \
  --resource-group $RG_NAME \
  --follow

# View in Azure Portal:
# Application Insights → Live Metrics
# Log Analytics → Logs → ContainerAppConsoleLogs_CL
```

### Application Insights Query
```bash
# Open Log Analytics in browser
az monitor app-insights show \
  --resource-group $RG_NAME \
  --app huron-prod-appinsights \
  --query "id" -o tsv | xargs -I{} echo "https://portal.azure.com/#blade/AppInsightsExtension/OverviewBlade/resourceId/{}"
```

---

## Scaling

### Manual Scaling
```bash
# Scale backend to 3 replicas
az containerapp update \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --min-replicas 3 \
  --max-replicas 10

# Scale frontend
az containerapp update \
  --name huron-prod-frontend \
  --resource-group $RG_NAME \
  --min-replicas 2 \
  --max-replicas 5
```

### Auto-Scaling (HTTP-based)
```bash
# Already configured in Terraform with HTTP concurrent requests scaling
# Backend scales at 100 concurrent requests per replica
# Frontend scales at 50 concurrent requests per replica
```

---

## Troubleshooting

### Container App Not Starting
```bash
# Check revision status
az containerapp revision list \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --output table

# Check container logs for errors
az containerapp logs show \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --tail 100

# Common issues:
# - Image pull error → Check ACR credentials
# - Health probe failing → Verify /health endpoint
# - Secret not found → Verify Key Vault access
```

### Database Connection Issues
```bash
# Check PostgreSQL connectivity
POSTGRES_FQDN=$(terraform output -raw postgres_fqdn)
echo "PostgreSQL: $POSTGRES_FQDN"

# Verify firewall rules allow Container Apps subnet
az postgres flexible-server firewall-rule list \
  --resource-group $RG_NAME \
  --name huron-prod-postgres
```

### Redis Connection Issues
```bash
# Get Redis hostname
REDIS_HOST=$(terraform output -raw redis_hostname)
echo "Redis: $REDIS_HOST"

# Check if private endpoint is working (from Container App exec)
az containerapp exec \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --command "/bin/sh -c 'nc -zv $REDIS_HOST 6380'"
```

---

## CI/CD with GitHub Actions

### Create Service Principal
```bash
# Create SP for GitHub Actions
SP_NAME="huron-github-actions"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az ad sp create-for-rbac \
  --name $SP_NAME \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME \
  --sdk-auth

# Output JSON → Add as GitHub Secret: AZURE_CREDENTIALS

# Grant ACR push access
ACR_ID=$(az acr show --name $KV_NAME --query id -o tsv)
az role assignment create \
  --assignee $(az ad sp list --display-name $SP_NAME --query "[0].appId" -o tsv) \
  --role AcrPush \
  --scope $ACR_ID
```

### GitHub Secrets Required
```
AZURE_CREDENTIALS     → Service Principal JSON
ACR_LOGIN_SERVER      → huronprod.azurecr.io
AZURE_RESOURCE_GROUP  → huron-prod-rg
```

---

## Cleanup (Destroy)

```bash
# ⚠️ WARNING: This deletes ALL resources including data!

# First, remove delete locks if any
az lock list --resource-group $RG_NAME

# Purge Key Vault soft-delete (required before full destroy)
az keyvault purge --name $KV_NAME --no-wait

# Destroy all resources
cd terraform/azure
terraform destroy

# Confirm with 'yes'

# Clean up purged Key Vault
az keyvault purge --name $KV_NAME --location eastus
```

---

## Cost Estimate

| Resource | Monthly Cost (approx) |
|----------|----------------------|
| Container Apps (2 backends + 2 frontends) | $50-100 |
| PostgreSQL Flexible Server | $50-80 |
| Azure Cache for Redis (C1) | $45-55 |
| Container Registry (Basic) | $5 |
| Log Analytics | $10-20 |
| Key Vault | $1-3 |
| **Total** | **$160-260/month** |

---

## Quick Reference

### Useful Commands
```bash
# List all resources
az resource list --resource-group $RG_NAME --output table

# Restart backend
az containerapp revision restart \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --revision REVISION_NAME

# Get backend URL
az containerapp show \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --query "properties.configuration.ingress.fqdn" -o tsv

# Check container health
az containerapp replica list \
  --name huron-prod-backend \
  --resource-group $RG_NAME \
  --output table
```

---

*Last updated: 2026-05-31*
