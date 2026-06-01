# Huron GenAI Knowledge Assistant - Project Structure

> **Architecture Update (v4.0):** This project uses **FastAPI + Next.js**, not Streamlit.
> Some legacy documentation in `/docs/archive/` may reference the old Streamlit architecture.

## Application Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HURON GENAI PLATFORM                               │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                  NEXT.JS 14 FRONTEND  (Port 3000)                   │   │
│   │  React 18 · TypeScript · Tailwind CSS · Radix UI · Framer Motion   │   │
│   └─────────────────────────┬───────────────────────────────────────────┘   │
│                             │  REST + SSE                                   │
│   ┌─────────────────────────▼───────────────────────────────────────────┐   │
│   │                   FASTAPI BACKEND  (Port 8004)                      │   │
│   │  Python 3.11 · JWT Auth · RBAC · ReAct Agent · SSE Streaming        │   │
│   └─────────────────────────┬───────────────────────────────────────────┘   │
│                             │                                               │
│   ┌─────────────────────────▼───────────────────────────────────────────┐   │
│   │                         DATA LAYER                                  │   │
│   │  Pinecone (Vector) · PostgreSQL/SQLite · Redis · OpenAI APIs        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

### `/backend/` - FastAPI Backend
```
backend/
├── main.py                 # Main FastAPI application (legacy monolith)
├── app.py                  # Refactored entry point (modular)
├── core/                   # Core utilities
│   ├── config.py           # Configuration & environment
│   ├── database.py         # Database connection utilities
│   ├── security.py         # JWT, auth, encryption
│   └── migrations.py       # Database schema migrations
├── models/                 # Pydantic schemas
│   └── schemas.py          # Request/response models
├── routes/                 # API route modules
│   ├── auth.py             # Authentication endpoints
│   ├── admin.py            # Admin/root endpoints
│   └── health.py           # Health check
├── agent/                  # ReAct Agent
│   ├── react_agent.py      # ReAct loop with OpenAI function calling
│   └── tools.py            # Pinecone tools with namespace enforcement
└── utils/                  # Utilities
    ├── ingestion_service.py # Versioned document ingestion
    └── tenant_context.py    # Multi-tenant context
```

### `/frontend/` - Next.js Frontend
```
frontend/
├── src/
│   ├── app/                # Next.js App Router
│   │   ├── dashboard/      # Dashboard pages
│   │   │   ├── agent/      # AI Agent interface
│   │   │   ├── chat/       # Chat Assistant
│   │   │   ├── query/      # Query Assistant (RAG)
│   │   │   ├── ingest/     # Document ingestion
│   │   │   ├── analytics/  # Analytics & feedback
│   │   │   ├── admin/      # Admin panel
│   │   │   └── indexes/    # Index management
│   │   └── (auth)/         # Auth pages (login, MFA)
│   ├── components/         # Reusable React components
│   ├── contexts/           # React contexts (auth, theme)
│   ├── hooks/              # Custom hooks (useAgentStream)
│   └── services/           # API client
├── package.json
└── Dockerfile.production
```

### `/terraform/` - Infrastructure as Code
```
terraform/
├── aws/                    # AWS ECS Fargate deployment
│   ├── main.tf             # VPC, ECS, RDS, Redis, WAF
│   ├── variables.tf        # Input variables
│   └── outputs.tf          # Output values
└── azure/                  # Azure Container Apps deployment
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

### `/config/` - Configuration Files
- `llm_config.yml` - LLM model configuration
- `security_config.json` - Auth provider settings
- `dept_namespace_registry.yml` - Department namespaces

### `/tests/` - Test Suite
```
tests/
├── unit/                   # Unit tests
├── integration/            # Integration tests
├── security/               # Security tests
├── test_agent_integration.py
├── test_agent_search.py
└── test_embeddings.py
```

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile.production` | Multi-stage FastAPI production build |
| `docker-compose.local.yml` | Local development with SQLite |
| `requirements_production.txt` | Python dependencies |
| `.env.example` | Environment variable template |
| `Makefile` | Common development commands |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI, Uvicorn, Python 3.11 |
| Vector DB | Pinecone (text-embedding-3-small, 1536-dim) |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Auth | JWT + bcrypt + TOTP MFA |
| Database | SQLite (dev) / PostgreSQL 15 (prod) |
| Cache | Redis 7 |
| IaC | Terraform (AWS + Azure) |

## Key Features

- **ReAct Agent** with live SSE streaming
- **Versioned Document Ingestion** with rollback
- **4-Tier RBAC** (root, dept_admin, power_user, user)
- **Namespace Isolation** per department
- **MCP Tool Layer** for Slack, Email, PDF exports
- **WAF + Rate Limiting** for security
