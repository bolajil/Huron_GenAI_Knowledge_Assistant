# VaultMind → Huron Enterprise Knowledge Platform
## Master Implementation Plan

**Project**: GenAI Knowledge Assistant Huron  
**Repository**: github.com/bolajil/genai-knowledge-assistant  
**Target**: Huron Consulting — Multi-Department Enterprise AI  
**Started**: May 2026  

---

## Current Status: Phase 0 — Project Setup ✅

| Item | Status |
|------|--------|
| New project directory created | ✅ |
| GitHub repo cloned | ✅ |
| Codebase structure verified | ✅ |

---

## Phase Overview

| Phase | Name | Weeks | Status | Blocker |
|-------|------|-------|--------|---------|
| **0** | Project Setup & Security Cleanup | 0 | 🔄 In Progress | None |
| **1** | Foundation & Namespace Migration | 1-4 | ⏳ Pending | Phase 0 |
| **2** | Advanced Ingestion Pipeline | 3-7 | ⏳ Pending | Phase 1 |
| **3** | Agentic RAG Orchestrator | 6-12 | ⏳ Pending | Phase 2 |
| **4** | HR Pilot Namespace | 10-14 | ⏳ Pending | Phase 3 |
| **5** | Full Department Rollout | 13-20 | ⏳ Pending | Phase 4 |
| **6** | Hardening, Security & GA | 20-24 | ⏳ Pending | Phase 5 |

---

## PHASE 0: Project Setup & Security Cleanup
**Duration**: Immediate (Day 1)  
**Blockers**: None  

### 0.1 Critical Security Tasks

| Task | Priority | File/Location | Status |
|------|----------|---------------|--------|
| Remove personal documents from git history | 🔴 CRITICAL | `archive_cleanup_20250919_082734/uploads/` | ⏳ |
| Run BFG Repo Cleaner or git-filter-repo | 🔴 CRITICAL | Entire repo | ⏳ |
| Audit .env.example for exposed secrets | 🔴 HIGH | `.env.example` | ⏳ |
| Check all .md files for sensitive data | 🟡 MEDIUM | Root directory | ⏳ |

### 0.2 File Consolidation (Required before Phase 1)

| Duplicate Set | Keep | Archive |
|--------------|------|---------|
| `chat_assistant*.py` (7 variants) | `chat_assistant_enterprise.py` | All others |
| `agent_assistant*.py` (5 variants) | `agent_assistant_enhanced.py` | All others |
| `enhanced_research*.py` (3 variants) | `enhanced_research_optimized.py` | All others |
| `chat_orchestrator*.py` (3 versions) | Single orchestrator | `chat_orchestrator2.py`, `query_llm.py` |
| `weaviate_adapter*.py` (2 versions) | `weaviate_adapter_fixed.py` | Original |
| `query_helpers.py` (3 locations) | `utils/query_helpers.py` | `app/utils/`, `template/` |
| `ingest_helpers.py` (4 locations) | `utils/ingest_helpers.py` | All others |

### 💡 My Suggestions for Phase 0

1. **Before running BFG**: Create a backup branch with `git checkout -b backup-original`
2. **Consolidation approach**: Create an `_archived/` folder rather than deleting — preserves code for reference
3. **Add pre-commit hooks**: Prevent future secrets from being committed
4. **.env.example audit**: I'll scan this file and flag any real credentials

---

## PHASE 1: Foundation & Namespace Migration
**Duration**: Weeks 1-4  
**Depends On**: Phase 0 complete  

### 1.1 Pinecone Namespace Enforcement

| Task | File | Change Required |
|------|------|-----------------|
| Add namespace parameter to `upsert()` | `utils/adapters/pinecone_adapter.py` | ~10 lines |
| Add namespace parameter to `query()` | `utils/adapters/pinecone_adapter.py` | ~10 lines |
| Reject calls without `dept_id` | `utils/adapters/pinecone_adapter.py` | Validation |
| Upgrade Pinecone to Enterprise plan | Pinecone Dashboard | Manual |
| Enable dedicated read nodes | Pinecone Dashboard | Finance, Legal, Clinical |

### 1.2 JWT Department Claims

| Task | File | Change Required |
|------|------|-----------------|
| Add `dept_id` to JWT payload | `app/auth/authentication.py` | `generate_token()` |
| Add `clearance_level` to JWT | `app/auth/authentication.py` | `generate_token()` |
| Extract dept from Okta groups | `app/auth/okta_connector.py` | Group mapping |
| Extract dept from Azure AD | `app/auth/ad_connector.py` | Group mapping |
| Add `dept_id` to User model | `app/auth/authentication.py` | SQLite schema |

