# Huron GenAI Knowledge Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?style=flat-square&logo=typescript)](https://typescriptlang.org)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-00C98E?style=flat-square)](https://pinecone.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=flat-square&logo=openai)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

> **Enterprise-grade, multi-tenant AI knowledge platform** — search, reason, and compare policy documents across departments using a production ReAct agent, versioned document ingestion, and role-based namespace isolation backed by Pinecone.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HURON GENAI PLATFORM                               │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                  NEXT.JS 14 FRONTEND  (Port 3000)                   │   │
│   │                                                                     │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │
│   │  │  Login   │ │Dashboard │ │  Chat    │ │  Query   │ │  Agent   │ │   │
│   │  │  + MFA   │ │ + Stats  │ │Assistant │ │Assistant │ │Assistant │ │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │
│   │  │ Document │ │  Index   │ │Analytics │ │  Admin   │ │  Access  │ │   │
│   │  │  Ingest  │ │  Mgmt    │ │ + Audit  │ │  Panel   │ │ Requests │ │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │   │
│   └─────────────────────────┬───────────────────────────────────────────┘   │
│                             │  REST + SSE                                    │
│   ┌─────────────────────────▼───────────────────────────────────────────┐   │
│   │                   FASTAPI BACKEND  (Port 8004)                       │   │
│   │                                                                      │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│   │  │  Auth Layer │  │  RBAC Gate  │  │  Audit Log  │  │Rate Limit │  │   │
│   │  │  JWT + MFA  │  │ 4-Tier Roles│  │ All Actions │  │  SlowAPI  │  │   │
│   │  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └───────────┘  │   │
│   │         │                │                                            │   │
│   │  ┌──────▼────────────────▼────────────────────────────────────────┐  │   │
│   │  │                      API ROUTES                                 │  │   │
│   │  │   /auth  /query  /chat  /ingest  /agent  /admin  /documents    │  │   │
│   │  └──────┬────────────────┬──────────────┬──────────────────────────┘  │   │
│   │         │                │              │                               │   │
│   │  ┌──────▼──────┐  ┌──────▼──────┐  ┌───▼──────────────────────────┐  │   │
│   │  │   ReAct     │  │  Versioned  │  │    RAG Orchestrator           │  │   │
│   │  │   Agent     │  │  Ingestion  │  │    + Source Guard             │  │   │
│   │  │  SSE Stream │  │  All Types  │  │                               │  │   │
│   │  └──────┬──────┘  └──────┬──────┘  └───┬───────────────────────────┘  │   │
│   └─────────┼────────────────┼──────────────┼───────────────────────────────┘   │
│             │                │              │                                     │
│   ┌─────────▼────────────────▼──────────────▼──────────────────────────────┐    │
│   │                         DATA LAYER                                      │    │
│   │                                                                         │    │
│   │  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────────┐ │    │
│   │  │   PINECONE   │  │  SQLite / Postgres│  │        OPENAI APIs        │ │    │
│   │  │  Vector DB   │  │                  │  │  text-embedding-3-small   │ │    │
│   │  │              │  │  users           │  │  gpt-4o / gpt-4o-mini     │ │    │
│   │  │ vaultmind-   │  │  departments     │  │  whisper-1 (audio/video)  │ │    │
│   │  │ huron-{dept} │  │  audit_log       │  └───────────────────────────┘ │    │
│   │  │ -general     │  │  agent_runs      │                                 │    │
│   │  │              │  │  document_       │  ┌───────────────────────────┐ │    │
│   │  │ hr · legal   │  │  versions        │  │   REDIS  (Production)     │ │    │
│   │  │ finance      │  │  access_requests │  │  Sessions + Rate Limits   │ │    │
│   │  │ clinical     │  │  feedback_log    │  └───────────────────────────┘ │    │
│   │  │ operations   │  │  token_blacklist │                                 │    │
│   │  │ it · mktg    │  └──────────────────┘                                 │    │
│   │  │ external     │                                                        │    │
│   │  └──────────────┘                                                        │    │
│   └──────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────────────┘
```
<img width="1651" height="1651" alt="Architecture Design - visual selection (1)" src="https://github.com/user-attachments/assets/bfbf608e-99da-44a6-b2ad-67b910d443d0" />

---

## Features

### AI Agent — Production ReAct Loop
- **Live SSE streaming** — every reasoning step, tool call, and result streams to the browser in real time
- **Namespace-enforced tools** — Pinecone access control lives in the tool layer, not the prompt; the LLM cannot override it
- **Multi-department search** — root and power users search all namespaces simultaneously with `multi_dept_search`
- **Policy comparison** — structured agreements / conflicts / gaps analysis via GPT-4o-mini JSON mode
- **Graceful stop** — mid-run cancel with partial summary generation

### Versioned Document Ingestion
- **All file types** — PDF, DOCX, PPTX, XLSX, CSV, TXT, HTML, JSON, MP4/video (Whisper), MP3/audio (Whisper)
- **Automatic versioning** — every ingest auto-assigns `doc_id` (slug from filename) and `version` (YYYY-MM)
- **is_latest filtering** — all queries filter `{"is_latest": {"$eq": True}}` — stale vectors never surface
- **One-click rollback** — restore any historical version; Pinecone metadata updated atomically
- **Version history panel** — per-department view with full audit trail, expand per-document history

### RBAC — 4-Tier Role System
| Role | Permissions |
|------|-------------|
| `root` | Full platform access — all departments, admin, cross-dept agent search |
| `dept_admin` | Manage users in own dept, approve access requests |
| `power_user` | Cross-department search, analytics, research, agent |
| `user` | Query, chat, ingest within own department namespace only |

### Security
- bcrypt (cost ≥ 12) password hashing — never stored in plaintext
- JWT with in-memory + SQLite token blacklist — logout immediately invalidates sessions
- TOTP MFA — Google Authenticator compatible
- Namespace scope enforced per-request from JWT claims — not from frontend state
- Rate limiting on all auth endpoints (SlowAPI)
- Full audit log written on every action

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript 5.3, Tailwind CSS, Radix UI, Framer Motion |
| Backend | FastAPI 0.115, Uvicorn, Python 3.11 |
| Vector DB | Pinecone — `text-embedding-3-small` (1536-dim), cosine similarity |
| LLM | OpenAI GPT-4o / GPT-4o-mini (function calling) |
| Transcription | OpenAI Whisper-1 — video and audio documents |
| Auth | PyJWT 2.10, bcrypt 4.2, pyotp 2.9 (TOTP) |
| Database | SQLite (development) / PostgreSQL 15 (production) |
| Cache | Redis 7 — production rate-limiting and sessions |
| Streaming | Server-Sent Events (SSE) — native FastAPI `StreamingResponse` |
| CI/CD | GitHub Actions — lint, type-check, security scan, Docker build |
| Deployment | Docker, Azure Container Apps, AWS ECS Fargate |

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Anaconda 3 recommended |
| Node.js | 18 LTS | |
| npm | 9+ | |
| OpenAI API key | — | GPT-4o + embeddings + Whisper |
| Pinecone API key | — | Free Starter plan supports dev |
| Git | 2.x | |

---

## Quick Start (Local Development)

### 1. Clone

```bash
git clone https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git
cd Huron_GenAI_Knowledge_Assistant
```

### 2. Backend — install dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS / Linux)
source venv/bin/activate

# Install core dependencies
pip install -r requirements_production.txt

# Install optional document parsers (recommended)
pip install pdfplumber python-docx python-pptx openpyxl
```

