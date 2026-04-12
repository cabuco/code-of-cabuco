# VaultExportToAzure.ps1 — Google Vault Systematic Export (Direct-to-Mount Archive)

This PowerShell script automates **Google Vault exports** for a set of **OPEN Vault Matters** whose names match a specific **litigation hold naming convention**, then **polls export status**, **downloads completed exports to a local mount path**, and **deletes the exports from Vault** once downloaded.

It is designed to be resumable (via a JSON state file) and to run multiple custodians concurrently (with throttling).

---

## What it does (high-level)

For each Vault Matter that matches the script’s `matterRegex`:

1. Creates **two** Vault exports per custodian:
   - **Gmail** corpus export (`mail`)
   - **Drive** corpus export (`drive`)
2. “Discovers” the export IDs by listing exports in the matter (robust against create output not returning IDs reliably).
3. Polls export status for both Gmail and Drive until both are `COMPLETED`.
4. Downloads both exports into a folder structure on a local mount:
   - `X:\201bce56\<email> hold\Gmail\...`
   - `X:\201bce56\<email> hold\Drive\...`
5. Deletes the exports in Google Vault after successful download.
6. Writes progress into `vault_automation_state.json` so it can resume.

---

## Requirements / prerequisites

### 1) Windows + PowerShell
- Windows host with PowerShell (Windows PowerShell 5.1 or PowerShell 7 should work).
- Ability to run scripts (execution policy permitting).

### 2) GAM installed and authenticated
This script uses **GAM** (Google Apps Manager) via the `gam` command.

You must have:
- `gam` available in your PATH (or modify the script to call it by full path).
- GAM configured/authenticated to a Google Workspace environment with permissions to:
  - List matters
  - Create exports
  - View export status
  - Download exports
  - Delete exports

> Note: Exact GAM setup varies by environment. Confirm that your GAM instance can run the commands used below.

### 3) Google Vault permissions
The account used by GAM must have appropriate Vault privileges (e.g., Vault admin / eDiscovery permissions) to:
- Access matters
- Create and manage exports for custodians/accounts

### 4) Local destination mount exists (or can be created)
The script writes to:

- `$targetMount = "X:\201bce56"`

The script will create the folder if it does not exist, but:
- The **drive letter/path must be valid**
- The user must have permission to write there
- Ensure there is enough free disk space for exports

If you are archiving “direct-to-cloud” (e.g., Azure Files / SMB mount), ensure the mount is connected before running.

---

## Naming convention / how it chooses custodians

The script only processes matters whose `name` matches:

```powershell
$matterRegex = '(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)'
```

That means matter names like:

- `@jane.doe lit hold`
- `@john lit-hold`
- `@custodian123 litigation hold`

From the match:
- `user` becomes the local-part of the custodian email (e.g., `jane.doe`)
- The email becomes: `<user>@<domain>`

The domain is currently hard-coded:

```powershell
$domain = "github.com"
```

### IMPORTANT: Set your real Workspace domain
Before running in a real Vault environment, change:

- `$domain = "your-company.com"`

Otherwise it will construct custodians like `user@github.com`.

---

## Concurrency / pacing

The script runs multiple custodians at once:

```powershell
$MaxConcurrentCustodians = 5
```

This controls how many custodians it will actively poll/download in parallel.

It also includes sleeps between operations to reduce rate limiting:
- 5s after create export (before listing exports)
- 10s between creating Gmail and Drive exports
- 300s (5 minutes) between status polls when still active

---

## Files created by the script

### 1) State file
A JSON state file is written next to the script:

- `vault_automation_state.json`

This is used to **resume** if the script stops mid-run. It records, per custodian email:
- MatterId
- Progress (`Exporting` / `Completed`)
- Gmail export ID
- Drive export ID
- (plus a `LinkedIds` field reserved for future use)

If the script is re-run and it sees `Progress = "Completed"` for an email, it will skip that custodian.

### 2) Download output folders
For each custodian (email), the script creates:

- `X:\201bce56\<email> hold\Gmail\`
- `X:\201bce56\<email> hold\Drive\`

And downloads the Vault export contents into those folders.

---

## How to run

1. Install/configure GAM and verify you can run it from a terminal:
   - `gam version`
2. Edit the script variables at the top as needed:
   - `$targetMount`
   - `$domain`
   - `$MaxConcurrentCustodians`
3. Open PowerShell **as a user with write access** to the target mount.
4. Run the script from its directory, for example:

```powershell
cd .\ai-scripts\bulk-gvault-export-v2\
.\VaultExportToAzure.ps1
```

If PowerShell blocks it due to execution policy, you can (depending on your org policy) run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\VaultExportToAzure.ps1
```

