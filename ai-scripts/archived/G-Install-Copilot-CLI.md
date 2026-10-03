# 🚀 GitHub Copilot CLI: One-Click Self-Healing Setup

This repository provides a "foolproof" installation script for the **GitHub Copilot CLI** on macOS. It is specifically designed for users who are not tech-savvy or those who have had previous installations fail.

## 🛠️ What This Script Does
Unlike a standard installation, this script is **self-healing**. It performs the following steps automatically:
1. **Detects Hardware:** Automatically configures paths for both Intel and Apple Silicon (M1/M2/M3) Macs.
2. **Environment Check:** Installs **Homebrew** (the Mac package manager) if it’s missing.
3. **Dependency Management:** Installs and updates the **GitHub CLI (`gh`)** and **Copilot CLI**.
4. **Self-Repair Loop:** If the installation fails or authentication is missing, it automatically attempts to repair the connection and re-tests up to 3 times.
5. **Interactive Login:** Triggers the official GitHub browser-based login flow to ensure your account is linked correctly.

---

## 💻 How to Run the Setup

1. Open your **Terminal** (Press `Command + Space`, type `Terminal`, and hit `Enter`).
2. **Copy and paste** the following block of code entirely into the Terminal window and press `Enter`:

```bash
clear; echo "🔄 Initializing Self-Healing Setup..."; \
setup_copilot() {
    # Fix Homebrew Pathing
    if [[ -f /opt/homebrew/bin/brew ]]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
    if [[ -f /usr/local/bin/brew ]]; then eval "$(/usr/local/bin/brew shellenv)"; fi
    
    # Install/Update Core Tools
    if ! command -v brew &> /dev/null; then
        echo "📦 Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL [https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh](https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh))"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo "📦 Installing/Updating GitHub CLI and Copilot..."
    brew install gh copilot-cli
    
    # Self-Test & Repair Loop
    for i in {1..3}; do
        echo "🧪 Testing Installation (Attempt $i)..."
        # Check if command exists AND if user is logged into gh
        if command -v copilot &> /dev/null && gh auth status &> /dev/null; then
            echo "✅ SUCCESS: Copilot is active and authenticated."; return 0
        else
            echo "🔧 Issues detected. Re-authenticating..."
            gh auth login -w -h github.com -s copilot
            copilot auth login
        fi
    done
}; setup_copilot
```

---

To test it, in terminal you'd run...

copilot -i "your question here"
