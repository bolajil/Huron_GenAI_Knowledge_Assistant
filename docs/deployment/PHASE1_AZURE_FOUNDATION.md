# Phase 1 — Azure Foundation

**Goal:** Stand up the full Azure infrastructure using Terraform, push Docker images to ACR,
and have both frontend and backend running healthy on Azure Container Apps.

**Status:** 🔲 Pending — requires Azure subscription
**Mirrors:** AWS Phase 1 deployment (same application, different cloud)

---

## Azure vs AWS Architecture Mapping

| AWS | Azure | Notes |
|-----|-------|-------|
| VPC + Subnets | Virtual Network (VNet) + Subnets | Container Apps subnet requires `/23` delegation |
| ECR | Azure Container Registry (ACR) Standard | `huronacr<suffix>` |
| ECS Fargate | Azure Container Apps | HTTP scale rule: 50 concurrent requests per replica |
| RDS PostgreSQL 15 | PostgreSQL Flexible Server 15 | Private DNS zone required |
| ElastiCache Redis | Azure Cache for Redis Standard C1 | TLS-only, `rediss://` URL |
| Secrets Manager | Azure Key Vault (Standard SKU) | Managed Identity for secret access |
| S3 | Storage Account + blob container `documents` | LRS, TLS 1.2+, versioning enabled |
| CloudWatch | Log Analytics Workspace + Application Insights | |
| IAM Roles | User-Assigned Managed Identity | Single identity for ACR pull + Key Vault read |
| ALB | Container Apps built-in ingress (HTTPS) | No separate load balancer needed |
| WAF | Azure Front Door + WAF Policy (Phase 2) | Not in initial deployment |

---

## Prerequisites

```bash
# 1. Azure CLI
winget install Microsoft.AzureCLI     # Windows
# or: brew install azure-cli           # Mac

# 2. Log in
az login

# 3. Set your subscription
az account set --subscription <your-subscription-id>

# 4. Verify
az account show --query "{name:name, id:id, tenantId:tenantId}"

# 5. Terraform 1.6+
terraform --version
```

---

## Steps to Deploy

### 1. Fill in `terraform/azure/terraform.tfvars`

```hcl
location     = "East US 2"
environment  = "dev"
project_name = "huron"

openai_api_key   = "sk-proj-..."
pinecone_api_key = "pcsk_..."
pinecone_index   = "huron-enterprise-knowledge"

jwt_secret         = "<minimum 32 chars>"
mcp_encryption_key = "<minimum 32 chars>"

postgres_admin_user     = "huron_admin"
postgres_admin_password = "<minimum 16 chars>"
postgres_db_name        = "huron_db"
postgres_sku            = "GP_Standard_D2ds_v4"   # ~$70/mo; use B_Standard_B1ms (~$12) for dev
postgres_storage_mb     = 32768

backend_cpu     = 1.0
backend_memory  = "2Gi"
frontend_cpu    = 0.5
frontend_memory = "1Gi"

backend_min_replicas = 1
backend_max_replicas = 10

jwt_expiration_hours = 8

backend_image  = ""   # leave blank — pulled from ACR after first push
frontend_image = ""
```

### 2. Initialise and apply

```bash
cd terraform/azure
terraform init
terraform validate
terraform plan -out=plan.tfplan
# Review: expect ~25 resources to add
terraform apply plan.tfplan
```

### 3. Push Docker images to ACR

```bash
# Get ACR name from terraform output
ACR_NAME=$(terraform output -raw acr_login_server | cut -d. -f1)

# Authenticate
az acr login --name $ACR_NAME

# Build and push backend (from project root)
docker build -t $(terraform output -raw acr_login_server)/huron-backend:latest \
  -f backend/Dockerfile.production .
docker push $(terraform output -raw acr_login_server)/huron-backend:latest

# Build and push frontend (bake backend URL at build time)
BACKEND_URL=$(terraform output -raw backend_url)
docker build -t $(terraform output -raw acr_login_server)/huron-frontend:latest \
  -f frontend/Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  --build-arg BACKEND_URL="$BACKEND_URL" \
  ./frontend
docker push $(terraform output -raw acr_login_server)/huron-frontend:latest
```

