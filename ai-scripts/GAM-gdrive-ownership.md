
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

---

# 1. Identify Accounts

- **Source account:** offboarded user  
- **Destination account:** manager

Example:
```
source@domain.com  
target@domain.com
```

---

# 2. Create the Transfer Folder

Create a folder in the source user’s MyDrive:

```bash
gam user source@domain.com create drivefile drivefilename "source-mydrive" mimetype gfolder
```

Record the returned folder ID — this is your **TRANSFER_ID**.

---

# 3. Recursively Copy the Source MyDrive

Copy everything from the user’s root into the transfer folder:

```bash
gam user source@domain.com copy drivefile "root" recursive parentid "TRANSFER_ID"
```

---

# 4. Grant the Destination User Writer Access

Writer access is required before transferring ownership:

```bash
gam user source@domain.com add drivefileacl "TRANSFER_ID" user target@domain.com role writer
```

---

# 5. Generate a Spreadsheet of All Items in the Transfer Folder

This spreadsheet allows bulk ownership transfer.

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
= "gam user source@domain.com add drivefileacl """ & E2 & """ user target@domain.com role owner"
```

Run all generated commands to transfer ownership of every file and folder inside the transfer folder.

---

# 6. Make the Transfer Folder Appear in the Destination’s MyDrive

After ownership transfer, the folder might not be visible. Fix this with the steps below.

---

## 6a. Transfer Ownership of the Top-Level Folder

```bash
gam user source@domain.com add drivefileacl "TRANSFER_ID" user target@domain.com role owner
```

---

## 6b. Move the Folder Into the Destination’s MyDrive

```bash
gam user target@domain.com update drivefile "TRANSFER_ID" addparent root
```

---

# Summary

This workflow ensures:

- A complete, organized replica of the offboarded user’s MyDrive  
- Manager receives a clean, single-location copy  
- IT retains the original MyDrive untouched for archival  
- No reliance on view-only access or confusing searches  
- A predictable, scalable offboarding process for GDrive environments