### 1.3 Configuration Files to Create

| File | Purpose |
|------|---------|
| `config/dept_namespace_registry.yml` | Department-to-namespace mapping + attention profiles |
| `config/namespace_encryption.json` | Per-namespace KMS key configuration |
| `config/audit_config.yml` | S3 WORM bucket settings for audit logs |

### 1.4 Tests Required

| Test | Expected Result |
|------|-----------------|
| Cross-namespace query attempt | HTTP 403 Forbidden |
| JWT without `dept_id` | HTTP 401 Unauthorized |
| Upsert without `dept_id` | ValueError raised |
| Query without `dept_id` | ValueError raised |

### 💡 My Suggestions for Phase 1

1. **Create a TenantContext class**: Centralize `dept_id`, `tenant_id`, `clearance_level` — inject everywhere
2. **Add middleware pattern**: FastAPI middleware to extract and validate JWT claims before any route
3. **Database migration**: Use Alembic to add `dept_id` column safely
4. **Unit test isolation**: Each namespace test should use a unique test namespace (e.g., `test_legal_001`)

---

## PHASE 2: Advanced Ingestion Pipeline
**Duration**: Weeks 3-7  
**Depends On**: Phase 1 complete  

### 2.1 Hierarchical Chunking

| Task | File | Change Required |
|------|------|-----------------|
| Replace `RecursiveCharacterTextSplitter(500/50)` | `app/utils/ingest_helpers.py` | New chunker |
| Implement parent (1024 token) / child (256 token) strategy | `utils/enterprise_semantic_chunking.py` | Extend |
| Add `parent_id` metadata to chunks | `app/utils/ingest_helpers.py` | Metadata injection |
| Add `dept_id` metadata to all chunks | `app/utils/ingest_helpers.py` | Metadata injection |

### 2.2 Document Processing

| Task | Tool/Library | Purpose |
|------|--------------|---------|
| PDF/DOCX/XLSX extraction | Unstructured.io | Table and form extraction |
| DLP scan before ingestion | AWS Macie | PHI/PII auto-redaction |
| Quality gate | `utils/ml_models/data_quality_checker.py` | Reject low-quality chunks |
| Document classification | `utils/ml_models/document_classifier.py` | Auto-categorization |

### 2.3 Web Crawling per Department

| Task | File | Configuration |
|------|------|---------------|
| Set up Firecrawl | `config/dept_namespace_registry.yml` | Per-dept seed URLs |
| Schedule crawlers | `celery_worker.py` | Recurring ingestion |
| Add 90-day TTL | External namespace | Auto-expire old content |

### 💡 My Suggestions for Phase 2

1. **Chunking strategy selector**: Different docs need different strategies — detect doc type first
2. **Parallel ingestion**: Use Celery to process multiple documents concurrently
3. **Progress tracking**: Add ingestion job status table for UI visibility
4. **Rollback capability**: Store original document alongside chunks for re-processing

---

## PHASE 3: Agentic RAG Orchestrator
**Duration**: Weeks 6-12  
**Depends On**: Phase 2 complete  

### 3.1 LangGraph Pipeline Stages

| Stage | Node | Existing Code | New Code |
|-------|------|---------------|----------|
| 1 | Query Ingestion | `auth_middleware.py` | Extract `dept_id` |
| 2 | Intent Classification | `query_intent_classifier.py` ✅ | Wire into LangGraph |
| 3 | Namespace-Locked Retrieval | `pinecone_adapter.py` | Hybrid search |
| 4 | Cross-Encoder Reranking | `advanced_reranker.py` ✅ | Wire + attention profiles |
| 5 | Hierarchical Context Assembly | `enterprise_semantic_chunking.py` | Auto-merge parent chunks |
| 6 | LLM Generation | `query_llm.py` | Dept prompt + guardrails |
| 7 | Faithfulness Validation | NEW | Ragas scoring + HITL |

### 3.2 Intent Routing

| Intent | Retrieval Strategy | LLM |
|--------|-------------------|-----|
| Factual | Direct FAISS/Pinecone | gpt-4o-mini |
| Analytical | Hybrid search | gpt-4o |
| Procedural | Section-based | gpt-4o |
| Comparative | Multi-source | gpt-4o |
| Exploratory | Web-augmented | gpt-4o |

### 3.3 Integration Points

