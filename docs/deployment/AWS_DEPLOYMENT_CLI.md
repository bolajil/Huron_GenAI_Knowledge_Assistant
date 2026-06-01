# AWS Deployment Guide — CLI Step-by-Step

> **Huron GenAI Knowledge Assistant**  
> ECS Fargate · RDS PostgreSQL · ElastiCache Redis · WAF · CloudWatch

---

## Prerequisites

### Required Tools
```bash
# Install AWS CLI v2
# Windows (PowerShell as Admin)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# macOS
brew install awscli

# Verify installation
aws --version
# aws-cli/2.x.x ...

# Install Terraform
# Windows (Chocolatey)
choco install terraform

# macOS
brew install terraform

# Verify
terraform --version
# Terraform v1.x.x

# Install Docker
# https://docs.docker.com/get-docker/
docker --version
```

### AWS Account Setup
```bash
# Configure AWS credentials
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-east-1
# Default output format: json

# Verify access
aws sts get-caller-identity
```

### Required API Keys
- **OpenAI API Key** — `sk-...` (GPT-4o + embeddings)
- **Pinecone API Key** — `pcsk_...`
- **JWT Secret** — Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **Database Password** — Strong password for RDS

---

## Step 1: Clone & Configure

```bash
# Clone repository
git clone https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git
cd Huron_GenAI_Knowledge_Assistant

# Navigate to Terraform AWS directory
cd terraform/aws
```

---

## Step 2: Create Variables File

```bash
# Create terraform.tfvars (NEVER commit this file)
cat > terraform.tfvars << 'EOF'
# ── Required Secrets ──────────────────────────────────────────────────────────
openai_api_key   = "sk-YOUR_OPENAI_API_KEY"
pinecone_api_key = "pcsk_YOUR_PINECONE_API_KEY"
jwt_secret       = "YOUR_GENERATED_JWT_SECRET_MIN_32_CHARS"
db_password      = "YourStrongDBPassword123!"
mcp_encryption_key = "YOUR_MCP_ENCRYPTION_KEY"

# ── Configuration ─────────────────────────────────────────────────────────────
aws_region   = "us-east-1"
environment  = "prod"
project_name = "huron"

# ── Database ──────────────────────────────────────────────────────────────────
db_username         = "huron_admin"
db_name             = "huron_db"
db_instance_class   = "db.t3.medium"
db_allocated_storage = 20
db_multi_az         = true

# ── ECS Resources ─────────────────────────────────────────────────────────────
backend_cpu     = 2048    # 2 vCPU
backend_memory  = 4096    # 4 GB
frontend_cpu    = 512     # 0.5 vCPU
frontend_memory = 1024    # 1 GB

# ── Scaling ───────────────────────────────────────────────────────────────────
backend_desired_count  = 2
frontend_desired_count = 2

# ── Optional: Custom Domain ───────────────────────────────────────────────────
# domain_name     = "huron.example.com"
# certificate_arn = "arn:aws:acm:us-east-1:123456789:certificate/xxx"

# ── Optional: Observability ───────────────────────────────────────────────────
# sentry_dsn  = "https://xxx@xxx.ingest.sentry.io/xxx"
# posthog_key = "phc_xxx"
EOF

echo "✅ Created terraform.tfvars"
```

---

## Step 3: Initialize Terraform

```bash
# Initialize Terraform (downloads providers)
terraform init

# Expected output:
# Terraform has been successfully initialized!
```

---

## Step 4: Review Deployment Plan

```bash
# Preview what will be created (DRY RUN)
terraform plan -out=tfplan

# Review the output carefully:
# - VPC with 2 public + 2 private + 2 database subnets
# - NAT Gateway for private subnet internet access
# - ECR repositories for backend/frontend images
# - ECS Cluster with Fargate services
# - RDS PostgreSQL (Multi-AZ)
# - ElastiCache Redis (2-node replication)
# - ALB with HTTP/HTTPS listeners
# - WAF with OWASP rules + rate limiting
# - S3 bucket for documents
# - Secrets Manager for API keys
# - CloudWatch log groups + alarms
# - VPC Endpoints (ECR, S3, Secrets Manager, Logs)

# Estimated cost: ~$200-400/month (depends on usage)
```

---

## Step 5: Deploy Infrastructure

```bash
# Apply the plan (creates all resources)
terraform apply tfplan

# This takes 12-18 minutes
# - RDS: ~8-10 min
# - ElastiCache: ~5-8 min
# - ECS services will fail initially (no images yet)

# Save the outputs
terraform output > deployment_outputs.txt
```