### 4. Update Container Apps to use new images

```bash
RESOURCE_GROUP=$(terraform output -raw resource_group_name)

az containerapp update \
  --name huron-dev-backend \
  --resource-group $RESOURCE_GROUP \
  --image $(terraform output -raw acr_login_server)/huron-backend:latest

az containerapp update \
  --name huron-dev-frontend \
  --resource-group $RESOURCE_GROUP \
  --image $(terraform output -raw acr_login_server)/huron-frontend:latest
```

### 5. Validate

```bash
BACKEND_URL=$(terraform output -raw backend_url)
curl $BACKEND_URL/health
```

Expected response:
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

## Key Differences from AWS Deployment

### No separate WAF in Phase 1

Azure WAF requires Azure Front Door or Application Gateway. Container Apps provide
HTTPS ingress by default (free TLS via managed certificates). WAF will be added in
Phase 2 via Azure Front Door Premium.

### HTTPS by default

Unlike AWS (where HTTPS requires an ACM certificate), Azure Container Apps automatically
provision a TLS certificate for the `*.azurecontainerapps.io` domain. The frontend URL
will be `https://huron-dev-frontend.<env-hash>.eastus2.azurecontainerapps.io`.

### Secrets via environment variables (not startup injection)

Azure Container Apps pass secrets as environment variables directly in the container
definition (set in Terraform). They are also stored in Key Vault for auditability.
There is no startup-time injection equivalent to ECS `valueFrom: secretsmanager`.

### Redis URL uses `rediss://` (TLS)

```
rediss://:<access-key>@<hostname>:6380
```
The backend's `REDIS_URL` env var is constructed from the Redis cache outputs in Terraform.

---

## Expected Terraform Outputs

```
frontend_url        = "https://huron-dev-frontend.<hash>.eastus2.azurecontainerapps.io"
backend_url         = "https://huron-dev-backend.<hash>.eastus2.azurecontainerapps.io"
api_docs_url        = "https://huron-dev-backend.<hash>.eastus2.azurecontainerapps.io/docs"
acr_login_server    = "huronacr<suffix>.azurecr.io"
postgres_fqdn       = "huron-dev-postgres-<suffix>.postgres.database.azure.com"
redis_hostname      = "huron-dev-redis-<suffix>.redis.cache.windows.net"
key_vault_uri       = "https://huron-kv-<suffix>.vault.azure.net/"
storage_account_name = "huronstore<suffix>"
resource_group_name = "huron-dev-rg"
```

---

## Cost Notes (Dev)

| Resource | Monthly estimate |
|----------|-----------------|
| PostgreSQL Flexible Server `GP_Standard_D2ds_v4` | ~$70 |
| Container Apps (2 apps, minimal load) | ~$10–20 |
| Azure Cache for Redis Standard C1 | ~$25 |
| Azure Container Registry Standard | ~$5 |
| Storage Account | ~$1 |
| Key Vault | ~$0 (free tier 10k operations/mo) |
| Log Analytics | ~$5 |
| **Subtotal (dev)** | **~$116–126/month** |

To reduce cost during dev: use `B_Standard_B1ms` PostgreSQL SKU (~$12/mo instead of $70).

---

## Validation Checklist

- [ ] `terraform apply` exits 0
- [ ] Resource group `huron-dev-rg` visible in Azure Portal
- [ ] PostgreSQL Flexible Server status: `Ready`
- [ ] Azure Cache for Redis status: `Running`
- [ ] ACR repositories exist with images pushed
- [ ] Container App `huron-dev-backend` revision: `Running`
- [ ] Container App `huron-dev-frontend` revision: `Running`
- [ ] `/health` returns `{ "status": "healthy" }` with all services green
- [ ] Key Vault secrets populated (openai-api-key, pinecone-api-key, jwt-secret, mcp-encryption-key)
