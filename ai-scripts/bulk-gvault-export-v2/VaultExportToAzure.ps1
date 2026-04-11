# ==============================================================================
# SCRIPT: Google Vault Systematic Export & Direct-to-Mount Archive (v29.0)
# FEATURES: Fallback ID Discovery, API Pacing, Slot Cleanup
# ==============================================================================

$MaxConcurrentCustodians = 5
$targetMount = "X:\201bce56"
$domain = "github.com"
$stateFile = Join-Path $PSScriptRoot "vault_automation_state.json"
$matterRegex = '(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)'

Write-Host " [1/6] Heartbeat enabled." -ForegroundColor Cyan
$KeepAliveJob = Start-Job -ScriptBlock {
    $wshell = New-Object -ComObject WScript.Shell
    while($true) { $wshell.SendKeys("{F15}"); Start-Sleep -Seconds 240 }
}

if (-not (Test-Path $targetMount)) { New-Item -ItemType Directory -Path $targetMount -Force | Out-Null }

$automationState = @() 
if (Test-Path $stateFile) {
    $automationState = Get-Content $stateFile | ConvertFrom-Json | ForEach-Object { $_ }
    Write-Host " [OK] Resuming session." -ForegroundColor Green
}

Write-Host "`n [3/6] Querying Google Vault..." -ForegroundColor Cyan
$rawOutput = & gam print vaultmatters matterstate OPEN
$csvStart = [array]::FindIndex($rawOutput, [Predicate[string]]{ $args -match "^matterId," })
$cleanCsv = $rawOutput[$csvStart..($rawOutput.Length-1)] | ConvertFrom-Csv
$PendingQueue = @()

foreach ($row in $cleanCsv) {
    if ($row.name.Trim() -match $matterRegex) {
        $user = $Matches['user']; $email = "$user@$domain"
        if (-not ($automationState | Where-Object { $_.Email -eq $email -and $_.Progress -eq "Completed" })) {
            $PendingQueue += [pscustomobject]@{ Id = $row.matterId; Name = $row.name.Trim(); User = $user; Email = $email }
        }
    }
}

$ActivePool = @()
while ($PendingQueue.Count -gt 0 -or $ActivePool.Count -gt 0) {
    while ($ActivePool.Count -lt $MaxConcurrentCustodians -and $PendingQueue.Count -gt 0) {
        $cust = $PendingQueue[0] 
        $PendingQueue = if ($PendingQueue.Count -gt 1) { $PendingQueue[1..($PendingQueue.Count-1)] } else { @() }
        
        $cState = $automationState | Where-Object { $_.Email -eq $cust.Email }
        if ($null -eq $cState) {
            $cState = [pscustomobject]@{ "Email" = $cust.Email; "MatterId" = $cust.Id; "Progress" = "Exporting"; "GmailId" = ""; "DriveId" = ""; "LinkedIds" = @() }
            $automationState += $cState
        }
        
        Write-Host " [QUEUE] Initiating: $($cust.Email)" -ForegroundColor Yellow
        
        # Robust function to create and then FIND the ID via list
        $getExportId = {
            param($mId, $name, $corp, $user)
            # 1. Attempt creation
            & gam create export matter "id:$mId" name "$name" corpus $corp accounts "$user" usenewexport true 2>&1 | Out-Null
            Start-Sleep -Seconds 5
            # 2. Immediately look it up in the matter to get the real ID
            $vaultList = & gam print vaultexports matter "id:$mId" 2>$null | ConvertFrom-Csv
            $match = $vaultList | Where-Object { $_.name -eq $name } | Sort-Object creationTime -Descending | Select-Object -First 1
            if ($match) { return $match.id }
            return ""
        }

        if ([string]::IsNullOrWhiteSpace($cState.GmailId)) {
            $cState.GmailId = & $getExportId $cust.Id "$($cust.Email) - Gmail" "mail" $cust.User
            Write-Host "   -> Gmail ID: $($cState.GmailId)" -ForegroundColor Gray
            Start-Sleep -Seconds 10
        }
        if ([string]::IsNullOrWhiteSpace($cState.DriveId)) {
            $cState.DriveId = & $getExportId $cust.Id "$($cust.Email) - Drive" "drive" $cust.User
            Write-Host "   -> Drive ID: $($cState.DriveId)" -ForegroundColor Gray
            Start-Sleep -Seconds 10
        }
        
        $ActivePool += $cust
        $automationState | ConvertTo-Json -Depth 10 | Out-File $stateFile -Force
    }

    Write-Host "`n --- POLLING STATUS ---" -ForegroundColor Gray
    $PoolToKeep = @()
    foreach ($cust in $ActivePool) {
        $cState = $automationState | Where-Object { $_.Email -eq $cust.Email }
        if ([string]::IsNullOrWhiteSpace($cState.GmailId)) { $PoolToKeep += $cust; continue }

        $gInfo = & gam info export "id:$($cState.GmailId)" matter "id:$($cust.Id)" 2>&1 | Out-String
        $gStatus = if ($gInfo -match 'status:\s*(\w+)') { $Matches[1] } else { "UNKNOWN" }
        
        $dInfo = & gam info export "id:$($cState.DriveId)" matter "id:$($cust.Id)" 2>&1 | Out-String
        $dStatus = if ($dInfo -match 'status:\s*(\w+)') { $Matches[1] } else { "UNKNOWN" }

        if ($gStatus -eq "COMPLETED" -and $dStatus -eq "COMPLETED") {
            Write-Host " [OK] $($cust.Email) ready. Downloading..." -ForegroundColor Green
            $custRoot = Join-Path $targetMount "$($cust.Email) hold"
            $gmailP = Join-Path $custRoot "Gmail"; $driveP = Join-Path $custRoot "Drive"
            New-Item -Path $gmailP, $driveP -ItemType Directory -Force | Out-Null
            & gam download vaultexport "id:$($cState.GmailId)" matter "id:$($cust.Id)" targetfolder "$gmailP" -s
            & gam download vaultexport "id:$($cState.DriveId)" matter "id:$($cust.Id)" targetfolder "$driveP" -s
            & gam delete vaultexport matter "id:$($cust.Id)" "id:$($cState.GmailId)"
            & gam delete vaultexport matter "id:$($cust.Id)" "id:$($cState.DriveId)"
            $cState.Progress = "Completed"
        } else {
            Write-Host " $($cust.Email) - Gmail: $gStatus, Drive: $dStatus" -ForegroundColor Gray
            $PoolToKeep += $cust
        }
    }
    $ActivePool = $PoolToKeep
    $automationState | ConvertTo-Json -Depth 10 | Out-File $stateFile -Force
    if ($ActivePool.Count -gt 0) { Start-Sleep -Seconds 300 }
}
Stop-Job $KeepAliveJob
