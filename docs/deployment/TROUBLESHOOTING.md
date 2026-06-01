# Troubleshooting Guide

Organized by deployment phase. For each issue: symptom, likely cause, and fix.

---

## Phase 0 — Local

### Backend container exits immediately

**Symptom:** `huron-backend-1 exited with code 1` right after `make up`

**Cause:** Missing or invalid environment variable, or Python import error.

**Fix:**
```bash
# View logs
docker compose -f docker-compose.local.yml logs backend

# Common cause: JWT_SECRET_KEY too short
# Edit docker-compose.local.yml: JWT_SECRET_KEY must be ≥ 32 chars

# Another common cause: import error in main.py
docker compose -f docker-compose.local.yml run --rm backend python -c "import main"
```

---

### Frontend can't reach backend (CORS / network error)

**Symptom:** Browser console: `Failed to fetch` or `CORS policy`

**Cause:** `BACKEND_URL` in docker-compose.local.yml is wrong, or containers aren't on the same network.

**Fix:**
```bash
# Verify backend is healthy
docker compose -f docker-compose.local.yml ps
# backend should show "healthy"

# Verify BACKEND_URL in docker-compose.local.yml is:
# BACKEND_URL=http://backend:8004   (container name, not localhost)
```

---

### `make test-int` fails — "connection refused" to postgres

**Symptom:** `psycopg2.OperationalError: could not connect to server`

**Cause:** PostgreSQL container hasn't finished starting, or `make up-test` wasn't run.

**Fix:**
```bash
make up-test
# Wait for "huron-postgres-1 is healthy" in output
docker compose -f docker-compose.test.yml ps
# postgres should show "healthy" before running tests
make test-int
```

---

### Redis JWT blacklist not activating

**Symptom:** `/health` shows `redis: {"status": "disabled"}` even though `REDIS_URL` is set.

**Cause:** Redis container isn't running, or `REDIS_URL` format is wrong.

**Fix:**
```bash
# Correct format: redis://host:port/db_number
# Example: redis://redis:6379/0

# Test Redis directly
docker compose -f docker-compose.test.yml exec redis redis-cli ping
# Expected: PONG
```

---

## Phase 1 — Terraform / AWS Infrastructure

### `terraform apply` fails — "ResourceLimitExceeded"

**Symptom:** Error creating NAT Gateway or Elastic IP: `AddressLimitExceeded`

**Cause:** AWS account default limit of 5 Elastic IPs per region.

**Fix:**
```bash
# Check current EIPs
aws ec2 describe-addresses --query "Addresses[].AllocationId"

# Release any unused EIPs, then retry:
terraform apply
```

Or request an EIP limit increase via AWS Support.

---

### RDS fails to create — "DBSubnetGroup doesn't cover enough AZs"

**Symptom:** `Error: DBSubnetGroup doesn't cover enough Availability Zones`

**Cause:** `db_multi_az = true` requires the subnet group to span ≥ 2 AZs, but the subnets are in only 1 AZ.

**Fix:**
Check `terraform/aws/main.tf` — the database subnet group must include subnets from at least 2 different AZs. Verify `aws_subnet.database` count is ≥ 2.

---

### WAF association fails — "WAF2 web ACL already associated"

**Cause:** An existing WAF ACL is already attached to the ALB.

**Fix:**
```bash
# Find existing association
aws wafv2 list-web-acl-associations \
  --scope REGIONAL \
  --resource-arn <alb-arn>

# Remove it
aws wafv2 disassociate-web-acl --resource-arn <alb-arn>

# Re-run terraform apply
```

---

## Phase 2 — ECS Deployment

### ECS tasks not reaching "RUNNING" state

**Symptom:** Tasks stuck in `PENDING` → stop with `CannotPullContainerError`

**Cause:** ECS can't pull the image from ECR. Check:
1. ECR repository exists and has the image tag
2. ECS task role has `ecr:GetAuthorizationToken`, `ecr:BatchGetImage` permissions
3. If in private subnet: ECR VPC endpoints are active

