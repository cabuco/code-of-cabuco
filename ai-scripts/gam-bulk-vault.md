
# Bulk Google Vault Exports via GAM (Automated Workflow)

## Overview
Manually creating individual Google Vault exports through the UI can be slow and repetitive. This workflow automates bulk Vault item extraction using a **CSV input file** and GAM commands.

This guide provides:
- Clear CSV preparation steps
- Command sections separated cleanly between *explanatory text* and *shell code*
- Automated counting and export generation
- A clean structure suited for GitHub documentation

---

# 1. Prepare Your CSV File
Create a CSV with **two columns**:

| ExportName | Query |
|------------|--------|
| Name of the Vault export folder | Search query terms |

Example:
```
ExportName,Query
export1,subject:("keyword1")
export2,from:(source@domain.com)
```

Upload this CSV to Cloud Shell. For this guide we assume the file is named:
```
vault_tasks.csv
```

---

# 2. Set GAM Threading to Avoid Rate-Limits
Reduce threads to prevent Vault API throttling.

```bash
gam config num_threads 1 save
```

**What this does:** Forces GAM to run single-threaded for Vault operations, minimizing quota/rate‑limit errors.

---

# 3. Get Vault Search Counts in Bulk
This script loops through each Query in your CSV and retrieves message counts for a specific account within a specific Vault matter.

## Shell Script
```bash
echo "Query,Account,Count" > final_counts_clean.csv
while IFS=, read -r ExportName Query; do
  # Skip the header row
  if [[ "$ExportName" == "ExportName" ]]; then continue; fi

  echo -n "$Query," >> final_counts_clean.csv
  gam print vaultcounts matter "@sourcehandle lit hold"       corpus mail accounts "source@domain.com"       terms "$Query"       start "2018-01-01"       end "2025-11-15" | grep "source@domain.com" | awk '{print $1","$2}' >> final_counts_clean.csv

done < vault_tasks.csv
```

**What this does:**
- Reads each row of your CSV
- Executes `gam print vaultcounts` for each Query
- Writes results to `final_counts_clean.csv`

The output file includes:
```
Query,Account,Count
"query1",source@domain.com,123
"query2",source@domain.com,52
```

---

# 4. Bulk-Create Vault Exports
Use the same CSV to automatically generate Vault exports.

```bash
gam csv vault_tasks.csv gam create export matter "@source lit hold" name "~~ExportName~~" corpus mail accounts "source@domain.com" terms "~~Query~~" start "2018-01-01" end "2025-11-15" format mbox usenewexport true
```

**What this does:**
- Creates an export for each row of your CSV
- Uses the ExportName and Query columns dynamically
- Generates MBOX-format exports in Vault

---

To see the live status and verify they are running

```bash
gam show vaultexports matter "@sourcehandle lit hold"
```



# Summary
This automated workflow:
- Eliminates repetitive manual Google Vault UI work
- Ensures consistent export formatting
- Provides count validation before export creation
- Allows large‑scale Vault extraction with minimal effort
