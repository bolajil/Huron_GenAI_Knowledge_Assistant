#!/usr/bin/env python3
"""
Phase 0 Security Cleanup Script
Huron GenAI Knowledge Assistant - Production Grade

This script:
1. Removes sensitive files from git tracking
2. Updates .gitignore for production security
3. Moves .md files to docs/legacy/
4. Removes duplicate utility files
5. Prepares for BFG history cleaning

Author: Production Scalability Team
Date: May 2026
"""

import os
import shutil
import subprocess
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Files to keep in root (everything else .md goes to docs/)
KEEP_IN_ROOT = {
    'README.md',
    'HURON_IMPLEMENTATION_MASTER.md',
    'PHASE_0_CHECKLIST.md',
}

# Sensitive paths to remove from git (not delete, just untrack)
SENSITIVE_PATHS = [
    'archive_cleanup_20250919_082734/uploads/',
]

# Duplicate files to archive (keep only utils/ versions)
DUPLICATE_FILES_TO_ARCHIVE = [
    'app/utils/ingest_helpers.py',  # Superseded by utils/ingestion_service.py
    'app/utils/query_helpers.py',   # Keep utils/query_helpers.py only
]

# Patterns to add to .gitignore
GITIGNORE_ADDITIONS = '''
# ===========================================
# PRODUCTION SECURITY - Phase 0 Additions
# ===========================================

# Sensitive uploads - NEVER commit
uploads/
**/uploads/
archive_cleanup_*/uploads/

# Personal documents
*.pdf
!docs/**/*.pdf
!assets/**/*.pdf

# Sensitive file patterns
*social-security*
*checkstub*
*w-4*
*w4*
*direct-deposit*
*DD.pdf

# Local development
.env
.env.local
*.local

# Database files
*.db
*.sqlite
*.sqlite3

# Secrets and keys
*.pem
*.key
*_key
*secret*
!app/auth/.encryption_key  # This is generated, not committed

# IDE and system
.idea/
.vscode/settings.json
*.swp
*.swo
.DS_Store
Thumbs.db

# Build artifacts
__pycache__/
*.pyc
*.pyo
.next/
node_modules/
dist/
build/

# Test artifacts
.coverage
htmlcov/
.pytest_cache/
'''


def run_git_command(cmd: list[str], cwd: Path = PROJECT_ROOT) -> tuple[int, str]:
    """Run a git command and return exit code and output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout + result.stderr


def remove_sensitive_from_git():
    """Remove sensitive files from git tracking (not from disk)."""
    print("\n" + "="*60)
    print("STEP 1: Removing sensitive files from git tracking")
    print("="*60)
    
    for path in SENSITIVE_PATHS:
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            print(f"  Untracking: {path}")
            run_git_command(['git', 'rm', '-r', '--cached', path])
        else:
            print(f"  [SKIP] Not found: {path}")


def update_gitignore():
    """Add production security patterns to .gitignore."""
    print("\n" + "="*60)
    print("STEP 2: Updating .gitignore for production security")
    print("="*60)
    
    gitignore_path = PROJECT_ROOT / '.gitignore'
    
    # Read existing content
    existing = ""
    if gitignore_path.exists():
        existing = gitignore_path.read_text()
    
    # Check if already updated
    if "PRODUCTION SECURITY - Phase 0" in existing:
        print("  [SKIP] .gitignore already has Phase 0 security rules")
        return
    
    # Append new rules
    with open(gitignore_path, 'a') as f:
        f.write(GITIGNORE_ADDITIONS)
    
    print("  [DONE] Added production security patterns to .gitignore")


def move_md_files():
    """Move .md files from root to docs/legacy/, keeping essential ones."""
    print("\n" + "="*60)
    print("STEP 3: Moving .md files to docs/legacy/")
    print("="*60)
    
    legacy_dir = PROJECT_ROOT / 'docs' / 'legacy'
    legacy_dir.mkdir(parents=True, exist_ok=True)
    
    moved_count = 0
    kept_count = 0
    
    for md_file in PROJECT_ROOT.glob('*.md'):
        if md_file.name in KEEP_IN_ROOT:
            print(f"  [KEEP] {md_file.name}")
            kept_count += 1
        else:
            dest = legacy_dir / md_file.name
            shutil.move(str(md_file), str(dest))
            print(f"  [MOVE] {md_file.name} -> docs/legacy/")
            moved_count += 1
    
    print(f"\n  Summary: {moved_count} moved, {kept_count} kept in root")


def archive_duplicate_files():
    """Move duplicate utility files to _archived/."""
    print("\n" + "="*60)
    print("STEP 4: Archiving duplicate utility files")
    print("="*60)
    
    archive_dir = PROJECT_ROOT / '_archived' / 'duplicate_utils'
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    for rel_path in DUPLICATE_FILES_TO_ARCHIVE:
        src = PROJECT_ROOT / rel_path
        if src.exists():
            dest = archive_dir / src.name
            shutil.move(str(src), str(dest))
            print(f"  [ARCHIVE] {rel_path} -> _archived/duplicate_utils/")
        else:
            print(f"  [SKIP] Not found: {rel_path}")


def print_bfg_instructions():
    """Print instructions for BFG history cleaning."""
    print("\n" + "="*60)
    print("STEP 5: BFG History Cleaning Instructions")
    print("="*60)
    print("""
  ⚠️  CRITICAL: The sensitive files are still in git HISTORY.
  
  You MUST run BFG Repo Cleaner to remove them from all commits:
  
  1. Install BFG:
     - Download from: https://rtyley.github.io/bfg-repo-cleaner/
     - Or: brew install bfg (macOS)
  
  2. Create a backup of your repo first:
     git clone --mirror https://github.com/bolajil/Huron_GenAI_Knowledge_Assistant.git backup-repo.git
  
  3. Run BFG to remove sensitive files:
     bfg --delete-files "social-security-statement.pdf" --no-blob-protection
     bfg --delete-files "Checkstub*.pdf" --no-blob-protection
     bfg --delete-files "syrencloud-w-4.pdf" --no-blob-protection
     bfg --delete-files "syrencloud_DD.pdf" --no-blob-protection
     bfg --delete-folders uploads --no-blob-protection
  
  4. Clean up and force push:
     git reflog expire --expire=now --all
     git gc --prune=now --aggressive
     git push --force
  
  5. All collaborators must re-clone the repository.
""")


def main():
    print("="*60)
    print("Huron GenAI Knowledge Assistant")
    print("Phase 0: Security Cleanup Script")
    print("="*60)
    
    # Step 1: Remove sensitive files from git tracking
    remove_sensitive_from_git()
    
    # Step 2: Update .gitignore
    update_gitignore()
    
    # Step 3: Move .md files
    move_md_files()
    
    # Step 4: Archive duplicates
    archive_duplicate_files()
    
    # Step 5: Print BFG instructions
    print_bfg_instructions()
    
    print("\n" + "="*60)
    print("Phase 0 Cleanup Complete!")
    print("="*60)
    print("""
  Next steps:
  1. Review the changes: git status
  2. Commit: git commit -m "chore(security): Phase 0 cleanup - remove sensitive files, organize docs"
  3. Run BFG to clean git history (see instructions above)
  4. Force push: git push --force
  5. Proceed to Phase 1: JWT + Namespace wire-up
""")


if __name__ == '__main__':
    main()
