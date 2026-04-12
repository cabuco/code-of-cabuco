# bulk-gvault-export-v2 — VaultExportToAzure.ps1 (v42.0)

This PowerShell script automates **systematic Google Vault exports** for a set of **OPEN matters** that follow a naming convention (litigation hold matters), and then **downloads completed exports directly to a mounted drive** (e.g., `X:\...`). It also persists progress to a local JSON “state” file so the script can be safely re-run and resume where it left off.

> Note: Despite the filename (`VaultExportToAzure.ps1`), the current script’s behavior is **direct-to-mount download + cleanup**. Any “Azure” step (upload/sync) is **not** implemented in the current form.

---

## What the script does (high level)

1. **Starts a keep-alive “heartbeat” job**
   - Uses `WScript.Shell` to send `{F15}` periodically (every 240 seconds) to prevent the session from idling/disconnecting.

2. **Ensures the target download directory exists**
   - Creates `$targetMount` if missing.

3. **Loads state from disk (resume support)**
   - Reads `vault_automation_state.json` from the script directory (if present).
   - This state tracks each custodian/email’s:
     - Matter ID
     - Export IDs (Gmail/Drive)
     - Progress (`Exporting` / `Completed`)

4. **Finds the set of “custodians” to process**
   - Calls GAM to list **OPEN** Vault matters:
     - `gam print vaultmatters matterstate OPEN`
   - Filters matters whose **name matches** a litigation-hold pattern (see “Matter naming convention” below).
   - Builds a pending queue of custodians that are not already marked `Completed` in the state file.

5. **Runs a bounded “concurrent” processing pool**
   - Uses `$MaxConcurrentCustodians` to cap how many custodians are active at once.
   - The script cycles in a loop:
     - Adds pending custodians into `$ActivePool` until it reaches the concurrency limit.
     - For each active custodian:
       - Creates Gmail + Drive exports (if export IDs not already captured).
       - Polls export status.
       - Downloads exports once both are completed.
       - Deletes exports after download.
       - Marks the custodian `Completed` in the state file.
     - Sleeps 300 seconds between polling rounds while work remains.

---

## Matter naming convention (how custodians are discovered)

The script only targets matters whose `name` matches:

- Starts with `@username`
- Followed by a variation of “lit hold” / “litigation hold”

Regex used:

```regex
(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)
```

From the matched `@username`, the script constructs:

- **User**: `username`
- **Email**: `username@$domain`

The `$domain` variable is currently set to:

- `github.com`

(Adjust this to your actual Google Workspace domain.)

---

## Export creation and “robust export ID capture”

For each custodian, the script creates two exports:

- `mail` corpus (Gmail)
- `drive` corpus (Google Drive)

It creates exports using GAM, then immediately lists exports for the matter and attempts to pick the correct export ID:

- Create:
  - `gam create export matter "id:<matterId>" name "<username>-<mail|drive>" corpus <mail|drive> accounts "<username>" usenewexport true`
- Capture ID:
  - `gam print vaultexports matter "id:<matterId>" | ConvertFrom-Csv`
  - Match by export `name` and ensure the returned `id` is **not** the **Matter ID** (a failure mode the script explicitly guards against).

If either export ID cannot be captured, the script logs:

- `ID Capture failed ... Matter ID was likely returned instead of Export ID.`
…and keeps the custodian in the active pool to try again on the next polling cycle.

---

## Status polling + download workflow

Once both export IDs are known, the script checks status for each export:

- `gam info export "id:<exportId>" matter "id:<matterId>"`

It parses the output for:

- `status: <VALUE>`

When **both** Gmail and Drive are `COMPLETED`:

1. Creates a custodian folder structure under the mount:

   - Root:
     - `<targetMount>\<email> hold`
   - Subfolders:
     - `Gmail`
     - `Drive`

2. Downloads exports:

   - `gam download vaultexport "id:<gmailExportId>" matter "id:<matterId>" targetfolder "<...>\Gmail"`
   - `gam download vaultexport "id:<driveExportId>" matter "id:<matterId>" targetfolder "<...>\Drive"`

3. Deletes the exports from Vault:

   - `gam delete vaultexport matter "id:<matterId>" "id:<exportId>"`

4. Marks custodian state as:

- `Progress = "Completed"`

If not completed yet, it prints the current statuses and continues polling.

---

## Files and outputs

### State file (resume support)
- **Path:** `vault_automation_state.json` (in the same directory as the script)
- Contains one entry per custodian/email with export IDs and progress.

### Download output structure
- Base folder: `$targetMount` (default: `X:\201bce56`)
- Per custodian:
  - `X:\201bce56\<email> hold\Gmail\...`
  - `X:\201bce56\<email> hold\Drive\...`

---

## Configuration knobs (edit these)

At the top of the script:

- `$MaxConcurrentCustodians = 5`
  - Limits active custodians processed per polling cycle.

- `$targetMount = "X:\201bce56"`
  - Where downloads are written.

- `$domain = "github.com"`
  - Used to build `user@domain` email addresses.

- `$matterRegex = ...`
  - Controls which matters are treated as holds and how the user is parsed.

---

## Prerequisites

- **Windows PowerShell** (or PowerShell 7 with Windows compatibility for COM automation).
- **GAM installed and available on PATH**
  - The script invokes `gam ...` commands directly.
- Sufficient Google Vault permissions to:
  - List matters
  - Create exports
  - Check export status
  - Download exports
  - Delete exports

---

## Running the script

From a PowerShell session with appropriate permissions:

```powershell
cd ai-scripts/bulk-gvault-export-v2
.\VaultExportToAzure.ps1
```

To resume after interruption, simply re-run it; it will read `vault_automation_state.json` and skip custodians already marked `Completed`.

---

## Operational notes / caveats

- **“Azure” not included:** If you want uploads to Azure Storage, add a post-download step (e.g., `AzCopy`, `Azure CLI`, or `Start-BitsTransfer` to a mounted SMB share backed by Azure Files).
- **Heartbeat job:** The keep-alive job runs continuously until the script exits, then is stopped with `Stop-Job`. If you terminate the script forcefully, you may need to manually stop/clean up jobs.
- **API pacing:** The script uses `Start-Sleep` delays and polls every 5 minutes (`300s`) while work remains.
- **Export name format:** Exports are created with names like `<username>-mail` and `<username>-drive`. If you change this naming, update the matching logic.

---

## Troubleshooting

- **No custodians detected**
  - Confirm matter names match the regex pattern.
  - Confirm matters are `OPEN`.
  - Confirm `$domain` is correct for email matching against the state file.

- **ID capture failing**
  - The script attempts to guard against GAM returning the Matter ID instead of the Export ID.
  - If you see repeated failures, manually run:
    - `gam print vaultexports matter "id:<matterId>"`
  - Verify the export `name` is exactly what the script created (`<username>-mail` / `<username>-drive`).

- **Downloads empty or incomplete**
  - Verify export status is truly `COMPLETED`.
  - Check GAM output and permissions for the service account / admin account running the script.
