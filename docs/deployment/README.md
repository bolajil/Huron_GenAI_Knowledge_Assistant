# Huron GenAI — Deployment Guide

## Overview

This guide covers the full path from local development to AWS production for the Huron GenAI Knowledge Assistant. The deployment is organized into four sequential phases. Each phase produces working, testable software and can be validated independently before proceeding.

```
Phase 0 → Local Foundation        ✅ Complete — Docker, SQLite, unit + integration tests
Phase 1 → AWS Foundation          ✅ Complete — ECS Fargate live, health: healthy (2026-05-31)
Phase 1 → Azure Foundation        🔲 Pending — Terraform ready, requires Azure subscription
Phase 2 → Staging / Observability 🔲 Next — custom domain, HTTPS cert, Grafana, CI/CD
Phase 3 → Production              🔲 Future — CloudFront, Pinecone PrivateLink, Blue/Green
```

---

## Quick Start (Local)

**Prerequisites:** Docker Desktop, Python 3.11, Node 20, make

```bash
# Clone and enter the project
cd "GenAI Knowledge Assistant Huron"

# Copy environment template
cp .env.example .env.local
# Edit .env.local: set OPENAI_API_KEY at minimum

# Start local containers (SQLite + in-memory, no cloud deps)
make up

# Visit http://localhost:3000
# API docs: http://localhost:8004/docs
```

**Run integration tests (PostgreSQL + Redis mirrors production):**

```bash
make up-test        # starts postgres + redis containers
make test-int       # runs tests against them
```

---

## Phase Navigation

| Doc | Status | What it covers |
|-----|--------|----------------|
| [PHASE0_LOCAL_FOUNDATION.md](PHASE0_LOCAL_FOUNDATION.md) | ✅ Done | Docker images, compose files, SQLite/PostgreSQL switching, unit + integration tests |
| [PHASE1_AWS_FOUNDATION.md](PHASE1_AWS_FOUNDATION.md) | ✅ Done | VPC, RDS, ElastiCache, ECR, ECS Fargate, Secrets Manager, WAF — live on AWS |
| [PHASE1_AZURE_FOUNDATION.md](PHASE1_AZURE_FOUNDATION.md) | 🔲 Pending | VNet, PostgreSQL Flexible, Redis, ACR, Container Apps, Key Vault — ready to deploy |
| [PHASE2_STAGING.md](PHASE2_STAGING.md) | 🔲 Next | Custom domain, HTTPS cert, Grafana dashboards, CI/CD pipeline |
| [PHASE3_PRODUCTION.md](PHASE3_PRODUCTION.md) | 🔲 Future | CloudFront, Pinecone PrivateLink, DNS, Blue/Green deployments |
| [OIDC_SSO_SETUP.md](OIDC_SSO_SETUP.md) | 🔲 Phase 3 | Active Directory SSO via Microsoft Entra ID |
| [GRAFANA_DASHBOARDS.md](GRAFANA_DASHBOARDS.md) | 🔲 Phase 2 | Amazon Managed Grafana — 5 dashboard definitions |
| [CICD_PIPELINE.md](CICD_PIPELINE.md) | 🔲 Phase 2 | GitHub Actions workflows, branch strategy, local validation |
| [COST_ESTIMATES.md](COST_ESTIMATES.md) | — | Itemized cost per phase |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | — | Common issues and fixes per phase |

---

## Architecture Summary

```
Internet → CloudFront (Phase 3) → ALB (HTTPS) → WAF
                                              ↓
                              ECS Frontend (Next.js :3000)
                              ECS Backend  (FastAPI :8004)
                                              ↓
                              RDS PostgreSQL  (private subnet)
                              ElastiCache Redis (private subnet)
                              S3 (documents)
                              Pinecone (vector store — external)
```

**Authentication flow:**
- Username/password → bcrypt → JWT (8h expiry)
- MFA (TOTP) → enforced for admin and root roles
- SSO (Active Directory via Entra ID OIDC) → AD group → Huron RBAC role mapping

**RBAC roles:** `root` → `dept_admin` → `power_user` → `user`

---

## Security Baseline

Before any environment is promoted:
- [ ] No secrets in source code (use Secrets Manager / `.env`)
- [ ] WAF enabled (OWASP core rules + rate limit)
- [ ] RDS encryption at rest enabled
- [ ] Redis encryption in transit + at rest
- [ ] All endpoints behind ALB (no direct task exposure)
- [ ] MFA enforced for admin/root
- [ ] Redis-backed JWT blacklist active (not in-memory)
- [ ] HIPAA BAA signed with AWS before clinical dept data ingested

---

## Key Ports and URLs

| Service | Local | Dev | Prod |
|---------|-------|-----|------|
| Frontend | :3000 | api-dev.huronconsultinggroup.com | huronconsultinggroup.com |
| Backend API | :8004 | api-dev.../api/v1 | api.huronconsultinggroup.com/api/v1 |
| API docs | :8004/docs | — | — (disabled in prod) |
| Grafana | — | — | Amazon Managed Grafana workspace URL |
