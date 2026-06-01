# ═══════════════════════════════════════════════════════════════════════════════
# AWS Deployment Script — Huron GenAI Knowledge Assistant (PowerShell)
# ═══════════════════════════════════════════════════════════════════════════════
# Usage: .\scripts\deploy-aws.ps1 -Environment dev -Initial
#
# This script handles the proper deployment order:
# 1. Creates infrastructure with ECS services at 0 tasks (no failures)
# 2. Builds and pushes Docker images to ECR
# 3. Scales up ECS services to pull images
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [switch]$Initial,
    
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# Project paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$TerraformDir = Join-Path $ProjectRoot "terraform\aws"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "  Huron GenAI — AWS Deployment" -ForegroundColor Blue
Write-Host "  Environment: $Environment" -ForegroundColor Yellow
Write-Host "  Initial Deploy: $Initial" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Blue

# Check for tfvars file
$TfvarsFile = Join-Path $TerraformDir "environments\$Environment.tfvars"
if (-not (Test-Path $TfvarsFile)) {
    $TfvarsFile = Join-Path $TerraformDir "terraform.tfvars"
}

if (-not (Test-Path $TfvarsFile)) {
    Write-Host "Error: No tfvars file found for environment '$Environment'" -ForegroundColor Red
    exit 1
}

Write-Host "`nUsing tfvars: $TfvarsFile" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Terraform Infrastructure
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n[Phase 1/4] Creating AWS Infrastructure..." -ForegroundColor Blue

Set-Location $TerraformDir

# Initialize if needed
if (-not (Test-Path ".terraform")) {
    Write-Host "Initializing Terraform..."
    terraform init
}

# On initial deployment, set initial_deployment=true to start ECS at 0 tasks
if ($Initial) {
    Write-Host "Initial deployment mode: ECS services will start with 0 tasks" -ForegroundColor Yellow
    terraform apply -var-file="$TfvarsFile" -var="initial_deployment=true" -auto-approve
} else {
    terraform apply -var-file="$TfvarsFile" -auto-approve
}

# Get outputs
$AwsRegion = terraform output -raw aws_region 2>$null
if (-not $AwsRegion) { $AwsRegion = "us-east-1" }

$EcrBackendUrl = terraform output -raw ecr_backend_url
$EcrFrontendUrl = terraform output -raw ecr_frontend_url
$EcsCluster = terraform output -raw ecs_cluster_name
$AlbUrl = terraform output -raw alb_dns_name

$AwsAccountId = $EcrBackendUrl.Split('.')[0]

Write-Host "✓ Infrastructure created successfully" -ForegroundColor Green
Write-Host "  ECR Backend:  $EcrBackendUrl"
Write-Host "  ECR Frontend: $EcrFrontendUrl"
Write-Host "  ECS Cluster:  $EcsCluster"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: Docker Login
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n[Phase 2/4] Logging into ECR..." -ForegroundColor Blue

$EcrPassword = aws ecr get-login-password --region $AwsRegion
$EcrPassword | docker login --username AWS --password-stdin "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com"

Write-Host "✓ ECR login successful" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: Build & Push Docker Images
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n[Phase 3/4] Building and pushing Docker images..." -ForegroundColor Blue

Set-Location $ProjectRoot

if (-not $SkipBuild) {
    # Build backend
    Write-Host "Building backend image..." -ForegroundColor Yellow
    docker build -f Dockerfile.production -t "${EcrBackendUrl}:latest" -t "${EcrBackendUrl}:$Environment" .

    # Build frontend
    Write-Host "Building frontend image..." -ForegroundColor Yellow
    Set-Location "frontend"
    docker build -f Dockerfile.production -t "${EcrFrontendUrl}:latest" -t "${EcrFrontendUrl}:$Environment" .
    Set-Location $ProjectRoot
}

# Push images
Write-Host "Pushing backend image..." -ForegroundColor Yellow
docker push "${EcrBackendUrl}:latest"
docker push "${EcrBackendUrl}:$Environment"

Write-Host "Pushing frontend image..." -ForegroundColor Yellow
docker push "${EcrFrontendUrl}:latest"
docker push "${EcrFrontendUrl}:$Environment"

Write-Host "✓ Images pushed successfully" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: Scale Up ECS Services
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n[Phase 4/4] Starting ECS services..." -ForegroundColor Blue

$ServicePrefix = $EcsCluster -replace "-cluster$", ""

if ($Initial) {
    # On initial deploy, re-apply with initial_deployment=false to scale up
    Write-Host "Scaling up ECS services..."
    Set-Location $TerraformDir
    terraform apply -var-file="$TfvarsFile" -var="initial_deployment=false" -auto-approve
} else {
    # Just force a new deployment to pull latest images
    aws ecs update-service `
        --cluster $EcsCluster `
        --service "$ServicePrefix-backend" `
        --force-new-deployment `
        --region $AwsRegion | Out-Null

    aws ecs update-service `
        --cluster $EcsCluster `
        --service "$ServicePrefix-frontend" `
        --force-new-deployment `
        --region $AwsRegion | Out-Null
}

Write-Host "✓ ECS services starting" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅ Deployment Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Application URL: $AlbUrl" -ForegroundColor Cyan
Write-Host "API Docs: $AlbUrl/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: ECS tasks may take 2-3 minutes to become healthy." -ForegroundColor Yellow
Write-Host "Monitor: https://console.aws.amazon.com/ecs/home?region=$AwsRegion#/clusters/$EcsCluster/services"
