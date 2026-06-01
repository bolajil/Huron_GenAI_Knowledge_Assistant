# Cost Estimates

All prices are USD, us-east-1, on-demand pricing (no reserved instances or savings plans applied). Add ~30% buffer for data transfer, CloudWatch logs storage, and miscellaneous API calls.

---

## Dev / Staging Tier

Intended for: developer testing, QA, stakeholder demos. Not HA, not HIPAA-ready.

| Service | Config | Monthly est. |
|---------|--------|-------------|
| RDS PostgreSQL 16 | db.t3.medium, 20 GB, single-AZ | $30 |
| ElastiCache Redis 7 | cache.t3.micro | $12 |
| ECS Fargate — Backend | 2 vCPU / 4 GB, 1 task, ~730 h/mo | $58 |
| ECS Fargate — Frontend | 0.5 vCPU / 1 GB, 1 task | $15 |
| ALB | 1 instance | $16 |
| NAT Gateway | 1 AZ + data transfer | $32–50 |
| VPC Interface Endpoints | 4 endpoints × $7.30 | $29 |
| ECR | 2 repos, ~2 GB stored | $0.20 |
| S3 | Documents storage, 50 GB | $1.15 |
| CloudWatch | Logs + metrics | $5–15 |
| WAF | $5/ACL + $0.60/1M requests | $10–20 |
| Grafana | 1 workspace, 1 editor | $9 |
| Secrets Manager | 8 secrets | $3.20 |
| **Total (dev/staging)** | | **~$220–260/month** |

---

## Production Tier

Intended for: live user traffic, HIPAA clinical data. Multi-AZ, HA, WAF, Pinecone PrivateLink.

| Service | Config | Monthly est. |
|---------|--------|-------------|
| RDS PostgreSQL 16 | db.t3.large, 100 GB, Multi-AZ | $150 |
| ElastiCache Redis 7 | cache.t3.small, cluster mode | $55 |
| ECS Fargate — Backend | 2 vCPU / 4 GB, 2–4 tasks | $116–230 |
| ECS Fargate — Frontend | 0.5 vCPU / 1 GB, 2 tasks | $30 |
| ALB | 1 instance + traffic | $25–40 |
| CloudFront | CDN for frontend | $5–20 |
| NAT Gateway | 2 AZs + data transfer | $65–100 |
| VPC Interface Endpoints | 4 endpoints × 2 AZs | $58 |
| ECR | 2 repos | $0.20 |
| S3 | Documents, 500 GB | $11.50 |
| CloudWatch | Logs + metrics + alarms | $20–40 |
| WAF | Higher traffic | $25–50 |
| Grafana | 1 workspace, 5 editors | $9 + $5/editor |
| Secrets Manager | 12 secrets | $4.80 |
| Route 53 | Hosted zone + queries | $1 |
| Pinecone PrivateLink | Contact Pinecone for pricing | ~$50–100 |
| **Total (prod)** | | **~$650–900/month** |

---

## LLM API Costs (separate from AWS)

These are Pinecone + OpenAI costs — not included in AWS estimates above.

| Service | Unit price | Estimate (1000 queries/day) |
|---------|-----------|---------------------------|
| OpenAI gpt-4o | $5/1M input tokens, $15/1M output | $200–400/month |
| OpenAI text-embedding-3-small | $0.02/1M tokens | $5–15/month |
| Pinecone | Serverless — $0.096/1M reads | $15–50/month |
| **Total LLM** | | **~$220–465/month** |

---

## Cost Optimization Tips

**Immediate wins (apply before production):**

1. **Savings Plans** — 1-year compute savings plan cuts ECS Fargate by ~20–30%
2. **RDS reserved instances** — 1-year reserved: ~40% discount on RDS
3. **S3 Intelligent-Tiering** — for documents not accessed in 30+ days, automatic archival
4. **CloudWatch log retention** — set 30-day retention on dev log groups (default is never-expire)

**As usage scales:**

5. **PgBouncer connection pooling** — defer RDS scale-up by 2–3x
6. **ElastiCache query result caching** — reduces OpenAI embedding calls for repeated queries
7. **CloudFront caching** — static asset caching reduces ALB + ECS frontend load

**Monitoring actual spend:**

- Enable AWS Cost Explorer with daily granularity
- Set billing alerts at $500, $750, $1000/month
- The Grafana "LLM Cost Tracking" dashboard (see GRAFANA_DASHBOARDS.md) shows application-level cost per department in near-real-time

---

## Phase-by-Phase Cumulative Cost

| Phase | What you're paying for | Running monthly |
|-------|------------------------|----------------|
| Phase 0 | Local dev only | $0 AWS |
| Phase 1 | Infrastructure standing up (no app traffic) | ~$100 |
| Phase 2 | Dev/staging with real traffic | ~$220–260 |
| Phase 3 | Production full-HA | ~$880–1,400 (AWS + LLM) |
