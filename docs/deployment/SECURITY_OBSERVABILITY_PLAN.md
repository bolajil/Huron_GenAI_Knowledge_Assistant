# Huron GenAI — Security & Observability Completion Plan

## Current Status Overview

```
✅ Implemented   ⚠️ Partial / Needs Fix   ❌ Not Yet Built
```

| Category | Status | Summary |
|----------|--------|---------|
| WAF / Network Security | ✅ | OWASP rules, rate limiting, VPC segmentation |
| RBAC / Auth | ✅ | 5-tier roles, department isolation, JWT |
| Audit Logging | ✅ | Login/logout/auth_failure events logged |
| Sentry Error Tracking | ✅ | Initialized, 20% trace sampling |
| CloudWatch Logs + Alarms | ✅ | 6 alarms, dashboard created |
| MFA | ⚠️ | Built but dev-bypass code still present |
| CORS | ⚠️ | Hardcoded localhost origins |
| Langfuse / LangSmith | ⚠️ | Env vars configured, SDK not wired in code |
| Grafana | ⚠️ | IAM role ready, workspace not deployed |
| Route 53 | ⚠️ | Config exists, zone/cert not provisioned |
| Alarm Notifications | ❌ | CloudWatch alarms fire but notify no one |
| Auth Rate Limiting | ❌ | WAF global limit only, no per-endpoint limit |
| Access Logging | ❌ | ALB, S3, RDS, VPC Flow Logs, CloudTrail all off |
| HTTP → HTTPS Redirect | ❌ | HTTP listener exists but no redirect rule |
| Container Scanning | ❌ | No Trivy or similar in CI |
| HIPAA PHI Audit Events | ❌ | Clinical dept access not specifically tracked |
| GDPR Data Deletion | ❌ | No right-to-be-forgotten API |

---

## Phase 1 — Critical Fixes (Do Before Production)

These are security gaps that must be closed before any real user data touches the system.

### 1.1 Remove MFA Dev Bypass

**File:** `backend/main.py` ~line 1186
**Risk:** Dev bypass code returning `"dev-bypass-token"` could be exploited in production.

```python
# REMOVE THIS:
if APP_ENV in ("dev", "local"):
    return {"access_token": "dev-bypass-token", ...}

# REPLACE WITH: real TOTP verification only
```

### 1.2 HTTP → HTTPS Redirect on ALB

**File:** `terraform/aws/main.tf` — add redirect rule to the port 80 listener

```hcl
resource "aws_lb_listener_rule" "http_to_https" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 1

  action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  condition {
    path_pattern { values = ["/*"] }
  }
}
```

### 1.3 Parameterize CORS Origins

**File:** `backend/main.py` ~line 84
**Risk:** Hardcoded localhost origins will block real users.

```python
# Replace hardcoded list with:
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")

app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, ...)
```

**Add to Secrets Manager in terraform:**
```hcl
"ALLOWED_ORIGINS" = "https://app.huron.ai,https://staging.huron.ai"
```

### 1.4 Auth Endpoint Rate Limiting

**File:** `backend/main.py` — add SlowAPI rate limiter to `/api/v1/auth/login`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/auth/login")
@limiter.limit("10/minute")   # max 10 login attempts per minute per IP
async def login(request: Request, ...):
```

### 1.5 CloudWatch Alarm Notifications (SNS)

**File:** `terraform/aws/main.tf`
**Risk:** Alarms fire silently — no one gets paged when CPU is 85% or disk is full.

```hcl
resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email        # add to variables.tf
}

# Add to every aws_cloudwatch_metric_alarm:
alarm_actions = [aws_sns_topic.alerts.arn]
ok_actions    = [aws_sns_topic.alerts.arn]
```

---

## Phase 2 — Observability Stack (LLM Tracing + Grafana)

### 2.1 Wire Langfuse into Backend Code

**Status:** Environment variables set in ECS task, but SDK never initialized.

**Install:**
```bash
pip install langfuse
# Add to requirements_production.txt
```

**Initialize in `backend/main.py`:**
```python
from langfuse import Langfuse

_langfuse = None
if os.getenv("LANGFUSE_PUBLIC_KEY"):
    _langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
