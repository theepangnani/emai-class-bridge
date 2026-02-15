# scripts/backup-create.ps1
# Create an on-demand Cloud SQL backup
# Usage: powershell -ExecutionPolicy Bypass -File scripts\backup-create.ps1

$GCLOUD = "C:\apps\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT = "emai-dev-01"
$INSTANCE = "emai-db"

Write-Host "=== ClassBridge: Create On-Demand Backup ===" -ForegroundColor Cyan
Write-Host "Instance: $INSTANCE"
Write-Host ""

$confirm = Read-Host "Create a backup of $INSTANCE now? (y/N)"
if ($confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host "Creating backup (this may take a few minutes)..." -ForegroundColor Yellow
& $GCLOUD sql backups create --instance=$INSTANCE --project=$PROJECT

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Backup created successfully." -ForegroundColor Green
    Write-Host "Run backup-verify.ps1 to confirm." -ForegroundColor Cyan
} else {
    Write-Host "ERROR: Backup creation failed." -ForegroundColor Red
    exit 1
}