| Component | Wire To | Purpose |
|-----------|---------|---------|
| `query_intent_classifier.py` | Stage 2 | Route query type |
| `advanced_reranker.py` | Stage 4 | Confidence scoring |
| `monitoring/alerts.py` | Stage 7 | Low faithfulness alerts |
| LangSmith | All stages | Tracing |

### 💡 My Suggestions for Phase 3

1. **Start with 3-stage MVP**: Intent → Retrieve → Generate — add reranking and validation after
2. **Create a pipeline config**: YAML-based stage configuration for easy tuning
3. **A/B testing framework**: Route 10% of queries to experimental pipeline
4. **Latency budgets**: Set per-stage timeout (e.g., Stage 2: 50ms, Stage 3: 500ms)

---

## PHASE 4: HR Pilot Namespace
**Duration**: Weeks 10-14  
**Depends On**: Phase 3 complete  

### 4.1 HR Document Ingestion

| Document Type | Source | Priority |
|--------------|--------|----------|
| HR Policies | Internal docs | High |
| Benefits Documents | HR portal | High |
| Org Charts | HRIS export | Medium |
| Employee Handbooks | Shared drives | High |

### 4.2 User Acceptance Testing

| Test | Queries | Target |
|------|---------|--------|
| Intent coverage | 50 queries across all 5 types | >90% routing accuracy |
| Faithfulness | 50 query-answer pairs | ≥0.85 Ragas score |
| Isolation | HR user → Legal namespace | 403 Forbidden |
| Latency | 100 queries | P95 < 2s |

### 4.3 Sign-Off Criteria

| Metric | Target | Measured By |
|--------|--------|-------------|
| Faithfulness | ≥ 0.85 | Ragas eval harness |
| Cross-namespace breaches | 0 | Security audit |
| P95 latency | < 2s | LangSmith traces |
| HITL queue functional | Yes | Manual test |

### 💡 My Suggestions for Phase 4

1. **Shadow mode first**: Run pipeline in parallel with existing system for 1 week
2. **Feedback loop**: Collect user feedback on every query during pilot
3. **Weekly tuning**: Adjust attention profiles based on HR team feedback
4. **Escape hatch**: Keep old system accessible during pilot

---

## PHASE 5: Full Department Rollout
**Duration**: Weeks 13-20  

### Rollout Schedule

| Week | Department | Namespace | Special Requirements |
|------|------------|-----------|---------------------|
| 13-14 | Finance | `finance` | Dedicated read nodes |
| 14-15 | Operations | `operations` | SOP-focused chunking |
| 15-16 | IT | `it` | Technical doc parsing |
| 16-17 | Legal | `legal` | Dedicated read nodes, regulatory focus |
| 17-18 | Marketing | `marketing` | Brand asset handling |
| 18-19 | External | `external` | Firecrawl configuration |
| 19-20 | Clinical | `clinical` | **HIPAA BAA required** |

### Per-Department Checklist

- [ ] Ingest all department documents
- [ ] Configure attention profile
- [ ] Wire SSO group mapping
- [ ] Run 50-query acceptance test
- [ ] Test cross-dept isolation (3 other depts)
- [ ] Train department admin

### 💡 My Suggestions for Phase 5

1. **Clinical last**: HIPAA BAA with Pinecone + OpenAI takes time — don't let it block others
2. **Template rollout script**: Automate namespace provisioning
3. **Department champions**: Assign one power user per dept for feedback
4. **Rollback plan**: Document per-dept rollback procedure

---

## PHASE 6: React Frontend Migration
**Duration**: Weeks 18-22  
**Reason**: Streamlit is slow for production; React provides better UX  

### 6.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  (Next.js 14 + TypeScript + Tailwind + shadcn/ui)       │
├─────────────────────────────────────────────────────────┤
│                    FastAPI Backend                       │
│  /api/v1/auth  /api/v1/ingest  /api/v1/query  /api/v1/admin │
├─────────────────────────────────────────────────────────┤
│     Pinecone    │    PostgreSQL    │    Redis Cache     │
└─────────────────────────────────────────────────────────┘
```

### 6.2 React App Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 14 app router
│   │   ├── (auth)/             # Login, register
│   │   ├── (dashboard)/        # Main dashboard
│   │   │   ├── chat/           # Chat assistant
│   │   │   ├── query/          # Query assistant
│   │   │   ├── ingest/         # Document ingestion
│   │   │   ├── admin/          # Admin panel
│   │   │   └── settings/       # User settings
│   │   └── api/                # API routes (proxy to FastAPI)
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── chat/               # Chat-specific components
│   │   ├── documents/          # Document list, viewer
│   │   └── admin/              # Admin components
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── auth.ts             # Auth utilities
│   │   └── tenant-context.ts   # Multi-tenant context
│   └── hooks/
│       ├── useChat.ts          # Chat state management
│       ├── useDocuments.ts     # Document CRUD
│       └── useTenant.ts        # Tenant context hook
├── package.json
└── tailwind.config.ts
```

