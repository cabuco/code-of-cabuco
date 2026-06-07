# CELA Mass-Data Migration Architecture & Sanitization Toolkit

This document serves as the master engineering ledger, code repository, and step-by-step deployment runbook for a mass-data migration campaign. It contains the documentation and script dependencies required to execute an automated namespace sanitization campaign on a macOS host using Standard GAM 7.x.

## Overview

This toolkit is designed to support the mass migration of corporate legal discovery files from Google Workspace Shared Drives to Microsoft 365 SharePoint Online.

In large migrations involving deep directory trees and high file counts, migration platforms can fail or skip content because of Microsoft 365 path limits and invalid-character restrictions. This toolkit provides an automated pipeline to:

- scan a Google Shared Drive
- identify migration blockers
- separate folder-level and file-level sanitization work
- generate CSV manifests for controlled bulk updates
- execute renaming actions with Standard GAM 7.x on macOS

## Core Strategy

To preserve source integrity and maintain traceability, the workflow uses an isolated staging approach:

1. **Preserve the source**  
   Do not modify the original production data directly. Duplicate the Shared Drive structure into a staging container first.

2. **Generate a tracking matrix**  
   Build a master inventory that records the immutable Google object ID for every file and folder.

3. **Use CSV-driven GAM execution**  
   Instead of relying on string-heavy batch commands, stream manifest values directly into `gam csv` variables such as `~GoogleObjectID` and `~SanitizedStagingName`.

## Technical Prerequisites

- **Operating System:** macOS or compatible arm64 macOS environment
- **Shell:** `zsh`
- **Python:** Python 3
- **GAM Requirement:** Standard GAM 7.32.03 or later
- **Expected GAM Path:** `[PATH_TO_GAM_BINARY]`
- **PATH Requirement:** `gam` should already be available in your shell `PATH`

## Repository Layout

This single document contains:

1. README-style project documentation
2. Folder manifest compiler script
3. File manifest compiler script
4. Deployment and execution runbook

---

## Folder Manifest Compiler (`BuildFolderManifest.py`)

```python
#!/usr/bin/env python3
# =======================================================================
#               MASS MIGRATION - FOLDER MANIFEST COMPILER
# =======================================================================
# Target Workspace: Staging Sandbox Container Only
# Operating System: macOS Environment (zsh)
# Automation Engine: Python 3 (Native Data Handling Plane)
# Core Binary Target: Standard GAM 7.32.03 Data Grid Specifications
# =======================================================================

import os
import csv
import re
import sys

csv_path = "./staging_inventory_fixed.csv"
output_path = "./gam_staging_folder_manifest.csv"

print("[+] Initializing directory tree scanning pass for folder structures...")

if not os.path.exists(csv_path):
    print(f"[-] CRITICAL ERROR: Reference inventory file missing at: {csv_path}")
    print("[!] Please ensure Step 1 inventory extraction has been performed successfully.")
    sys.exit(1)

# Compile M365 SharePoint Online prohibited character arrays
blockers_regex = re.compile(r'[:\\/\*\?"<>\|]')
consecutive_hyphens_regex = re.compile(r'-+')

manifest_rows = []
count = 0

with open(csv_path, mode='r', encoding='utf-8-sig') as infile:
    reader = csv.DictReader(infile)

    # Ensure correct column schemas exist
    if not {'id', 'name', 'mimeType'}.issubset(reader.fieldnames):
        print("[-] CRITICAL ERROR: Input CSV column headers must contain 'id', 'name', and 'mimeType'.")
        sys.exit(1)

    for row in reader:
        # Isolate folder structures explicitly to rebuild directory hierarchies first
        if row['mimeType'] == 'application/vnd.google-apps.folder':
            original_name = row['name']
            folder_id = row['id']

            if not original_name or not folder_id:
                continue

            # Enforce strict character replacement rules
            clean_name = original_name.strip()
            clean_name = blockers_regex.sub('-', clean_name)
            clean_name = consecutive_hyphens_regex.sub('-', clean_name)
            clean_name = clean_name.strip('-').strip()

            # If the target directory name requires modification for M365 compliance, queue it
            if original_name != clean_name and clean_name != "":
                count += 1
                manifest_rows.append({
                    'GoogleObjectID': folder_id,
                    'OriginalProdName': original_name,
                    'SanitizedStagingName': clean_name,
                    'ObjectType': 'Folder'
                })

# Export directly to a flat, comma-separated data matrix utilizing standard rules
fieldnames = ['GoogleObjectID', 'OriginalProdName', 'SanitizedStagingName', 'ObjectType']
with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(manifest_rows)

print("=======================================================================")
print("             FOLDER DATA MATRIX GENERATION COMPLETE                    ")
print("=======================================================================")
print(f"[SUCCESS] Mapped {count} custom folder mutations into the staging data plane.")
print(f"[SUCCESS] Folder update manifest securely written to: {output_path}")
print("[ACTION] You are now clear to launch Step 3 zsh renaming pass.")
```

---

## File Manifest Compiler (`BuildFileManifest.py`)

