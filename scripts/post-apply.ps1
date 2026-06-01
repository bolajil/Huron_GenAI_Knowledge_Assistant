# ===============================================================================
# Post-Apply — Windows PowerShell version
# Run after EVERY terraform apply to sync outputs to GitHub Variables.
#
# Usage: .\scripts\post-apply.ps1 -Env dev|staging|prod
# ===============================================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev","staging","prod")]
    [string]$Env
)

$REPO   = "bolajil/Huron_GenAI_Knowledge_Assistant"
$TFDIR  = "terraform\aws"
$PREFIX = $Env.ToUpper()

Write-Host "Reading Terraform outputs for: $Env"
Push-Location $TFDIR

# ── Read outputs ───────────────────────────────────────────────────────────────
$ALB_URL      = terraform output -raw alb_dns_name       2>$null
$ECR_BACKEND  = terraform output -raw ecr_backend_url    2>$null
$ECR_FRONTEND = terraform output -raw ecr_frontend_url   2>$null
$ECS_CLUSTER  = terraform output -raw ecs_cluster_name   2>$null

Pop-Location

if (-not $ALB_URL) {
    Write-Error "No Terraform outputs found. Run terraform apply first."
    exit 1
}

# ── Push to GitHub Variables ───────────────────────────────────────────────────
Write-Host "Setting GitHub Variables for $PREFIX..."
$ALB_URL      | gh variable set "${PREFIX}_ALB_URL"      --repo $REPO
$ECR_BACKEND  | gh variable set "${PREFIX}_ECR_BACKEND"  --repo $REPO
$ECR_FRONTEND | gh variable set "${PREFIX}_ECR_FRONTEND" --repo $REPO
$ECS_CLUSTER  | gh variable set "${PREFIX}_ECS_CLUSTER"  --repo $REPO

if ($Env -eq "prod") {
    $ALB_URL | gh variable set "PROD_URL" --repo $REPO
}

Write-Host ""
Write-Host "GitHub Variables updated:"
Write-Host "  ${PREFIX}_ALB_URL      = $ALB_URL"
Write-Host "  ${PREFIX}_ECR_BACKEND  = $ECR_BACKEND"
Write-Host "  ${PREFIX}_ECR_FRONTEND = $ECR_FRONTEND"
Write-Host "  ${PREFIX}_ECS_CLUSTER  = $ECS_CLUSTER"
Write-Host ""
Write-Host "Push to the '$Env' branch to trigger deployment."