### 6.3 Key React Features

| Feature | Technology | Benefit |
|---------|------------|---------|
| Real-time chat | React Query + WebSocket | No page refreshes |
| Document upload | React Dropzone | Drag-and-drop UX |
| State management | Zustand or Jotai | Lightweight, fast |
| Auth | NextAuth.js | SSO, OAuth, JWT |
| UI Components | shadcn/ui | Enterprise-grade look |
| Streaming | Server-Sent Events | Token streaming for LLM |

### 6.4 Migration Strategy

| Week | Task |
|------|------|
| 18 | Set up Next.js project, auth flow |
| 19 | Build chat interface with streaming |
| 20 | Document ingestion UI, query interface |
| 21 | Admin panel, department selector |
| 22 | Testing, deployment, Streamlit deprecation |

### 💡 Suggestion

Keep Streamlit for **internal admin/debugging** while React serves production users.

---

## PHASE 7: Hardening, Security & GA
**Duration**: Weeks 22-26  

### 6.1 Security & Compliance

| Task | Owner | Evidence |
|------|-------|----------|
| Penetration testing | External firm | Report |
| Cross-namespace isolation verification | Security team | Test results |
| SOC 2 Type II evidence collection | Compliance | Audit package |
| HITRUST CSF gap analysis (Clinical) | Compliance | Report |

### 6.2 Performance Validation

| Test | Target | Duration |
|------|--------|----------|
| 500 concurrent users | P95 < 2s | 1 hour |
| Namespace node failure | Graceful fallback | Chaos test |
| Query burst (1000 RPS) | No 5xx errors | 5 minutes |

### 6.3 GA Sign-Off

| Metric | Target |
|--------|--------|
| All 8 namespaces live | ✅ |
| Faithfulness score | ≥ 0.90 |
| Cross-namespace breaches | 0 |
| Pen test passed | ✅ |
| SOC 2 evidence complete | ✅ |

---

## Immediate Next Steps (Priority Order)

| # | Action | Blocker | Can Start |
|---|--------|---------|-----------|
| 1 | Remove personal docs from git history | None | ✅ Now |
| 2 | Consolidate duplicate tab files | None | ✅ Now |
| 3 | Add `dept_id` to JWT | Phase 0 done | After #1, #2 |
| 4 | Add namespace to `pinecone_adapter.py` | Phase 0 done | After #1, #2 |
| 5 | Create `dept_namespace_registry.yml` | None | ✅ Now |
| 6 | Wire `query_intent_classifier.py` | Phase 1 done | After #3, #4 |
| 7 | Wire `AdvancedReranker` | Phase 1 done | After #3, #4 |
| 8 | Set up LangSmith tracing | None | ✅ Now |
| 9 | Upgrade Pinecone to Enterprise | Budget approval | When ready |
| 10 | Begin HR pilot ingestion | Phases 1-3 done | Week 10 |

---

## File Index: What Exists vs What To Create

### ✅ Existing (Reuse)
- `app/agents/controller_agent.py` — Core execution engine
- `utils/adapters/pinecone_adapter.py` — Needs namespace upgrade
- `utils/ml_models/query_intent_classifier.py` — Full TF LSTM model
- `utils/advanced_reranker.py` — Multi-signal reranker
- `app/auth/authentication.py` — JWT generation
- `app/auth/enterprise_auth.py` — MFA + SSO

### 🆕 To Create
- `config/dept_namespace_registry.yml` — Department config
- `utils/tenant_context.py` — Centralized tenant/dept context
- `api/middleware/tenant_middleware.py` — JWT claim extraction
- `utils/hierarchical_chunker.py` — Parent/child chunking
- `utils/faithfulness_validator.py` — Ragas integration
- `tabs/dept_namespace_admin.py` — Namespace management UI

---

## Progress Tracking

This document will be updated as each phase completes. See individual phase checklists in:
- `PHASE_0_CHECKLIST.md`
- `PHASE_1_CHECKLIST.md`
- (etc.)

---

**Next Action**: Start Phase 0 — Security cleanup and file consolidation
