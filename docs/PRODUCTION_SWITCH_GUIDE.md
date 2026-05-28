# Huron GenAI — Production Switch Guide

> **Purpose:** Step-by-step instructions to move from local development to a fully hardened,
> scalable production deployment. Each section identifies the exact file(s) to change,
> the environment variable to set, and a test to confirm it works.

---

## Quick Reference — What Changes Where

| Area | Dev (now) | Production | Files to change |
|---|---|---|---|
| Database | SQLite | PostgreSQL | `backend/main.py`, `backend/.env` |
| Sessions / Cache | Python dict | Redis | `backend/main.py`, `backend/.env` |
| Secrets | `.env` file | Secrets Manager | `backend/main.py`, CI/CD pipeline |
| ML Inference | OpenAI API | OpenAI API + local GPU (optional) | `backend/main.py`, `backend/.env` |
| Backend server | Uvicorn single | Gunicorn + Uvicorn workers | `Dockerfile.production`, `docker/` |
| Frontend | `next dev` | `next build && next start` | `frontend/Dockerfile`, `.env.production` |
| Auth | SQLite token blacklist | Redis token blacklist | `backend/main.py` |
| Rate limiting | SlowAPI in-memory | SlowAPI + Redis backend | `backend/main.py` |
| Logging | stdout | Structured JSON → CloudWatch | `backend/main.py` |
| CORS | Allow all origins | Strict allowlist | `backend/main.py` |
| MFA | Optional | Enforced for admin/power_user | `backend/main.py` |

---

## Step 1 — PostgreSQL (replace SQLite)

### What to change

**File:** `backend/main.py`

Find the `db_conn()` function and `init_db()`. They currently use SQLite.
Replace with PostgreSQL using `psycopg2` (sync) or `asyncpg` (async).

```python
# backend/main.py — replace the db_conn block

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "")   # set in production .env

@contextmanager
def db_conn():
    """Context manager — returns SQLite in dev, PostgreSQL in production."""
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
        finally:
            conn.close()
    else:
        # Dev fallback: SQLite (existing behaviour)
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
```

### Environment variable

```bash
# backend/.env (production)
DATABASE_URL=postgresql://huron_admin:STRONG_PASS@your-rds-host:5432/huron_db
```

### Migration

```bash
# Run the existing migration script
python migrate_sqlite_to_postgres.py

# Verify row counts match
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
```

### Test

```bash
# Should return 200 with user count > 0
curl -s http://localhost:8004/health | python -m json.tool
```

---

## Step 2 — Redis (sessions, cache, rate limiting, token blacklist)

### What to change

**File:** `backend/main.py`

```python
# At top of main.py — add Redis client

import redis as _redis

REDIS_URL = os.getenv("REDIS_URL", "")

def get_redis():
    """Returns a Redis client or None (falls back to in-memory in dev)."""
    if REDIS_URL:
        return _redis.from_url(REDIS_URL, decode_responses=True)
    return None

_redis_client = get_redis()
```

#### Token blacklist — switch to Redis

```python
# Replace the in-memory set:
#   _token_blacklist: set = set()
# With:

def blacklist_token(jti: str, ttl_seconds: int = TOKEN_HOURS * 3600):
    if _redis_client:
        _redis_client.setex(f"blacklist:{jti}", ttl_seconds, "1")
    else:
        _token_blacklist.add(jti)          # dev fallback

def is_blacklisted(jti: str) -> bool:
    if _redis_client:
        return _redis_client.exists(f"blacklist:{jti}") > 0
    return jti in _token_blacklist         # dev fallback
```

#### Rate limiting — switch to Redis backend

```python
# In the SlowAPI setup, replace:
#   limiter = Limiter(key_func=get_remote_address)
# With:

from slowapi import Limiter
from slowapi.util import get_remote_address

_limiter_storage = f"redis://{REDIS_URL.replace('redis://', '')}" if REDIS_URL else "memory://"
limiter = Limiter(key_func=get_remote_address, storage_uri=_limiter_storage)
```

### Environment variable

```bash
# backend/.env (production)
REDIS_URL=redis://your-elasticache-host:6379/0
# or with auth:
REDIS_URL=rediss://:AUTH_TOKEN@your-elasticache-host:6379/0
```

### Test

```bash
# Login, then logout — token should be blacklisted in Redis
redis-cli -u $REDIS_URL keys "blacklist:*"
# Should show the JTI of the logged-out token

# Hit a rate-limited endpoint 11 times fast
for i in $(seq 1 11); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8004/api/v1/auth/login; done
# 11th should return 429
```

---

## Step 3 — Secrets Management (no secrets in .env files)

### What to change

**Never commit `.env` files.** In production, load secrets from AWS Secrets Manager or
Azure Key Vault at startup.