---

## Step 6: Build & Push Docker Images

```bash
# Get ECR login credentials
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(terraform output -raw ecr_backend_url | cut -d'/' -f1)

# Navigate to project root
cd ../..

# Build backend image
docker build -f Dockerfile.production -t huron-backend:latest .

# Tag for ECR
docker tag huron-backend:latest $(cd terraform/aws && terraform output -raw ecr_backend_url):latest

# Push backend
docker push $(cd terraform/aws && terraform output -raw ecr_backend_url):latest

echo "✅ Backend image pushed"

# Build frontend image
cd frontend
docker build -f Dockerfile.production \
  --build-arg NEXT_PUBLIC_API_URL="$(cd ../terraform/aws && terraform output -raw backend_url)" \
  -t huron-frontend:latest .

# Tag for ECR
docker tag huron-frontend:latest $(cd ../terraform/aws && terraform output -raw ecr_frontend_url):latest

# Push frontend
docker push $(cd ../terraform/aws && terraform output -raw ecr_frontend_url):latest

echo "✅ Frontend image pushed"
cd ..
```

---

## Step 7: Restart ECS Services

```bash
cd terraform/aws

# Force ECS to pull new images
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service huron-prod-backend \
  --force-new-deployment

aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service huron-prod-frontend \
  --force-new-deployment

echo "⏳ ECS services restarting... (2-5 minutes)"
```

---

## Step 8: Verify Deployment

```bash
# Wait for services to stabilize
aws ecs wait services-stable \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services huron-prod-backend huron-prod-frontend

echo "✅ Services are stable"

# Test health endpoint
curl -f $(terraform output -raw backend_url | sed 's|/api||')/health
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

## Step 9: Post-Deployment Tasks

### Create Pinecone Index (First Time Only)
```python
# Run this Python script once
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="YOUR_PINECONE_API_KEY")
pc.create_index(
    name="huron-enterprise-knowledge",
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
print("✅ Pinecone index created")
```

### Set Up GitHub Actions CI/CD
```bash
# Get CI/CD user credentials (create access key in AWS Console)
# IAM → Users → huron-prod-cicd-user → Security credentials → Create access key

# Add to GitHub repository secrets:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_REGION (us-east-1)
```

---

## Monitoring & Logs

```bash
# View backend logs
aws logs tail /ecs/huron-prod/backend --follow

# View frontend logs
aws logs tail /ecs/huron-prod/frontend --follow

# Check ECS service events
aws ecs describe-services \
  --cluster huron-prod-cluster \
  --services huron-prod-backend \
  --query 'services[0].events[:5]'
```

---

## Troubleshooting

### ECS Tasks Failing to Start
```bash
# Check task failures
aws ecs describe-tasks \
  --cluster huron-prod-cluster \
  --tasks $(aws ecs list-tasks --cluster huron-prod-cluster --service huron-prod-backend --query 'taskArns[0]' --output text)

# Common issues:
# - Image not found → Re-push images
# - Health check failing → Check /health endpoint
# - Secrets not accessible → Verify IAM roles
```

### Database Connection Issues
```bash
# Test RDS connectivity from ECS (use ECS Exec)
aws ecs execute-command \
  --cluster huron-prod-cluster \
  --task TASK_ID \
  --container backend \
  --interactive \
  --command "/bin/sh"

# Inside container:
# psql -h $DATABASE_URL
```

---

## Cleanup (Destroy)

```bash
# ⚠️ WARNING: This deletes ALL resources including data!

# Disable deletion protection on RDS first
aws rds modify-db-instance \
  --db-instance-identifier huron-prod-postgres \
  --no-deletion-protection \
  --apply-immediately

# Wait for modification
aws rds wait db-instance-available --db-instance-identifier huron-prod-postgres

# Destroy all resources
cd terraform/aws
terraform destroy

# Confirm with 'yes'
```

---

## Cost Estimate

| Resource | Monthly Cost (approx) |
|----------|----------------------|
| ECS Fargate (4 tasks) | $60-100 |
| RDS db.t3.medium (Multi-AZ) | $80-100 |
| ElastiCache (2 nodes) | $25-40 |
| NAT Gateway | $35-45 |
| ALB | $20-25 |
| S3 + CloudWatch | $5-15 |
| **Total** | **$225-325/month** |

---

*Last updated: 2026-05-31*