```

**Wrap every LLM call:**
```python
# In query handler:
trace = _langfuse.trace(name="query", user_id=user_id, input=query_text) if _langfuse else None
# ... LLM call ...
if trace:
    trace.update(output=response, metadata={"dept": dept, "sources": sources_count})
```

### 2.2 Wire LangSmith into Backend Code

**Status:** `LANGCHAIN_TRACING_V2` env var set, but LangChain calls not verified.

**Verify in any LangChain usage:**
```python
# LangSmith auto-traces if env vars are set — verify these are in .env:
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=huron-genai
LANGCHAIN_API_KEY=<key>
```

No code changes needed if LangChain is used — tracing is automatic once env vars are set.

### 2.3 Deploy Grafana Workspace

**File:** `terraform/aws/main.tf` — uncomment and enable

```hcl
# In variables.tf — add:
variable "create_grafana" {
  type    = bool
  default = false
}

# In main.tf — uncomment the grafana workspace block:
resource "aws_grafana_workspace" "main" {
  count                    = var.create_grafana ? 1 : 0
  name                     = "${local.prefix}-grafana"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "SERVICE_MANAGED"
  role_arn                 = aws_iam_role.grafana[0].arn
  data_sources             = ["CLOUDWATCH", "PROMETHEUS"]
}
```

**Enable in staging.tfvars:**
```hcl
create_grafana = true
alert_email    = "devops@huron.ai"
```

**Grafana dashboards to create:**
- ECS service CPU/Memory per task
- API request rate, error rate, latency (p50/p95/p99)
- Database connections and query time
- LLM query volume and response times (from Langfuse)
- Failed login attempts over time

### 2.4 Add Prometheus Metrics Endpoint

**Install:**
```bash
pip install prometheus-fastapi-instrumentator
```

**Add to `backend/main.py`:**
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

This gives Grafana a `/metrics` endpoint to scrape latency histograms, request counts, and error rates per endpoint.

---

## Phase 3 — Access Logging & Audit Trail

### 3.1 Enable CloudTrail

```hcl
resource "aws_cloudtrail" "main" {
  name                          = "${local.prefix}-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail_logs.id
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::${aws_s3_bucket.documents.id}/"]
    }
  }
}
```

### 3.2 Enable ALB Access Logs

```hcl
# Add to aws_lb resource in main.tf:
access_logs {
  bucket  = aws_s3_bucket.alb_logs.id
  prefix  = "alb"
  enabled = true
}
```

### 3.3 Enable VPC Flow Logs

```hcl
resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id
}
```

### 3.4 Add HIPAA PHI Audit Events

**File:** `backend/main.py` — add to `write_audit()` calls in clinical query handlers:

```python
# When a clinical/hipaa_phi namespace is queried:
if dept_classification == "hipaa_phi":
    write_audit(
        user_id, username,
        "phi_access",
        dept_code=dept,
        namespace=namespace,
        detail=f"query: {query_text[:100]}... | sources: {sources_count}"
    )
```

### 3.5 Add Audit Log to Migration

**File:** `backend/migrations/versions/002_audit_log_table.sql`

```sql
-- Migration 002: Add audit_log and query_log tables
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username    TEXT,
    action      TEXT NOT NULL,
    dept_code   TEXT,
    namespace   TEXT,
    detail      TEXT,
    ip_address  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id   ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action    ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

