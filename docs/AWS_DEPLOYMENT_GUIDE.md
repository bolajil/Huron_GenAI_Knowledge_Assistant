# AWS Deployment Guide — Huron GenAI Knowledge Assistant

## Table of Contents
- [Quick Start](#quick-start)
- [Multi-Environment Setup](#multi-environment-setup)
- [CI/CD Pipeline with GitHub](#cicd-pipeline-with-github)
- [Blue/Green Deployments](#bluegreen-deployments)
- [Route 53 DNS Configuration](#route-53-dns-configuration)
- [Monitoring & Observability](#monitoring--observability)

---

## Quick Start

### Prerequisites
```bash
# Install required tools
brew install terraform awscli docker

# Configure AWS credentials
aws configure
```

### Deploy Dev Environment (Free Tier)
```bash
cd terraform/aws

# Copy and configure variables
cp environments/dev.tfvars.example environments/dev.tfvars
# Edit dev.tfvars with your API keys

# Initialize and deploy
terraform init
terraform apply -var-file=environments/dev.tfvars
```

### Build & Push Docker Images
```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(terraform output -raw ecr_backend_url | cut -d'/' -f1)

# Build and push backend
docker build -f Dockerfile.production -t $(terraform output -raw ecr_backend_url):latest .
docker push $(terraform output -raw ecr_backend_url):latest

# Build and push frontend
cd frontend
docker build -f Dockerfile.production -t $(terraform output -raw ecr_frontend_url):latest .
docker push $(terraform output -raw ecr_frontend_url):latest

# Restart ECS services
aws ecs update-service --cluster $(terraform output -raw ecs_cluster_name) --service $(terraform output -raw ecs_backend_service) --force-new-deployment
aws ecs update-service --cluster $(terraform output -raw ecs_cluster_name) --service $(terraform output -raw ecs_frontend_service) --force-new-deployment
```

---

## Multi-Environment Setup

### Environment Files
```
terraform/aws/environments/
├── dev.tfvars.example      # Development (Free Tier)
├── staging.tfvars.example  # Staging (mirrors prod)
└── prod.tfvars.example     # Production (full HA)
```

### Deploy Different Environments

```bash
# Development
terraform workspace new dev
terraform apply -var-file=environments/dev.tfvars

# Staging
terraform workspace new staging
terraform apply -var-file=environments/staging.tfvars

# Production
terraform workspace new prod
terraform apply -var-file=environments/prod.tfvars
```

### Environment Comparison

| Feature | Dev | Staging | Prod |
|---------|-----|---------|------|
| Instance Size | t3.micro | t3.small | t3.medium |
| Multi-AZ | ❌ | ❌ | ✅ |
| Backups | 0 days | 3 days | 7 days |
| Auto-scaling | 1-2 | 2-3 | 3-10 |
| Blue/Green | ❌ | ✅ | ✅ |
| Free Tier | ✅ | ❌ | ❌ |

---

## CI/CD Pipeline with GitHub

### Step 1: Create GitHub Connection
1. Go to AWS Console → CodePipeline → Settings → Connections
2. Click "Create connection"
3. Select "GitHub" and follow OAuth flow
4. Copy the Connection ARN

### Step 2: Enable CI/CD in Terraform
```hcl
# In your .tfvars file
enable_cicd           = true
github_repo           = "your-org/huron-genai"
github_branch         = "main"
github_connection_arn = "arn:aws:codestar-connections:us-east-1:123456789012:connection/xxx"
```

### Step 3: Apply Changes
```bash
terraform apply -var-file=environments/prod.tfvars
```

### Pipeline Stages
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Source    │ →  │    Build    │ →  │   Deploy    │
│   GitHub    │    │  CodeBuild  │    │    ECS      │
└─────────────┘    └─────────────┘    └─────────────┘
     │                   │                   │
     │                   │                   │
   Push to          Build Docker        Rolling or
   branch           images, push        Blue/Green
                    to ECR              deployment
```

### Automatic Deployments
Once configured, every push to your configured branch will:
1. Trigger CodePipeline automatically
2. Build Docker images with CodeBuild
3. Push images to ECR
4. Deploy to ECS (rolling or Blue/Green)

---

## Blue/Green Deployments

### Enable Blue/Green
```hcl
# In your .tfvars file
enable_blue_green = true
```

### How It Works
```
                    ┌──────────────┐
                    │     ALB      │
                    │  Port 443    │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 │                 ▼
┌─────────────────┐        │        ┌─────────────────┐
│  Blue (Current) │        │        │  Green (New)    │
│  Target Group   │◄───────┘        │  Target Group   │
│  Port 8004      │                 │  Port 8004      │
└─────────────────┘                 └─────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  ECS Tasks v1   │                 │  ECS Tasks v2   │
└─────────────────┘                 └─────────────────┘
```

### Deployment Flow
1. **Deploy Green**: New version deploys to green target group
2. **Test Traffic**: Port 8080 routes to green for validation
3. **Shift Traffic**: Gradual traffic shift (10% every minute)
4. **Terminate Blue**: Old tasks terminated after 5 minutes

### Rollback
If deployment fails health checks, CodeDeploy automatically rolls back:
```bash
# Manual rollback
aws deploy stop-deployment --deployment-id <deployment-id> --auto-rollback-enabled
```

---

## Route 53 DNS Configuration

### Prerequisites
1. Register domain or transfer to Route 53
2. Create hosted zone (or note existing zone ID)
3. Create ACM certificate for HTTPS

### Step 1: Create ACM Certificate
```bash
# Request certificate (must be in us-east-1 for ALB)
aws acm request-certificate \
  --domain-name "huron.example.com" \
  --subject-alternative-names "*.huron.example.com" \
  --validation-method DNS \
  --region us-east-1
```

### Step 2: Configure Terraform
```hcl
# In your .tfvars file
domain_name     = "huron.example.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxx"
route53_zone_id = "Z1234567890ABC"
```

### Step 3: Apply Changes
```bash
terraform apply -var-file=environments/prod.tfvars
```

### DNS Records Created
| Record | Type | Target |
|--------|------|--------|
| huron.example.com | A (Alias) | ALB |
| www.huron.example.com | A (Alias) | ALB |
| api.huron.example.com | A (Alias) | ALB |

---

## Monitoring & Observability

### CloudWatch Dashboard
Access at: `https://console.aws.amazon.com/cloudwatch/home#dashboards:name=huron-{env}-dashboard`

Metrics included:
- ECS CPU/Memory utilization
- ALB request count and latency
- RDS CPU, connections, storage
- Redis cache hits/misses

### CloudWatch Alarms
| Alarm | Threshold | Action |
|-------|-----------|--------|
| Backend CPU High | > 80% | Auto-scale |
| Backend Memory High | > 85% | Alert |
| RDS CPU High | > 80% | Alert |
| RDS Connections High | > 80 | Alert |
| RDS Storage Low | < 5GB | Alert |

### LLM Observability
```hcl
# Langfuse (recommended)
langfuse_public_key = "pk-lf-xxx"
langfuse_secret_key = "sk-lf-xxx"
langfuse_host       = "https://cloud.langfuse.com"

# OR LangSmith
langsmith_api_key = "lsv2_xxx"
langsmith_project = "huron-genai"
```

### Amazon Managed Grafana
```bash
# Enable Grafana workspace (requires manual console setup)
# 1. Go to Amazon Grafana console
# 2. Create workspace
# 3. Use IAM role: huron-{env}-grafana-role
```

---

## Troubleshooting

### ECS Tasks Not Starting
```bash
# Check task logs
aws logs get-log-events \
  --log-group-name "/ecs/huron-prod-backend" \
  --log-stream-name "ecs/backend/xxx"

# Describe service events
aws ecs describe-services \
  --cluster huron-prod-cluster \
  --services huron-prod-backend \
  --query 'services[0].events[:5]'
```

### CodePipeline Failures
```bash
# Get pipeline state
aws codepipeline get-pipeline-state --name huron-prod-pipeline

# Retry failed action
aws codepipeline retry-stage-execution \
  --pipeline-name huron-prod-pipeline \
  --stage-name Deploy \
  --pipeline-execution-id xxx
```

### Blue/Green Deployment Stuck
```bash
# List deployments
aws deploy list-deployments --application-name huron-prod-backend

# Get deployment details
aws deploy get-deployment --deployment-id xxx

# Stop and rollback
aws deploy stop-deployment --deployment-id xxx --auto-rollback-enabled
```

---

## Cost Optimization

### Free Tier (Dev)
```hcl
use_free_tier = true
# Uses: db.t3.micro, cache.t3.micro, no backups
# Estimated: $0-5/month (within free tier limits)
```

### Production Estimate
| Resource | Size | Monthly Cost |
|----------|------|--------------|
| ECS Fargate | 3 tasks | ~$50 |
| RDS PostgreSQL | db.t3.medium | ~$30 |
| ElastiCache | cache.t3.micro | ~$12 |
| ALB | 1 | ~$20 |
| NAT Gateway | 1 | ~$35 |
| S3/CloudWatch | Variable | ~$5 |
| **Total** | | **~$150/month** |

---

## Security Checklist

- [ ] Use Secrets Manager for all sensitive values
- [ ] Enable WAF with OWASP rules
- [ ] Enable RDS encryption (production)
- [ ] Enable Redis encryption in transit
- [ ] Configure VPC endpoints for AWS services
- [ ] Enable CloudTrail logging
- [ ] Use private subnets for ECS/RDS/Redis
- [ ] Regular security group audit
