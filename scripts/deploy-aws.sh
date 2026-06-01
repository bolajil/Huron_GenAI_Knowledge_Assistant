#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# AWS Deployment Script — Huron GenAI Knowledge Assistant
# ═══════════════════════════════════════════════════════════════════════════════
# Usage: ./scripts/deploy-aws.sh [dev|staging|prod] [--initial]
#
# This script handles the proper deployment order:
# 1. Creates infrastructure with ECS services at 0 tasks (no failures)
# 2. Builds and pushes Docker images to ECR
# 3. Scales up ECS services to pull images
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
ENVIRONMENT="${1:-dev}"
INITIAL_DEPLOY=false

for arg in "$@"; do
    case $arg in
        --initial)
            INITIAL_DEPLOY=true
            shift
            ;;
    esac
done

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform/aws"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Huron GenAI — AWS Deployment${NC}"
echo -e "${BLUE}  Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "${BLUE}  Initial Deploy: ${YELLOW}$INITIAL_DEPLOY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Check for tfvars file
TFVARS_FILE="$TERRAFORM_DIR/environments/${ENVIRONMENT}.tfvars"
if [ ! -f "$TFVARS_FILE" ]; then
    TFVARS_FILE="$TERRAFORM_DIR/terraform.tfvars"
fi

if [ ! -f "$TFVARS_FILE" ]; then
    echo -e "${RED}Error: No tfvars file found for environment '$ENVIRONMENT'${NC}"
    echo "Expected: $TERRAFORM_DIR/environments/${ENVIRONMENT}.tfvars"
    exit 1
fi

echo -e "\n${GREEN}Using tfvars: $TFVARS_FILE${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Terraform Infrastructure
# ─────────────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}[Phase 1/4] Creating AWS Infrastructure...${NC}"

cd "$TERRAFORM_DIR"

# Initialize if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# On initial deployment, set initial_deployment=true to start ECS at 0 tasks
if [ "$INITIAL_DEPLOY" = true ]; then
    echo -e "${YELLOW}Initial deployment mode: ECS services will start with 0 tasks${NC}"
    terraform apply -var-file="$TFVARS_FILE" -var="initial_deployment=true" -auto-approve
else
    terraform apply -var-file="$TFVARS_FILE" -auto-approve
fi

# Get outputs
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-1")
ECR_BACKEND_URL=$(terraform output -raw ecr_backend_url)
ECR_FRONTEND_URL=$(terraform output -raw ecr_frontend_url)
ECS_CLUSTER=$(terraform output -raw ecs_cluster_name)
ALB_URL=$(terraform output -raw alb_dns_name)

AWS_ACCOUNT_ID=$(echo "$ECR_BACKEND_URL" | cut -d'.' -f1)

echo -e "${GREEN}✓ Infrastructure created successfully${NC}"
echo -e "  ECR Backend:  $ECR_BACKEND_URL"
echo -e "  ECR Frontend: $ECR_FRONTEND_URL"
echo -e "  ECS Cluster:  $ECS_CLUSTER"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: Docker Login
# ─────────────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}[Phase 2/4] Logging into ECR...${NC}"

aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo -e "${GREEN}✓ ECR login successful${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: Build & Push Docker Images
# ─────────────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}[Phase 3/4] Building and pushing Docker images...${NC}"

cd "$PROJECT_ROOT"

# Build backend
echo -e "${YELLOW}Building backend image...${NC}"
docker build -f Dockerfile.production -t "$ECR_BACKEND_URL:latest" -t "$ECR_BACKEND_URL:$ENVIRONMENT" .

# Build frontend
echo -e "${YELLOW}Building frontend image...${NC}"
cd frontend
docker build -f Dockerfile.production -t "$ECR_FRONTEND_URL:latest" -t "$ECR_FRONTEND_URL:$ENVIRONMENT" .
cd ..

# Push images
echo -e "${YELLOW}Pushing backend image...${NC}"
docker push "$ECR_BACKEND_URL:latest"
docker push "$ECR_BACKEND_URL:$ENVIRONMENT"

echo -e "${YELLOW}Pushing frontend image...${NC}"
docker push "$ECR_FRONTEND_URL:latest"
docker push "$ECR_FRONTEND_URL:$ENVIRONMENT"

echo -e "${GREEN}✓ Images pushed successfully${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: Scale Up ECS Services
# ─────────────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}[Phase 4/4] Starting ECS services...${NC}"

if [ "$INITIAL_DEPLOY" = true ]; then
    # On initial deploy, re-apply with initial_deployment=false to scale up
    echo "Scaling up ECS services..."
    cd "$TERRAFORM_DIR"
    terraform apply -var-file="$TFVARS_FILE" -var="initial_deployment=false" -auto-approve
else
    # Just force a new deployment to pull latest images
    aws ecs update-service \
        --cluster "$ECS_CLUSTER" \
        --service "${ECS_CLUSTER%-cluster}-backend" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null

    aws ecs update-service \
        --cluster "$ECS_CLUSTER" \
        --service "${ECS_CLUSTER%-cluster}-frontend" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null
fi

echo -e "${GREEN}✓ ECS services starting${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "\n${BLUE}Application URL:${NC} $ALB_URL"
echo -e "${BLUE}API Docs:${NC} $ALB_URL/docs"
echo -e "\n${YELLOW}Note: ECS tasks may take 2-3 minutes to become healthy.${NC}"
echo -e "Monitor: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$ECS_CLUSTER/services"
