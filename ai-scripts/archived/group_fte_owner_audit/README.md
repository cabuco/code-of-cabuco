# Google Groups FTE Ownership Audit

## Overview
This project generates a compliance report for all Google Groups in a Google Workspace domain, ensuring each group has **two Full-Time Employee (FTE) owners**. It identifies groups that meet governance requirements and flags those that need review.

## Features
- Audits **all Google Groups** in the Workspace.
- Lists:
  - Group Display Name
  - Group Email
  - Group Aliases
  - All Members
  - Two FTE Owners (Owner 1 and Owner 2)
  - Status (`OK` or `FLAGGED`)
  - Flag Reason for quick remediation
- Prioritizes **existing FTE owners**; fills gaps with other FTE members.
- Outputs a **single CSV file** for easy review and action.

## Requirements
- **Google Workspace Admin access**
- **GAM (Google Apps Manager)** installed in Cloud Shell or local environment
- Python 3.x
- `pandas` library (`pip install pandas`)

## Input Files
1. **groups.csv**  
   Exported via GAM:
   ```bash
   gam print groups fields name,email,aliases > groups.csv
   ```
2. **members.csv**  
   Exported via GAM:
   ```bash
   gam print group-members fields groupemail,useremail,role,type,status > members.csv
   ```
3. **FTE.csv**  
   A CSV file with Column A containing FTE email addresses.

## Output
- **group_fte_owner_audit.csv**  
  Columns:
  ```
  Google Group Display Name | Google Group Email | Google Group Aliases | Google Group Members | Owner 1 | Owner 2 | Status | Flag Reason
  ```

## Setup
1. Place `groups.csv`, `members.csv`, and `FTE.csv` in the same directory.
2. Install dependencies:
   ```bash
   pip install pandas
   ```
3. Save the Python script as:
   ```
   build_group_fte_owner_audit.py
   ```

## Run the Script
```bash
python3 build_group_fte_owner_audit.py
```

**Result:**  
`group_fte_owner_audit.csv` will be created in the same directory.

## Logic
- Normalize all emails (case-insensitive).
- Prefer existing FTE owners.
- Fill remaining slots with other FTE members.
- Flag groups with fewer than two FTEs:
  - `No FTE in group`
  - `Only 1 FTE in group`
  - `No members in group`
  - `Unable to assign 2 FTE owners`

## Optional Enhancements
- Generate **GAM enforcement commands** to:
  - Add FTE owners
  - Remove non-FTE owners
- Export to Excel (.xlsx) for easier sharing.

## Project Name
`group_fte_owner_audit`
