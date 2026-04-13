# Google Vault Systematic Bulk Export (GAM + PowerShell)

This folder contains a PowerShell script that **automates “systematic” Google Vault exports** for a set of Vault matters that follow a **naming convention**, then **downloads the completed exports directly to a network (or local) mount**, and finally (by default) **deletes the exports from Vault after verifying files exist on disk**.

Script:
- `gvault-bulk-export.ps1`

---

## What this is for

Use this when your organization has many Google Vault matters (often legal / litigation hold matters) and you want a repeatable way to:

1. **Find all OPEN matters** that match a specific naming convention (example: `@username lit hold`)
2. For each matching matter:
   - Ensure there is a **Gmail export** and a **Drive export**
   - Poll until both exports are **COMPLETED**
   - Download both exports to a **target archive path**
   - Verify downloads exist (basic verification)
   - Delete the exports in Vault *(this is what the script currently does; you can disable it if policy requires)*
3. Track progress in a local **state file** so reruns can resume without redoing completed custodians

---

## The “high level” explanation (plain English)

Think of this as an “assembly line”:

- **Google Vault matters** are like “cases” (containers that may have custodians and data).
- This script looks for cases whose *names* follow a pattern (like `@username lit hold`).  
  That’s how it decides which custodians to process without needing a separate input list.
- For each matching case, it makes sure the two exports you care about exist:
  - one for **Gmail**
  - one for **Drive**
- Exports can take a long time, so the script **waits and checks periodically**.
- Once both exports are ready, it **downloads** them into an organized folder layout on your archive storage.
- After it confirms the download produced files, it **marks that custodian as completed** so reruns don’t repeat work.
- Finally, it **cleans up the Vault exports** (optional, but enabled as written) so Vault doesn’t accumulate exports over time.

---

## Why the script does things “this way” (design rationale)

This section explains the *why* behind the choices so the behavior is intuitive.

### 1) Why use a matter naming convention + regex?
**Goal:** avoid maintaining a separate roster/spreadsheet of custodians.

- Many orgs already follow a consistent matter naming scheme (for example: the custodian is embedded in the name).
- A regex makes the script “self-targeting”: it only acts on matters that match the pattern and **audits** (prints) those that don’t.
- Benefit: reduces human error and makes the process repeatable (new matters become eligible automatically if they follow the naming rule).

> If your organization doesn’t embed the user in the matter name, you’ll want to modify the regex (or the selection logic) accordingly.

### 2) Why create *two* exports (Gmail + Drive)?
**Goal:** capture the two most common corpuses in separate exports.

- Vault exports are scoped by corpus. Separating them keeps the output simpler:
  - Gmail data ends up in `Gmail/`
  - Drive data ends up in `Drive/`
- It also makes it easier to troubleshoot (if Drive export is slow/failing, Gmail can still complete, and you can see that status clearly).

### 3) Why poll instead of “fire once and exit”?
**Goal:** Vault exports are asynchronous and can take minutes to hours.

- When you create a Vault export, it typically does not complete immediately.
- The script periodically checks status so you don’t have to babysit the process manually.
- The 10-minute sleep between pool polls is a compromise:
  - frequent enough to make progress
  - not so frequent that it spams Vault/GAM calls

### 4) Why use a “pool” with `$MaxConcurrentCustodians`?
**Goal:** parallelism without going out of control.

- If you have many matters, running them strictly one-by-one can be very slow.
- If you run *all* at once, you can overwhelm your environment (or just create operational chaos).
- The pool size gives you a throttle: it allows “some parallel” work while keeping it bounded and predictable.

### 5) Why keep a local `vault_automation_state.json` file?
**Goal:** resumability and idempotency.

- Vault exports and downloads are long-running operations.
- Workstations restart, network mounts disconnect, exports fail, etc.
- The state file is a lightweight “checkpoint system”:
  - custodians marked `Completed` are skipped on future runs
  - you can re-run the script safely after interruptions

