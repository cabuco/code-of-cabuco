# Slack DM Converter (Created with GPT)

**Slack DM Converter** is a cross-platform Python application that allows you to convert Slack direct message (DM) exports from a `.zip` file into a single, readable HTML report. It automatically resolves user IDs to display names, sorts messages chronologically, and can be run with a simple drag-and-drop GUI.

---

## Features

- Converts Slack DM exports from `.zip` into **HTML reports**.
- Automatically resolves Slack user IDs to display names.
- Maintains chronological order of messages with timestamps.
- Supports multiple DM conversations in a single export.
- Simple **drag-and-drop GUI**—no terminal commands required.
- Fully standalone if packaged via PyInstaller (macOS, Windows, Linux).

---

## Requirements

- Python 3.7 or higher
- Standard Python libraries: `os`, `json`, `zipfile`, `datetime`, `tkinter`, `webbrowser`, `tempfile`, `shutil`
- No external dependencies required.

> **Optional:** You can package the app as a standalone executable using [PyInstaller](https://www.pyinstaller.org/) for cross-platform distribution.

---

## Installation

1. **Clone or download** the project repository:

`git clone <your-repo-url>`
`cd slack-dm-converter`

2. **Run directly with Python**:

`python3 slack_dm_converter.py`

3. **Optional:** Build a standalone executable for macOS:

`pyinstaller --onefile --windowed slack_dm_converter.py`

The resulting executable will be located in the `dist/` folder.

---

## Usage

1. Launch the app:

`python3 slack_dm_converter.py`

or, if using the standalone app, double-click the executable.

2. **Select your Slack DM export `.zip` file**:
   - The GUI will prompt you to browse and choose the `.zip`.

3. Click **Convert to HTML**:
   - The app extracts the `.zip`, finds all DM JSON files, resolves user IDs, and generates a single HTML report.

4. **View the report**:
   - The HTML report opens automatically in your default web browser.
   - Output is saved next to the original `.zip` file as `slack_dm_report.html`.

---

## Directory Structure

Slack DM export `.zip` files can vary in structure. The converter automatically searches for:

- `users.json` (anywhere inside the extracted folders)
- DM folders containing `*.json` files for messages

**Example export contents:**
