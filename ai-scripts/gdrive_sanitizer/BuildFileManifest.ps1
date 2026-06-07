# =======================================================================
#               CELA MIGRATION - FILE MANIFEST COMPILER      
# =======================================================================
# Target Workspace: Staging Sandbox Container Only
# Operating System: Windows 11 VM Environment
# Automation Engine: PowerShell 7+ (Native Data Handling Plane)
# Core Binary Target: Standard GAM 7.40.00 Data Grid Specifications
# =======================================================================

$CsvPath = "C:\CELA_Migration\staging_inventory_fixed.csv"
$OutputPath = "C:\CELA_Migration\gam_staging_file_manifest.csv"

Write-Host "[+] Initializing child directory scanning pass for individual file assets..." -ForegroundColor Cyan

if (-not (Test-Path $CsvPath)) {
    Write-Host "[-] CRITICAL ERROR: Reference inventory file missing at: $CsvPath" -ForegroundColor Red
    return
}

# Safely extract data plane rows from the uncorrupted master inventory log
$InventoryData = Import-Csv -Path $CsvPath
$ManifestRows = @()
$Count = 0

# Track and isolate M365 SharePoint Online prohibited character arrays
$Blockers = '[:\/\\\*\?\"<>\|]'

foreach ($Row in $InventoryData) {
    # Exclude folder mimeTypes to evaluate nested file objects explicitly
    if ($Row.mimeType -ne "application/vnd.google-apps.folder") {
        $OriginalName = $Row.name
        $FileId = $Row.id
        
        if (-not $OriginalName -or -not $FileId) { continue }
        
        # Enforce strict character replacement and trim trailing whitespaces before extensions
        $CleanName = $OriginalName.Trim()
        $CleanName = $CleanName -replace $Blockers, '-'
        $CleanName = $CleanName -replace '-+', '-'
        $CleanName = $CleanName.Trim('-').Trim()
        
        # If the file object requires modification to clear M365 ingestion errors, queue it
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

# Export directly to a flat, comma-separated data matrix utilizing standard ASCII rules
$ManifestRows | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding ascii

Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "             FILE DATA MATRIX GENERATION COMPLETE                      " -ForegroundColor Green
Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Mapped $Count file-level mutations into the staging data plane." -ForegroundColor Yellow
Write-Host "[SUCCESS] File update manifest securely written to: $OutputPath" -ForegroundColor Cyan
Write-Host "[ACTION] You are now clear to launch Step 5 CMD Renaming Pass." -ForegroundColor White
