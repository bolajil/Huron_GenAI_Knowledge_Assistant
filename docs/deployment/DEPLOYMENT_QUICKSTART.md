# Huron GenAI — Cloud Deployment Quick Start

## Choose Your Platform

| Platform | Guide | Est. Time | Est. Cost |
|----------|-------|-----------|-----------|
| **AWS** | [AWS_DEPLOYMENT_CLI.md](./AWS_DEPLOYMENT_CLI.md) | 20-30 min | ~$250/mo |
| **Azure** | [AZURE_DEPLOYMENT_CLI.md](./AZURE_DEPLOYMENT_CLI.md) | 15-25 min | ~$200/mo |

---

## Prerequisites Checklist

- [ ] **OpenAI API Key** — `sk-...` (required for GPT-4o + embeddings)
- [ ] **Pinecone API Key** — `pcsk_...` (required for vector storage)
- [ ] **Terraform** installed (`terraform --version`)
- [ ] **Docker** installed (`docker --version`)
- [ ] **Cloud CLI** installed:
  - AWS: `aws --version` + configured credentials
  - Azure: `az --version` + logged in

---

## Quick Deploy — AWS

```bash
# 1. Navigate to AWS Terraform
cd terraform/aws

# 2. Create variables file
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your API keys

# 3. Deploy
terraform init
terraform apply

# 4. Build & push images
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(terraform output -raw ecr_backend_url | cut -d'/' -f1)
cd ../..
docker build -f Dockerfile.production -t huron-backend .
docker tag huron-backend $(cd terraform/aws && terraform output -raw ecr_backend_url):latest
docker push $(cd terraform/aws && terraform output -raw ecr_backend_url):latest

# 5. Restart ECS
aws ecs update-service --cluster $(cd terraform/aws && terraform output -raw ecs_cluster_name) --service huron-prod-backend --force-new-deployment

# 6. Test
python scripts/deployment_test.py --url $(cd terraform/aws && terraform output -raw frontend_url)
```

---

## Quick Deploy — Azure

```bash
# 1. Navigate to Azure Terraform
cd terraform/azure

# 2. Create variables file
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your API keys + subscription ID

# 3. Deploy
terraform init
terraform apply

# 4. Build & push images
az acr login --name $(terraform output -raw acr_login_server | cut -d'.' -f1)
cd ../..
docker build -f Dockerfile.production -t huron-backend .
docker tag huron-backend $(cd terraform/azure && terraform output -raw acr_login_server)/huron-backend:latest
docker push $(cd terraform/azure && terraform output -raw acr_login_server)/huron-backend:latest

# 5. Update Container App
az containerapp update --name huron-prod-backend --resource-group $(cd terraform/azure && terraform output -raw resource_group_name) --image $(terraform output -raw acr_login_server)/huron-backend:latest

# 6. Test
python scripts/deployment_test.py --url $(cd terraform/azure && terraform output -raw backend_url)
```

---

## Post-Deployment

### 1. Change Default Password
```bash
# Login to the app and change root password immediately!
# Default: username=root, password=HuronRoot2026!
```

### 2. Create Pinecone Index (First Time)
```python
from pinecone import Pinecone, ServerlessSpec
pc = Pinecone(api_key="YOUR_KEY")
pc.create_index("huron-enterprise-knowledge", dimension=1536, metric="cosine", 
                spec=ServerlessSpec(cloud="aws", region="us-east-1"))
```

### 3. Verify Deployment
```bash
# Python test script
python scripts/deployment_test.py --url https://YOUR-DEPLOYMENT-URL

# Or bash script
./scripts/deployment_test.sh https://YOUR-DEPLOYMENT-URL
```

---

## Deployment Test Output

```
═══════════════════════════════════════════════════════════════
  Huron GenAI Deployment Verification
═══════════════════════════════════════════════════════════════

  Target URL: https://huron-alb-123456.us-east-1.elb.amazonaws.com
  Timestamp:  2026-05-31T20:30:00

═══════════════════════════════════════════════════════════════
  1. Health Check
═══════════════════════════════════════════════════════════════

  ✓ PASS GET /health returns healthy (45ms)

═══════════════════════════════════════════════════════════════
  2. API Documentation
═══════════════════════════════════════════════════════════════

  ✓ PASS Swagger UI accessible (120ms)
  ✓ PASS OpenAPI schema valid (85ms) - 42 endpoints

═══════════════════════════════════════════════════════════════
  3. Authentication
═══════════════════════════════════════════════════════════════

  ✓ PASS Protected endpoints reject unauthenticated (32ms)
  ✓ PASS Login as root (156ms)

═══════════════════════════════════════════════════════════════
  4. Authorized API Access
═══════════════════════════════════════════════════════════════

  ✓ PASS GET /api/v1/auth/me (42ms) - role=root
  ✓ PASS GET /api/v1/root/departments (68ms) - 8 departments

═══════════════════════════════════════════════════════════════
  Summary
═══════════════════════════════════════════════════════════════

  All 7 tests passed!

  ✓ Deployment is healthy and operational.
```

---

## Troubleshooting

| Issue | AWS Solution | Azure Solution |
|-------|--------------|----------------|
| ECS/Container not starting | `aws logs tail /ecs/huron-prod/backend --follow` | `az containerapp logs show --name huron-prod-backend -g RG_NAME --follow` |
| Image pull error | Re-run ECR login + push | Re-run `az acr login` + push |
| Health check failing | Verify `/health` returns 200 | Check container revision status |
| Database connection | Check security groups | Check VNet integration |

---

## Cost Optimization Tips

### Development/Staging
```hcl
# AWS - Use smaller instances
db_instance_class    = "db.t3.micro"
db_multi_az          = false
backend_cpu          = 512
backend_memory       = 1024
backend_desired_count = 1

# Azure - Use burstable SKUs
db_sku_name          = "B_Standard_B1ms"
redis_sku_name       = "Basic"
backend_min_replicas = 0  # Scale to zero when idle
```

---

*Last updated: 2026-05-31*
