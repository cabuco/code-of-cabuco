# =======================================================================
#               FOLDER MANIFEST COMPILER
# =======================================================================
# Purpose: Build a rename manifest for folder objects that require
# namespace sanitization before Microsoft 365 / SharePoint migration.
# =======================================================================

$CsvPath = Join-Path $PSScriptRoot "staging_inventory_fixed.csv"
$OutputPath = Join-Path $PSScriptRoot "gam_staging_folder_manifest.csv"

Write-Host "[+] Initializing folder manifest build..." -ForegroundColor Cyan

if (-not (Test-Path $CsvPath)) {
    Write-Host "[-] ERROR: Inventory file not found: $CsvPath" -ForegroundColor Red
    Write-Host "[!] Run the inventory export step first." -ForegroundColor Yellow
    return
}

$InventoryData = Import-Csv -Path $CsvPath
$ManifestRows = @()
$Count = 0

$Blockers = '[:\/\\\*\?"<>\|]'

foreach ($Row in $InventoryData) {
    if ($Row.mimeType -eq "application/vnd.google-apps.folder") {
        $OriginalName = $Row.name
        $FolderId = $Row.id

        if (-not $OriginalName -or -not $FolderId) { continue }

        $CleanName = $OriginalName.Trim()
        $CleanName = $CleanName -replace $Blockers, '-'
        $CleanName = $CleanName -replace '-+', '-'
        $CleanName = $CleanName.Trim('-').Trim()

        if ($OriginalName -ne $CleanName -and $CleanName -ne "") {
            $Count++
            $ManifestRows += [PSCustomObject]@{
                GoogleObjectID       = $FolderId
                OriginalProdName     = $OriginalName
                SanitizedStagingName = $CleanName
                ObjectType           = "Folder"
            }
        }
    }
}

$ManifestRows | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding ascii

Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "             FOLDER MANIFEST GENERATION COMPLETE                       " -ForegroundColor Green
Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Queued $Count folder rename entries." -ForegroundColor Yellow
Write-Host "[SUCCESS] Manifest written to: $OutputPath" -ForegroundColor Cyan
Write-Host "[ACTION] Review the CSV, then run the folder rename step." -ForegroundColor White
