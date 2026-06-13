# Google Vault to Azure Blob Migration Pipeline

A three-script PowerShell pipeline that automates the export of Google Vault legal matter holds and streams them into an Azure Blob Storage container, with built-in staging cleanup and real-time visibility into upload progress.

## Overview

This toolkit was built to solve a recurring problem during legal hold migrations: exporting large volumes of Google Vault matter data, compressing it efficiently, and getting it into Azure storage without manually babysitting every step or running out of local disk space.

The pipeline runs as three cooperating processes:

| Script | Role | Run In |
|---|---|---|
| `VaultExportEngine.ps1` (the "Producer") | Triggers Vault exports via GAM, polls for completion, downloads results, compresses to ZIP, and cleans up the Vault export container | Window 1 (primary admin PowerShell) |
| `azCopyLoop.ps1` (the "Consumer") | Continuously watches the staging folder for finished ZIPs and uploads them to Azure via AzCopy, purging local copies after a successful transfer | Window 2 (background PowerShell) |
| `MountAzureDrive.ps1` (the "Monitor") | Mounts the Azure Blob container as a drive letter via rclone so you can visually confirm uploads landing in real time | Window 3 (standard user window, optional) |

Because the Producer and Consumer run independently, exports, compression, and uploads happen in parallel rather than as one long blocking sequence — once the first archive lands in the staging folder, the Consumer starts uploading it while the Producer moves on to the next user.

## Prerequisites

### Tools
- **GAM** (or GAMADV) — configured and authenticated with a service account that has Google Vault API access and the appropriate admin scopes for the matter you're exporting
- **7-Zip** — `7z.exe` available locally for compression
- **AzCopy** — Microsoft's command-line utility for high-throughput Azure transfers
- **rclone** — only required if you want the live mount/monitor view

### Access & Permissions
- Google Vault matter ID with export permissions for the target accounts
- Azure Storage container with a SAS URL that has **write** (and **list**, if mounting) permissions, scoped with an appropriate expiry
- Sufficient local disk space for at least one user's uncompressed export plus its compressed archive at any given time

### Input File
- A CSV file with a header row containing an `Email` column, listing every account whose Vault data should be exported

## Setup

1. Place all three scripts in a working directory accessible from your admin PowerShell session.
2. Edit the configuration block at the top of each script:

**VaultExportEngine.ps1**
- `$gamPath` — full path to your GAM executable
- `$workspaceDir` — local temp folder for in-progress exports
- `$zipOutDir` — staging folder where finished ZIPs wait for upload (shared with the AzCopy loop)
- `$sevenZipPath` — full path to `7z.exe`
- `$userListPath` — path to your migration CSV
- `$matterId` — your Google Vault matter ID

**azCopyLoop.ps1**
- `$azcopyPath` — full path to `azcopy.exe`
- `$zipOutDir` — must match the same path used above
- `$sasUrl` — your Azure container SAS URL

**MountAzureDrive.ps1**
- `$rcloneDir` — folder containing `rclone.exe`
- `$driveLetter` — unused drive letter to mount the container to
- `$sasUrl` — same Azure container SAS URL

3. Confirm `$zipOutDir` is the **same path** in both `VaultExportEngine.ps1` and `azCopyLoop.ps1` — this folder is the handoff point between the two scripts.

## Usage

1. **Start the Consumer first**, in its own PowerShell window:
   ```powershell
   .\azCopyLoop.ps1
   ```
   This runs an infinite loop, checking the staging folder every 5 minutes (or immediately processing anything already present).

2. **Start the Producer** in your main admin window:
   ```powershell
   .\VaultExportEngine.ps1
   ```
   This works through your CSV one account at a time: triggers the Vault export, polls every 60 seconds until it's ready, downloads it, compresses it, and deletes the remote export container.

3. **(Optional) Mount the Azure container** in a third window to watch files arrive:
   ```powershell
   .\MountAzureDrive.ps1
   ```
   Leave this window open; press `Ctrl+C` or close it to unmount.

4. Let the Producer run to completion. The Consumer loop will keep draining the staging folder as archives appear, and will continue running afterward — stop it manually (`Ctrl+C`) once all uploads are confirmed complete.

## Cautions & Considerations

- **Destructive cleanup by design**: Both the Producer and Consumer delete local data after a successful operation (raw export workspace and ZIP files, respectively). Do not run this against your only copy of anything — verify Azure upload integrity before relying on the automatic purge, especially on early runs.
- **Vault export deletion is irreversible via this script**: Step 5 of the Producer deletes the cloud export container immediately after a successful local download and compression. If the ZIP is later found to be corrupt, you cannot re-trigger that exact export — you'd need to create a new one from Vault.
- **SAS URL expiry**: Generate SAS URLs with enough lifetime to cover the full migration window. If a SAS token expires mid-run, AzCopy or rclone operations will fail silently into the `[CRITICAL]` branches — monitor console output.
- **7-Zip compression level**: The script uses `-mx=1` (fastest/lowest compression) to prioritize pipeline throughput over storage savings. Adjust if bandwidth, not CPU/disk I/O, is your bottleneck.
- **No retry limit on Vault polling**: The export polling loop will run indefinitely until Vault reports `completed` or `failed`. A matter stuck in an unexpected state could loop forever — keep an eye on long-running exports.
- **Failed uploads are preserved, not retried automatically**: If AzCopy fails for a given ZIP, the file stays in the staging folder and will be retried on the *next* 5-minute pass, but there's no backoff or alerting — check console output for `[CRITICAL]` entries.
- **Credentials in plaintext**: SAS URLs and paths are stored as plaintext variables in the scripts. Treat these files as sensitive once populated, and avoid committing populated versions to source control.
- **Run order matters**: Starting the Producer before the Consumer is harmless (ZIPs will simply queue), but starting the Consumer first ensures no archive sits idle for up to 5 minutes before its first upload attempt.

## Architecture Notes

This design intentionally decouples export/compression from upload using a filesystem-based queue (the staging directory). This means:

- The Producer never blocks on network upload speed
- The Consumer never blocks on Vault API latency
- Either script can be restarted independently without losing progress, as long as the staging folder is preserved
