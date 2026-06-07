# =======================================================================
#               CELA MIGRATION - FOLDER MANIFEST COMPILER      
# =======================================================================
# Target Workspace: Staging Sandbox Container Only
# Operating System: Windows 11 VM Environment
# Automation Engine: PowerShell 7+ (Native Data Handling Plane)
# Core Binary Target: Standard GAM 7.40.00 Data Grid Specifications
# =======================================================================

$CsvPath = "C:\CELA_Migration\staging_inventory_fixed.csv"
$OutputPath = "C:\CELA_Migration\gam_staging_folder_manifest.csv"

Write-Host "[+] Initializing directory tree scanning pass for folder structures..." -ForegroundColor Cyan

if (-not (Test-Path $CsvPath)) {
    Write-Host "[-] CRITICAL ERROR: Reference inventory file missing at: $CsvPath" -ForegroundColor Red
    Write-Host "[!] Please ensure Step 1 Inventory extraction has been performed successfully." -ForegroundColor Yellow
    return
}

# Safely extract data plane rows from the uncorrupted master inventory log
$InventoryData = Import-Csv -Path $CsvPath
$ManifestRows = @()
$Count = 0

# Track and isolate M365 SharePoint Online prohibited character arrays
$Blockers = '[:\/\\\*\?\"<>\|]'

foreach ($Row in $InventoryData) {
    # Isolate folder structures explicitly to rebuild directory hierarchies first
    if ($Row.mimeType -eq "application/vnd.google-apps.folder") {
        $OriginalName = $Row.name
        $FolderId = $Row.id
        
        if (-not $OriginalName -or -not $FolderId) { continue }
        
        # Enforce strict character replacement rules
        $CleanName = $OriginalName.Trim()
        $CleanName = $CleanName -replace $Blockers, '-'
        $CleanName = $CleanName -replace '-+', '-'
        $CleanName = $CleanName.Trim('-').Trim()
        
        # If the target directory name requires modification for M365 compliance, queue it
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

# Export directly to a flat, comma-separated data matrix utilizing standard ASCII rules
$ManifestRows | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding ascii

Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "             FOLDER DATA MATRIX GENERATION COMPLETE                    " -ForegroundColor Green
Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Mapped $Count custom folder mutations into the staging data plane." -ForegroundColor Yellow
Write-Host "[SUCCESS] Folder update manifest securely written to: $OutputPath" -ForegroundColor Cyan
Write-Host "[ACTION] You are now clear to launch Step 3 CMD Renaming Pass." -ForegroundColor White
