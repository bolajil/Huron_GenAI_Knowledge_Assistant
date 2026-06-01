# Grafana Dashboards

Amazon Managed Grafana is provisioned via Terraform and provides the external monitoring visuals referenced in user reports and cost tracking. It reads from CloudWatch — no data leaves AWS.

---

## Access

1. Get the workspace URL from Terraform:
   ```bash
   cd terraform/aws && terraform output grafana_workspace_url
   ```
2. Open the URL in a browser
3. Sign in with your Active Directory account (via IAM Identity Center / AWS SSO)

First-time admins: assign user access via the Grafana workspace in the AWS Console → **Amazon Managed Grafana → Workspaces → huron-observability → User and group management**

---

## Data Source Setup

After first login:

1. **Configuration → Data Sources → Add data source → CloudWatch**
2. Settings:
   - **Default Region:** us-east-1
   - **Auth Provider:** AWS SDK Default (uses workspace IAM role)
3. Click **Save & Test** — should show "Data source is working"

---

## Dashboard 1 — API Performance

**Purpose:** Monitor backend response times, throughput, and error rates. Include in user-facing reports showing system health.

**Metrics:**
- `AWS/ApplicationELB → TargetResponseTime` — P50, P95, P99 latency
- `AWS/ApplicationELB → HTTPCode_Target_5XX_Count` — error rate
- `AWS/ApplicationELB → RequestCount` — throughput
- Custom CloudWatch metric: `HuronAPI/QueryLatency` (emitted by backend)

**Import JSON:**
```json
{
  "title": "Huron API Performance",
  "panels": [
    {
      "title": "P95 Response Time (ms)",
      "type": "timeseries",
      "targets": [{
        "namespace": "AWS/ApplicationELB",
        "metricName": "TargetResponseTime",
        "statistics": ["p95"],
        "dimensions": { "LoadBalancer": "${alb_suffix}" }
      }]
    },
    {
      "title": "Request Rate (req/min)",
      "type": "stat",
      "targets": [{
        "namespace": "AWS/ApplicationELB",
        "metricName": "RequestCount",
        "statistics": ["Sum"],
        "period": 60
      }]
    },
    {
      "title": "5xx Error Rate (%)",
      "type": "gauge",
      "thresholds": { "steps": [{"color": "green","value": 0},{"color": "yellow","value": 1},{"color": "red","value": 5}] }
    }
  ]
}
```

---

## Dashboard 2 — Infrastructure Health

**Purpose:** ECS task CPU/memory, RDS performance, Redis hit rate.

**Panels:**
- ECS Backend CPU Utilization (avg + max across tasks)
- ECS Backend Memory Utilization
- RDS CPU Utilization + FreeStorageSpace
- ElastiCache CacheHits vs CacheMisses + CacheHitRate
- ECS task count (desired vs running)

**Key metrics:**
```
AWS/ECS → CPUUtilization     (ClusterName=huron-prod, ServiceName=huron-backend-prod)
AWS/ECS → MemoryUtilization
AWS/RDS → CPUUtilization     (DBInstanceIdentifier=huron-prod-db)
AWS/RDS → FreeStorageSpace
AWS/ElastiCache → CacheHits, CacheMisses
```

**Alert thresholds:**
- ECS CPU > 85% → Warning
- RDS CPU > 80% → Warning
- RDS free storage < 5 GB → Critical

---

## Dashboard 3 — LLM Cost Tracking

**Purpose:** Real-time cost visibility by department and query type. Can be embedded in department admin reports.

**How it works:**
The backend logs token counts per query to CloudWatch custom metrics:
```
HuronAPI/TokensUsed     dimensions: {Department, Model}
HuronAPI/EstimatedCost  dimensions: {Department, Model}
```

**Panels:**
- Daily token usage by department (stacked bar chart)
- Estimated daily cost by department (table)
- Top 10 most expensive queries (log insights widget)
- Month-to-date cost trend vs budget

**CloudWatch Logs Insights query for expensive queries:**
```
fields @timestamp, dept_code, query_text, tokens_used, estimated_cost
| filter estimated_cost > 0.01
| sort estimated_cost desc
| limit 20
```

**AWS Cost Explorer integration:**
Add the `ce:GetCostAndUsage` metric source to pull actual AWS bill data alongside application-level estimates.

---

## Dashboard 4 — Security & Auth Events

**Purpose:** Login activity, failed auth attempts, MFA usage, RBAC permission denials.

**CloudWatch log filter patterns:**
```
# Failed logins
{ $.event = "login_failed" }

# MFA failures
{ $.event = "mfa_failed" }

# Permission denied
{ $.status_code = 403 }
```

**Panels:**
- Failed login attempts (last 24h) — bar chart by hour
- Successful logins by role (pie chart)
- WAF blocked requests (from `AWS/WAFV2`)
- Geographic origin of requests (CloudWatch Contributor Insights)

---

## Dashboard 5 — Department Usage

**Purpose:** Per-department query volume, document count, active users. Used in department admin reports.

**Panels:**
- Query volume by department (7-day trend)
- Active users per department (unique users with queries)
- Documents per department (from `HuronAPI/DocumentCount` custom metric)
- Average query response time per department

**Sharing dashboards in user reports:**
1. Open the dashboard in Grafana
2. Click the share icon → **Snapshot** → **Publish to snapshot.raintank.io** (or use "Link sharing" for internal use)
3. Paste the URL into the report template

For embedding in the frontend (future work): use Grafana's iframe embed feature with the workspace's public URL and a read-only API key.

---

## Alerts via SNS

Connect Grafana alerts to SNS for Slack/email notifications:

1. **Alerting → Contact points → Add contact point**
2. Type: `AWS SNS`
3. Topic ARN: `arn:aws:sns:us-east-1:<account>:huron-alerts`
4. Subscribe the SNS topic to Slack via AWS Chatbot or email

**Recommended alert rules:**
- Backend P95 latency > 3s for 5 min → notify #huron-ops
- 5xx rate > 2% → notify #huron-ops (page-worthy at 5%)
- ECS task count drops to 0 → PagerDuty (critical)
- RDS free storage < 3 GB → notify DBA
- WAF rate limit blocks > 100/min → notify security team
