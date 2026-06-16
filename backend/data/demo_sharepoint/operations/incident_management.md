# Incident Management Procedure (Demo Document)
**Version:** 2026.1 | **Classification:** Internal | **Owner:** Operations

---

## 1. Purpose

This procedure defines how Huron identifies, classifies, responds to, and learns from operational and IT incidents. A consistent incident management process ensures rapid restoration of services, limits business impact, and drives continuous improvement.

---

## 2. Incident Definition

An **incident** is any unplanned interruption or degradation of a Huron business service, system, or tool that impacts employee productivity, client delivery, or data integrity.

**Not an incident:** Planned maintenance windows, approved changes, or user error with no system impact.

---

## 3. Severity Classification

| Severity | Description | Examples | Target Response |
|---|---|---|---|
| **P1 — Critical** | Complete outage of a critical service; active data breach; client delivery blocked | Email system down firm-wide, Huron platform unreachable, active ransomware | 15 minutes |
| **P2 — High** | Significant degradation of a critical service; single major client blocked | 50%+ users unable to log in, Workday sync failed for 3+ days, video conferencing down | 1 hour |
| **P3 — Medium** | Partial degradation; workaround exists | Single user unable to access a tool, reporting dashboard slow, non-critical API errors | 4 hours |
| **P4 — Low** | Minor issue; no immediate business impact | Cosmetic UI bug, single report wrong, documentation error | Next business day |

---

## 4. Incident Lifecycle

### Phase 1: Detection & Reporting
Incidents are detected via:
- Automated monitoring alerts (PagerDuty)
- Employee reports via the IT Help Desk (helpdesk.huron-demo.ai or ext. 4567)
- Client-reported issues (escalated through Account Manager)

**Any employee** who suspects an incident should report it immediately — do not wait to confirm. False positives are far better than delayed discovery.

### Phase 2: Initial Triage (< 15 min for P1/P2)
The on-call engineer:
1. Acknowledges the alert in PagerDuty
2. Assigns a severity (P1–P4)
3. Posts initial update in #incidents Slack channel: `[P1] Email gateway down — investigating`
4. For P1/P2: Pages Incident Commander (IC) and relevant service owner

### Phase 3: Incident Response
The Incident Commander (IC) leads the response:
- **Bridge:** Opens a video bridge for P1/P2 (Zoom link pinned in #incidents)
- **Roles:** Assigns Communications Lead, Technical Lead, and Timeline Scribe
- **Updates:** Posts status updates every 15 minutes (P1), 30 minutes (P2) to #incidents and status page

Resolution actions are documented in real-time in the Incident Ticket (ServiceNow).

### Phase 4: Resolution & Recovery
- IC declares incident resolved when service is restored and monitoring confirms stability
- Final status posted: `[P1 RESOLVED] Email gateway restored at 14:37 UTC — cause: expired TLS cert on MX relay`
- Affected users notified via email/Slack

### Phase 5: Post-Incident Review (PIR)
| Severity | PIR Required | Timeline |
|---|---|---|
| P1 | Yes — mandatory | Within 48 hours |
| P2 | Yes | Within 5 business days |
| P3 | Optional | As capacity allows |
| P4 | No | — |

PIR output: Blameless write-up covering timeline, root cause, contributing factors, and action items with owners and due dates. Published to Confluence (Operations → Incident Reviews).

---

## 5. Incident Roles

| Role | Responsibility |
|---|---|
| **Incident Commander (IC)** | Overall accountability; makes prioritization calls; controls the bridge |
| **Technical Lead** | Owns the technical investigation and fix |
| **Communications Lead** | Manages internal/external updates; updates status page |
| **Timeline Scribe** | Logs all actions with timestamps in the incident ticket |
| **Subject Matter Expert (SME)** | Called in as needed; owns specific systems |

The on-call rotation is published in PagerDuty. IC rotation covers one week; the schedule is set 4 weeks in advance.

---

## 6. Communication Templates

### Internal Slack Update (every 15 min for P1)
```
[P1 UPDATE - 14:22 UTC] Email gateway still down. Root cause identified: expired TLS cert.
Fix in progress — cert renewal submitted. ETA to restore: 30 minutes.
IC: @jsmith | Tech Lead: @kwilliams
```

### External Client Communication (sent by Account Manager)
```
Subject: Huron Platform — Service Disruption Update

We are currently experiencing an issue affecting [describe impact].
Our team is actively working on a resolution.

Current Status: Investigating / Identified / Resolving / Resolved
Expected Resolution: [time] / [we will update you in X minutes]

We apologize for any inconvenience and will provide updates every [30 minutes].
```

---

## 7. Escalation Path

```
Employee / Alert → IT Help Desk → On-Call Engineer (P3/P4)
                                → Incident Commander (P1/P2)
                                        → VP Operations (if > 2 hours)
                                        → CTO + CEO (if client-impacting > 4 hours)
                                        → Legal + PR (if data breach confirmed)
```

---

## 8. Tools & Access

| Tool | Purpose | Access |
|---|---|---|
| PagerDuty | Alerting and on-call rotation | All engineers |
| ServiceNow | Incident ticketing | All employees |
| Zoom (bridge link) | P1/P2 response bridge | Published in #incidents |
| Statuspage | External status page | IC and Communications Lead |

---

*Operations questions: ops@huron-demo.ai | On-call: PagerDuty (eng-oncall) | Help Desk: ext. 4567*
