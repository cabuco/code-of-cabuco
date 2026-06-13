# ==============================================================================
# SCRIPT: Google Vault Automation Engine (The Producer)
# Location: Run inside your primary Administrator PowerShell window (Window 1)
# ==============================================================================

# Explicit Configuration Framework
$gamPath       = "<path_to_your_gam_or_gyb_executable>"
$workspaceDir  = "<path_to_your_local_temp_workspace_folder>"
$zipOutDir     = "<path_to_your_local_staging_zip_out_folder>"
$sevenZipPath  = "<path_to_your_7zip_executable_7z.exe>"
$userListPath  = "<path_to_your_migration_users_csv>"
$matterId      = "<your_google_vault_legal_matter_id>"

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ENGINE INITIALIZED: Autonomous Google Vault Production Architecture" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green

# Import target migration matrix (Expects a CSV with an 'Email' column)
$users = Import-Csv -Path $userListPath

foreach ($user in $users) {
    $targetEmail = $user.Email
    $timeStamp   = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $exportName  = "Migration_Hold_" + $targetEmail + "_" + $timeStamp
    $userWorkDir = Join-Path $workspaceDir $targetEmail
    
    # Create isolated workspace directory for this specific user
    New-Item -ItemType Directory -Path $userWorkDir -Force | Out-Null
    
    $currentTime = (Get-Date).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "[$currentTime] Starting processing for: $targetEmail" -ForegroundColor Cyan
    
    # 1. Initiate the Google Vault Export Request via API
    Write-Host " [Vault API] Triggering remote export container: $exportName" -ForegroundColor Yellow
    & $gamPath vault create export name $exportName matter $matterId query accounts $targetEmail corpus mail
    
    # 2. Poll the API and Wait for Export Completion
    $exportComplete = $false
    while (-not $exportComplete) {
        Write-Host " [Vault API] Polling export status... sleeping 60 seconds." -ForegroundColor Gray
        Start-Sleep -Seconds 60
        
        # Check current status via management tool binary
        $statusCheck = & $gamPath vault show export name $exportName matter $matterId
        if ($statusCheck -match "status: completed" -or $statusCheck -match "COMPLETED") {
            $exportComplete = $true
            Write-Host " [SUCCESS] Remote export completed by Google infrastructure." -ForegroundColor Green
        } elseif ($statusCheck -match "status: failed" -or $statusCheck -match "FAILED") {
            Write-Host " [CRITICAL] Google Vault failed to compile export for $targetEmail. Skipping." -ForegroundColor Red
            break
        }
    }
    
    if (-not $exportComplete) { continue }
    
    # 3. Download Content Locally to Staging Workspace
    Write-Host " [Download] Extracting remote data stream down to: $userWorkDir" -ForegroundColor Yellow
    & $gamPath vault download export name $exportName matter $matterId targetdir $userWorkDir
    
    # 4. In-Line High Compression to Staging Waiting Room
    $targetZipFile = Join-Path $zipOutDir ($targetEmail + "_Hold.zip")
    Write-Host " [Compression] Handing off to multi-threaded 7-Zip engine..." -ForegroundColor Yellow
    
    # Executes 7z: 'a' adds to archive, '-mx=1' uses fast compression for optimal pipeline throughput
    & $sevenZipPath a -mx=1 $targetZipFile ($userWorkDir + "\*")
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [SUCCESS] Created archive package: $targetZipFile" -ForegroundColor Green
        
        # Immediate local scratch space sanitation to save local storage capacity
        Remove-Item -Path $userWorkDir -Recurse -Force
        Write-Host " [INSULATION] Scratch workspace cleared for $targetEmail. Onward." -ForegroundColor Magenta
    } else {
        Write-Host " [CRITICAL] 7-Zip compression failure encountered for $targetEmail. Preserving raw workspace." -ForegroundColor Red
    }
    
    # 5. Clean up remote Vault instance to avoid hitting Google cloud storage quotas
    Write-Host " [Vault Cleanup] Deleting cloud export metadata container..." -ForegroundColor Gray
    & $gamPath vault delete export name $exportName matter $matterId
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " MIGRATION WAVE COMPLETE: All targeted accounts processed." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
