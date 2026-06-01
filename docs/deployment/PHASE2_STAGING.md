# Phase 2 — Staging Deployment

**Goal:** Deploy application containers to ECS, migrate data from SQLite to PostgreSQL, and wire up observability (Grafana + Langfuse).

**Expected time:** 2–4 hours.

---

## Prerequisites

- Phase 1 complete (infrastructure exists)
- ECR images pushed (at least `latest` tags)
- GitHub Actions CI passing on `develop` branch

---

## Steps

### 1. Build and push images via GitHub Actions

Push to the `develop` branch to trigger `deploy-dev.yml`:

```bash
git checkout develop
git push origin develop
```

Watch the workflow at: `https://github.com/<org>/huron/actions`

**Expected outcome:** Both services deployed to `huron-dev` ECS cluster. `deploy-dev.yml` waits for `services-stable` and runs a health smoke test.

### 2. Run the database migration task

The backend's `init_db()` is called on startup, but for a clean PostgreSQL install you should run the migration script once before services start:

```bash
# Run as a one-off ECS task (substituting your cluster/subnet/sg values)
aws ecs run-task \
  --cluster huron-dev \
  --task-definition huron-backend-migrate \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"huron-backend","command":["python","migrate_sqlite_to_postgres.py"]}]}'
```

Monitor completion:
```bash
aws ecs describe-tasks --cluster huron-dev --tasks <task-arn> \
  --query "tasks[0].lastStatus"
# Wait until: "STOPPED"

# Verify exit code was 0
aws ecs describe-tasks --cluster huron-dev --tasks <task-arn> \
  --query "tasks[0].containers[0].exitCode"
```

### 3. Verify health endpoint

```bash
curl https://api-dev.huronconsultinggroup.com/health
```

Expected:
```json
{
  "status": "healthy",
  "version": "4.0.0",
  "db": {"status": "ok", "backend": "postgresql"},
  "redis": {"status": "ok"},
  "pinecone": {"status": "ok"},
  "timestamp": "2026-..."
}
```

If `redis.status` is `error`: check the `REDIS_URL` secret in Secrets Manager and that the ECS task role can read it.

### 4. Smoke test the application

```bash
# Login
TOKEN=$(curl -s -X POST https://api-dev.huronconsultinggroup.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"<root-password>"}' | jq -r .access_token)

# Verify token works
curl -s -H "Authorization: Bearer $TOKEN" \
  https://api-dev.huronconsultinggroup.com/api/v1/admin/stats
```

### 5. Configure Grafana

See [GRAFANA_DASHBOARDS.md](GRAFANA_DASHBOARDS.md) for the full setup guide. Short version:

1. Open the Grafana workspace URL from Terraform output
2. Add CloudWatch data source (region: `us-east-1`, auth: workspace IAM role)
3. Import the 5 dashboards defined in GRAFANA_DASHBOARDS.md

### 6. Configure Langfuse (optional but recommended)

Langfuse traces LLM calls for cost visibility and quality monitoring.

```bash
# Add to Secrets Manager
aws secretsmanager update-secret \
  --secret-id huron/dev/langfuse-public-key \
  --secret-string "pk-..."

aws secretsmanager update-secret \
  --secret-id huron/dev/langfuse-secret-key \
  --secret-string "sk-..."
```

Then update the ECS task definition to add:
```
LANGFUSE_PUBLIC_KEY  = <from secrets>
LANGFUSE_SECRET_KEY  = <from secrets>
LANGFUSE_HOST        = https://cloud.langfuse.com
```

Redeploy: `aws ecs update-service --cluster huron-dev --service huron-backend-dev --force-new-deployment`

---

## Multi-Container JWT Blacklist Verification

With Redis active, confirm logout tokens are shared across tasks:

```bash
# Login, get token, logout on task A
TOKEN=$(curl -s -X POST .../api/v1/auth/login ... | jq -r .access_token)
curl -X POST -H "Authorization: Bearer $TOKEN" .../api/v1/auth/logout

# Immediately try the same token — should return 401 regardless of which task handles it
curl -H "Authorization: Bearer $TOKEN" .../api/v1/admin/stats
# Expected: 401 {"detail": "Invalid or expired token"}
```

---

## Validation Checklist

- [ ] ECS services stable (both backend and frontend)
- [ ] `/health` returns `{"status": "healthy"}` with all subsystems `ok`
- [ ] Login + JWT works end to end
- [ ] DB migration completed (exit code 0)
- [ ] Redis blacklist active (`redis.status: ok` in `/health`)
- [ ] Grafana workspace accessible with at least one dashboard
- [ ] CloudWatch log groups receiving logs from both services
