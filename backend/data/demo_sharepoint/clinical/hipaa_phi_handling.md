# HIPAA & PHI Handling Guidelines (Demo Document)
**Version:** 2026.1 | **Classification:** Confidential | **Owner:** Clinical Compliance

---

## 1. Purpose

This document establishes mandatory requirements for how Huron team members handle Protected Health Information (PHI) in the course of client engagements. All Huron employees, contractors, and business associates who access PHI are subject to these guidelines.

---

## 2. What Is PHI?

Protected Health Information is any individually identifiable health information that relates to:
- A past, present, or future physical or mental health condition
- The provision of health care to an individual
- Past, present, or future payment for health care

PHI includes information in any form: paper, electronic (ePHI), or verbal.

### Common PHI Identifiers
The following 18 HIPAA-defined identifiers turn health information into PHI:
1. Name
2. Geographic data (smaller than state level)
3. Dates (other than year) related to the individual
4. Phone number
5. Fax number
6. Email address
7. Social Security Number
8. Medical record number
9. Health plan beneficiary number
10. Account number
11. Certificate/license number
12. Vehicle identifiers and serial numbers
13. Device identifiers
14. Web URLs
15. IP addresses
16. Biometric identifiers (fingerprints, voiceprints)
17. Full-face photographs
18. Any unique identifying number or code

---

## 3. Minimum Necessary Standard

When accessing or sharing PHI, use **only the minimum necessary** to accomplish the intended purpose.

- Request only the fields required for your analysis
- Do not download full datasets if a query result suffices
- Do not share PHI via email — use the secure file transfer portal
- Never include PHI in Slack, Teams, or other collaboration tools

---

## 4. Data Handling Requirements

### Storage
| Location | Permitted |
|---|---|
| Client-approved secure data room | Yes |
| Huron encrypted virtual drive (DLP-enabled) | Yes |
| Personal laptop local disk (unencrypted) | No |
| Personal cloud storage (Google Drive, iCloud, Dropbox) | No |
| USB flash drives | No (unless encrypted and approved) |

### Transmission
- Encrypt all ePHI at rest (AES-256) and in transit (TLS 1.2+)
- Use the secure file transfer portal for PHI sharing with clients
- Never send PHI via regular email; use encrypted email (S/MIME or portal)
- Client VPN or dedicated data room access required for remote PHI access

### De-identification
PHI may be de-identified using one of two HIPAA-approved methods:
1. **Expert Determination** — A qualified statistician certifies re-identification risk is very small
2. **Safe Harbor** — All 18 identifiers removed and no actual knowledge of re-identification risk

De-identified data is no longer PHI and is not subject to these restrictions.

---

## 5. Breach Notification

A breach occurs when PHI is accessed, used, disclosed, or acquired in a way not permitted by HIPAA.

### If You Suspect a Breach
1. **Immediately** stop any ongoing unauthorized access
2. **Within 1 hour:** Report to your Engagement Manager and the Huron Privacy Officer (privacy@huron-demo.ai)
3. **Do not** attempt to investigate independently or notify the client without guidance
4. Preserve all evidence — do not delete files, emails, or logs

### Notification Timeline
| Party | Deadline |
|---|---|
| Huron Privacy Officer | Within 1 hour of discovery |
| Huron Legal Counsel | Within 4 hours |
| Client | Per BAA terms (typically 24-48 hours) |
| HHS Secretary | Within 60 days (via client's reporting obligation) |
| Individuals affected | Within 60 days (if 500+ individuals; if <500, annual log to HHS) |

---

## 6. Business Associate Agreements

Huron operates as a **Business Associate (BA)** under HIPAA when working with Covered Entities. Before accessing any PHI:

- Confirm a signed Business Associate Agreement (BAA) is on file with the client
- Contact Legal (legal@huron-demo.ai) if no BAA exists — do not proceed without one

Huron's standard BAA is maintained by the Legal team. Client-proposed BAAs must be reviewed and approved by Legal before signing.

---

## 7. Training Requirements

All employees who access PHI must complete:
- **Initial HIPAA Training:** Within 30 days of hire
- **Annual Refresher Training:** By January 31 each year
- **Incident-Specific Training:** Required after any breach or near-miss

Training is tracked in the HR Learning Management System. Non-compliance is escalated to the employee's manager and HR Business Partner.

---

*For questions, contact: privacy@huron-demo.ai | Clinical Compliance Team*
