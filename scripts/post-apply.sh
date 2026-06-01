#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Step 6 — Sync terraform outputs → GitHub Actions Variables
#
# Run after EVERY terraform apply so workflows always have the correct URLs.
# Non-sensitive values only (ALB URL, ECR URLs, cluster name).
#
# Usage: ./scripts/post-apply.sh dev|staging|prod
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

ENV=${1:-dev}
REPO="bolajil/Huron_GenAI_Knowledge_Assistant"
TFDIR="terraform/aws"

# Run from project root regardless of where the script is called from
cd "$(dirname "$0")/.."

echo "Reading Terraform outputs for: $ENV"
cd "$TFDIR"

# ── Read outputs ──────────────────────────────────────────────────────────────
ALB_URL=$(terraform output -raw alb_dns_name 2>/dev/null)
ECR_BACKEND=$(terraform output -raw ecr_backend_url 2>/dev/null)
ECR_FRONTEND=$(terraform output -raw ecr_frontend_url 2>/dev/null)
ECS_CLUSTER=$(terraform output -raw ecs_cluster_name 2>/dev/null)

if [ -z "$ALB_URL" ]; then
  echo "ERROR: No terraform outputs found. Run terraform apply first."
  exit 1
fi

# ── Push to GitHub Variables ──────────────────────────────────────────────────
PREFIX=$(echo "$ENV" | tr '[:lower:]' '[:upper:]')

echo "Setting GitHub Actions Variables for $PREFIX ..."
gh variable set "${PREFIX}_ALB_URL"      --body "$ALB_URL"      --repo "$REPO"
gh variable set "${PREFIX}_ECR_BACKEND"  --body "$ECR_BACKEND"  --repo "$REPO"
gh variable set "${PREFIX}_ECR_FRONTEND" --body "$ECR_FRONTEND" --repo "$REPO"
gh variable set "${PREFIX}_ECS_CLUSTER"  --body "$ECS_CLUSTER"  --repo "$REPO"

# Prod uses PROD_URL (without the prefix pattern) for the health check
if [ "$ENV" = "prod" ]; then
  gh variable set "PROD_URL" --body "$ALB_URL" --repo "$REPO"
fi

echo ""
echo "GitHub Variables updated:"
echo "  ${PREFIX}_ALB_URL      = $ALB_URL"
echo "  ${PREFIX}_ECR_BACKEND  = $ECR_BACKEND"
echo "  ${PREFIX}_ECR_FRONTEND = $ECR_FRONTEND"
echo "  ${PREFIX}_ECS_CLUSTER  = $ECS_CLUSTER"
echo ""
echo "Push to the '$ENV' branch to trigger an automated deployment."
