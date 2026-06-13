# ==============================================================================
# SCRIPT: AzCopy Background Consumer & Staging Purge Loop
# Location: Run inside a dedicated background PowerShell window
# ==============================================================================

# Explicit Configuration Framework
$azcopyPath = "C:\Program Files\AzCopy\azcopy.exe"
$zipOutDir  = "C:\VaultTemp\ZipOut"

# Paste your real Azure Container SAS URL connection string below
$sasUrl     = "https://<your_storage_account>.blob.core.windows.net/<your_container>?<your_sas_token_parameters>"

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ENGINE INITIALIZED: Autonomous Cloud Synchronization Architecture" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green

while ($true) {
    $timeStamp = (Get-Date).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "[$timeStamp] Scanning Exchange Waiting Room for finalized archives..." -ForegroundColor Cyan
    
    # Identify completed file containers resting on local storage
    $zipFiles = Get-ChildItem -Path $zipOutDir -Filter "*.zip"
    
    if ($zipFiles.Count -eq 0) {
        Write-Host " [Staging Status] Exchange directory clear. Sleeping for 5 minutes..." -ForegroundColor Gray
    } else {
        Write-Host " [Staging Status] Identified $($zipFiles.Count) package(s) ready for cloud deployment." -ForegroundColor Yellow
        
        foreach ($file in $zipFiles) {
            # Extract core target entity out of string profile
            $entityIdentity = $file.Name -replace "_Hold\.zip$", ""
            
            Write-Host ""
            Write-Host " >>> Deploying Archive Package: $entityIdentity <<<" -ForegroundColor White -BackgroundColor DarkGreen
            
            # Execute Native high-speed copy stream operation 
            & $azcopyPath copy $file.FullName $sasUrl --recursive
            
            # Reclaim local workspace storage assets upon verified transfer success
            if ($LASTEXITCODE -eq 0) {
                Write-Host " [SUCCESS] Cloud target committed successfully for $entityIdentity." -ForegroundColor Green
                
                # Immediate local disk sanitation lock
                Remove-Item $file.FullName -Force
                Write-Host " [INSULATION] Staging file safely purged from local drive array: $($file.Name)" -ForegroundColor Magenta
            } else {
                Write-Host " [CRITICAL] AzCopy execution faulted for $entityIdentity. Preserving file for re-evaluation pass." -ForegroundColor Red
            }
        }
    }
    
    Start-Sleep -Seconds 300
}