CREATE TABLE IF NOT EXISTS query_log (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    dept_code     TEXT,
    query_text    TEXT,
    response_ms   INTEGER,
    faithfulness  REAL,
    sources_count INTEGER,
    vector_backend TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_log_user_id    ON query_log(user_id);
CREATE INDEX IF NOT EXISTS idx_query_log_dept_code  ON query_log(dept_code);
CREATE INDEX IF NOT EXISTS idx_query_log_created_at ON query_log(created_at DESC);
```

---

## Phase 4 — Route 53 & SSL (When Domain is Ready)

### 4.1 Get Prerequisites from Huron IT

- [ ] Domain name (e.g., `huron.ai` or `huronconsulting.com`)
- [ ] Route 53 hosted zone ID (or permission to create one)
- [ ] ACM certificate ARN for `*.huron.ai`

### 4.2 Add to prod.tfvars

```hcl
domain_name       = "app.huron.ai"
route53_zone_id   = "Z1234567890ABC"      # from Huron IT
certificate_arn   = "arn:aws:acm:us-east-1:..."   # from ACM
```

### 4.3 Request ACM Certificate

```bash
# Run once before terraform apply:
aws acm request-certificate \
  --domain-name "*.huron.ai" \
  --validation-method DNS \
  --region us-east-1
# Copy the ARN into prod.tfvars certificate_arn
```

Route 53 validation records are already in `route53.tf` — they will auto-create once the zone ID and cert ARN are provided.

---

## Phase 5 — CI/CD Security Hardening

### 5.1 Add npm audit to CI

**File:** `.github/workflows/ci.yml` — add after `npm ci`:

```yaml
- name: Audit frontend dependencies
  run: npm audit --audit-level=high
  working-directory: frontend
  continue-on-error: true   # warn but don't block initially
```

### 5.2 Add Container Image Scanning (Trivy)

**File:** `.github/workflows/ci.yml` — add to docker-build job:

```yaml
- name: Scan backend image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: huron-backend:ci
    format: table
    exit-code: 1
    severity: CRITICAL,HIGH
    ignore-unfixed: true
```

### 5.3 Add GitHub CodeQL (SAST)

Create `.github/workflows/codeql.yml`:

```yaml
name: CodeQL Security Scan
on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 6 * * 1'   # weekly Monday 6am

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    strategy:
      matrix:
        language: [python, javascript]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
```

---

## Phase 6 — Compliance (SOC 2 / HIPAA / GDPR)

### 6.1 GDPR Data Deletion API

**File:** `backend/main.py` — add endpoint (admin/root only):

```python
@app.delete("/api/v1/admin/users/{user_id}/data")
async def delete_user_data(user_id: int, p=Depends(require_root)):
    """GDPR right to erasure — deletes all PII and query history for a user."""
    with db_conn() as conn:
        conn.execute("DELETE FROM query_log   WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM audit_log   WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM sessions    WHERE user_id=?", (user_id,))
        # Anonymize user record rather than delete (preserves audit trail integrity)
        conn.execute("""UPDATE users SET
            username='deleted_user', email='deleted@deleted.invalid',
            full_name='Deleted User', password_hash='',
            is_active=FALSE WHERE id=?""", (user_id,))
        conn.commit()
    write_audit(p["user_id"], p["sub"], "gdpr_erasure", detail=f"user_id={user_id}")
    return {"status": "erased", "user_id": user_id}
```

### 6.2 SOC 2 Immutable Audit Storage

Enable S3 Object Lock on the audit log bucket so logs cannot be altered:

```hcl
resource "aws_s3_bucket_object_lock_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 365
    }
  }
}
```

---

## Implementation Priority

| Priority | Phase | Items | When |
|----------|-------|-------|------|
| 🔴 **Before prod launch** | 1 | Remove MFA bypass, HTTPS redirect, CORS fix, rate limiting, SNS alerts | Before real users |
| 🟠 **Within 30 days of prod** | 2 | Langfuse wiring, Grafana deployment, Prometheus metrics | After launch |
| 🟡 **Within 60 days** | 3 | CloudTrail, ALB access logs, VPC Flow Logs, HIPAA audit events | Compliance prep |
| 🟢 **When domain is ready** | 4 | Route 53, SSL certificate, HTTPS enforcement | With Huron IT |
| 🔵 **CI hardening** | 5 | npm audit, Trivy, CodeQL | Ongoing |
| ⚪ **For enterprise compliance** | 6 | GDPR deletion API, SOC 2 immutable logs | Before SOC 2 audit |

---

## What to Request from Huron IT / Security Team

- [ ] AWS account with SOC 2 and HIPAA Business Associate Agreement (BAA) signed
- [ ] Domain name and Route 53 hosted zone
- [ ] ACM wildcard certificate for the domain
- [ ] Alert email/Slack for CloudWatch SNS notifications
- [ ] Langfuse account (self-hosted or cloud) — public/secret key
- [ ] LangSmith API key (if using LangSmith instead of Langfuse)
- [ ] Grafana Cloud account (or use AWS Managed Grafana)
- [ ] Decision on SIEM tool (Splunk, Datadog, or AWS Security Hub)
- [ ] HIPAA BAA from AWS (required before storing PHI)
- [ ] Pen test schedule (recommended before production launch)
