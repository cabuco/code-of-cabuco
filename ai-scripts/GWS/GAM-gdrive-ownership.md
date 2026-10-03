
# GDrive Offboarding: Full-Fidelity Ownership Transfer (GAM Workflow)

## Why This Process Is Needed

When an employee is offboarded, Google automatically transfers the user’s MyDrive to IT after **90 days**. Managers often need access sooner, but giving **view-only** access creates several issues:

- View-only users **cannot copy folders**, preventing bulk copying.
- Search-based access becomes confusing after ownership is transferred to IT’s service account.
- Managers end up with scattered access instead of one organized location.
- IT must preserve the *original* MyDrive for permanent archival.

### Solution

Create a **full recursive copy** of the user’s MyDrive, place it into a dedicated folder, and transfer its ownership to the manager. This provides:

- A complete replica of the user’s data
- A single folder containing everything
- Zero impact on the original MyDrive that IT will archive

To assist with accurate GAM command creation, you may copy and use this helpful **Formula Sheet**:

➡️ https://docs.google.com/spreadsheets/d/1GIsNVNZtXEuc7QI_HjD88dzq33s4YZOZwgyQdHaMxpQ/edit?usp=sharing

---

# 1. Identify Accounts

- **Source account:** Offboarded user
- **Destination account:** Manager

Example:
```
source@domain.com
target@domain.com
```

---

# 2. Create the Transfer Folder & Transfer Ownership

Create a folder in the source user’s MyDrive:

```bash
gam user source@domain.com create drivefile drivefilename "source-mydrive" mimetype gfolder
```

Record the returned folder ID — this is your **TRANSFER_ID**.

Transfer folder ownership to the destination account:

```bash
gam user source@domain.com add drivefileacl "TRANSFER_ID" user target@domain.com role owner
```

---

# 3. Recursively Copy the Source MyDrive

Copy everything from the source user’s root into the transfer folder:

```bash
gam user source@domain.com copy drivefile "root" recursive parentid "TRANSFER_ID"
```

---

# 4. Generate a Spreadsheet of All Items in the Transfer Folder

This spreadsheet is necessary for bulk ownership transfer.

```bash
gam user source@domain.com print filetree select TRANSFER_ID fields id,mimetype,parents todrive
```

### Expected Columns (A–G)

- User
- index
- name
- id
- mimeType
- parents
- (system columns may vary)

### Ownership Transfer Formula

Paste the following into **H2** of the generated Google Sheet, then fill down:

```text
= "gam user source@domain.com add drivefileacl "" & E2 & "" user target@domain.com role owner"
```

Run all generated commands to fully transfer ownership of every file and folder inside the transfer folder.

---

# 5. Make the Transfer Folder Appear in the Destination’s MyDrive

After ownership transfer, the folder may not appear immediately in the destination user’s MyDrive.

Run the following command to attach it to MyDrive:

```bash
gam user target@domain.com update drivefile "TRANSFER_ID" addparent root
```

---

# Summary

This workflow ensures:

- A complete, fully organized replica of the offboarded user's MyDrive
- A single easy-to-access folder for the manager
- Preservation of the original MyDrive for IT archival
- No dependency on view-only access or error-prone Drive searches
- A scalable, reliable offboarding workflow for Google Workspace environments
