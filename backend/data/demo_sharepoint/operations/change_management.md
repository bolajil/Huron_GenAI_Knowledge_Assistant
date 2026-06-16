# Change Management Procedure (Demo Document)
**Version:** 2026.1 | **Classification:** Internal | **Owner:** Operations & IT

---

## 1. Purpose

This procedure governs how changes to Huron's production systems, infrastructure, and business-critical tools are planned, approved, tested, and implemented. Proper change management reduces the risk of unplanned outages and data integrity issues caused by uncoordinated modifications.

---

## 2. Scope

This procedure applies to all changes to:
- Production infrastructure (cloud, on-premises servers, network)
- Business-critical SaaS platforms (Workday, Salesforce, SharePoint, ServiceNow)
- Huron-developed applications (internal and client-facing)
- Security controls, access permissions, and firewall rules
- Database schemas and configurations in production

It does **not** apply to: development/staging environments, personal workstations, or pre-approved standard operating procedures (SOPs).

---

## 3. Change Categories

### Standard Change
A **pre-approved, low-risk, repeatable** change following a documented, tested procedure. No individual review required.
- Examples: OS patch during maintenance window, user account provisioning, certificate renewal
- Process: Submit Standard Change request in ServiceNow → auto-approved → implement during allowed window

### Normal Change
A **planned change** requiring risk assessment and CAB approval before implementation.
- Examples: Application deployment, infrastructure upgrade, new integration, schema migration
- Lead time: Minimum **5 business days** before planned implementation date

### Emergency Change
An **unplanned change** required to immediately resolve a P1/P2 incident or critical security vulnerability.
- Verbal approval from Change Manager + VP Operations before implementation
- Full documentation retroactively within 24 hours
- Reviewed at next CAB meeting

---

## 4. Normal Change Process

### Step 1: Submit Change Request (CR)
The Change Requestor submits a CR in ServiceNow (IT → Changes → Create New) with:
- **Summary:** What is changing and why
- **Business Justification:** Impact if not done
- **Technical Implementation Plan:** Step-by-step; who does what
- **Rollback Plan:** How to revert if the change fails (must exist for every change)
- **Testing Plan:** How success is verified
- **Risk Assessment:** Low / Medium / High, with rationale
- **Scheduled Window:** Proposed date/time and expected duration
- **Affected Systems:** All impacted services, dependencies

### Step 2: Technical Review
The relevant system owner and a peer engineer review the CR for technical accuracy and completeness. Peer review must be documented in ServiceNow comments.

### Step 3: CAB Review
The Change Advisory Board (CAB) reviews all Normal Changes weekly (Thursdays at 2:00 PM CT).
- **Quorum:** Change Manager + 2 of: Infrastructure Lead, Security Lead, Application Lead
- **Outcome:** Approved / Approved with conditions / Deferred / Rejected
- Requestor must attend the CAB meeting if the change is High risk

### Step 4: Pre-Implementation
- Change Manager confirms approval in ServiceNow (status → Approved)
- Requestor notifies affected teams at least 24 hours in advance
- Maintenance window communicated on internal status page

### Step 5: Implementation
- Begin only within the approved maintenance window
- Log all actions in the CR with timestamps
- Test per the documented Testing Plan
- If rollback triggered, notify Change Manager and log reason immediately

### Step 6: Post-Implementation Review
- Update CR status to Successful / Unsuccessful / Rolled Back
- Document outcome and any deviations
- Lessons learned added if rollback was triggered or duration exceeded estimate by >50%

---

## 5. Maintenance Windows

| Window | Schedule | Permitted Changes |
|---|---|---|
| Standard | Saturdays 10 PM – 2 AM CT | Low/Medium risk normal changes |
| Extended | Sundays 6 PM – 6 AM CT (monthly) | High risk or extended changes |
| Emergency | Any time, with approval | Emergency changes only |
| Frozen (Change Freeze) | Per calendar below | Emergency changes only |

### Change Freeze Dates (2026)
| Period | Reason |
|---|---|
| Dec 23 – Jan 2 | Holiday freeze |
| Mar 30 – Apr 3 | Q1 Financial Close |
| Jun 30 – Jul 2 | H1 Financial Close |
| Sep 30 – Oct 2 | Q3 Financial Close |

---

## 6. Risk Assessment Guide

| Factor | Low | Medium | High |
|---|---|---|---|
| Users affected | < 50 | 50–500 | > 500 |
| Downtime expected | None | < 1 hour | > 1 hour |
| Rollback complexity | Simple, tested | Moderate | Complex or untested |
| Testing environment | Full staging parity | Partial | No staging |
| Change frequency | Done before | Infrequent | First time |

A single High factor elevates the overall risk to the next tier.

---

## 7. Contacts

| Role | Name | Contact |
|---|---|---|
| Change Manager | Operations Team | changes@huron-demo.ai |
| Infrastructure Lead | IT Team | infra@huron-demo.ai |
| Security Lead | Security Team | security@huron-demo.ai |
| Emergency Approver | VP Operations | On-call via PagerDuty |

---

*All change requests: ServiceNow → IT → Changes | Change freeze calendar: Confluence → Operations → Change Calendar*
