# Google Vault Systematic Export & Direct-to-Mount Archive

Automates **Google Vault exports** for multiple custodians by:
1) discovering in-scope **open matters** via a naming convention,
2) creating **mail + drive** exports when missing,
3) polling until exports are **COMPLETED**,
4) downloading results **directly to a mount / network path**, and
5) verifying the archive isn’t empty before marking work as completed and cleaning up remote exports.

This script is designed for **repeatable, resumable “lit hold style” bulk exports** where you may be exporting dozens/hundreds of custodians and want consistent structure, fewer operator mistakes, and a persistent record of what’s done.

---

## What problem this solves (and why you’d want it)

Bulk exporting from Google Vault is operationally annoying because:
- Exports are **asynchronous** (you create them, then wait).
- Exports can be **interrupted** mid-download (VPN drop, laptop sleep, drive disconnect).
- It’s easy to lose track of which custodians are finished, especially across multiple runs.
- Leaving old exports in Vault increases clutter and may hit limits or policy constraints.

This script provides:
- **Idempotent operation**: you can re-run it safely; it won’t redo completed custodians (based on a local state file).
- **Concurrency control**: processes multiple custodians in parallel (via a “pool” model) without you managing them manually.
- **Integrity gating**: refuses to mark a custodian “Completed” unless downloads contain real files.
- **Consistent archive layout**: deterministic folders per custodian and corpus (Gmail vs Drive).
- **Cleanup**: deletes remote exports after a verified local archive exists.

---

## How it works (high level)

### 1) Scope by Matter naming convention (regex)
The script queries Vault matters and filters them by a regex (`$matterRegex`) that expects matter names like:

- `@username lit hold`
- `@username lit-hold`
- `@username litigation hold`

This convention makes it easy to:
- self-document which matters are “automation eligible”
- map a matter to a custodian username
- avoid accidentally exporting unrelated matters

### 2) Create exports only when missing
For each in-scope matter (custodian), the script ensures two exports exist:
- `username-mail` (corpus: mail)
- `username-drive` (corpus: drive)

If one/both exports are missing, it creates them and returns the custodian to the polling pool.

### 3) Poll until both exports are COMPLETED
Exports are not immediately downloadable; Vault needs time to build them. The script polls every cycle and prints status.

### 4) Download to a mount with a stable folder structure
Once both exports are `COMPLETED`, it downloads to:

```
<targetMount>\<email>_Hold\Gmail\
<targetMount>\<email>_Hold\Drive\
```

### 5) Verify archive integrity before marking Completed
After download, it checks that each target folder contains **at least one file** (not just empty folders). Only then does it:
- mark custodian as `Completed` in the local state file, and
- delete the remote Vault exports.

If verification fails, it retries in a future polling cycle.

---

## Requirements

### Environment
- Windows PowerShell (script is written in PowerShell style)
- Access to a mounted path (network share or external volume) for `$targetMount`
- Sufficient permissions in Google Workspace / Vault to:
  - list matters
  - create exports
  - download exports
  - delete exports

### Tools
- **GAM** (Google Apps Manager / Google Management tool) installed and available in your PATH as `gam`
  - The script uses commands like:
    - `gam print vaultmatters`
    - `gam print vaultexports`
    - `gam create export ...`
    - `gam download vaultexport ...`
    - `gam delete vaultexport ...`

> Note: The exact GAM subcommands/flags can vary by GAM version and configuration. If you see command errors, validate your GAM version and Vault/GAM support for the flags used.

---

## Setup (edit the configuration)

Open `vault_automation.sh` (despite the extension, it contains PowerShell) and set:

1) **Concurrency**
```powershell
$MaxConcurrentCustodians = 5
```
- Higher = faster, but more load and more parallel exports/downloads
- Start conservatively and tune

2) **Archive mount**
```powershell
$targetMount = "Z:\Path\To\Your\Archive"
```
- Must exist when the script starts (script exits if not found)
- Use a stable mount to avoid partial/failed transfers

3) **Domain**
```powershell
$domain = "example.com"
```
- Used to build custodian email addresses like `username@example.com`

4) **State file**
```powershell
$stateFile = Join-Path $PSScriptRoot "vault_automation_state.json"
```
- Leave as-is unless you want state stored elsewhere

