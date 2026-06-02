# ─────────────────────────────────────────────────────────────────────────────
# Take an RDS snapshot before terraform destroy
# Usage: .\scripts\db-snapshot.ps1 -Env dev|staging|prod
# ─────────────────────────────────────────────────────────────────────────────

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev","staging","prod")]
    [string]$Env
)

$REGION    = "us-east-1"
$DB_ID     = "huron-$Env-db"
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmm"
$SNAP_ID   = "huron-$Env-manual-$TIMESTAMP"

Write-Host "Taking RDS snapshot before destroy..."
Write-Host "  DB Instance : $DB_ID"
Write-Host "  Snapshot ID : $SNAP_ID"
Write-Host ""

# Check instance exists
$db = aws rds describe-db-instances --db-instance-identifier $DB_ID --region $REGION 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "No RDS instance '$DB_ID' found — skipping snapshot"
    exit 0
}

# Create snapshot
aws rds create-db-snapshot `
    --db-instance-identifier $DB_ID `
    --db-snapshot-identifier $SNAP_ID `
    --region $REGION | Out-Null

Write-Host "Waiting for snapshot to complete (this takes 5-10 minutes)..."
aws rds wait db-snapshot-completed `
    --db-snapshot-identifier $SNAP_ID `
    --region $REGION

Write-Host ""
Write-Host "Snapshot complete: $SNAP_ID"
Write-Host "To restore: aws rds restore-db-instance-from-db-snapshot --db-instance-identifier $DB_ID --db-snapshot-identifier $SNAP_ID"
Write-Host ""
Write-Host "Now safe to run: terraform apply -destroy -var-file environments/$Env.tfvars -auto-approve"