**Fix:**
```bash
# Verify image exists
aws ecr describe-images --repository-name huron-backend

# Verify VPC endpoints
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.ecr.dkr" \
  --query "VpcEndpoints[0].State"
# Expected: available
```

---

### Backend task starts but `/health` returns `db: error`

**Symptom:** ECS task is `RUNNING` but health check shows PostgreSQL connection failure.

**Cause:** `DATABASE_URL` secret is wrong, or RDS security group blocks the ECS task.

**Fix:**
```bash
# Check the secret value
aws secretsmanager get-secret-value --secret-id huron/dev/database-url

# Check RDS security group inbound rules
aws ec2 describe-security-groups --group-ids <rds-sg-id>
# Should have inbound rule: TCP 5432 from ECS security group
```

---

### Redis connection error in `/health`

**Symptom:** `redis: {"status": "error", "detail": "..."}` in `/health`

**Fix:**
```bash
# Check REDIS_URL secret
aws secretsmanager get-secret-value --secret-id huron/dev/redis-url
# Format: redis://<elasticache-endpoint>:6379/0

# Check ElastiCache security group allows ECS on port 6379
aws ec2 describe-security-groups --group-ids <redis-sg-id>
```

---

### Migration task fails with "relation already exists"

**Cause:** Migration ran twice. `init_db()` uses `CREATE TABLE IF NOT EXISTS` — safe to re-run.

The explicit error usually means the `migrate_sqlite_to_postgres.py` script ran against an already-migrated database.

**Fix:** The script is idempotent for most operations. If it's a hard failure, check the specific table in the logs and run only the missing parts manually.

---

## Phase 3 — Production

### Blue/Green deploy stalls — no traffic shift after 5 minutes

**Symptom:** CodeDeploy deployment in `IN_PROGRESS` longer than expected. Green task set running but no traffic shift.

**Cause:** ALB health checks on the Green target group are failing.

**Fix:**
```bash
# Check Green target group health
aws elbv2 describe-target-health \
  --target-group-arn <green-tg-arn>

# Check ECS task logs for startup errors
aws logs tail /ecs/huron-backend-prod --since 10m
```

---

### SSO redirect loop after OIDC login

**Symptom:** User logs in via Microsoft, gets redirected back to login page repeatedly.

**Cause:** `OIDC_REDIRECT_URI` in Secrets Manager doesn't match the registered URI in Entra ID, or the frontend `sso-complete` page isn't handling the token correctly.

**Fix:**
1. Verify `OIDC_REDIRECT_URI` exactly matches the Entra ID app registration (including trailing slash)
2. Check backend logs for the OIDC callback: `aws logs tail /ecs/huron-backend-prod`
3. Verify `FRONTEND_URL` env var is set correctly (the backend redirects to `FRONTEND_URL/auth/sso-complete`)

---

### Pinecone queries fail after PrivateLink activation

**Symptom:** Vector search returns errors after switching to PrivateLink endpoint.

**Cause:** The Pinecone client is still using the public API URL.

**Fix:** Update the Pinecone client initialization in `backend/utils/` to use the private endpoint host provided by Pinecone support. The host format is typically: `<index-name>-<project-id>.svc.<environment>.pinecone.io` but via PrivateLink it uses a VPC-internal DNS name.

---

## General — Useful Commands

```bash
# Tail ECS logs in real time
aws logs tail /ecs/huron-backend-prod --follow

# Force new deployment (rolling restart)
aws ecs update-service --cluster huron-prod --service huron-backend-prod --force-new-deployment

# Scale down to 0 tasks (emergency stop)
aws ecs update-service --cluster huron-prod --service huron-backend-prod --desired-count 0

# List running tasks
aws ecs list-tasks --cluster huron-prod --service-name huron-backend-prod

# Exec into running container (debugging)
aws ecs execute-command \
  --cluster huron-prod \
  --task <task-id> \
  --container huron-backend \
  --interactive \
  --command "/bin/bash"
```
