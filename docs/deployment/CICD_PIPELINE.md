# CI/CD Pipeline

## Overview

Three GitHub Actions workflows cover the full path from local code to production:

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | `.github/workflows/ci.yml` | Every push + PR | Lint, type-check, unit tests, integration tests, Docker build smoke |
| Deploy Dev | `.github/workflows/deploy-dev.yml` | Push to `develop` | Build + push ECR → rolling deploy to ECS dev |
| Deploy Prod | `.github/workflows/deploy-prod.yml` | Push to `main` + manual gate | Build + push ECR → Blue/Green prod deploy |

---

## Branch Strategy

```
feature/xxx  →  develop  →  main
                   ↓              ↓
                (auto)          (manual approval)
              Deploy Dev       Deploy Prod
```

- **Feature branches:** All code changes. CI runs on every push.
- **`develop`:** Integration branch. Deploys automatically to Dev ECS. This is what you validate on staging.
- **`main`:** Production-ready code only. Requires a reviewer approval in the `production` GitHub environment before deploy begins.

---

## What CI validates

For every push, CI runs all four jobs in parallel where possible:

```
backend-unit ─┐
              ├─ integration (needs both to pass)
frontend-check┘
backend-unit ──── docker-build (parallel with integration)
```

1. **backend-unit**: pytest on `tests/unit/` with no external deps (SQLite, in-memory)
2. **frontend-check**: TypeScript compilation + ESLint on frontend source
3. **integration**: pytest on `tests/integration/` against real PostgreSQL + Redis (GitHub Actions service containers)
4. **docker-build**: `docker build` for both images to catch Dockerfile errors early

**If CI is red on a feature branch:** do not merge to `develop`.

---

## Required GitHub Repository Secrets

Set these in: **GitHub → Settings → Secrets and variables → Actions**

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user or OIDC role for ECR + ECS access |
| `AWS_SECRET_ACCESS_KEY` | Corresponding secret |

**Recommended:** Replace IAM user keys with GitHub OIDC (`aws-actions/configure-aws-credentials` supports `role-to-assume`). This avoids long-lived credentials in GitHub.

---

## Required GitHub Environments

Create in: **GitHub → Settings → Environments**

| Environment | Protection rules |
|-------------|-----------------|
| `production` | Required reviewers: 2 people; deployment branches: `main` only |

Without the `production` environment configured, the prod workflow's `gate` job will fail.

---

## Local → Dev Validation Loop

Before pushing to `develop`, run this loop locally:

```bash
# 1. Unit tests pass
make test

# 2. Integration tests pass (needs up-test running)
make up-test
make test-int

# 3. TypeScript + lint clean
make typecheck
make lint

# 4. Docker builds clean
docker build -f backend/Dockerfile.production -t huron-backend:local .
docker build -f frontend/Dockerfile.production -t huron-frontend:local frontend/

# 5. Push to develop — triggers deploy-dev.yml
git push origin develop
```

Watch the deployment at `https://github.com/<org>/huron/actions`.

After deploy-dev completes, manually test the key flows on `api-dev.huronconsultinggroup.com` before merging to `main`.

---

## Blue/Green Deploy Flow (Production)

```
Push to main
    ↓
Reviewer approves (GitHub environment gate)
    ↓
Build images → push to ECR as prod-<sha>
    ↓
Update ECS task definition with new image
    ↓
CodeDeploy creates Green task set (new version)
    ↓
ALB health checks on Green (5 min)
    ↓
  [PASS] → Traffic shifts: Blue (old) → Green (new)
  [FAIL] → Automatic rollback, no traffic shift
    ↓
Old Blue task set terminated (10 min retention)
```

**Manual rollback (if needed after traffic shift):**
```bash
aws codedeploy stop-deployment \
  --deployment-id d-XXXXXXXXX \
  --auto-rollback-enabled
```

---

## Adding New Environment Variables

When a new feature requires a new env var:

1. Add to `terraform/aws/variables.tf`
2. Add to Secrets Manager (via Terraform or AWS Console)
3. Add to the ECS task definition in `terraform/aws/main.tf` (in the `environment` or `secrets` block)
4. Add to `docker-compose.local.yml` (with a sensible default or blank)
5. Add to `docker-compose.test.yml`
6. Add to `.env.example` (with placeholder value, never real value)
7. Document in the relevant phase guide

---

## Monitoring CI Health

- Failed CI on `develop` → check GitHub Actions tab, fix before deploying
- Failed deploy-dev → check ECS service events in AWS Console
- Failed deploy-prod → CodeDeploy automatically rolls back; check CloudWatch logs for the error

**Alert on failed CI (optional):**
Add a Slack notification step to any workflow:
```yaml
- name: Notify Slack on failure
  if: failure()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
      -d '{"text":"CI failed on ${{ github.ref }}: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}'
```