### 3. Configure environment

```bash
# Copy template
cp .env.example backend/.env
```

Open `backend/.env` and fill in:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX=huron-enterprise-knowledge
JWT_SECRET=your-secret-key-minimum-32-characters-long
JWT_EXPIRATION_HOURS=8
# DATABASE_URL=          ← leave blank to use SQLite for development
```

### 4. Create your Pinecone index (first time only)

```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="YOUR_PINECONE_API_KEY")
pc.create_index(
    name="huron-enterprise-knowledge",
    dimension=1536,        # text-embedding-3-small
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
```

### 5. Start the backend

```bash
# From the backend/ directory (with venv active)
python main.py

# Output: Uvicorn running on http://0.0.0.0:8004
# API docs: http://localhost:8004/docs
```

### 6. Frontend — install and configure

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8004" > .env.local
```

### 7. Start the frontend

```bash
npm run dev
# Open: http://localhost:3000
```

### 8. First login

```
URL:      http://localhost:3000
Username: root
Password: HuronRoot2026!
```

> Change the root password immediately after first login via Admin → Users.

---

## Environment Variables Reference

```env
# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...              # Required — LLM + embeddings + Whisper

# ── Pinecone ──────────────────────────────────────────────────────────────────
PINECONE_API_KEY=pcsk_...          # Required
PINECONE_INDEX=huron-enterprise-knowledge

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL=                      # Blank = SQLite (dev)
# Production PostgreSQL:
# DATABASE_URL=postgresql://huron:password@db.host:5432/huron_db

# ── Auth ──────────────────────────────────────────────────────────────────────
JWT_SECRET=<min-32-char-secret>    # Required
JWT_EXPIRATION_HOURS=8

# ── Redis (production only) ───────────────────────────────────────────────────
# REDIS_URL=redis://localhost:6379

# ── Server ────────────────────────────────────────────────────────────────────
PORT=8004
```

---

## Project Structure

```
├── backend/
│   ├── main.py                      # FastAPI app — all routes, auth, RBAC, DB
│   ├── agent/
│   │   ├── react_agent.py           # ReAct loop — OpenAI function calling + SSE
│   │   └── tools.py                 # Pinecone tools with namespace enforcement
│   └── utils/
│       ├── ingestion_service.py     # Versioned multi-format document ingest
│       └── tenant_context.py        # TenantContext dataclass
│
├── frontend/
│   └── src/
│       ├── app/dashboard/
│       │   ├── agent/page.tsx       # AI Agent — live ReAct step streaming
│       │   ├── chat/page.tsx        # Chat Assistant
│       │   ├── query/page.tsx       # Query Assistant (RAG)
│       │   ├── ingest/page.tsx      # Document Ingest + Version History
│       │   ├── analytics/page.tsx   # Analytics + Feedback
│       │   ├── admin/               # Admin Panel (users, depts, access requests)
│       │   └── indexes/page.tsx     # Index Management
│       ├── components/
│       │   ├── Auth/Login.tsx       # WebGL glassmorphism login + TOTP MFA
│       │   ├── Ingestion/DocumentUpload.tsx   # Versioned upload + history panel
│       │   ├── sidebar.tsx          # RBAC-gated navigation with role badge
│       │   └── header.tsx           # Namespace badge + async logout
│       ├── contexts/auth-context.tsx         # JWT state + hasPermission helpers
│       ├── hooks/useAgentStream.ts           # SSE hook for live agent steps
│       └── services/api.ts                   # Full typed API client
│
├── terraform/
│   ├── azure/                       # Azure Container Apps deployment
│   │   ├── providers.tf
│   │   ├── variables.tf
│   │   ├── main.tf
│   │   └── outputs.tf
│   └── aws/                         # AWS ECS Fargate deployment
│       ├── providers.tf
│       ├── variables.tf
│       ├── main.tf
│       └── outputs.tf
│
├── tests/
│   ├── test_agent_integration.py
│   ├── test_agent_search.py
│   └── test_embeddings.py
│
├── config/                          # YAML / JSON configuration files
├── docs/                            # Technical documentation
├── requirements_production.txt      # Backend Python dependencies
├── Dockerfile.production            # Multi-stage production Docker build
└── .env.example                     # Environment variable template
```

---

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/login` | POST | — | Username + password → JWT |
| `/api/v1/auth/mfa/verify` | POST | — | TOTP code → session token |
| `/api/v1/auth/logout` | POST | JWT | Blacklist token |
| `/api/v1/auth/me` | GET | JWT | Current user profile |
| `/api/v1/query` | POST | JWT | RAG query with cited sources |
| `/api/v1/chat` | POST | JWT | Conversational chat |
| `/api/v1/ingest` | POST | JWT | Upload + version + index document |
| `/api/v1/documents/{dept}` | GET | JWT | List latest indexed documents |
| `/api/v1/documents/{dept}/{id}/versions` | GET | JWT | Full version history |
| `/api/v1/documents/{dept}/{id}/rollback` | POST | JWT | Restore a version |
| `/api/v1/documents/{dept}/{id}` | DELETE | JWT | Delete all versions |
| `/api/v1/agent/run` | POST | JWT | Start ReAct agent run |
| `/api/v1/agent/stream/{id}` | GET | `?token=` | SSE live step stream |
| `/api/v1/agent/stop/{id}` | POST | JWT | Stop mid-run |
| `/api/v1/agent/runs` | GET | JWT | Run history |
| `/api/v1/admin/users` | GET | JWT (admin) | List all users |
| `/api/v1/admin/stats` | GET | JWT (admin) | Platform-wide statistics |
| `/api/v1/access-requests` | POST | JWT | Submit access request |
| `/health` | GET | — | Backend health check |

Full interactive docs available at `http://localhost:8004/docs` (Swagger UI).

---

## Docker Deployment

Create `docker-compose.yml` at the project root:

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: ../Dockerfile.production
    ports:
      - "8004:8004"
    env_file:
      - ./backend/.env
    volumes:
      - backend_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8004
    depends_on:
      backend:
        condition: service_healthy

volumes:
  backend_data:
```

```bash
docker compose up --build -d
```

---

## Cloud Deployment

Terraform configurations are in `terraform/azure/` and `terraform/aws/`.

### Azure — Container Apps

```bash
cd terraform/azure

# Initialize
terraform init

# Preview
terraform plan -var="openai_api_key=sk-..." \
               -var="pinecone_api_key=pcsk_..." \
               -var="jwt_secret=your-secret"

# Deploy (approx 8-12 minutes)
terraform apply
```

**Resources provisioned:** Resource Group · VNet · Azure Container Registry · Container Apps Environment · Backend Container App · Frontend Container App · PostgreSQL Flexible Server · Azure Cache for Redis · Key Vault · Storage Account · Application Insights

### AWS — ECS Fargate

```bash
cd terraform/aws

terraform init

terraform plan -var="openai_api_key=sk-..." \
               -var="pinecone_api_key=pcsk_..." \
               -var="jwt_secret=your-secret" \
               -var="aws_region=us-east-1"

# Deploy (approx 12-18 minutes)
terraform apply
```

**Resources provisioned:** VPC · Subnets · Security Groups · ECR · ECS Cluster · Fargate Services · ALB · RDS PostgreSQL · ElastiCache Redis · Secrets Manager · S3 · CloudFront · CloudWatch · IAM Roles

---

## Migrate SQLite → PostgreSQL (Production)

```bash
# Set your production DATABASE_URL
export DATABASE_URL=postgresql://huron:password@host:5432/huron_db

# Run migration
python migrate_sqlite_to_postgres.py
```

---

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v --cov=.

# Run specific suite
pytest tests/test_agent_integration.py -v
```

---

## Contributing

1. Fork and create a feature branch: `git checkout -b feature/your-feature`
2. Follow the code style — no unnecessary comments, no premature abstractions
3. Verify TypeScript: `cd frontend && npm run build`
4. Submit a PR against `main`

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*FastAPI · Next.js 14 · Pinecone · OpenAI · Terraform · Azure · AWS*
