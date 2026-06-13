# Google Vault to Azure Blob Automated Migration Engine

A robust, production-tested, asynchronous pipeline designed to migrate massive, multi-terabyte legal compliance archives from Google Vault directly into Azure Blob Storage at enterprise scale. 

This engine solves critical enterprise architecture constraints by splitting the migration into an asynchronous Producer-Consumer pipeline. This isolates heavy API downloading and local disk compression from high-speed network uploads, optimizing local drive usage and maximizing cloud bandwidth saturation.

---

## Core Architecture Pipeline

The migration is handled across two independent, simultaneous execution frames:

               [ GOOGLE VAULT CLOUD ]
                         │
                         │ (Window 1: Multi-Threaded Staged Download)
                         ▼
             📂 C:\VaultTemp\Workspace  (Transient Processing Folder)
                         │
                         │ (7-Zip Inline High Compression)
                         ▼
             📦 C:\VaultTemp\ZipOut\    (Staging Waiting Room)
                         │
                         │ (Window 2: High-Speed Engine Sweep Loop)
                         ▼
               [ AZURE BLOB STORAGE ]   (Native Cloud Warehouse)
                         │
                         └─► [Purge Local Zip File] (Automated Drive Insulation)

1. The Producer (Window 1): A master automation script coordinates account exports from Google Vault, downloads raw items sequentially, compresses them locally using multi-threaded 7-Zip binaries into structured .zip target packages inside a waiting folder, and instantly drops the uncompressed staging directory to reclaim local disk space.
2. The Consumer (Window 2): An autonomous background loop mirrors completed archive containers, calling Microsoft's native binary copy engine to blast the data to Azure at maximum pipe capability and instantly deleting the local .zip file upon cloud verification.

---

## 🛠️ Prerequisites & Environmental Requirements

Before launching execution frameworks, the migration host node must be configured with the following binaries and access structures:

### 1. Local Staging Folder Architecture
Ensure your migration workstation node has a fast local scratch disk (SSD preferred) with at least 300GB–500GB of working headroom. Establish the following structure:
* C:\VaultTemp\ - Root workspace
* C:\VaultTemp\ZipOut\ - Inter-process exchange staging directory
* C:\rclone\ - Binaries and tracking registry root

### 2. Required Execution Binaries
* AzCopy Engine: Download the stand-alone executable from Microsoft and install/extract it into C:\Program Files\AzCopy\azcopy.exe.
* RClone Engine (Optional Verification Mount): Extract the standalone rclone engine utility to C:\rclone\rclone.exe.

### 3. Authentication Tokens & Endpoint Security
* Google Cloud Identity Console: Ensure your running profile holds API delegation authority over the target Google Vault retention categories.
* Azure SAS Token URL: Acquire an active Shared Access Signature (SAS) token URL routing into your destination Azure Blob Storage container with explicit Read/Write/Create/Delete permissions.

---

## ⚖️ Execution Guide & Workflows

### Step 1: Initialize the Master Download Engine (Window 1)
Launch your primary Administrator PowerShell terminal context. Execute your master collection framework script targeting your global user query matrix. This window handles account acquisition, data downloading, and compression.

### Step 2: Launch the Intelligent Upload Loop (Window 2)
Open a separate, independent PowerShell window. Paste the following optimized background consumer script block. 

*Sanitization Note: Update the $sasUrl variable inside the script with your real target Azure container endpoint link.*

--------------------------------------------------------------------------------
# POWERSHELL CONSUMER SCRIPT CORE (PASTE INTO WINDOW 2)
--------------------------------------------------------------------------------
# Explicit Configuration Framework
$azcopyPath = "C:\Program Files\AzCopy\azcopy.exe"
$zipOutDir  = "C:\VaultTemp\ZipOut"

# Paste your real Azure Container SAS URL connection string below
$sasUrl     = "https://<your_storage_account>.blob.core.windows.net/<your_container>?<your_sas_token_parameters>"

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ENGINE INITIALIZED: Autonomous Cloud Synchronization Architecture" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green

while($true) {
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Scanning Exchange Waiting Room for finalized archives..." -ForegroundColor Cyan
    
    # Identify completed file containers resting on local storage
    $zipFiles = Get-ChildItem -Path $zipOutDir -Filter "*.zip"
    
    if ($zipFiles.Count -eq 0) {
        Write-Host " [Staging Status] Exchange directory clear. Sleeping for 5 minutes..." -ForegroundColor Gray
    } else {
        Write-Host " [Staging Status] Identified $($zipFiles.Count) package(s) ready for cloud deployment." -ForegroundColor Yellow
        
        foreach ($file in $zipFiles) {
            # Extract core target entity out of string profile
            $entityIdentity = $file.Name -replace "_Hold\.zip$", ""
            
            Write-Host "`n >>> Deploying Archive Package: $entityIdentity <<<" -ForegroundColor White -BackgroundColor DarkGreen
            
            # Execute Native high-speed copy stream operation 
            & $azcopyPath copy $file.FullName $sasUrl --recursive
            
            # Reclaim local workspace storage assets upon verified transfer success
            if ($LASTEXITCODE -eq 0) {
                Write-Host " [SUCCESS] Cloud target committed successfully for $entityIdentity." -ForegroundColor Green
                
                # Immediate local disk sanitation lock
                Remove-Item $file.FullName -Force
                Write-Host " [INSULATION] Staging file safely purged from local drive array: $($file.Name)" -ForegroundColor Magenta
            } else {
                Write-Host " [CRITICAL] AzCopy execution faulted for $entityIdentity. Preserving file for re-evaluation pass." -ForegroundColor Red
            }
        }
    }
    
    Start-Sleep -Seconds 300
}
--------------------------------------------------------------------------------

---

## Real-Time Monitoring & Verification Frameworks

### Checking Drive Volumetrics
Because the Consumer engine clears the waiting room every 5 minutes on a per-file confirmation basis, C:\VaultTemp\ZipOut should remain low in total file counts. If this directory builds more than 50 items, it indicates that your local download/compression array outpaces your external network internet upload bandwidth capability.

### Instant Explorer Cloud Mount Verification (RClone Mount Workflow)
If you need to verify your data architecture live within a GUI environment, you can map the Azure Cloud container directly to your Windows File Explorer as a virtual network adapter drive letter.

Open a regular PowerShell terminal session (non-administrative session preferred to expose the mapping globally across your standard user profile) and execute the following rclone mount directive:

cd C:\rclone
.\rclone.exe mount :azureblob: z: --azureblob-sas-url "https://<your_storage_account>.blob.core.windows.net/<your_container>?<your_sas_token_parameters>" --vfs-cache-mode writes --network-mode

*Note: Keep that terminal window open. Minimize it, and navigate to This PC in Windows File Explorer. You will see a functional Z: drive connected straight to your Azure container.*

---

## Engineering & Operational Safeguards

* Self-Healing File Locks: If Window 2 sweeps a file while Window 1 is actively building it, the file write-lock generated by Windows will trip a safe skip. AzCopy will bypass the partial file without breaking error thresholds, successfully capturing it on the next 5-minute loop once completed.
* Network Interruption Resiliency: If internet routing drops or the Azure Endpoint forces throttling controls, AzCopy terminates with a non-zero exit code. The script catches this state, leaves the local file entirely safe on local storage, logs a red warning notice, and attempts the deployment again on the subsequent pass.
* Insulated Staging Storage: Local file systems are protected against memory leak exhaustion by verifying exit codes completely before calling the destructive Remove-Item file purge routine.

---
