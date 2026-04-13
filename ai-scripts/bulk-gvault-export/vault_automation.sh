# ==============================================================================
# SCRIPT: Google Vault Systematic Export & Direct-to-Mount Archive (v59.1-Public)
# Status: PRODUCTION STABLE - Sanitized for Public Release
# Description: Automates Google Vault exports for multiple custodians based on 
#              matter naming regex and downloads to a specified network mount.
# ==============================================================================

# --- CONFIGURATION ---
$MaxConcurrentCustodians = 5
$targetMount = "Z:\Path\To\Your\Archive"  # Replace with your actual mount point
$domain = "example.com"                   # Replace with your organization's domain
$stateFile = Join-Path $PSScriptRoot "vault_automation_state.json"

# Regex to identify matters in scope (e.g., matching "@username lit hold")
$matterRegex = '(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)'

# --- LOGIC: VERIFICATION FUNCTION ---
# Prevents marking a matter "Completed" if the download was interrupted or empty.
function Test-ArchiveIntegrity {
    param($path)
    if (-not (Test-Path $path)) { return $false }
    # Count files while excluding folders to verify actual data transfer occurred
    $files = Get-ChildItem -Path $path -Recurse | Where-Object { -not $_.PSIsContainer }
    return ($null -ne $files -and $files.Count -gt 0)
}

# --- INITIALIZATION ---
Write-Host " [1/6] Heartbeat enabled." -ForegroundColor Cyan
$KeepAliveJob = Start-Job -ScriptBlock {
    $wshell = New-Object -ComObject WScript.Shell
    while($true) { $wshell.SendKeys("{F15}"); Start-Sleep -Seconds 240 }
}

if (-not (Test-Path $targetMount)) { 
    Write-Host "[!] ERROR: Target Mount $targetMount not found!" -ForegroundColor Red
    exit 
}

$automationState = @() 
if (Test-Path $stateFile) { 
    $automationState = Get-Content $stateFile | ConvertFrom-Json | ForEach-Object { $_ } 
}

Write-Host "`n [3/6] Querying Google Vault Matters..." -ForegroundColor Cyan
# Requires GAM (Google Management Tool) installed and configured in system path
$rawOutput = & gam print vaultmatters matterstate OPEN
$headerIndex = [array]::FindIndex($rawOutput, [Predicate[string]]{ $args -match "^matterId," })
$cleanCsv = $rawOutput[$headerIndex..($rawOutput.Length-1)] | ConvertFrom-Csv

$PendingQueue = @()
$SkippedMatters = @()

# --- MATTER FILTERING ---
foreach ($row in $cleanCsv) {
    $matterName = $row.name.Trim()
    if ($matterName -match $matterRegex) {
        $user = $Matches['user']; $email = "$user@$domain"
        # Only add to queue if not already marked "Completed" in state file
        if (-not ($automationState | Where-Object { $_.Email -eq $email -and $_.Progress -eq "Completed" })) {
            $PendingQueue += [pscustomobject]@{ Id = $row.matterId; User = $user; Email = $email }
        }
    } else {
        $SkippedMatters += $matterName
    }
}

# --- AUDIT: SKIPPED MATTERS ---
if ($SkippedMatters.Count -gt 0) {
    Write-Host "`n [!] AUDIT: The following $($SkippedMatters.Count) matters skipped (Naming Convention):" -ForegroundColor Yellow
    foreach ($m in $SkippedMatters) { Write-Host "     - $m" -ForegroundColor Gray }
}

Write-Host "`n [OK] Found $($PendingQueue.Count) matters within scope." -ForegroundColor Green

