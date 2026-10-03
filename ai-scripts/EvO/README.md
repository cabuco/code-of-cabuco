# Entra Vs. Okta Suite (EvO) — Features & Usage Guide

**Entra Vs. Okta Suite (EvO)** is an enterprise IT automation app built with Python and Streamlit. It automates directory identity mapping, group entitlement reconciliation across Okta and Microsoft Entra ID, guest UPN translation, and offboarding ticket workflows[cite: 23, 24].

---

## 🚀 Key Modules & Architecture

### 📋 1. Primary Identity Mapper
* **Purpose:** Maps individual user identities between Okta/directory profiles and Microsoft Entra ID Object IDs[cite: 24].
* **Key Features:** Supports bidirectional translation (`Source Email ➔ Microsoft ObjectID` or `Microsoft Email ➔ Source Email`) with options to bypass active-status filters for deprovisioning audits[cite: 24].
* **Output:** Clean CSV exports and an Unmapped Discrepancy Matrix identifying unmatched profiles and their system status[cite: 24].

---

### 🔄 2. Group Reconciliation Engine
* **Purpose:** Audits Okta auto-distribution groups (Source of Truth) against manual Entra ID groups[cite: 24].
* **Key Features:** Queries the Okta API live to stream group rosters, translates handles to corporate UPNs, and calculates drift[cite: 24].
* **Output:** Generates two formatted bulk-operation CSV files for the Azure Portal:
  * **Additions CSV:** Members present in Okta but missing from Entra[cite: 24].
  * **Removals CSV:** Rogue members present in Entra who no longer belong in the Okta source group[cite: 24].

---

### 🪪 3. External Identity Resolver
* **Purpose:** Resolves third-party vendor and guest contractor identities[cite: 24].
* **Key Features:** Translates external email addresses into Azure Guest UPN format (`vendor_domain.com#EXT#@tenant.onmicrosoft.com`) and resolves their underlying Entra Object IDs (`id`)[cite: 24].

---

### 📊 4. Account Status Checker
* **Purpose:** Bulk-verifies employee employment status in Okta[cite: 24].
* **Key Features:** Audits user lists to confirm whether accounts are `ACTIVE`, `SUSPENDED`, or `DEACTIVATED`, returning metrics and cross-referenced corporate aliases[cite: 24].

---

### 🌐 5. Group Roster API Fetcher
* **Purpose:** Real-time group membership discovery[cite: 24].
* **Key Features:** Connects live to the Okta API to search for security groups or distribution lists by name or direct Group ID, exporting complete member rosters[cite: 24].

---

### 🤖 6. The Terminator — Automated Offboarding & Ticket Resolution Engine
* **Purpose:** Automates offboarding device audits and Zendesk ticket cleanup[cite: 24].
* **Key Features:**
  * Streams user devices from Okta's API for batch offboardings[cite: 24].
  * Categorizes offboarding tickets into **No Enrolled Devices**, **Non-MacBook Assets**, and **MacBook Assets requiring ABM verification**[cite: 24].
  * Automatically builds chunked Zendesk search queries using `type:ticket ticket_id:"<ID>"` syntax (respecting Zendesk's ~64-word search caps)[cite: 24].
  * Includes an **ABM Reconciliation Stop-Gap** to reconcile missing serials and output resolution queries for non-ABM tickets[cite: 24].

#### Bulk Extraction Workflow
1. Select and copy all text from your Zendesk Offboarding view[cite: 24].
2. Paste into an AI assistant with the prompt:
   > *"Extract the username and corresponding ticket ID for each offboarding ticket in this text, and output them line-by-line in the format: `username ticket_id`"*
3. Copy the clean list directly into **The Terminator**[cite: 24].
