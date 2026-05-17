# Phase 0: Project Setup & Security Cleanup
## Duration: Day 1 (Immediate)

---

## 🔴 CRITICAL: Security Cleanup

### Task 0.1: Audit Archive Directory for Sensitive Files

The `archive_cleanup_20250919_082734/` directory was flagged in the production guide as containing personal documents (SSN statements, pay stubs, personal PDFs).

**Status**: ⏳ Pending  
**Action Required**: 
1. [ ] List contents of `archive_cleanup_20250919_082734/uploads/`
2. [ ] Identify any personal/sensitive files
3. [ ] Document findings
4. [ ] Remove from git history using BFG Repo Cleaner

### Task 0.2: Remove Sensitive Files from Git History

**Commands** (after identifying files):
```bash
# Install BFG Repo Cleaner
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

# Create backup first
git checkout -b backup-before-cleanup

# Remove specific files/folders
java -jar bfg.jar --delete-folders uploads archive_cleanup_20250919_082734

# Or use git-filter-repo (alternative)
pip install git-filter-repo
git filter-repo --path archive_cleanup_20250919_082734 --invert-paths
```

**Status**: ⏳ Pending

### Task 0.3: Audit .env.example

Check for any real credentials or API keys that may have been committed.

**Status**: ⏳ Pending

---

## 📁 File Consolidation

### Task 0.4: Consolidate Duplicate Tabs

| Keep | Archive | Reason |
|------|---------|--------|
| `tabs/chat_assistant.py` or `tabs/chat_assistant_enterprise.py` | All other `chat_assistant_*.py` variants | 7 variants is unmaintainable |
| `tabs/agent_assistant_enhanced.py` | All other `agent_assistant_*.py` variants | 5 variants |
| `tabs/enhanced_research_optimized.py` | Other `enhanced_research_*.py` | 3 variants |

**Commands**:
```bash
# Create archive directory
mkdir -p _archived/tabs_duplicates

# Move duplicates (after deciding which to keep)
mv tabs/chat_assistant_enhanced.py _archived/tabs_duplicates/
mv tabs/chat_assistant_fixed.py _archived/tabs_duplicates/
# ... etc
```

**Status**: ⏳ Pending

### Task 0.5: Consolidate Duplicate Utils

| Keep | Archive | Location |
|------|---------|----------|
| `utils/query_helpers.py` | `app/utils/query_helpers.py`, `template/query_helpers.py` | 3 copies |
| `utils/ingest_helpers.py` | `app/utils/ingest_helpers.py`, `template/ingest_helpers.py` | 4 copies |
| `utils/adapters/weaviate_adapter_fixed.py` | `utils/adapters/weaviate_adapter.py` | 2 versions |

**Status**: ⏳ Pending

### Task 0.6: Clean Root Directory

The root has 100+ `.md` files. Many are outdated or superseded.

**Recommendation**:
1. Move all `*_GUIDE.md`, `*_README.md` files to `docs/`
2. Keep only: `README.md`, `HURON_IMPLEMENTATION_MASTER.md`, `PHASE_*.md`
3. Archive the rest to `_archived/docs/`

**Status**: ⏳ Pending

---

## 🔧 Environment Setup

### Task 0.7: Create Clean .env

```bash
# Copy example
cp .env.example .env

# Edit with your actual values
# Required for Phase 1:
# - PINECONE_API_KEY
# - OPENAI_API_KEY
# - JWT_SECRET (generate new one)
```

**Status**: ⏳ Pending

### Task 0.8: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install requirements
pip install -r requirements.txt
pip install -r requirements-enterprise.txt
pip install -r requirements-ml-models.txt
```

**Status**: ⏳ Pending

### Task 0.9: Verify Key Components Load

```python
# Test script to verify imports
python -c "
from app.agents.controller_agent import *
from utils.adapters.pinecone_adapter import *
from utils.ml_models.query_intent_classifier import *
from utils.advanced_reranker import *
from app.auth.authentication import *
print('All key components import successfully')
"
```

**Status**: ⏳ Pending

---

## 📋 Verification Checklist

Before marking Phase 0 complete:

- [ ] No personal/sensitive files in repository
- [ ] Git history cleaned (if needed)
- [ ] Duplicate files consolidated or archived
- [ ] Root directory organized
- [ ] `.env` file created with required keys
- [ ] Dependencies installed
- [ ] Key components import without errors
- [ ] Application starts without critical errors

---

## 💡 Cascade Suggestions

### Suggestion 0.A: Pre-Commit Hooks
Add pre-commit hooks to prevent future issues:

```bash
pip install pre-commit
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: detect-aws-credentials
      - id: check-added-large-files
        args: ['--maxkb=500']
```

### Suggestion 0.B: Gitignore Additions
Add to `.gitignore`:
```
# Prevent future sensitive file commits
*.pem
*.key
*_secret*
*ssn*
*payslip*
*paystub*
uploads/
archive_*/
```

### Suggestion 0.C: Create _archived Structure
```
_archived/
├── tabs_duplicates/      # Archived tab variants
├── utils_duplicates/     # Archived util variants
├── docs_legacy/          # Old documentation
└── README.md             # Why these are archived
```

---

## Next Phase

Once Phase 0 is complete → Proceed to **Phase 1: Foundation & Namespace Migration**

---

## Commands Quick Reference

```bash
# Check current branch
git branch

# Create backup branch
git checkout -b backup-original

# Check for large files
git ls-files -s | sort -k4 -n -r | head -20

# Find potential sensitive files
find . -name "*secret*" -o -name "*password*" -o -name "*ssn*"

# Count files in root
ls -1 *.md | wc -l
```
