#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Step 5 — Create IAM access keys and add them to GitHub Actions secrets
#
# Run ONCE after first terraform apply for an environment.
# Requires: aws cli, gh cli (GitHub CLI), jq
#
# Usage: ./scripts/setup-github-secrets.sh dev|staging|prod
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

ENV=${1:-dev}
REPO="bolajil/Huron_GenAI_Knowledge_Assistant"
IAM_USER="huron-${ENV}-cicd-user"

echo "Setting up GitHub Actions secrets for environment: $ENV"
echo "IAM user: $IAM_USER"
echo "Repo: $REPO"
echo ""

# ── Check prerequisites ───────────────────────────────────────────────────────
command -v aws  >/dev/null 2>&1 || { echo "ERROR: aws cli not found"; exit 1; }
command -v gh   >/dev/null 2>&1 || { echo "ERROR: gh cli not found. Install: https://cli.github.com"; exit 1; }
command -v jq   >/dev/null 2>&1 || { echo "ERROR: jq not found"; exit 1; }

# ── Check GitHub auth ─────────────────────────────────────────────────────────
gh auth status >/dev/null 2>&1 || { echo "ERROR: Not logged into GitHub CLI. Run: gh auth login"; exit 1; }

# ── Create IAM access key ─────────────────────────────────────────────────────
echo "Creating IAM access key for $IAM_USER ..."
KEY_JSON=$(aws iam create-access-key --user-name "$IAM_USER" 2>&1)

if echo "$KEY_JSON" | grep -q "NoSuchEntity"; then
  echo "ERROR: IAM user '$IAM_USER' does not exist."
  echo "Run terraform apply first to create the user, then re-run this script."
  exit 1
fi

ACCESS_KEY_ID=$(echo "$KEY_JSON" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$KEY_JSON" | jq -r '.AccessKey.SecretAccessKey')

echo "IAM key created: $ACCESS_KEY_ID"
echo ""

# ── Set GitHub Actions secrets ────────────────────────────────────────────────
echo "Setting GitHub Actions secrets ..."
gh secret set AWS_ACCESS_KEY_ID     --body "$ACCESS_KEY_ID"     --repo "$REPO"
gh secret set AWS_SECRET_ACCESS_KEY --body "$SECRET_ACCESS_KEY" --repo "$REPO"

echo ""
echo "Done. Secrets set in $REPO:"
echo "  AWS_ACCESS_KEY_ID     = $ACCESS_KEY_ID"
echo "  AWS_SECRET_ACCESS_KEY = [hidden]"
echo ""
echo "Next: run ./scripts/post-apply.sh $ENV to set GitHub Variables (ALB URL, ECR URLs, etc.)"