> This is why the script updates the state file frequently—so you don’t lose progress if something stops mid-run.

### 6) Why verify downloads by checking “folder has files”?
**Goal:** perform a *basic* sanity check without complex parsing.

- The script’s current verification is intentionally simple:
  - “Did something land in Gmail folder?”
  - “Did something land in Drive folder?”
- This avoids format-specific assumptions about Vault export contents.
- Tradeoff: it does not guarantee completeness, only that downloads produced output.

If you need stronger verification, common upgrades include:
- checking for expected file types / naming patterns
- minimum total size thresholds
- hashing/manifest checks (if available)

### 7) Why delete the Vault exports after download?
**Goal:** reduce clutter/cost and avoid “export buildup.”

- Vault exports can accumulate and become an administrative burden.
- If you consider the archive mount to be the system-of-record for exports, cleanup is sensible.
- **However:** some environments require exports to remain in Vault for audit or retention reasons. If that’s your case, remove/comment out the delete steps.

### 8) Why the “keep-awake / heartbeat” job (F15)?
**Goal:** reduce failures caused by sleep/lock in long unattended runs.

- Export polling + downloads can run for hours.
- Some environments pause network drives, drop authentication, or disrupt sessions when a machine sleeps/locks.
- The heartbeat is a pragmatic “keep the session alive” approach.

If you run on a server or in a controlled scheduled environment, you may prefer to disable this and instead ensure:
- the machine never sleeps
- the script runs in a context where mounts and credentials are stable

---

## How it works (step-by-step)

1. **Heartbeat / keep-awake job**  
   Starts a background job that sends a periodic keypress to keep the session active.

2. **Mount check**  
   Exits early if `$targetMount` doesn’t exist. This fails fast rather than running for a long time and failing at download time.

3. **Load state**
   Reads `vault_automation_state.json` if present; otherwise starts fresh.

4. **Query Vault matters (OPEN only)**
   Runs:
   - `gam print vaultmatters matterstate OPEN`  
   Then parses CSV output and selects matters that match `$matterRegex`.

5. **Queue + audit**
   - Matching matters go into the pending queue (unless already `Completed`).
   - Non-matching matters are printed for audit visibility.

6. **Processing loop**
   - Maintains an active pool up to `$MaxConcurrentCustodians`.
   - For each custodian in the pool:
     - checks existing exports
     - creates missing exports
     - polls status until both are `COMPLETED`

7. **Download + folder structure**
   Downloads into:
   - `<targetMount>\<email>_Archive\Gmail`
   - `<targetMount>\<email>_Archive\Drive`

8. **Verify + cleanup + state update**
   - If folders have files, mark completed and (by default) delete exports.
   - Always updates `vault_automation_state.json` so reruns can resume.

---

## Prerequisites (must do before running)

### 1) Windows + PowerShell
- Windows environment that can run PowerShell.
- Recommended: PowerShell 5.1+ or PowerShell 7+.

### 2) GAM installed and working
This script depends on **GAM (Google Apps Manager / Google Admin command line tool)** and uses it by calling `gam` directly.

You must have:
- GAM installed on the machine running this script
- `gam` available in your PATH, OR you must modify the script to call the full path to `gam.exe`
- GAM authenticated and authorized for Vault operations

**Minimum GAM capabilities used by this script:**
- Print matters
- Print exports
- Create exports (mail and drive)
- Download exports
- Delete exports

### 3) Google Workspace permissions / Vault access
The account GAM runs as must have appropriate admin/Vault permissions to:
- list Vault matters
- create exports for matters
- download exports
- delete exports

If the account lacks permissions, GAM commands will fail and the script may loop indefinitely or repeatedly retry.

### 4) A target mount (archive destination) that exists
The script requires that the destination path exists before it starts.

In the script:
- `$targetMount = "Z:\Your\Archive\Path"`

