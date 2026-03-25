# Google Vault Automation Script

## Overview

`vault_automation.sh` is a **safe, resumable automation script** for exporting **Gmail (MBOX)** and **Google Drive** data from **Google Vault matters** using **GAM**.

The script:

- Discovers **OPEN** Vault matters
- Filters to matters whose names start with `@`
- Exports Gmail and Drive data per user
- Downloads exports locally
- Deletes Vault exports after download
- Tracks progress so it can resume safely
- Handles API throttling and transient errors
- Can be stopped safely mid‑run

---

## What the Script Exports

For each **OPEN** Vault matter where:

- Matter name starts with `@`
- Matter state is **OPEN**

The script will:

1. Extract the username from the matter name  
   Example: `@jdoe Legal Hold` → `jdoe`
2. Create a **Gmail export** (MBOX format)
3. Create a **Drive export** (all Drive data)
4. Download both exports locally
5. Delete the Vault exports after successful download

---

## Directory Structure

All output is written to:

```
./vault_exports/
```

Example:

```
vault_exports/
├── logs/
│   └── vault_automation.log
├── state/
│   └── progress.json
├── @jdoe Legal Hold/
│   ├── Gmail/
│   │   └── *.mbox
│   └── Drive/
│       └── *.zip
```

If multiple **OPEN** matters share the same name, the script appends a short ID to prevent folder collisions.

---

## Prerequisites

The following commands must be installed and available in `PATH`:

- `gam`
- `jq`
- `python3`
- `sed`
- `awk`
- `wc`

The script exits immediately if any dependency is missing.

---

## Required GAM Permissions

GAM must be authorized to:

- List Vault matters
- Create Vault exports
- Check export status
- Download Vault exports
- Delete Vault exports

---

## Progress Tracking

Progress is stored in:

```
vault_exports/state/progress.json
```

Per matter, the script records:

- Gmail export name
- Drive export name
- Gmail completion status
- Drive completion status

You can safely re‑run the script at any time. Completed exports are skipped automatically.

---

## Safe Stop Mechanism

To stop the script gracefully, create the following file:

```
vault_exports/STOP_VAULT_AUTOMATION
```

The script checks for this file between major steps and exits cleanly without corrupting state.

To resume:

1. Remove the STOP file
2. Re‑run the script

---

## How to Run

```bash
chmod +x vault_automation.sh
./vault_automation.sh
```

No arguments are required.

---

## Logging

Logs are written to:

```
vault_exports/logs/vault_automation.log
```

Logs include:

- Timestamps
- Matter names and IDs
- Export creation and completion
- Download activity
- Retry and backoff events
- Error details with context

---

## Error Handling and Retries

The script includes:

- Automatic retries for transient Google API errors
- Exponential backoff (up to 10 minutes)
- Immediate failure on non‑retryable errors
- Full error context (line number and command)

After fixing an issue, you can re‑run the script safely.

---

## Export Naming Convention

Exports follow this pattern:

```
gmail_<user>_<matter>_<short-id>
drive_<user>_<matter>_<short-id>
```

Names are sanitized and the script uses `id:<uuid>` references internally to avoid Vault lookup errors.

---

## Important Notes

- Gmail exports are created in **MBOX** format
- Drive exports include **all Drive data**
- Vault exports are deleted **after successful download**
- GAM threading is forced to `num_threads=1` to reduce Vault throttling

---

## Script Exit Conditions

The script exits cleanly (not an error) if:

- No OPEN Vault matters exist
- No OPEN matters start with `@`

This behavior is logged.

---

## Intended Use Cases

- Legal holds
- Offboarding exports
- eDiscovery preparation
- Large‑scale Vault data extraction
- Long‑running unattended export jobs

---

## Summary

This script is designed to be:

- ✅ Safe
- ✅ Idempotent
- ✅ Resumable
- ✅ Throttle‑aware
- ✅ Admin‑friendly