---

## Understanding console output / statuses

The script prints operational messages with prefixes. Key ones:

### Startup
- ` [1/6] Heartbeat enabled.`
  - Starts a background job that sends an “unused key” (`F15`) every 240 seconds to prevent the session from sleeping/locking.

- ` [OK] Resuming session.`
  - Found `vault_automation_state.json` and loaded it.

### Queueing / export creation
- ` [QUEUE] Initiating: user@domain.com`
  - Custodian has been queued for processing.

- `   -> Gmail ID: <id>`
- `   -> Drive ID: <id>`
  - The export IDs discovered for the newly created exports.

### Polling
- ` --- POLLING STATUS ---`
  - The script is checking export statuses for each active custodian.

- ` user@domain.com - Gmail: <STATUS>, Drive: <STATUS>`
  - Current status values parsed from `gam info export ...`.

Common statuses you may see include:
- `COMPLETED` — ready to download
- `IN_PROGRESS` / `RUNNING` (depends on Vault/GAM output) — still processing
- `UNKNOWN` — script couldn’t parse a status from GAM output (investigate the raw GAM output)

### Downloading
- ` [OK] user@domain.com ready. Downloading...`
  - Both exports are `COMPLETED`. The script will:
    1) Create target folders
    2) Download Gmail export
    3) Download Drive export
    4) Delete both exports from Vault
    5) Mark Progress as `Completed` in the state file

---

## Resuming after interruption

You can safely re-run the script. It will:
- Load `vault_automation_state.json`
- Skip custodians already marked `Completed`
- Continue polling/downloading custodians that were started but not completed

If you want to re-run everything from scratch:
1. Delete or rename `vault_automation_state.json`
2. (Optionally) remove/clear destination folders under the target mount

---

## Customization checklist (most common edits)

Open `VaultExportToAzure.ps1` and review:

- **Destination mount**
  - `$targetMount = "X:\201bce56"`

- **Email domain**
  - `$domain = "github.com"`

- **Matter naming convention**
  - `$matterRegex = ...`

- **Parallelism**
  - `$MaxConcurrentCustodians = 5`

---

## Troubleshooting

### “gam is not recognized…”
- GAM is not installed or not in PATH.
- Fix by installing GAM and/or adding it to PATH, or update the script to call the full path to `gam.exe`.

### Status shows `UNKNOWN`
The script extracts status using:

```powershell
if ($gInfo -match 'status:\s*(\w+)') { ... }
```

If your GAM output format differs, update the regex or print `$gInfo` for debugging.

### Exports never complete / stuck polling
- Check Vault export status directly in Google Vault UI.
- You may be rate-limited or have permissions issues.
- Consider increasing polling interval or reducing `$MaxConcurrentCustodians`.

### Downloads incomplete or fail
- Confirm disk space and permissions on `$targetMount`.
- Confirm network/mount stability (especially if it’s a cloud file share).
- Re-run; the script will resume based on state, but note it deletes exports only after attempting downloads when both are completed.

---

## Operational notes / safety

- The script **deletes the Vault exports** after downloading. If you need to retain exports in Vault, comment out:
  - `gam delete vaultexport ...`

- This script assumes “one custodian == one matter matching regex”.
  - If your Vault organization uses different matter layouts, adjust the matter selection logic.

---

## Command reference (what the script runs)

The script uses these GAM commands (conceptually):

- List OPEN matters:
  - `gam print vaultmatters matterstate OPEN`

- Create an export:
  - `gam create export matter "id:<matterId>" name "<name>" corpus <mail|drive> accounts "<user>" usenewexport true`

- List exports in a matter (to discover ID):
  - `gam print vaultexports matter "id:<matterId>"`

- Check export status:
  - `gam info export "id:<exportId>" matter "id:<matterId>"`

- Download export:
  - `gam download vaultexport "id:<exportId>" matter "id:<matterId>" targetfolder "<path>" -s`

- Delete export:
  - `gam delete vaultexport matter "id:<matterId>" "id:<exportId>"`

---

## Support / handoff notes

If handing this to someone new, provide them:
- The correct Workspace domain to set in `$domain`
- The correct destination mount/path to set in `$targetMount`
- The expected Vault matter naming convention (or updated regex)
- A validated GAM config/profile that can access Vault and perform exports