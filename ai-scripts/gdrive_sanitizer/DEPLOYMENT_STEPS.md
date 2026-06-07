# Repository Asset Manifest

This repository contains the official system architecture, recovery playbook, and production-ready sanitization engines for the **CELA Mass-Data Migration Campaign**.

To replicate this exact data-cleaning pipeline for a different Shared Drive or workspace migration, save the files below into your repository exactly as structured.

---

## 1. REPOSITORY README (`README.md`)

# CELA Mass-Data Migration: Google Drive to SharePoint Online Naming Sanitization Engine

## Overview
This repository houses the specialized system design, operational playbooks, and production-ready automation scripts used to facilitate the mass data migration of corporate legal discovery files from Google Workspace (GWS) Shared Drives to Microsoft 365 (M365) SharePoint Online.

During large-scale data liftoffs involving complex directory trees (130,000+ files), enterprise cloud-to-cloud migration engines frequently fail, omit files, or drop folder pathways due to strict path limits and character filtering rules enforced by Microsoft 365 storage planes. 

This toolkit provides a complete, automated pipeline to scan a Google Shared Drive, identify upcoming migration blockers, isolate structure-level properties from nested file-level properties, and execute atomic sanitization updates concurrently using **Standard GAM 7.x** on a **Windows 11 VM infrastructure**.

## Architectural Framework & Core Strategy
To ensure absolute legal defensibility and chain-of-custody transparency throughout the migration, this toolkit executes an **Isolated Metadata Sandbox Transformation**:
1. **Withheld Source Preservation:** The original operational data plane is never touched. The entire Shared Drive folder structure is duplicated into a dedicated cloud staging container.
2. **Metadata Matrix Compilation:** A master tracking table (`CELA_Migration_Rosetta_Stone.csv`) is generated to record the unique, immutable `GoogleObjectID` for every file and folder.
3. **Decoupled Variable Execution (`gam csv`):** Traditional string pass-through scripts (`gam batch`) break down when evaluating multi-line text arrays containing un-escaped double quotes, parentheses, spaces, or leading dashes. This engine permanently eliminates command-line token-parsing bugs by streaming row data straight from an autonomous CSV manifest directly into GAM parameter variables (`~GoogleObjectID` and `~SanitizedStagingName`).

## Technical Prerequisites
* **Operating System:** Windows 11 Desktop or Virtual Machine.
* **Consoles:** Windows Command Prompt (`cmd.exe`) and PowerShell 7+ (specifically optimized for version 7.6.2).
* **Binary Requirements:** Strictly **Standard GAM** (not GAMADV-XTD3), Version **7.40.00** or higher, pre-installed at `C:\GAM7\gam.exe` and mapped to the system environment `PATH`.

## Operational Deployment Sequence
1. **Extraction:** Execute the inventory capture process using PowerShell 7 to resolve UTF-16 stream carriage redirection corruption.
2. **Folder Campaign:** Run the Folder Manifest Compiler in PowerShell 7, then execute the renaming transaction using the `gam csv` grid processor in `cmd.exe`.
3. **File Campaign:** Run the File Manifest Compiler in PowerShell 7, then execute the file property cleaning transaction using the matching `gam csv` framework in `cmd.exe`.
4. **Hand-off:** Intersect the final ingestion success logs provided by the landing team with the generated Rosetta Stone sheet to append the permanent destination SharePoint URLs.

---

## 2. COMPILER 1: FOLDER STRUCTURE SANITIZER (`BuildFolderManifest.ps1`)

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

---

## 3. COMPILER 2: NESTED FILE ASSET SANITIZER (`BuildFileManifest.ps1`)

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

---

## 4. DEPLOYMENT STEP DOCUMENTATION (`DEPLOYMENT_STEPS.md`)

# Execution Guide: Shared Drive Namespace Sanitization Runbook

Follow these exact steps inside your Windows 11 VM environment to complete the sanitization pipeline.

### Step 1: Extract a Clean Local Inventory File
Run this command block inside your **PowerShell 7** prompt to capture the full raw metadata layer from Google Drive. This method pipes the output stream accurately to completely eliminate the null-byte character corruption associated with legacy Command Prompt redirects:

```powershell
cd C:\CELA_Migration
C:\GAM7\gam.exe user [ADMIN_EMAIL] print filelist select shareddriveid [TARGET_DRIVE_ID] showownedby any fields id,name,mimeType | Out-File -Encoding utf8 C:\CELA_Migration\staging_inventory_fixed.csv
