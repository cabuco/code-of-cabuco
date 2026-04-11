# ==============================================================================
# SCRIPT: Google Vault Systematic Export & Direct-to-Mount Archive (v16.0)
# ENVIRONMENT: Windows 11 / PowerShell 7.6.0 / GAM 7.40.00 / Rclone Mount (X:)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. System Persistence (Proven Heartbeat Method)
# ------------------------------------------------------------------------------
Write-Host " [1/6] Enabling system persistence heartbeat..." -ForegroundColor Cyan
$KeepAliveScript = {
    $wshell = New-Object -ComObject WScript.Shell
    while($true) {
        # F15 virtual key prevents sleep without interfering with your work
        $wshell.SendKeys("{F15}")
        Start-Sleep -Seconds 240
    }
}
$KeepAliveJob = Start-Job -ScriptBlock $KeepAliveScript
Write-Host " [OK] Persistence heartbeat started in background." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Mounted Drive Path Validation
# ------------------------------------------------------------------------------
# Based on your image, container folder is '201bce56' inside 'X:'
$targetMount = "X:\201bce56"

if (-not (Test-Path "X:\")) {
    Write-Error " [!] Drive 'X:' is not visible to this script."
    Write-Host " Note: If Rclone was started in a non-admin window, you must run this script in a non-admin window too." -ForegroundColor Yellow
    exit
}

if (-not (Test-Path $targetMount)) {
    Write-Host " [!] Found X: but folder '$targetMount' is missing. Creating it..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $targetMount -Force | Out-Null
}
Write-Host " [OK] Target mount path confirmed: $targetMount" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 3. Resume / Start Fresh Management
# ------------------------------------------------------------------------------
$stateFile = Join-Path $PSScriptRoot "vault_automation_state.json"
$automationState = @{ "Custodians" = @{} }

if (Test-Path $stateFile) {
    $choice = Read-Host "`n Existing progress detected. Resume? (Y) or Start Fresh (N)"
    if ($choice.ToUpper() -eq 'Y') {
        $automationState = Get-Content $stateFile | ConvertFrom-Json
        Write-Host " Resuming session. Checking progress..." -ForegroundColor Green
    } else {
        Remove-Item $stateFile -Force
        Write-Host " Starting fresh session." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------------------------
# 4. Matter Discovery (Header-Seek Method for GAM 7.40 Noise)
# ------------------------------------------------------------------------------
Write-Host "`n [3/6] Querying Google Vault for active matters..." -ForegroundColor Cyan
$rawOutput = & gam print vaultmatters matterstate OPEN

# Find the exact line where CSV data begins
$csvStart = [array]::FindIndex($rawOutput, [Predicate[string]]{ $args -match "^matterId," })
if ($csvStart -lt 0) { 
    Write-Error " Could not find matter list. Verify GAM Vault permissions."
    exit 
}

# Extract clean CSV data and parse
$cleanCsv = $rawOutput | ConvertFrom-Csv
$matterRegex = '(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)$'

$validMatters = @()
$skippedReport = @()

foreach ($row in $cleanCsv) {
    if ($row.name -match $matterRegex) {
        $user = $Matches['user']
        $email = "$user@github.com"
        # Only add if not already marked completed in the state file
        if (-not $automationState.Custodians.$email -or $automationState.Custodians.$email.Progress -ne "Completed") {
            $validMatters += @{ Id = $row.matterId; Name = $row.name; User = $user; Email = $email }
        }
    } else { $skippedReport += $row.name }
}
Write-Host " [OK] Identified $($validMatters.Count) valid matters to process." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. Systematic Processing Loop (Direct Download to X:)
# ------------------------------------------------------------------------------
foreach ($cust in $validMatters) {
    Write-Host "`n >>> PROCESSING CUSTODIAN: $($cust.Email) <<<" -ForegroundColor Yellow
    
    if (-not $automationState.Custodians.$($cust.Email)) {
        $automationState.Custodians.$($cust.Email) = @{ "MatterId" = $cust.Id; "Progress" = "Started"; "GmailId" = ""; "DriveId" = ""; "LinkedIds" = @() }
    }
    $cState = $automationState.Custodians.$($cust.Email)

    # Establish paths directly on the mounted drive
    $custRoot   = Join-Path $targetMount "$($cust.Email) lit hold"
    $gmailPath  = Join-Path $custRoot "$($cust.Email) Gmail Export"
    $linkedPath = Join-Path $gmailPath "$($cust.Email) Linked Drive Files"
    $drivePath  = Join-Path $custRoot "$($cust.Email) Drive Export"
    
    New-Item -Path $linkedPath -ItemType Directory -Force | Out-Null
    New-Item -Path $drivePath  -ItemType Directory -Force | Out-Null

    # -- 5a. Trigger Exports (if not already tracked) --
    if ($cState.GmailId -eq "") {
        Write-Host " [GMAIL] Creating Vault Export..."
        $gRes = & gam create export matter "id:$($cust.Id)" name "$($cust.Email) - Gmail Export" corpus mail accounts "$($cust.User)" format mbox showconfidentialmodecontent true exportlinkeddrivefiles true usenewexport true
        $cState.GmailId = ($gRes -match 'id:\s*([\w-]+)' -replace '.*id:\s*([\w-]+).*', '$1') | Select-Object -First 1
    }
    if ($cState.DriveId -eq "") {
        Write-Host " Creating Drive Vault Export..."
        $dRes = & gam create export matter "id:$($cust.Id)" name "$($cust.Email) - Drive Export" corpus drive accounts "$($cust.User)" includeshareddrives False includeaccessinfo False usenewexport true
        $cState.DriveId = ($dRes -match 'id:\s*([\w-]+)' -replace '.*id:\s*([\w-]+).*', '$1') | Select-Object -First 1
    }
    $automationState | ConvertTo-Json | Out-File $stateFile -Force

    # -- 5b. Polling (5-Minute Loop) --
    $gReady = $false ; $dReady = $false
    while (-not ($gReady -and $dReady)) {
        Write-Host " $(Get-Date -Format 'HH:mm:ss') - Polling Vault... (5 min wait)" -ForegroundColor Gray
        
        if (-not $gReady) {
            $gInfo = & gam info export "id:$($cState.GmailId)" matter "id:$($cust.Id)"
            if (($gInfo -match 'status:\s*COMPLETED')) { $gReady = $true; Write-Host " [GMAIL] Ready." -ForegroundColor Green }
            elseif (($gInfo -match 'status:\s*FAILED')) { $gReady = $true; Write-Warning " [!] Gmail Export FAILED." }
        }
        if (-not $dReady) {
            $dInfo = & gam info export "id:$($cState.DriveId)" matter "id:$($cust.Id)"
            if (($dInfo -match 'status:\s*COMPLETED')) { $dReady = $true; Write-Host " Drive Export Ready." -ForegroundColor Green }
            elseif (($dInfo -match 'status:\s*FAILED')) { $dReady = $true; Write-Warning " [!] Drive Export FAILED." }
        }

        if (-not ($gReady -and $dReady)) { Start-Sleep -Seconds 300 }
    }

    # -- 5c. Direct Streaming to X: Mount --
    Write-Host " Downloading Gmail artifacts to mount..."
    & gam download vaultexport "id:$($cState.GmailId)" matter "id:$($cust.Id)" targetfolder "$gmailPath" -s
    
    # Check for child Linked Drive exports 
    $listExp = & gam print vaultexports matter "id:$($cust.Id)"
    $hIdx = [array]::FindIndex($listExp, [Predicate[string]]{ $args -match "^id," })
    if ($hIdx -ge 0) {
        $exports = $listExp[$hIdx..($listExp.Length - 1)] | ConvertFrom-Csv
        foreach ($exp in $exports) {
            if ($exp.parentExportId -eq $cState.GmailId) {
                Write-Host " Downloading Linked Drive child artifact (Export: $($exp.id))..."
                & gam download vaultexport "id:$($exp.id)" matter "id:$($cust.Id)" targetfolder "$linkedPath" -s
                if ($exp.id -notin $cState.LinkedIds) { $cState.LinkedIds += $exp.id }
            }
        }
    }
    Write-Host " Downloading Drive artifacts (Expecting 5 files)..."
    & gam download vaultexport "id:$($cState.DriveId)" matter "id:$($cust.Id)" targetfolder "$drivePath" -s

    # -- 5d. Cleanup Vault (Free up organization slots) --
    Write-Host " Deleting exports from Google Vault (slot management)..." -ForegroundColor Gray
    & gam delete vaultexport matter "id:$($cust.Id)" "id:$($cState.GmailId)"
    & gam delete vaultexport matter "id:$($cust.Id)" "id:$($cState.DriveId)"
    foreach ($lId in $cState.LinkedIds) {
        & gam delete vaultexport matter "id:$($cust.Id)" "id:$lId"
    }
    
    $cState.Progress = "Completed"
    $automationState | ConvertTo-Json | Out-File $stateFile -Force
    Write-Host " Custodian $($cust.Email) retrieval finished." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 6. Final Reporting
# ------------------------------------------------------------------------------
Stop-Job $KeepAliveJob
Write-Host "`n" + ("=" * 80)
Write-Host " POST-JOB SUMMARY" -ForegroundColor Cyan
Write-Host " Processed: $($automationState.Custodians.PSObject.Properties.Count)"
Write-Host " Skipped (Naming Mismatch):  $($skippedReport.Count)"
if ($skippedReport.Count -gt 0) {
    Write-Host "`n Skipped Matter List:" -ForegroundColor Yellow
    foreach ($item in $skippedReport) { Write-Host " - $item" }
}
Write-Host ("=" * 80)
Write-Host "`n Job complete at $(Get-Date)." -ForegroundColor Green