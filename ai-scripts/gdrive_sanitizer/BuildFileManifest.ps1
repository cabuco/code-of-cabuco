# =======================================================================
#               FILE MANIFEST COMPILER
# =======================================================================
# Purpose: Build a rename manifest for non-folder objects that require
# namespace sanitization before Microsoft 365 / SharePoint migration.
# =======================================================================

$CsvPath = Join-Path $PSScriptRoot "staging_inventory_fixed.csv"
$OutputPath = Join-Path $PSScriptRoot "gam_staging_file_manifest.csv"

Write-Host "[+] Initializing file manifest build..." -ForegroundColor Cyan

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
    if ($Row.mimeType -ne "application/vnd.google-apps.folder") {
        $OriginalName = $Row.name
        $FileId = $Row.id

        if (-not $OriginalName -or -not $FileId) { continue }

        $CleanName = $OriginalName.Trim()
        $CleanName = $CleanName -replace $Blockers, '-'
        $CleanName = $CleanName -replace '-+', '-'
        $CleanName = $CleanName.Trim('-').Trim()

        if ($OriginalName -ne $CleanName -and $CleanName -ne "") {
            $Count++
            $ManifestRows += [PSCustomObject]@{
                GoogleObjectID       = $FileId
                OriginalProdName     = $OriginalName
                SanitizedStagingName = $CleanName
                ObjectType           = "File"
            }
        }
    }
}

$ManifestRows | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding ascii

Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "             FILE MANIFEST GENERATION COMPLETE                         " -ForegroundColor Green
Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Queued $Count file rename entries." -ForegroundColor Yellow
Write-Host "[SUCCESS] Manifest written to: $OutputPath" -ForegroundColor Cyan
Write-Host "[ACTION] Review the CSV, then run the file rename step." -ForegroundColor White