5) **Matter scope regex**
```powershell
$matterRegex = '(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)'
```
- Controls which matters are in-scope and how usernames are derived
- The `(?<user>...)` capture group is what becomes `username@domain`

---

## Running the script

From PowerShell, run from the directory containing the script:

```powershell
cd ai-scripts/bulk-gvault-export
.\vault_automation.sh
```

If your execution policy blocks scripts:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\vault_automation.sh
```

---

## Output and artifacts

### Archive output
For each custodian:
- `<targetMount>\<email>_Hold\Gmail\...`
- `<targetMount>\<email>_Hold\Drive\...`

### State tracking
`vault_automation_state.json` is used to record completed custodians:
- If a custodian is listed with `"Progress": "Completed"`, the script will skip re-exporting them on subsequent runs.
- This is what enables safe restarts after failures or interruptions.

---

## Why the script does certain “odd” things

### “Heartbeat enabled” / sending F15
The script starts a background job that sends an F15 keypress periodically. This is a pragmatic workaround to prevent:
- workstation sleep
- screen lock policies that pause network/VPN access
- long-running export/download processes from being interrupted

If your environment doesn’t require this, you can remove the keep-alive job, but it exists to improve reliability in real-world ops.

### Pool-based concurrency rather than true parallel downloads
Vault exports complete at unpredictable times. The script uses a pool/poll model so it can:
- keep multiple custodians “in flight”
- create exports when missing
- only download when both exports are actually ready
- avoid complex multi-threaded download coordination

### Integrity verification is “file count > 0”
The integrity check is intentionally conservative and simple:
- It prevents “Completed” status when a download produced an empty folder (common when a connection drops early).
- It doesn’t attempt cryptographic verification because Vault export formats can vary; the goal is to catch obvious failures cheaply.

If you want stronger guarantees, enhance `Test-ArchiveIntegrity` to validate:
- expected file extensions
- non-zero file sizes
- presence of a manifest/metadata file
- minimum size thresholds

### Deleting remote exports after verified download
This reduces:
- export clutter in Vault
- risk of hitting export limits
- confusion about which export is the “real one”

If your retention policy requires keeping exports in Vault, remove the delete steps—but be aware you may accumulate many exports over time.

---

## Operational tips

- Run the script from a machine with **stable network + stable mount access**.
- Prefer a wired connection / reliable VPN.
- Start with low concurrency (`$MaxConcurrentCustodians = 2` or `3`) and increase once you confirm stability.
- Use consistent matter naming so scope selection is predictable.
- If you change naming conventions, update `$matterRegex` accordingly.

---

## Troubleshooting

### Target mount not found
You’ll see:
- `ERROR: Target Mount ... not found!`

Fix:
- Confirm the drive letter/path is mounted **before** running.
- Confirm the account running the script has access.

### No matters found / unexpected skipping
The script will print an audit list of skipped matter names (naming convention mismatch).
- Adjust matter names or update `$matterRegex`.

### GAM command errors
Common causes:
- GAM not installed / not in PATH
- insufficient Vault permissions
- wrong GAM syntax for your version

Validate by running these manually:
```powershell
gam print vaultmatters matterstate OPEN
gam print vaultexports matter "id:<matterId>"
```

### Script repeats a custodian forever
Likely causes:
- downloads are not producing files (permissions, export empty, download failing)
- mount path intermittently disconnecting

Check:
- the custodian’s Gmail/Drive folders for actual downloaded content
- network/mount stability
- GAM download output/errors (you may want to capture output to logs)

---

## Safety notes / disclaimers

- This script performs **destructive cleanup** in Vault (deletes exports) *after* local verification.
- Test in a non-production or limited-scope environment first.
- Confirm your org’s legal/compliance requirements for export handling and retention.

---

## Suggested enhancements (optional)
If you plan to run this regularly at scale, consider adding:
- structured logging to a timestamped log file
- per-custodian retry counters and a “Failed” terminal state
- stronger integrity checks (size thresholds, manifests)
- separate config file (JSON/YAML) for environment-specific values

---

## License / usage
Intended as an operational automation utility. Adjust to match your org’s compliance and legal requirements before production use.
