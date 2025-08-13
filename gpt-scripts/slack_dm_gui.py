#!/usr/bin/env python3
import os
import json
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import webbrowser
import tempfile
import shutil

# ---------------- Helper Functions ---------------- #
def format_timestamp(ts):
    try:
        dt = datetime.utcfromtimestamp(float(ts))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return "Unknown time"

def load_users_from_dir(export_dir):
    # Try to locate users.json in any folder inside the extracted export
    for root, dirs, files in os.walk(export_dir):
        if "users.json" in files:
            users_path = os.path.join(root, "users.json")
            with open(users_path, "r", encoding="utf8") as f:
                users_list = json.load(f)
            return {u.get("id", ""): (u.get("real_name") or u.get("name") or "Unknown User") for u in users_list}
    return {}

def parse_dm_folders(export_dir, users):
    # Only consider folders (ignore top-level JSONs)
    dm_folders = [os.path.join(export_dir, f) for f in os.listdir(export_dir)
                  if os.path.isdir(os.path.join(export_dir, f))]
    all_messages = []

    for dm_path in sorted(dm_folders):
        conversation_name = os.path.basename(dm_path)
        messages = []

        for file in sorted(os.listdir(dm_path)):
            if file.endswith(".json"):
                file_path = os.path.join(dm_path, file)
                try:
                    with open(file_path, "r", encoding="utf8") as f:
                        day_msgs = json.load(f)
                        messages.extend(day_msgs)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

        messages.sort(key=lambda m: float(m.get("ts", 0)))
        all_messages.append((conversation_name, messages))
    return all_messages

def generate_html(all_messages, users, output_file):
    html = [
        '<html><head><title>Slack DM Report</title>',
        '<style>',
        'body {font-family: Arial, sans-serif; background: #f7f7f7; padding: 20px;}',
        'h1, h2 {color: #333;}',
        '.chat {background: white; border: 1px solid #ccc; padding: 10px; margin-bottom: 40px; border-radius: 5px;}',
        '.message {margin-bottom: 12px;}',
        '.timestamp {color: #999; font-size: 0.85em; margin-right: 10px;}',
        '.user {font-weight: 600; margin-right: 5px;}',
        '</style></head><body>'
    ]
    html.append("<h1>Slack DM Export Report</h1>")

    for conversation_name, messages in all_messages:
        html.append(f"<h2>Conversation: {conversation_name}</h2>")
        html.append("<div class='chat'>")
        for msg in messages:
            user_id = msg.get("user") or msg.get("bot_id") or "Unknown"
            user_name = users.get(user_id, user_id)
            text = msg.get("text", "").replace('\n', '<br>')
            ts = format_timestamp(msg.get("ts", "0"))
            html.append(f"<div class='message'><span class='timestamp'>{ts}</span> "
                        f"<span class='user'>{user_name}:</span> {text}</div>")
        html.append("</div>")

    html.append("</body></html>")

    with open(output_file, "w", encoding="utf8") as f:
        f.write("\n".join(html))

# ---------------- GUI ---------------- #
class SlackDMConverterGUI:
    def __init__(self, root):
        self.root = root
        root.title("Slack DM Converter")
        root.geometry("450x150")

        self.label = tk.Label(root, text="Select a Slack DM export ZIP to convert:")
        self.label.pack(pady=10)

        self.select_button = tk.Button(root, text="Choose ZIP", command=self.select_zip)
        self.select_button.pack(pady=5)

        self.convert_button = tk.Button(root, text="Convert to HTML", command=self.convert_zip, state=tk.DISABLED)
        self.convert_button.pack(pady=10)

        self.zip_path = None

    def select_zip(self):
        self.zip_path = filedialog.askopenfilename(title="Select Slack DM ZIP", filetypes=[("ZIP files", "*.zip")])
        if self.zip_path:
            self.convert_button.config(state=tk.NORMAL)

    def convert_zip(self):
        if not self.zip_path:
            messagebox.showerror("Error", "No ZIP file selected.")
            return

        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(self.zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract ZIP: {e}")
            shutil.rmtree(temp_dir)
            return

        users = load_users_from_dir(temp_dir)
        if not users:
            messagebox.showerror("Error", "users.json not found in the export!")
            shutil.rmtree(temp_dir)
            return

        all_messages = parse_dm_folders(temp_dir, users)

        output_file = os.path.join(os.path.dirname(self.zip_path), "slack_dm_report.html")
        generate_html(all_messages, users, output_file)

        shutil.rmtree(temp_dir)
        messagebox.showinfo("Success", f"Report generated:\n{output_file}")
        webbrowser.open(f"file://{output_file}")

# ---------------- Run App ---------------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = SlackDMConverterGUI(root)
    root.mainloop()
