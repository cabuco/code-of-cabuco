# 📜 Rosetta — Slack Export PDF Converter

Rosetta converts official, unstructured Slack export `.zip` archives into clean, human-readable PDF reports for Legal, HR, and compliance investigations.

---

## ⚡ Quick Start: Launching in GitHub Codespaces

You can run Rosetta directly in your browser without installing system libraries locally using GitHub Codespaces.

### Step 1: Open the Codespace
1. From the root of the repository (`code-of-cabuco`), click the green **`<> Code`** button near the top right.
2. Select the **`Codespaces`** tab.
3. Click the **`...`** (three dots) next to the `+` button and select **`New with options...`**
4. Under **Dev container configuration**, select **`Rosetta — Slack Export PDF Converter`**.
5. Click **Create codespace**.

---

### Step 2: What to Expect & Navigating Pop-ups

* **⏳ Loading Time:** The initial container build takes **2 to 4 minutes**. GitHub is installing required C-libraries (`pango`, `harfbuzz`, fonts) and Python PDF components (`weasyprint`) via `setup.sh`.
* **🛡️ Security / Trust Prompt:** If VS Code in the browser asks *"Do you trust the authors of the files in this folder?"*, click **Yes, I trust the authors**.
* **🌐 Browser Pop-up Blocker / Auto-Open:** Once the environment passes its WeasyPrint health check, Codespaces will attempt to automatically open the web app on port **8080** in a new browser tab.
  * If your browser blocks pop-ups, look for a small toast notification in the bottom-right corner saying *"Your application running on port 8080 is available."* Click **Open in Browser**.

---

### Step 3: Manual Launch via Ports Tab (If the App Doesn't Open)

If a pop-up blocker prevents auto-opening or if you closed the tab, you can manually open the interface at any time:

1. In the bottom pane of the Codespaces VS Code window, click on the **`Ports`** tab (next to *Terminal*).
2. Locate **Port `8080`** (labeled `Rosetta Web App`).
3. Hover over the link in the **Forwarded Address** column and click the **`🌐 Open in Browser`** globe icon (or right-click and select *Open in Browser*).

> **Note:** Streamlit takes ~5–10 seconds to render its interface on initial launch. If the tab appears blank initially, give it a moment to load.

---

## ✨ Features

- **🧪 Built-in Demo Mode:** Generates a sample export archive (`Sample_Slack_Export_Demo.zip`) in memory so you can immediately test PDF conversion without providing a real Slack export.
- **Identity Resolution:** Resolves raw Slack user IDs, channel IDs, DMs, group DMs, bots, and deactivated accounts into real display names.
- **Large Export Support:** Streams archives day-by-day to prevent memory crashes, splitting large conversations into manageable PDF parts.
- **Privacy-First Architecture:** Operates entirely inside an isolated container with zero external data transmission.
- **Interactive UI:** Built with Streamlit to let users filter by specific conversations or date ranges.

---

## 🚀 Usage

### Option A: Demo Mode (Quick Test)
1. Select **🧪 Demo / Sample Export Mode** in the left sidebar.
2. Select `Sample_Slack_Export_Demo.zip` from the dropdown.
3. Click **Translate archive to PDF** to test rendering and download the resulting sample PDFs.

### Option B: Custom Slack Export
1. Select **📁 Local Upload / Folder Archive** in the left sidebar.
2. Place your Slack export `.zip` archive inside the `ai-scripts/slack/rosetta/input/` directory.
3. Refresh the archive list, select conversations, set date filters or page chunks, and click **Translate archive to PDF**.
4. Download the compiled PDF archive or review generated execution reports inside `ai-scripts/slack/rosetta/output/`.
