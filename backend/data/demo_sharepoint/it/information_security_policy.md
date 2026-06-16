# Information Security Policy (Demo Document)
**Version:** 2026.1 | **Classification:** Internal | **Owner:** Chief Information Security Officer

---

## 1. Purpose & Scope

This policy establishes Huron's minimum security standards for protecting company and client information assets. It applies to all employees, contractors, consultants, and third parties who access Huron information systems, data, or networks.

Non-compliance with this policy may result in disciplinary action up to and including termination and legal action where applicable.

---

## 2. Information Classification

All Huron data must be classified and handled according to its sensitivity:

| Classification | Description | Examples | Handling |
|---|---|---|---|
| **Public** | Approved for external release | Marketing materials, published case studies | No restrictions |
| **Internal** | For Huron employees only; not for external sharing | This policy, internal memos, org charts | Do not share outside Huron without approval |
| **Confidential** | Sensitive business or client information | Client data, financial results, strategy docs | Encrypt at rest and in transit; need-to-know access only |
| **Restricted** | Highest sensitivity; legal or regulatory impact | PHI, PII, credentials, legal holds | Encrypted, access-logged, minimum necessary access |

When in doubt, classify at the next higher level.

---

## 3. Access Control

### Principle of Least Privilege
Users receive the minimum access necessary to perform their job functions. Access is granted by role, not by individual request, except for exceptions reviewed by the CISO.

### Account Management
- **New hires:** Access provisioned on first day via Workday/IT integration
- **Role changes:** Excess access removed within 48 hours of role change
- **Separations:** All access revoked within 1 hour of termination effective time
- **Third-party access:** Time-limited; reviewed quarterly; revoked when engagement ends

### Privileged Access
Privileged accounts (admin, root, service accounts) require:
- Justification documented in ServiceNow
- Manager + Security Team approval
- Multi-factor authentication (MFA) — mandatory, no exceptions
- 90-day access reviews
- All privileged actions logged (immutable audit log, 1-year retention)

---

## 4. Authentication Requirements

| System Type | Required Controls |
|---|---|
| All Huron systems | Unique username + strong password + MFA |
| Cloud infrastructure | MFA + hardware security key for production |
| Executive accounts | MFA + session recording |
| Service accounts | Certificate or managed identity only; no human passwords |

### Password Standards
- Minimum 14 characters
- Must include: uppercase, lowercase, number, special character
- No reuse of last 12 passwords
- Maximum age: 180 days (systems enforce rotation)
- Prohibited: Dictionary words, personal information, sequential patterns ("Password1!")

### Multi-Factor Authentication
MFA is mandatory for:
- All Huron Microsoft 365 / Azure services
- All VPN connections
- All administrative access to production systems
- Remote desktop access

Approved MFA methods: Microsoft Authenticator app, hardware FIDO2 keys. SMS-based OTP is **not** approved for privileged access.

---

## 5. Endpoint Security

All Huron-managed devices must have:
- [ ] Full-disk encryption (BitLocker for Windows, FileVault for Mac)
- [ ] Endpoint Detection & Response (EDR) agent (CrowdStrike Falcon)
- [ ] Approved operating system (Windows 11 or macOS 14+; no older versions on production systems)
- [ ] Automatic OS patch installation within 14 days of release
- [ ] Screen lock after 5 minutes of inactivity (enforced via MDM)

### Personal Devices (BYOD)
Personal devices may be used for Huron email and calendar via managed Outlook app only. Access to internal systems from personal devices requires Intune device enrollment.

---

## 6. Network Security

- All remote access must go through Huron VPN (GlobalProtect)
- Public Wi-Fi use requires VPN — no exceptions for work on client data
- Home networks must use WPA3 or WPA2 with a strong passphrase (>12 chars)
- Split-tunneling on VPN is disabled; all traffic routes through Huron network

### Prohibited Network Activities
- Connecting unauthorized devices to Huron office network
- Bypassing network security controls (proxy bypass, Tor, unauthorized Wi-Fi hotspots)
- Port scanning or network reconnaissance without Security team authorization

---

## 7. Data Protection

### Encryption Standards
| Data State | Standard |
|---|---|
| At rest (disks, databases) | AES-256 |
| In transit | TLS 1.2 or higher; TLS 1.0/1.1 prohibited |
| Backups | Encrypted with separate key management |
| Email (Confidential/Restricted content) | S/MIME or secure portal |

### Data Loss Prevention (DLP)
Huron's Microsoft Purview DLP policies:
- Block sending Confidential/Restricted data to personal email addresses
- Alert on bulk downloads of client data (>1,000 records in a session)
- Block uploading Confidential data to non-approved cloud storage

---

## 8. Security Incident Reporting

**All suspected security incidents must be reported immediately:**
- Email: security@huron-demo.ai
- Phone: Security Operations Center (SOC) at x4911 (24/7)
- Escalation: If SOC unreachable, contact CISO directly

Reportable events include:
- Phishing email clicked or credentials entered on suspicious site
- Lost or stolen device containing Huron data
- Unexpected account lockout or suspicious login alert
- Malware detection alert from CrowdStrike
- Any suspected data breach or unauthorized access

Do not attempt to investigate independently or delete suspicious content — preserve all evidence.

---

## 9. Security Training Requirements

| Training | Audience | Frequency |
|---|---|---|
| Security Awareness Training | All employees | Annual (by Jan 31) |
| Phishing Simulation | All employees | Quarterly |
| HIPAA / PHI Handling | Clinical practice employees | Annual |
| Secure Coding | Software engineers | Annual |
| Privileged User Training | Sysadmins, DBAs | Biannual |

Failure to complete mandatory training escalates to manager and HR after 30-day grace period.

---

*Questions: security@huron-demo.ai | SOC: ext. 4911 (24/7) | Policy owner: CISO*