# --- PROCESSING LOOP ---
$ActivePool = @()
while ($PendingQueue.Count -gt 0 -or $ActivePool.Count -gt 0) {
    # Refill active pool up to MaxConcurrentCustodians
    while ($ActivePool.Count -lt $MaxConcurrentCustodians -and $PendingQueue.Count -gt 0) {
        $cust = $PendingQueue[0]
        $PendingQueue = if ($PendingQueue.Count -gt 1) { $PendingQueue[1..($PendingQueue.Count-1)] } else { @() }
        $ActivePool += $cust
    }

    Write-Host "`n --- POLLING POOL STATUS: $(Get-Date -Format 'HH:mm:ss') ---" -ForegroundColor Gray
    $PoolToKeep = @()

    foreach ($cust in $ActivePool) {
        Start-Sleep -Seconds 2 
        
        # Check current status of exports in Vault
        $currentExports = & gam print vaultexports matter "id:$($cust.Id)" | ConvertFrom-Csv
        $gExp = $currentExports | Where-Object { $_.name -eq "$($cust.User)-mail" } | Sort-Object creationTime -Descending | Select-Object -First 1
        $dExp = $currentExports | Where-Object { $_.name -eq "$($cust.User)-drive" } | Sort-Object creationTime -Descending | Select-Object -First 1

        if (-not $gExp -or -not $dExp) {
            Write-Host " [QUEUE] Creating missing exports: $($cust.Email)" -ForegroundColor Yellow
            if (-not $gExp) { & gam create export matter "id:$($cust.Id)" name "$($cust.User)-mail" corpus mail accounts "$($cust.User)" usenewexport true 2>&1 | Out-Null }
            if (-not $dExp) { & gam create export matter "id:$($cust.Id)" name "$($cust.User)-drive" corpus drive accounts "$($cust.User)" usenewexport true 2>&1 | Out-Null }
            $PoolToKeep += $cust
        } 
        else {
            if ($gExp.status -eq "COMPLETED" -and $dExp.status -eq "COMPLETED") {
                Write-Host " [READY] $($cust.Email) ready." -ForegroundColor Green
                
                # Setup folder structure on archive mount
                $custRoot = Join-Path $targetMount "$($cust.Email)_Hold"
                $gmailP = Join-Path $custRoot "Gmail"
                $driveP = Join-Path $custRoot "Drive"
                
                if (-not (Test-Path $gmailP)) { New-Item -Path $gmailP -ItemType Directory -Force | Out-Null }
                if (-not (Test-Path $driveP)) { New-Item -Path $driveP -ItemType Directory -Force | Out-Null }
                
                # --- DOWNLOAD PHASE ---
                Write-Host " [DOWNLOADING] Pulling data for $($cust.Email)..." -ForegroundColor White
                & gam download vaultexport "$($gExp.name)" matter "id:$($cust.Id)" targetfolder "$gmailP"
                & gam download vaultexport "$($dExp.name)" matter "id:$($cust.Id)" targetfolder "$driveP"

                # --- VERIFICATION & CLEANUP ---
                if ((Test-ArchiveIntegrity -path $gmailP) -and (Test-ArchiveIntegrity -path $driveP)) {
                    Write-Host " [VERIFIED] Integrity check passed for $($cust.Email)." -ForegroundColor Cyan
                    
                    # Delete remote exports once local copy is verified
                    & gam delete vaultexport "$($gExp.name)" matter "id:$($cust.Id)" | Out-Null
                    & gam delete vaultexport "$($dExp.name)" matter "id:$($cust.Id)" | Out-Null
                    
                    # Update local state
                    $cState = $automationState | Where-Object { $_.Email -eq $cust.Email }
                    if ($cState) { $cState.Progress = "Completed" } else { $automationState += [pscustomobject]@{ Email=$cust.Email; Progress="Completed" } }
                } else {
                    Write-Host " [!] VERIFICATION FAILED (Empty/Partial Transfer) for $($cust.Email). Retrying..." -ForegroundColor Red
                    $PoolToKeep += $cust
                }
            } else {
                Write-Host " [...] $($cust.Email) - Gmail: $($gExp.status), Drive: $($dExp.status)" -ForegroundColor Gray
                $PoolToKeep += $cust
            }
        }
        # Save state progress after each custodian check
        $automationState | ConvertTo-Json -Depth 10 | Out-File $stateFile -Force
    }
    $ActivePool = $PoolToKeep
    # Wait 10 minutes before next polling cycle if matters are still in progress
    if ($ActivePool.Count -gt 0) { Start-Sleep -Seconds 600 }
}

Stop-Job $KeepAliveJob
Write-Host "`n[FINISHED] All tasks completed." -ForegroundColor Magenta