```python
# backend/main.py — add at top, before other imports

def _load_aws_secrets():
    """Pull secrets from AWS Secrets Manager if running in AWS."""
    secret_name = os.getenv("AWS_SECRET_NAME", "")
    if not secret_name:
        return   # local dev — use .env file
    import boto3, json
    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
    secret = json.loads(client.get_secret_value(SecretId=secret_name)["SecretString"])
    for key, value in secret.items():
        os.environ.setdefault(key, value)   # only set if not already set

_load_aws_secrets()
```

### Environment variables (production only — set in ECS task definition or Azure Container App)

```bash
AWS_SECRET_NAME=huron/prod/app-secrets
AWS_REGION=us-east-1
# Remove these from .env — they come from Secrets Manager:
# OPENAI_API_KEY, PINECONE_API_KEY, JWT_SECRET, DB_PASSWORD
```

### Security rules

```bash
# JWT secret must be 64+ characters in production
JWT_SECRET=$(openssl rand -hex 64)

# Remove ALL default credentials before first deploy
# In main.py, find ROOT_PASSWORD / default admin setup and remove hardcoded values
```

### Test

```bash
# Confirm no secrets in environment came from .env
env | grep -E "OPENAI|PINECONE|JWT_SECRET|DB_PASSWORD"
# All values should be present (loaded from Secrets Manager), not empty
```

---

## Step 4 — CORS Hardening

### What to change

**File:** `backend/main.py`

```python
# Replace:
#   allow_origins=["*"]
# With:

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"          # dev default
).split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Environment variable

```bash
# backend/.env (production)
ALLOWED_ORIGINS=https://huron.yourcompany.com,https://api.huron.yourcompany.com
```

### Test

```bash
# Should be REJECTED (wrong origin)
curl -H "Origin: https://evil.com" -I http://localhost:8004/api/v1/auth/login
# Access-Control-Allow-Origin header should NOT appear in response

# Should be ACCEPTED (correct origin)
curl -H "Origin: https://huron.yourcompany.com" -I http://localhost:8004/api/v1/auth/login
# Access-Control-Allow-Origin: https://huron.yourcompany.com
```

---

## Step 5 — HTTP Security Headers

### What to change

**File:** `backend/main.py` — add middleware after CORS

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["Referrer-Policy"]           = "no-referrer"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### Test

```bash
curl -I https://your-production-url/health
# Should show all security headers in response
```

---

## Step 6 — MFA Enforcement for Privileged Roles

### What to change

**File:** `backend/main.py` — in the `current_user` dependency

```python
# Add after token verification:

ENFORCE_MFA_ROLES = {"root", "dept_admin", "power_user"}
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

def current_user_strict(p: dict = Depends(current_user)):
    """Requires MFA verification for privileged roles in production."""
    if ENVIRONMENT == "production":
        role = p.get("role", "user")
        mfa_verified = p.get("mfa_verified", False)
        if role in ENFORCE_MFA_ROLES and not mfa_verified:
            raise HTTPException(
                status_code=403,
                detail="MFA verification required for your role in production"
            )
    return p
```

### Environment variable

```bash
ENVIRONMENT=production
```

### Test

```bash
# Log in as dept_admin WITHOUT completing MFA
# Try to access /api/v1/admin/stats
# Should return 403 with MFA message
```

---

## Step 7 — ML Inference GPU Switch (optional — only if hosting models locally)

> **Skip this step** if you continue using the OpenAI API for GPT-4o and embeddings.
> Only needed when you switch to locally-hosted models (cost reduction at scale).

### Step 7a — Local Whisper (replaces OpenAI Whisper-1 API)

```bash
pip install faster-whisper
```

```python
# backend/utils/ingestion_service.py — replace the _transcribe_audio method

import torch

INFERENCE_DEVICE = os.getenv("INFERENCE_DEVICE", "cpu")   # set "cuda" in production
WHISPER_MODEL    = os.getenv("WHISPER_MODEL", "base")      # base/small/medium/large-v3

def _get_whisper():
    from faster_whisper import WhisperModel
    compute_type = "float16" if INFERENCE_DEVICE == "cuda" else "int8"
    return WhisperModel(WHISPER_MODEL, device=INFERENCE_DEVICE, compute_type=compute_type)

async def _transcribe_audio_local(audio_path: str) -> str:
    model = await asyncio.to_thread(_get_whisper)
    segments, _ = await asyncio.to_thread(model.transcribe, audio_path)
    return " ".join(seg.text for seg in segments)
```

### Step 7b — Local Embeddings (replaces OpenAI text-embedding-3-small)

```bash
pip install sentence-transformers
```

```python
# backend/utils/ingestion_service.py

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "")   # empty = use OpenAI API
INFERENCE_DEVICE = os.getenv("INFERENCE_DEVICE", "cpu")

_local_embedder = None

