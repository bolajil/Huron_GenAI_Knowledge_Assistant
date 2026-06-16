# Huron GenAI Knowledge Assistant — Demo Guide

## Deploy (From Your Machine)

```bash
cd "GenAI Knowledge Assistant Huron/terraform/azure"
source .secrets.sh
./deploy.sh
```

> **Skip rebuild if images are already in ACR:**
> ```bash
> ./deploy.sh --skip-build
> ```

**Live URLs after deploy:**

| | URL |
|---|---|
| **Frontend** | https://huron-dev-frontend.blacksky-5ed69c74.westus.azurecontainerapps.io |
| **API Docs** | https://huron-dev-backend.blacksky-5ed69c74.westus.azurecontainerapps.io/docs |

---

## Demo Users

| Username | Password | Role | Department | What They See |
|---|---|---|---|---|
| `blanre2026-demo@outlook.com` | Microsoft SSO | **Root Admin** | All | Full admin panel, all departments, all users |
| `root` | `HuronRoot2026!` | **Root Admin** | All | Same as above via username/password |
| `demo_admin` | `HuronDemo2026!` | Dept Admin | HR | HR dept only, can manage HR users |
| `demo_power` | `HuronDemo2026!` | Power User | Finance | Finance dept, advanced query access |
| `demo_user` | `HuronDemo2026!` | Standard User | Operations | Operations dept, read-only queries |
| `demo_viewer` | `HuronDemo2026!` | Viewer | Marketing | Marketing dept, view-only access |

**Demo flow recommendation:**
1. Log in as `root` → show Admin panel and full system view
2. Log out → log in as `demo_admin` (HR) → show dept-scoped experience
3. Log out → log in as `demo_user` (Operations) → show restricted user view

---

## Sample Questions by Department

### HR Department (`demo_admin` / HuronDemo2026!)

**Chat Assistant**
- *"What is the company's parental leave policy and how do I apply for it?"*
- *"Can you explain the steps for a performance improvement plan?"*
- *"What documentation do I need to onboard a new contractor?"*

**Query Assistant**
- `What are the eligibility requirements for FMLA leave?`
- `Summarize the employee disciplinary policy`
- `What is the process for requesting a remote work arrangement?`

**Enhanced Research**
- `Analyze HR compliance requirements for healthcare organizations in 2026`
- `What are best practices for employee engagement in hybrid work environments?`

---

### Finance Department (`demo_power` / HuronDemo2026!)

**Chat Assistant**
- *"What is the expense reimbursement process and what receipts do I need?"*
- *"Walk me through the budget approval workflow for a new project"*
- *"What are the thresholds for purchase order approvals?"*

**Query Assistant**
- `What is the approval process for capital expenditures over $50,000?`
- `Summarize the travel and entertainment expense policy`
- `What financial controls are in place for vendor payments?`

**Enhanced Research**
- `Research healthcare financial benchmarking and cost reduction strategies`
- `What are the latest CMS reimbursement changes affecting hospital revenue cycles?`

---

### Operations Department (`demo_user` / HuronDemo2026!)

**Chat Assistant**
- *"What is the standard procedure for incident reporting?"*
- *"How do I escalate a patient safety concern?"*
- *"What are the steps for scheduling planned maintenance downtime?"*

**Query Assistant**
- `What is the protocol for handling a system outage during patient care hours?`
- `Summarize the supply chain vendor qualification process`
- `What are the SLA requirements for critical infrastructure uptime?`

**Enhanced Research**
- `Research operational efficiency frameworks for hospital systems`
- `What are leading practices for clinical workflow optimization?`

---

### Marketing Department (`demo_viewer` / HuronDemo2026!)

**Chat Assistant**
- *"What are the brand guidelines for external presentations?"*
- *"What is the approval process before publishing a press release?"*
- *"Who do I contact to get the Huron logo in the correct format?"*

**Query Assistant**
- `What is the content approval workflow for social media posts?`
- `Summarize the external communications policy`
- `What are the guidelines for co-branding with healthcare clients?`

**Enhanced Research**
- `Research digital marketing trends in healthcare consulting for 2026`
- `What are best practices for thought leadership content in the consulting industry?`

---

## What to Highlight in the Demo

| Feature | Where to Show It | Talking Point |
|---|---|---|
| SSO Login | Click "Sign in with Microsoft" | No new passwords — uses existing corporate credentials |
| Role-based access | Switch between demo_admin and demo_user | Each employee only sees their department's data |
| Chat Assistant | Ask an HR question as demo_admin | Conversational AI grounded in internal policies, not the public internet |
| Query Assistant | Run a Finance query as demo_power | Retrieval from internal document store with source citations |
| Enhanced Research | Run a research query as root | Combines internal knowledge + live web sources into a structured report |
| Admin Dashboard | Log in as root → Dashboard tab | Real-time usage metrics across departments |
| Audit Trail | Root → Admin → Users | Every query logged by user, department, and timestamp |

---

## What This Platform Brings to Huron

See the [Value Proposition](#value-proposition) section below.

---

## Value Proposition

### Huron GenAI Knowledge Assistant — Business Impact

Huron operates across HR, Finance, Operations, Clinical, and Marketing with thousands of policies, procedures, and compliance documents. Today, employees lose productive time searching for answers across SharePoint sites, email threads, and phone calls to colleagues. This platform changes that.

| Capability | Current State | With Huron GenAI |
|---|---|---|
| **Policy Lookup** | Staff search SharePoint manually (avg. 15–20 min per query) | Instant answer in seconds, cited to source document |
| **Compliance Awareness** | Quarterly training sessions, high knowledge decay | Always-on, accurate answers grounded in current policy |
| **Cross-Department Knowledge** | Siloed — HR doesn't see Finance procedures and vice versa | Role-based access ensures the right people see the right content |
| **New Employee Onboarding** | HR team spends hours answering repetitive FAQs | Employees self-serve from day one |
| **Research & Synthesis** | Consultants manually compile reports from multiple sources | Enhanced Research generates structured reports in under 60 seconds |
| **Audit & Governance** | No visibility into who asked what or when | Full audit trail — every query logged by user, role, and department |
| **Security** | Documents shared over email, risk of oversharing | Least-privilege access — each user sees only their department's content |
| **Integration** | Documents locked in SharePoint, Workday, Teams silos | Single interface connecting SharePoint, Workday HR data, and Teams |

### Why Now

| Driver | Detail |
|---|---|
| **CMS 2026 Compliance** | New prior authorization rules require rapid policy lookups during clinical workflow |
| **AI Adoption Momentum** | Huron clients are deploying AI; Huron must demonstrate it internally first |
| **Cost Pressure** | Healthcare consulting margins are tightening — knowledge efficiency is a direct cost lever |
| **Talent Retention** | Staff cite "can't find information quickly" as a top frustration in exit interviews |

### Technical Differentiators

| Capability | Detail |
|---|---|
| **No vendor lock-in** | LLM cascade: OpenAI → Mistral → DeepSeek. System works if any provider goes down |
| **On-premises ready** | SQLite default, PostgreSQL for production — no mandatory cloud database vendor |
| **Secure by design** | JWT auth, bcrypt passwords, RBAC on every endpoint, audit log on every query |
| **Built for Huron's stack** | Azure Container Apps, Azure AD SSO, SharePoint connector, Workday sync |
| **Extensible** | Agent framework supports custom tools — Workday lookups, SharePoint search, Teams notifications |
