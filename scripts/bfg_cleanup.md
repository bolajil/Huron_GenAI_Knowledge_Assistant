# BFG Repo Cleaner - Remove Sensitive Files from Git History

## Step 2: Purge Sensitive Data from Git History

This removes sensitive files that were previously committed but are now gitignored.

### Prerequisites
1. Download BFG: https://rtyley.github.io/bfg-repo-cleaner/
2. Java Runtime (JRE) installed

### Files to Remove from History

```
# Sensitive HR/Employee Data
W-4.pdf
SSN*.pdf
pay_stub*.pdf
*_ssn_*.pdf
employee_*_confidential.pdf

# API Keys and Secrets
.env
*.pem
*.key
*_credentials.json
service_account*.json

# Database files with potential PII
*.db
*.sqlite
```

### Commands to Run

```bash
# 1. Create backup
git clone --mirror https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git backup-repo

# 2. Download BFG (if not already)
# curl -O https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 3. Run BFG to remove sensitive files
java -jar bfg-1.14.0.jar --delete-files "W-4.pdf" backup-repo
java -jar bfg-1.14.0.jar --delete-files "*.db" backup-repo
java -jar bfg-1.14.0.jar --delete-files ".env" backup-repo

# 4. Clean up
cd backup-repo
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Push cleaned history (FORCE PUSH - coordinate with team!)
git push --force
```

### Post-Cleanup Verification

```bash
# Search for any remaining sensitive patterns
git log --all --full-history -- "*ssn*"
git log --all --full-history -- "*.pem"
git log --all --full-history -- ".env"
```

### Important Notes

1. **Coordinate with team** - Force push will rewrite history
2. **All team members must re-clone** after cleanup
3. **Rotate any exposed credentials** (API keys, passwords)
4. Run `detect-secrets scan` to verify no secrets remain

---
*Generated for Huron GenAI Knowledge Assistant production cleanup*
