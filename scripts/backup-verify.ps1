# scripts/backup-verify.ps1
# Verify Cloud SQL backup health
# Usage: powershell -ExecutionPolicy Bypass -File scripts\backup-verify.ps1

$GCLOUD = "C:\apps\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT = "emai-dev-01"
$INSTANCE = "emai-db"

Write-Host "=== ClassBridge: Backup Verification ===" -ForegroundColor Cyan
Write-Host ""

# 1. Instance health
Write-Host "[1/4] Instance status..." -ForegroundColor Yellow
$state = & $GCLOUD sql instances describe $INSTANCE --project=$PROJECT --format="value(state)" 2>&1
if ($state -eq "RUNNABLE") {
    Write-Host "  Instance state: $state (healthy)" -ForegroundColor Green
} else {
    Write-Host "  Instance state: $state (UNEXPECTED)" -ForegroundColor Red
}

# 2. Backup configuration
Write-Host ""
Write-Host "[2/4] Backup configuration..." -ForegroundColor Yellow
& $GCLOUD sql instances describe $INSTANCE --project=$PROJECT `
    --format="table(settings.backupConfiguration.enabled,settings.backupConfiguration.startTime,settings.backupConfiguration.pointInTimeRecoveryEnabled,settings.backupConfiguration.backupRetentionSettings.retainedBackups)"

# 3. Recent backups
Write-Host ""
Write-Host "[3/4] Recent backups (last 7)..." -ForegroundColor Yellow
& $GCLOUD sql backups list --instance=$INSTANCE --project=$PROJECT --limit=7 `
    --format="table(id,windowStartTime.date('%Y-%m-%d %H:%M UTC'),status,type)"

# 4. Check most recent backup status
Write-Host ""
Write-Host "[4/4] Latest backup status..." -ForegroundColor Yellow
$latestStatus = & $GCLOUD sql backups list --instance=$INSTANCE --project=$PROJECT --limit=1 `
    --format="value(status)" 2>&1

if ($latestStatus -eq "SUCCESSFUL") {
    Write-Host "  Latest backup: SUCCESSFUL" -ForegroundColor Green
} elseif ([string]::IsNullOrWhiteSpace($latestStatus)) {
    Write-Host "  No backups found yet. Run backup-create.ps1 or wait until 02:00 UTC." -ForegroundColor Yellow
} else {
    Write-Host "  Latest backup: $latestStatus (investigate!)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
