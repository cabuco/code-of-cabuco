# Entra Vs. Okta Suite (EvO) — Features & Usage Guide

**Entra Vs. Okta Suite (EvO)** is an enterprise IT automation app built with Python and Streamlit. It automates directory identity mapping, group entitlement reconciliation across Okta and Microsoft Entra ID, guest UPN translation, and offboarding ticket workflows.

---

## ⚡ Quick Start: Launching in GitHub Codespaces

You can run EvO directly in your browser without installing anything locally using GitHub Codespaces.

### Step 1: Open the Codespace
1. From the root of the repository (`code-of-cabuco`), click the green **`<> Code`** button near the top right.
2. Select the **`Codespaces`** tab.
3. Click the **`...`** (three dots) next to the `+` button and select **`New with options...`**
4. Under **Dev container configuration**, select **`Entra Vs. Okta Suite (EvO)`**.
5. Click **Create codespace**.

---

### Step 2: What to Expect & Navigating Pop-ups

* **⏳ Loading Time:** The initial build takes **1 to 3 minutes**. GitHub is spinning up a cloud container, updating system dependencies, and installing Python packages (`streamlit`, `pandas`, `requests`).
* **🛡️ Security / Trust Prompt:** If VS Code in the browser asks *"Do you trust the authors of the files in this folder?"*, click **Yes, I trust the authors**.
* **🌐 Browser Pop-up Blocker / Auto-Open:** Once the app is healthy, Codespaces will attempt to automatically open the web app on port **8501** in a new browser tab or preview frame. 
  * If your browser blocks pop-ups, you will see a small banner in the bottom-right corner saying *"Your application running on port 8501 is available."* Click **Open in Browser**.

---

### Step 3: Manual Launch via Ports Tab (If the App Doesn't Open)

If a pop-up blocker prevents auto-opening or if you closed the tab, you can manually open the app at any time:

1. In the bottom pane of the Codespaces VS Code window, click on the **`Ports`** tab (next to *Terminal*).
2. Locate **Port `8501`** (labeled `Entra Vs. Okta Suite (EvO) Web App`).
3. Hover over the address in the **Forwarded Address** column and click the **`🌐 Open in Browser`** globe icon (or right-click and select *Open in Browser*).

> **Note:** Streamlit takes ~5–10 seconds to compile its interface on first load. If you see a blank page initially, give it a moment to render.

---

## 🧪 Execution Modes

- **🧪 Demo / Mock Data Mode (Default):** Pre-populates the app with sample Okta directory records so reviewers can test mapping, reconciliation, and offboarding workflows immediately without API keys.
- **⚡ Live Okta API Connection:** Connects via a Read-Only SSWS token to stream user directory profiles and group rosters directly from an active Okta org.
- **📁 Upload / Paste CSV File:** Allows manual uploading or pasting of raw exported Okta CSV files.

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
