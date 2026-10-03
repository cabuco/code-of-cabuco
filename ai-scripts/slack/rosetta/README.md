# 📜 Rosetta — Slack Export PDF Converter

Rosetta converts official, unstructured Slack export `.zip` archives into clean, human-readable PDF reports for Legal, HR, and compliance investigations.

---

## ✨ Features

- **Identity Resolution:** Resolves raw Slack user IDs, channel IDs, DMs, group DMs, bots, and deactivated accounts into real display names.
- **Large Export Support:** Streams archives day-by-day to prevent memory crashes, splitting large conversations into manageable PDF parts.
- **Privacy-First Architecture:** Operates entirely inside an isolated container with zero external data transmission.
- **Interactive UI:** Built with Streamlit to let users filter by specific conversations or date ranges.

---

## 🚀 Usage

1. Place your Slack export `.zip` archive inside the `ai-scripts/slack/rosetta/input/` directory.
2. Launch the application UI or refresh the archive list.
3. Select conversations, configure date filters and message caps per PDF, and click **Translate archive to PDF**.
4. Download the compiled PDF archive or review generated execution reports inside `ai-scripts/slack/rosetta/output/`.