```python
#!/usr/bin/env python3
# =======================================================================
#               MASS MIGRATION - FILE MANIFEST COMPILER
# =======================================================================
# Target Workspace: Staging Sandbox Container Only
# Operating System: macOS Environment (zsh)
# Automation Engine: Python 3 (Native Data Handling Plane)
# Core Binary Target: Standard GAM 7.32.03 Data Grid Specifications
# =======================================================================

import os
import csv
import re
import sys

csv_path = "./staging_inventory_fixed.csv"
output_path = "./gam_staging_file_manifest.csv"

print("[+] Initializing child directory scanning pass for individual file assets...")

if not os.path.exists(csv_path):
    print(f"[-] CRITICAL ERROR: Reference inventory file missing at: {csv_path}")
    sys.exit(1)

# Compile M365 SharePoint Online prohibited character arrays
blockers_regex = re.compile(r'[:\\/\*\?"<>\|]')
consecutive_hyphens_regex = re.compile(r'-+')

manifest_rows = []
count = 0

with open(csv_path, mode='r', encoding='utf-8-sig') as infile:
    reader = csv.DictReader(infile)

    if not {'id', 'name', 'mimeType'}.issubset(reader.fieldnames):
        print("[-] CRITICAL ERROR: Input CSV column headers must contain 'id', 'name', and 'mimeType'.")
        sys.exit(1)

    for row in reader:
        # Exclude folder mimeTypes to evaluate nested file objects explicitly
        if row['mimeType'] != 'application/vnd.google-apps.folder':
            original_name = row['name']
            file_id = row['id']

            if not original_name or not file_id:
                continue

            # Enforce strict character replacement and trim whitespace
            clean_name = original_name.strip()
            clean_name = blockers_regex.sub('-', clean_name)
            clean_name = consecutive_hyphens_regex.sub('-', clean_name)
            clean_name = clean_name.strip('-').strip()

            # If the file object requires modification to clear M365 ingestion errors, queue it
            if original_name != clean_name and clean_name != "":
                count += 1
                manifest_rows.append({
                    'GoogleObjectID': file_id,
                    'OriginalProdName': original_name,
                    'SanitizedStagingName': clean_name,
                    'ObjectType': 'File'
                })

# Export directly to a flat, comma-separated data matrix utilizing standard rules
fieldnames = ['GoogleObjectID', 'OriginalProdName', 'SanitizedStagingName', 'ObjectType']
with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(manifest_rows)

print("=======================================================================")
print("             FILE DATA MATRIX GENERATION COMPLETE                      ")
print("=======================================================================")
print(f"[SUCCESS] Mapped {count} file-level mutations into the staging data plane.")
print(f"[SUCCESS] File update manifest securely written to: {output_path}")
print("[ACTION] You are now clear to launch Step 5 zsh renaming pass.")
```

---

## Deployment Steps

Follow these steps in a macOS `zsh` terminal.

### Step 1: Extract a Clean Local Inventory File

Capture the raw metadata inventory from the Shared Drive:

```bash
cd ./[WORKING_DIRECTORY]
gam user "[ADMIN_EMAIL]" print filelist select shareddriveid "[TARGET_DRIVE_ID]" showownedby any fields id,name,mimeType > ./staging_inventory_fixed.csv
```

### Step 2: Build the Folder Renaming Manifest

Generate a CSV manifest for folder renames:

```bash
python3 ./BuildFolderManifest.py
```

### Step 3: Execute the Folder Renaming Campaign

Apply folder name updates in bulk using `gam csv`:

```bash
gam csv ./gam_staging_folder_manifest.csv gam user "[ADMIN_EMAIL]" update drivefile "~GoogleObjectID" newfilename "~SanitizedStagingName"
```

### Step 4: Build the File Renaming Manifest

Generate a CSV manifest for file renames:

```bash
python3 ./BuildFileManifest.py
```

### Step 5: Execute the File Renaming Campaign

Apply file name updates in bulk using `gam csv`:

```bash
gam csv ./gam_staging_file_manifest.csv gam user "[ADMIN_EMAIL]" update drivefile "~GoogleObjectID" newfilename "~SanitizedStagingName"
```

---

## Notes

- Run all renaming activity only against the staging sandbox, not the production source.
- The workflow assumes `staging_inventory_fixed.csv` is generated first and remains in the working directory.
- Folder renames should be executed before file renames.
- The generated manifests act as an auditable record of proposed naming changes.

## Suggested Output Files

- `staging_inventory_fixed.csv`
- `gam_staging_folder_manifest.csv`
- `gam_staging_file_manifest.csv`

## Sanitization Review

The content in this README has been normalized to use generic placeholders for potentially identifying values, including:

- administrator email addresses
- target Shared Drive IDs
- working directory names
- local GAM binary paths
- environment-specific naming

Replace placeholders such as `[ADMIN_EMAIL]`, `[TARGET_DRIVE_ID]`, `[WORKING_DIRECTORY]`, and `[PATH_TO_GAM_BINARY]` with your environment-specific values at execution time.
