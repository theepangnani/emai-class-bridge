# scripts/backup-setup.ps1
# One-time setup for Cloud SQL automated backups and monitoring
# Usage: powershell -ExecutionPolicy Bypass -File scripts\backup-setup.ps1

$ErrorActionPreference = "Stop"

$GCLOUD = "C:\apps\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT = "emai-dev-01"
$INSTANCE = "emai-db"
$REGION = "us-central1"

Write-Host "=== ClassBridge: Cloud SQL Backup Setup ===" -ForegroundColor Cyan
Write-Host "Project:  $PROJECT"
Write-Host "Instance: $INSTANCE"
Write-Host "Region:   $REGION"
Write-Host ""

# Step 1: Enable automated backups with PITR
Write-Host "[1/4] Configuring automated backups (02:00 UTC, 7-day retention, PITR enabled)..." -ForegroundColor Yellow
& $GCLOUD sql instances patch $INSTANCE `
    --project=$PROJECT `
    --backup-start-time="02:00" `
    --enable-point-in-time-recovery `
    --retained-backups-count=7 `
    --retained-transaction-log-days=7 `
    --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to configure backups" -ForegroundColor Red
    exit 1
}
Write-Host "  Automated backups configured successfully." -ForegroundColor Green

# Step 2: Verify configuration
Write-Host ""
Write-Host "[2/4] Verifying backup configuration..." -ForegroundColor Yellow
& $GCLOUD sql instances describe $INSTANCE `
    --project=$PROJECT `
    --format="table(settings.backupConfiguration.enabled,settings.backupConfiguration.startTime,settings.backupConfiguration.pointInTimeRecoveryEnabled,settings.backupConfiguration.backupRetentionSettings.retainedBackups,settings.backupConfiguration.transactionLogRetentionDays)"

# Step 3: Create log-based metric for backup failures
Write-Host ""
Write-Host "[3/4] Creating log-based metric for backup failure detection..." -ForegroundColor Yellow
$filter = 'resource.type = "cloudsql_database" AND severity >= ERROR'
& $GCLOUD logging metrics create cloudsql-backup-failure `
    --project=$PROJECT `
    --description="Cloud SQL backup failures for emai-db" `
    "--log-filter=$filter" 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  Log-based metric may already exist or requires manual creation." -ForegroundColor Yellow
    Write-Host "  Check: GCP Console > Logging > Log-based Metrics" -ForegroundColor Yellow
} else {
    Write-Host "  Log-based metric created." -ForegroundColor Green
}

# Step 4: Create the backup failure alert policy
Write-Host ""
Write-Host "[4/4] Creating backup failure monitoring alert..." -ForegroundColor Yellow
$ALERT_POLICY_PATH = Join-Path $PSScriptRoot "monitoring\backup-failure-alert-policy.json"

if (Test-Path $ALERT_POLICY_PATH) {
    & $GCLOUD beta monitoring policies create `
        --project=$PROJECT `
        --policy-from-file=$ALERT_POLICY_PATH 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Alert policy may already exist or requires manual creation." -ForegroundColor Yellow
        Write-Host "  The JSON template is at: $ALERT_POLICY_PATH" -ForegroundColor Yellow
    } else {
        Write-Host "  Backup failure alert created." -ForegroundColor Green
    }
} else {
    Write-Host "  Alert policy file not found at $ALERT_POLICY_PATH" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Backups will run daily at 02:00 UTC with 7-day retention."
Write-Host "PITR enabled with 7 days of transaction log retention."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run backup-create.ps1 to create an immediate on-demand backup"
Write-Host "  2. Run backup-verify.ps1 to confirm everything is working"
Write-Host "  3. Check GCP Console > SQL > emai-db > Backups after 02:00 UTC"
