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
             📂 <your_temp_workspace_folder>
                         │
                         │ (7-Zip Inline High Compression)
                         ▼
             📦 <your_staging_zip_out_folder>
                         │
                         │ (Window 2: High-Speed Engine Sweep Loop)
                         ▼
               [ AZURE BLOB STORAGE ]   (Native Cloud Warehouse)
                         │
                         └─► [Purge Local Zip File] (Automated Drive Insulation)

1. The Producer (Window 1): A master automation script coordinates account exports from Google Vault, downloads raw items sequentially, compresses them locally using multi-threaded 7-Zip binaries into structured .zip target packages inside a waiting folder, and instantly drops the uncompressed staging directory to reclaim local disk space.
2. The Consumer (Window 2): An autonomous background loop mirrors completed archive containers, calling Microsoft's native binary copy engine to blast the data to Azure at maximum pipe capability and instantly deleting the local .zip file upon cloud verification.

---

## Prerequisites & Environmental Requirements

Before launching execution frameworks, the migration host node must be configured with the following binaries and access structures:

### 1. Local Staging Folder Architecture
Ensure your migration workstation node has a fast local scratch disk (SSD preferred) with adequate working headroom. Establish the following structure:
* <your_temp_workspace_folder> - Root workspace
* <your_staging_zip_out_folder> - Inter-process exchange staging directory
* <your_rclone_binary_directory> - Binaries and tracking registry root

### 2. Required Execution Binaries
* AzCopy Engine: Download the stand-alone executable from Microsoft and install/extract it into your system's executable path or utility folder.
* RClone Engine (Optional Verification Mount): Extract the standalone rclone engine utility to your local binaries directory.

### 3. Authentication Tokens & Endpoint Security
* Google Cloud Identity Console: Ensure your running profile holds API delegation authority over the target Google Vault retention categories.
* Azure SAS Token URL: Acquire an active Shared Access Signature (SAS) token URL routing into your destination Azure Blob Storage container with explicit Read/Write/Create/Delete permissions.

---

## Execution Guide & Workflows

### Step 1: Initialize the Master Download Engine (Window 1)
Launch your primary Administrator PowerShell terminal context. Execute your master collection framework script targeting your global user query matrix. This window handles account acquisition, data downloading, and compression.

### Step 2: Launch the Intelligent Upload Loop (Window 2)
Open a separate, independent PowerShell window. Run the optimized background upload script loop (`AzCopyLoop.ps1`) to handle automated staging clearance.

---

## Real-Time Monitoring & Verification Frameworks

### Checking Drive Volumetrics
Because the Consumer engine clears the waiting room every 5 minutes on a per-file confirmation basis, the staging directory should remain low in total file counts. If this directory builds more than 50 items, it indicates that your local download/compression array outpaces your external network internet upload bandwidth capability.

### Instant Explorer Cloud Mount Verification (RClone Mount Workflow)
If you want to verify your data architecture live within a graphical environment, you can map the remote Azure Cloud container directly to your Windows File Explorer as a virtual network adapter drive letter. 

Open a standard user PowerShell prompt and execute the following unified command line:

cd "<path_to_your_rclone_folder>"; .\rclone.exe mount :azureblob: <desired_drive_letter>: --azureblob-sas-url "<your_azure_container_sas_url>" --vfs-cache-mode writes --network-mode

Note: Keep that terminal window open. Minimize it, and navigate to "This PC" in Windows File Explorer. You will see a functional, browseable drive letter connected straight to your cloud container.

---

## Engineering & Operational Safeguards

* Self-Healing File Locks: If Window 2 sweeps a file while Window 1 is actively building it, the file write-lock generated by Windows will trip a safe skip. AzCopy will bypass the partial file without breaking error thresholds, successfully capturing it on the next 5-minute loop once completed.
* Network Interruption Resiliency: If internet routing drops or the Azure Endpoint forces throttling controls, AzCopy terminates with a non-zero exit code. The script catches this state, leaves the local file entirely safe on local storage, logs a red warning notice, and attempts the deployment again on the subsequent pass.
* Insulated Staging Storage: Local file systems are protected against memory leak exhaustion by verifying exit codes completely before calling the destructive Remove-Item file purge routine.

---
