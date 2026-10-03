# 📜 Rosetta — Slack Export PDF Converter

Rosetta converts official, unstructured Slack export `.zip` archives into clean, human-readable PDF reports for Legal, HR, and compliance investigations.

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