def get_embedder():
    global _local_embedder
    if EMBEDDING_MODEL and _local_embedder is None:
        _local_embedder = SentenceTransformer(EMBEDDING_MODEL, device=INFERENCE_DEVICE)
    return _local_embedder

async def embed_texts(texts: list[str]) -> list[list[float]]:
    embedder = get_embedder()
    if embedder:
        # Local GPU model
        vecs = await asyncio.to_thread(embedder.encode, texts, normalize_embeddings=True)
        return vecs.tolist()
    else:
        # OpenAI API fallback (current behaviour)
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [d.embedding for d in resp.data]
```

### Environment variables for GPU

```bash
# backend/.env (production with GPU)
INFERENCE_DEVICE=cuda
WHISPER_MODEL=large-v3               # best accuracy
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5   # best open-source embedding model

# Keep OpenAI for LLM calls — only switch embeddings + Whisper to local GPU
OPENAI_API_KEY=sk-...
```

### Minimum GPU spec for this hybrid approach

```
Single NVIDIA T4 16GB    — handles embeddings + Whisper for up to ~500 concurrent users
Two NVIDIA A10G 24GB     — handles up to ~2,000 concurrent users
Four NVIDIA A100 40GB    — handles up to ~10,000 concurrent users
```

---

## Step 8 — Backend: Multi-Worker Production Server

### What to change

**File:** `Dockerfile.production` — ensure it uses Gunicorn

```dockerfile
# Dockerfile.production — backend section

FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ .

# Gunicorn with Uvicorn workers
# Formula: workers = (2 × CPU cores) + 1
CMD ["gunicorn", "main:app",
     "--workers", "4",
     "--worker-class", "uvicorn.workers.UvicornWorker",
     "--bind", "0.0.0.0:8004",
     "--timeout", "120",
     "--keep-alive", "5",
     "--access-logfile", "-",
     "--error-logfile", "-"]
```

### Environment variable

```bash
WEB_CONCURRENCY=4    # overrides worker count at runtime
```

### Test

```bash
# Load test — 50 concurrent users, 100 requests each
pip install locust
locust -f tests/locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:8004
# Target: p95 response time < 2000ms, 0% error rate
```

---

## Step 9 — Frontend Production Build

### What to change

**File:** `frontend/.env.production`

```bash
NEXT_PUBLIC_API_URL=https://api.huron.yourcompany.com
NEXT_PUBLIC_APP_ENV=production
```

**File:** `frontend/next.config.js` — add security headers

```javascript
const nextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'no-referrer' },
        ],
      },
    ]
  },
  // Disable source maps in production
  productionBrowserSourceMaps: false,
}
```

### Build & test

```bash
cd frontend
npm run build          # must complete with 0 errors
npm run start          # test production build locally on port 3000

# Check bundle size
npx next build 2>&1 | grep "First Load JS"
# Target: < 300 kB shared JS
```

---

## Step 10 — Structured Logging

### What to change

**File:** `backend/main.py`

```python
# Replace basicConfig logging with structured JSON logging in production

import logging
import json as _json

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            return _json.dumps({
                "time":    self.formatTime(record),
                "level":   record.levelname,
                "logger":  record.name,
                "message": record.getMessage(),
                "module":  record.module,
            })
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("huron")
```

---

## Step 11 — S3 / Blob Storage for Uploaded Files

Currently uploaded files are processed in-memory and discarded. In production,
store originals for audit/reprocessing.

```python
# backend/main.py — in ingest_endpoint, after processing

STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "")   # empty = skip upload

async def _archive_to_s3(file_bytes: bytes, key: str):
    if not STORAGE_BUCKET:
        return
    import boto3
    s3 = boto3.client("s3")
    await asyncio.to_thread(
        s3.put_object,
        Bucket=STORAGE_BUCKET,
        Key=key,
        Body=file_bytes,
        ServerSideEncryption="AES256",
    )
```

### Environment variable

```bash
STORAGE_BUCKET=huron-documents-prod    # AWS S3 bucket name
```

---

## Step 12 — Remove Dev-Only Defaults

**File:** `backend/main.py` — search for these and remove/env-gate them before deploy:

```python
# FIND AND REMOVE / REPLACE:

# 1. Any hardcoded root password or default credentials
#    Search: "HuronRoot" or default_password
#    Replace: Must be set via INITIAL_ROOT_PASSWORD env var, one-time use

# 2. Debug endpoints
#    Search: @app.get("/debug") or similar
#    Replace: Guard with:  if os.getenv("ENVIRONMENT") != "production":

# 3. SQLite auto-seeding of test users
#    Search: seed_demo_users() or similar
#    Replace: Only run when SEED_DEMO_DATA=true (never in production)
```

---

## Pre-Deployment Testing Protocol

### Phase 1 — Unit Tests

```bash
cd "GenAI Knowledge Assistant Huron"
pytest tests/ -v --tb=short
# Target: 100% pass, 0 failures
```

### Phase 2 — Integration Tests

```bash
# Start backend
python backend/main.py &

