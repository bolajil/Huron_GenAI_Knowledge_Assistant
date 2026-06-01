# Phase 3 — Production

**Goal:** Promote staging to production with CloudFront CDN, Pinecone PrivateLink, DNS cutover, and Blue/Green zero-downtime deployments via CodeDeploy.

**Expected time:** 1–2 days (DNS propagation, Pinecone PrivateLink provisioning can take 24h).

---

## Prerequisites

- Phase 2 stable for at least 48 hours with no critical errors in Sentry/CloudWatch
- HIPAA BAA signed with AWS (required before clinical dept PHI data is ingested)
- Pinecone PrivateLink provisioning requested and confirmed
- Domain registered, hosted in Route 53 or DNS accessible
- ACM certificate issued and validated for production domain
- GitHub `production` environment configured with required reviewers

---

## Steps

### 1. Enable Pinecone PrivateLink

Contact Pinecone support to provision a VPC endpoint for your index. This keeps all vector store traffic inside the AWS network — required for clinical department HIPAA compliance.

While waiting for Pinecone to provision (can take 24–48h), proceed with the other steps.

When approved, add to `terraform.tfvars` (prod workspace):
```hcl
pinecone_private_endpoint_id = "vpce-xxxxxxxxxxxxxxxxx"
```

Update the Pinecone client initialization in `backend/utils/` to use the private endpoint URL instead of the public API.

### 2. Set production Terraform workspace

```bash
cd terraform/aws
terraform workspace new prod
terraform workspace select prod
```

Create `terraform.tfvars.prod`:
```hcl
environment  = "prod"
db_multi_az  = true          # Multi-AZ mandatory for production
backend_cpu    = 2048
backend_memory = 4096
db_instance_class = "db.t3.large"
# ... all prod-tier values
```

```bash
terraform plan -var-file=terraform.tfvars.prod -out=plan-prod.tfplan
terraform apply plan-prod.tfplan
```

### 3. Configure CodeDeploy for Blue/Green

The `deploy-prod.yml` workflow uses CodeDeploy. Create the required appspec file:

```yaml
# .aws/appspec.yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: huron-backend
          ContainerPort: 8004
        PlatformVersion: LATEST
```

Create the CodeDeploy application and deployment group in AWS Console (or Terraform):
- Application: `huron-backend-prod`
- Deployment group: `huron-backend-bg`
- Deployment type: Blue/green
- Traffic rerouting: After 5 minutes of health checks passing
- Rollback: On alarm or on failure

### 4. DNS cutover

```bash
# Verify production ALB is healthy first
curl https://<prod-alb-dns>/health

# Create Route 53 alias records
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.huronconsultinggroup.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "<alb-hosted-zone-id>",
          "DNSName": "<prod-alb-dns>",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### 5. CloudFront distribution (frontend)

Create a CloudFront distribution pointing to the ALB or S3 for the frontend. This adds CDN caching and provides DDoS protection at the edge.

Key settings:
- Origin: ECS frontend service via ALB
- Cache policy: `CachingOptimized` for static assets, `CachingDisabled` for `/api/*`
- Viewer protocol policy: Redirect HTTP to HTTPS
- SSL: Use the ACM certificate (must be in `us-east-1` for CloudFront)

### 6. Configure OIDC/SSO (if Active Directory integration is ready)

See [OIDC_SSO_SETUP.md](OIDC_SSO_SETUP.md) for step-by-step setup.

Add to Secrets Manager:
```bash
aws secretsmanager update-secret --secret-id huron/prod/oidc-client-id     --secret-string "<app-client-id>"
aws secretsmanager update-secret --secret-id huron/prod/oidc-client-secret  --secret-string "<app-client-secret>"
aws secretsmanager update-secret --secret-id huron/prod/oidc-authority      --secret-string "https://login.microsoftonline.com/<tenant-id>"
aws secretsmanager update-secret --secret-id huron/prod/oidc-redirect-uri   --secret-string "https://huronconsultinggroup.com/api/v1/auth/oidc/callback"
```

### 7. Production deployment via GitHub Actions

```bash
git checkout main
git merge develop       # after staging sign-off
git push origin main    # triggers deploy-prod.yml
```

The workflow will:
1. Pause at the `production` GitHub environment for reviewer approval
2. Build and push `prod-<sha>` images to ECR
3. Update ECS task definition
4. Trigger CodeDeploy Blue/Green deployment
5. Wait for health checks (5 min)
6. Shift traffic to new deployment
7. Run production smoke test

### 8. Post-deploy verification

```bash
curl https://api.huronconsultinggroup.com/health
# Expected: {"status": "healthy", ...}

# Verify Blue/Green completed (old task set terminated)
aws ecs describe-services --cluster huron-prod --services huron-backend-prod \
  --query "services[0].deployments"
# Should show only ONE deployment with status ACTIVE
```

---

## Rollback

If the smoke test fails or an alarm fires within 5 minutes of traffic shift, CodeDeploy automatically rolls back.

Manual rollback:
```bash
aws ecs update-service \
  --cluster huron-prod \
  --service huron-backend-prod \
  --task-definition <previous-task-def-arn>
```

---

## Validation Checklist

- [ ] DNS propagated — `nslookup api.huronconsultinggroup.com` resolves to CloudFront/ALB IP
- [ ] HTTPS enforced — HTTP redirects to HTTPS
- [ ] `/health` returns healthy from production domain
- [ ] Login works on production URL
- [ ] Pinecone PrivateLink active (check backend logs for no public Pinecone calls)
- [ ] CloudWatch alarms configured for CPU, memory, 5xx errors, RDS
- [ ] HIPAA BAA signed (mandatory before clinical data ingest)
- [ ] Blue/Green test deploy completed successfully
- [ ] Sentry receiving events from production environment