You must:
- Replace this with a real path (UNC path or mapped drive)
- Ensure the path is reachable from the machine running the script
- Ensure you have write permissions

> Tip: UNC paths (e.g. `\\server\share\archive`) can be more reliable than drive letters, depending on how the script is executed.

### 5) Your domain configured
In the script:
- `$domain = "example.com"`

Replace with your organization’s Google Workspace domain (used to build email addresses from `@username` matter names).

### 6) Matter naming convention matches the regex
The script only processes matters whose names match:

```powershell
$matterRegex = '(?i)^@(?<user>[\w\.-]+)\s+(lit\s+hold|lit-hold|litigation\s+hold)'
```

Examples that match:
- `@jane.doe lit hold`
- `@john-smith litigation hold`
- `@user.name lit-hold`

If your matter naming differs, adjust `$matterRegex`.

---

## What you must edit in the script (configuration checklist)

Open `gvault-bulk-export.ps1` and set:

- **Archive path**
  - `$targetMount = "..."`

- **Domain**
  - `$domain = "..."`

Optional tuning:
- **Concurrency**
  - `$MaxConcurrentCustodians = 5`

- **Regex**
  - `$matterRegex = '...'`

---

## Running the script

From PowerShell, in the script directory:

```powershell
.\gvault-bulk-export.ps1
```

Recommended (to avoid policy issues and to capture logs):

```powershell
PowerShell -ExecutionPolicy Bypass -File .\gvault-bulk-export.ps1 *>&1 | Tee-Object -FilePath .\gvault-bulk-export.log
```

---

## Output structure (what gets created)

For each matching custodian (`<email>`), the script creates:

```
<targetMount>\
  <email>_Archive\
    Gmail\
    Drive\
```

Exports are downloaded into the `Gmail` and `Drive` folders.

---

## State file (resume support)

The script writes progress to:

- `vault_automation_state.json` (in the same folder as the script)

If the script is interrupted, rerunning it will skip custodians already marked:

- `Progress: "Completed"`

If you want to re-run everything from scratch:
- delete `vault_automation_state.json` (or edit entries), then rerun

---

## Important notes / operational cautions

- **It deletes exports after successful download.**  
  The script calls `gam delete vaultexport ...` once it sees files in both download folders. If your retention / audit process requires keeping exports in Vault, remove or comment out those delete lines.

- **Download verification is minimal.**  
  The check is basically “does each folder contain at least one item”. It does not validate completeness, checksums, or expected file counts.

- **Long-running behavior.**  
  The script polls in a loop and waits **10 minutes** between polling cycles when work remains:
  - `Start-Sleep -Seconds 600`

- **Keep-awake job.**  
  It starts a background job sending `{F15}`. If you run this on a server or in an environment where simulated keystrokes are undesirable, remove that section.

- **Mapped drives in non-interactive sessions.**  
  If you run via Task Scheduler or as a service account, mapped drives (like `Z:`) often do not exist. Prefer a UNC path for `$targetMount`.

---

## Troubleshooting

### “Target Mount not found”
- Confirm `$targetMount` exists and is reachable.
- Prefer a UNC path instead of a drive letter if running unattended.

### GAM command not found
- Install GAM or add it to PATH.
- Test in the same PowerShell session:
  ```powershell
  gam version
  ```

### No matters found / everything skipped
- Your matter names likely don’t match the regex.
- Print out a few matter names and adjust `$matterRegex`.

### Exports never reach COMPLETED
- Vault exports can take time depending on data size.
- Ensure the GAM account has access and the matter is valid.
- Check `gam print vaultexports matter "id:<matterId>"` manually for status/details.

---

## Security / compliance reminder

Vault exports can contain sensitive or regulated data. Ensure:
- archive storage is approved (encryption, access controls, retention)
- downloads are stored and handled according to your org’s policies
- execution is performed by authorized personnel only
