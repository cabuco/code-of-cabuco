# Entra Vs. Okta Suite (EvO) — Features & Usage Guide

**Entra Vs. Okta Suite (EvO)** is an enterprise IT automation app built with Python and Streamlit. It automates directory identity mapping, group entitlement reconciliation across Okta and Microsoft Entra ID, guest UPN translation, and offboarding ticket workflows.

---

## 🚀 Key Modules & Architecture

### 📋 1. Primary Identity Mapper
* **Purpose:** Maps individual user identities between Okta/directory profiles and Microsoft Entra ID Object IDs.
* **Key Features:** Supports bidirectional translation (`Source Email ➔ Microsoft ObjectID` or `Microsoft Email ➔ Source Email`) with options to bypass active-status filters for deprovisioning audits.
* **Output:** Clean CSV exports and an Unmapped Discrepancy Matrix identifying unmatched profiles and their system status.

---

### 🔄 2. Group Reconciliation Engine
* **Purpose:** Audits Okta auto-distribution groups (Source of Truth) against manual Entra ID groups.
* **Key Features:** Queries the Okta API live to stream group rosters, translates handles to corporate UPNs, and calculates drift.
* **Output:** Generates two formatted bulk-operation CSV files for the Azure Portal:
  * **Additions CSV:** Members present in Okta but missing from Entra.
  * **Removals CSV:** Rogue members present in Entra who no longer belong in the Okta source group.

---

### 🪪 3. External Identity Resolver
* **Purpose:** Resolves third-party vendor and guest contractor identities.
* **Key Features:** Translates external email addresses into Azure Guest UPN format (`vendor_domain.com#EXT#@tenant.onmicrosoft.com`) and resolves their underlying Entra Object IDs (`id`).

---

### 📊 4. Account Status Checker
* **Purpose:** Bulk-verifies employee employment status in Okta.
* **Key Features:** Audits user lists to confirm whether accounts are `ACTIVE`, `SUSPENDED`, or `DEACTIVATED`, returning metrics and cross-referenced corporate aliases.

---

### 🌐 5. Group Roster API Fetcher
* **Purpose:** Real-time group membership discovery.
* **Key Features:** Connects live to the Okta API to search for security groups or distribution lists by name or direct Group ID, exporting complete member rosters.

---

### 🤖 6. The Terminator — Automated Offboarding & Ticket Resolution Engine
* **Purpose:** Automates offboarding device audits and Zendesk ticket cleanup.
* **Key Features:**
  * Streams user devices from Okta's API for batch offboardings.
  * Categorizes offboarding tickets into **No Enrolled Devices**, **Non-MacBook Assets**, and **MacBook Assets requiring ABM verification**.
  * Automatically builds chunked Zendesk search queries using `type:ticket ticket_id:"<ID>"` syntax (respecting Zendesk's ~64-word search caps).
  * Includes an **ABM Reconciliation Stop-Gap** to reconcile missing serials and output resolution queries for non-ABM tickets.

#### Bulk Extraction Workflow
1. Select and copy all text from your Zendesk Offboarding view.
2. Paste into an AI assistant with the prompt:
   > *"Extract the username and corresponding ticket ID for each offboarding ticket in this text, and output them line-by-line in the format: `username ticket_id`"*
3. Copy the clean list directly into **The Terminator**.
