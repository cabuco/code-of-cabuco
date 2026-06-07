# CELA Mass-Data Migration: Google Drive to SharePoint Online Naming Sanitization Engine

## Overview
This repository houses the specialized system design, operational playbooks, and production-ready automation scripts used to facilitate the mass data migration of corporate legal discovery files from Google Workspace (GWS) Shared Drives to Microsoft 365 (M365) SharePoint Online.

During large-scale data liftoffs involving complex directory trees (130,000+ files), enterprise cloud-to-cloud migration engines frequently fail, omit files, or drop folder pathways due to strict path limits and character filtering rules enforced by Microsoft 365 storage planes. 

This toolkit provides a complete, automated pipeline to scan a Google Shared Drive, identify upcoming migration blockers, isolate structure-level properties from nested file-level properties, and execute atomic sanitization updates concurrently using **Standard GAM 7.x** on a **Windows 11 VM infrastructure**.

## Architectural Framework & Core Strategy
To ensure absolute legal defensibility and chain-of-custody transparency throughout the migration, this toolkit executes an **Isolated Metadata Sandbox Transformation**:
1. **frozen Source Preservation:** The original operational data plane is never touched. The entire Shared Drive folder structure is duplicated into a dedicated cloud staging container.
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