# Auth flow
pytest tests/test_auth.py -v

# RBAC — confirm each role sees only what it should
pytest tests/test_rbac.py -v

# RAG pipeline — query returns results
pytest tests/test_rag.py -v

# Agent run — completes within 60s
pytest tests/test_agent.py -v --timeout=60
```

### Phase 3 — Security Scan

```bash
# Python dependency vulnerabilities
pip-audit

# Check for secrets accidentally committed
pip install truffleHog
trufflehog git file://. --only-verified

# OWASP ZAP quick scan (requires ZAP running)
zap-cli quick-scan --self-contained --start-options "-config api.disablekey=true" http://localhost:8004
```

### Phase 4 — Load Test

```bash
# Install Locust
pip install locust

# Run load test (file already in tests/)
locust -f tests/locustfile.py \
  --headless \
  -u 100 \            # 100 concurrent users
  -r 10 \             # 10 new users per second ramp-up
  --run-time 120s \
  --host http://localhost:8004

# Pass criteria:
#   p50 response time < 500ms
#   p95 response time < 2000ms
#   Error rate < 0.1%
#   No memory leaks (check RSS over 2 min)
```

### Phase 5 — Smoke Tests After Deploy

```bash
# Run against production URL after deploy
PROD_URL=https://api.huron.yourcompany.com

# Health check
curl -f $PROD_URL/health

# Login works
TOKEN=$(curl -s -X POST $PROD_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"$ROOT_PASSWORD"}' | jq -r .access_token)

# Stats load
curl -H "Authorization: Bearer $TOKEN" $PROD_URL/api/v1/admin/stats

# Query works
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"test","department":"general"}' $PROD_URL/api/v1/query

echo "Smoke tests passed"
```

---

## Production Deploy Order

Run steps in this exact sequence:

```
1.  Set all environment variables in Secrets Manager / ECS task definition
2.  Run database migration:  python migrate_sqlite_to_postgres.py
3.  Verify PostgreSQL row counts match SQLite
4.  Deploy backend container (Fargate / Container App)
5.  Run smoke test against backend only
6.  Deploy frontend container
7.  Verify frontend loads and can log in
8.  Run full smoke test suite
9.  Enable CloudWatch alarms / Datadog monitors
10. Change DNS to point to new ALB / App Gateway
11. Monitor error rate for 30 minutes
12. Remove old SQLite DB from container image
```

---

## Rollback Plan

If anything fails after deploy:

```bash
# ECS rollback (AWS)
aws ecs update-service \
  --cluster huron-cluster \
  --service huron-backend \
  --task-definition huron-backend:PREVIOUS_REVISION \
  --force-new-deployment

# Azure rollback
az containerapp revision activate \
  --name huron-backend \
  --resource-group huron-rg \
  --revision PREVIOUS_REVISION_NAME

# Database rollback (only if schema changed)
psql $DATABASE_URL < backups/pre-deploy-$(date +%Y%m%d).sql
```

---

## Environment Variable Master List

```bash
# ── Required in ALL environments ─────────────────────────
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX=huron-enterprise-knowledge
JWT_SECRET=<64-char random hex>

# ── Required in production only ───────────────────────────
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/huron_db
REDIS_URL=redis://host:6379/0
ALLOWED_ORIGINS=https://huron.yourcompany.com
STORAGE_BUCKET=huron-documents-prod
AWS_SECRET_NAME=huron/prod/app-secrets
AWS_REGION=us-east-1

# ── Optional GPU inference (Step 7) ─────────────────────
INFERENCE_DEVICE=cuda
WHISPER_MODEL=large-v3
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# ── Optional tuning ──────────────────────────────────────
WEB_CONCURRENCY=4
TOKEN_HOURS=8
SOURCE_GUARD_THRESHOLD=0.6
```

---

## Summary Checklist

- [ ] PostgreSQL running and migrated
- [ ] Redis running and tested (blacklist + rate limit)
- [ ] All secrets in Secrets Manager (nothing in `.env` committed)
- [ ] CORS restricted to production domain
- [ ] Security headers active
- [ ] MFA enforced for privileged roles
- [ ] Default credentials removed / changed
- [ ] Debug endpoints removed
- [ ] Multi-worker Gunicorn config in Dockerfile
- [ ] Frontend built with `next build` (0 errors)
- [ ] All unit + integration tests passing
- [ ] Load test passing (p95 < 2s, errors < 0.1%)
- [ ] Security scan clean (pip-audit + truffleHog)
- [ ] Smoke tests passing against production URL
- [ ] Monitoring / alerts configured
- [ ] Rollback plan tested in staging
