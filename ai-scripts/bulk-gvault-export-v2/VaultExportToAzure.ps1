# ==============================================================================
# SCRIPT: Google Vault Systematic Export & Direct-to-Mount Archive (v42.0)
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
}

Write-Host "`n [3/6] Querying Google Vault Matters..." -ForegroundColor Cyan
$rawOutput = & gam print vaultmatters matterstate OPEN
$headerIndex = [array]::FindIndex($rawOutput, [Predicate[string]]{ $args -match "^matterId," })
$cleanCsv = $rawOutput[$headerIndex..($rawOutput.Length-1)] | ConvertFrom-Csv
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
        $cust = $PendingQueue[0]; $PendingQueue = if ($PendingQueue.Count -gt 1) { $PendingQueue[1..($PendingQueue.Count-1)] } else { @() }
        $ActivePool += $cust
    }

    Write-Host "`n --- POLLING STATUS at $(Get-Date -Format 'HH:mm:ss') ---" -ForegroundColor Gray
    $PoolToKeep = @()

    foreach ($cust in $ActivePool) {
        $cState = $automationState | Where-Object { $_.Email -eq $cust.Email }
        if ($null -eq $cState) {
            $cState = [pscustomobject]@{ "Email" = $cust.Email; "MatterId" = $cust.Id; "Progress" = "Exporting"; "GmailId" = ""; "DriveId" = "" }
            $automationState += $cState
        }
        
        # --- ROBUST EXPORT ID CAPTURE ---
        if ([string]::IsNullOrWhiteSpace($cState.GmailId) -or [string]::IsNullOrWhiteSpace($cState.DriveId)) {
            Write-Host " [QUEUE] Initiating Vault tasks for: $($cust.Email)" -ForegroundColor Yellow
            $types = @("mail", "drive")
            foreach ($t in $types) {
                $eName = "$($cust.User)-$t"
                & gam create export matter "id:$($cust.Id)" name "$eName" corpus $t accounts "$($cust.User)" usenewexport true 2>&1 | Out-Null
                Start-Sleep -Seconds 8
                
                # Fetch only the exports for this matter in CSV format
                $exportList = & gam print vaultexports matter "id:$($cust.Id)" | ConvertFrom-Csv
                
                # Find the export where the name matches our creation name
                # We select the most recent one that IS NOT the Matter ID
                $match = $exportList | Where-Object { ($_.name -eq $eName) -and ($_.id -ne $cust.Id) } | Sort-Object creationTime -Descending | Select-Object -First 1
                
                if ($match) {
                    if ($t -eq "mail") { $cState.GmailId = $match.id } else { $cState.DriveId = $match.id }
                }
            }
            Write-Host "   -> IDs: Gmail($($cState.GmailId)) Drive($($cState.DriveId))" -ForegroundColor Gray
        }

        # --- STATUS CHECK ---
        if ($cState.GmailId -and $cState.DriveId) {
            $gInfo = & gam info export "id:$($cState.GmailId)" matter "id:$($cust.Id)" 2>&1 | Out-String
            $gStatus = if ($gInfo -match 'status:\s*(\w+)') { $Matches[1] } else { "UNKNOWN" }
            
            $dInfo = & gam info export "id:$($cState.DriveId)" matter "id:$($cust.Id)" 2>&1 | Out-String
            $dStatus = if ($dInfo -match 'status:\s*(\w+)') { $Matches[1] } else { "UNKNOWN" }

            if ($gStatus -eq "COMPLETED" -and $dStatus -eq "COMPLETED") {
                Write-Host " [OK] $($cust.Email) ready. Downloading..." -ForegroundColor Green
                $custRoot = Join-Path $targetMount "$($cust.Email) hold"; $gmailP = Join-Path $custRoot "Gmail"; $driveP = Join-Path $custRoot "Drive"
                New-Item -Path $gmailP, $driveP -ItemType Directory -Force | Out-Null
                
                & gam download vaultexport "id:$($cState.GmailId)" matter "id:$($cust.Id)" targetfolder "$gmailP"
                & gam download vaultexport "id:$($cState.DriveId)" matter "id:$($cust.Id)" targetfolder "$driveP"
                
                & gam delete vaultexport matter "id:$($cust.Id)" "id:$($cState.GmailId)"
                & gam delete vaultexport matter "id:$($cust.Id)" "id:$($cState.DriveId)"
                $cState.Progress = "Completed"
            } else {
                Write-Host " $($cust.Email) - Gmail: $gStatus, Drive: $dStatus" -ForegroundColor Gray
                $PoolToKeep += $cust
            }
        } else {
            Write-Host " [!] ID Capture failed for $($cust.Email). Matter ID was likely returned instead of Export ID." -ForegroundColor Red
            $PoolToKeep += $cust
        }
        $automationState | ConvertTo-Json -Depth 10 | Out-File $stateFile -Force
    }
    $ActivePool = $PoolToKeep
    if ($ActivePool.Count -gt 0) { Start-Sleep -Seconds 300 }
}
Stop-Job $KeepAliveJob
