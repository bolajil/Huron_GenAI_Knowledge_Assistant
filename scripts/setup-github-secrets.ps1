# ===============================================================================
# Setup GitHub Actions Secrets — Windows PowerShell version
# Run ONCE after first terraform apply for each environment.
#
# Usage: .\scripts\setup-github-secrets.ps1 -Env dev|staging|prod
# ===============================================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev","staging","prod")]
    [string]$Env
)

$REPO      = "bolajil/Huron_GenAI_Knowledge_Assistant"
$IAM_USER  = "huron-$Env-cicd-user"

Write-Host "Setting up GitHub Actions secrets for: $Env"
Write-Host "IAM user : $IAM_USER"
Write-Host "Repo     : $REPO"
Write-Host ""

# ── Check prerequisites ────────────────────────────────────────────────────────
foreach ($cmd in @("aws","gh")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "$cmd not found. Install it first."
        exit 1
    }
}

# ── Verify IAM user exists ─────────────────────────────────────────────────────
$userCheck = aws iam get-user --user-name $IAM_USER 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "IAM user '$IAM_USER' does not exist. Run terraform apply first."
    exit 1
}

# ── Delete all existing keys (max 2 allowed, clean slate) ─────────────────────
Write-Host "Cleaning up old access keys..."
$existingKeys = aws iam list-access-keys --user-name $IAM_USER | ConvertFrom-Json
foreach ($key in $existingKeys.AccessKeyMetadata) {
    aws iam delete-access-key --user-name $IAM_USER --access-key-id $key.AccessKeyId | Out-Null
    Write-Host "  Deleted: $($key.AccessKeyId)"
}

# ── Create fresh access key ────────────────────────────────────────────────────
Write-Host "Creating new access key..."
$keyJson = aws iam create-access-key --user-name $IAM_USER | ConvertFrom-Json
$accessKeyId     = $keyJson.AccessKey.AccessKeyId
$secretAccessKey = $keyJson.AccessKey.SecretAccessKey
Write-Host "  Created: $accessKeyId"

# ── Set GitHub Secrets ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Setting GitHub Actions Secrets..."
$accessKeyId     | gh secret set AWS_ACCESS_KEY_ID     --repo $REPO
$secretAccessKey | gh secret set AWS_SECRET_ACCESS_KEY --repo $REPO
Write-Host "  AWS_ACCESS_KEY_ID     = $accessKeyId"
Write-Host "  AWS_SECRET_ACCESS_KEY = [hidden]"

Write-Host ""
Write-Host "Done. Run .\scripts\post-apply.ps1 -Env $Env next to set GitHub Variables."
