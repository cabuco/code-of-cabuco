#!/usr/bin/env python3
"""Rosetta - Slack export (.zip) -> readable PDFs. Streamlit UI.

The heavy lifting happens in converter.py, launched as a separate background process,
so large conversions survive browser disconnects and never block the UI.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile
from datetime import date, datetime
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from converter import scan

REPO = HERE.parents[2]  # Navigates to repository root from ai-scripts/slack/rosetta
INPUT_DIR = HERE / "input"
OUTPUT_DIR = HERE / "output"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_BROWSER_DOWNLOAD_MB = 500

st.set_page_config(page_title="Rosetta - Slack Export PDF Converter", page_icon="📜", layout="centered")
st.title("📜 Rosetta")
st.caption("Turn an official Slack export .zip into readable PDFs with real names instead of IDs.")
st.info(
    "🔒 Everything runs inside **your isolated environment** — nothing is sent anywhere else. "
    "Your export and the generated PDFs stay on disk until you remove them "
    "(see **Clean up** at the bottom, or delete the environment when finished)."
)

# ----------------------------------------------------------------------------- helpers
def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024

def find_zips():
    seen = {}
    for d in (INPUT_DIR, REPO, HERE):
        for p in d.glob("*.zip"):
            seen[p.resolve()] = p
    return sorted(seen, key=lambda p: p.stat().st_mtime, reverse=True)

def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False

@st.cache_resource
def engine_error():
    """None if WeasyPrint works, else the error text."""
    try:
        from weasyprint import HTML
        HTML(string="<p>self-test</p>").write_pdf()
        return None
    except Exception as e:
        return f"{type(e).__name__}: {e}"

@st.cache_data(show_spinner="Reading archive index...")
def cached_scan(path, mtime, size):
    return scan(path)

def tail(path, n=15):
    try:
        return "\n".join(Path(path).read_text(errors="replace").splitlines()[-n:])
    except OSError:
        return ""

def show_job(job: Path):
    sp = job / "status.json"
    try:
        s = json.loads(sp.read_text())
    except (OSError, ValueError):
        s = {"state": "starting"}
    state = s.get("state")

    if state in ("starting", "running"):
        if state == "running" and not pid_alive(s.get("pid")):
            st.error("The conversion process stopped unexpectedly.")
            st.code(tail(job / "converter.log") or "(no log)")
            return
        total, done = s.get("total") or 0, s.get("done") or 0
        st.progress(done / total if total else 0.0,
                    text=f"{done}/{total} day-files · {s.get('pdfs', 0)} PDFs · {s.get('current', '')}")
        st.caption("Large exports can take time. Keep this tab open while processing.")
        if st.button("Cancel conversion") and s.get("pid"):
            try:
                os.kill(int(s["pid"]), signal.SIGTERM)
            except OSError:
                pass
        time.sleep(2)
        st.rerun()
    elif state == "done":
        st.success(f"Done: {s['pdf_count']} PDF file(s), {s['error_count']} error(s), "
                   f"{s['unresolved']} ID(s) could not be resolved.")
        zip_path = Path(s["zip"])
        st.write(f"Output folder: `{job}/pdf`")
        if zip_path.exists():
            size = zip_path.stat().st_size
            if size <= MAX_BROWSER_DOWNLOAD_MB * 1024 * 1024:
                with open(zip_path, "rb") as f:
                    st.download_button(f"📥 Download all PDFs ({human(size)})", f,
                                       file_name=zip_path.name, mime="application/zip")
            else:
                st.warning(f"Result is {human(size)} — download directly from the file explorer.")
        report = job / "report.txt"
        if report.exists():
            with st.expander("Conversion report"):
                st.code(report.read_text(errors="replace")[:20000])
    elif state == "cancelled":
        st.warning("Conversion cancelled. PDFs written so far are in the output folder.")
    else:
        st.error(s.get("error", "Unknown error"))
        st.code(tail(job / "converter.log") or "(no log)")

# ----------------------------------------------------------------------------- health check
err = engine_error()
if err:
    st.error("PDF engine (WeasyPrint) is not working in this environment.")
    st.code(err)
    st.markdown("Fix: Open a terminal and run `bash ai-scripts/slack/rosetta/setup.sh`, then `bash ai-scripts/slack/rosetta/start.sh`.")
    st.stop()

if "job" not in st.session_state:
    for sp in sorted(OUTPUT_DIR.glob("*/status.json"), reverse=True):
        try:
            if json.loads(sp.read_text()).get("state") == "running":
                st.session_state["job"] = str(sp.parent)
                break
        except (OSError, ValueError):
            pass

if st.session_state.get("job"):
    st.subheader("Conversion status")
    show_job(Path(st.session_state["job"]))
    if st.button("Start a new conversion"):
        del st.session_state["job"]
        st.rerun()
    st.divider()

# ----------------------------------------------------------------------------- step 1: choose file
st.subheader("1 · Choose your Slack export")
st.markdown(
    "Drag your Slack export **.zip** into the **`ai-scripts/slack/rosetta/input`** folder in the Explorer panel, "
    "then click **Refresh list**."
)
zips = find_zips()
if st.button("🔄 Refresh list"):
    st.rerun()
zip_path = None
if zips:
    zip_path = st.selectbox("Detected archives", zips,
                            format_func=lambda p: f"{p.name}  ({human(p.stat().st_size)})")
else:
    st.warning("No .zip files found yet. Place one in `ai-scripts/slack/rosetta/input` and click Refresh list.")

if not zip_path:
    st.stop()

# ----------------------------------------------------------------------------- step 2: options
try:
    info = cached_scan(str(zip_path), zip_path.stat().st_mtime, zip_path.stat().st_size)
except zipfile.BadZipFile:
    st.error("This file is not a valid .zip archive.")
    st.stop()
except Exception as e:
    st.error(f"Could not read the archive: {type(e).__name__}: {e}")
    st.stop()

rows = info["conversations"]
if not rows:
    st.error("No message files found. Expected folders containing files named like `2024-01-31.json`.")
    st.stop()

st.success(f"Found {len(rows)} conversations and {info['users']} users in `{zip_path.name}`.")
if not info["has_users_json"]:
    st.warning("No users.json found — names can only be resolved where messages carry profile info.")

st.subheader("2 · Options")
labels = {r["folder"]: f"{r['label']}  ({r['days']} days, {r['first']} → {r['last']})" for r in rows}
all_folders = [r["folder"] for r in rows]
if st.checkbox("Convert all conversations", value=True):
    selected = all_folders
else:
    selected = st.multiselect("Conversations", all_folders, format_func=labels.get)

date_from = date_to = None
if st.checkbox("Limit date range"):
    lo, hi = date.fromisoformat(min(r["first"] for r in rows)), date.fromisoformat(max(r["last"] for r in rows))
    c1, c2 = st.columns(2)
    date_from = c1.date_input("From", value=lo, min_value=lo, max_value=hi)
    date_to = c2.date_input("To", value=hi, min_value=lo, max_value=hi)

chunk = st.select_slider("Max messages per PDF file (larger conversations are split into parts)",
                         options=[500, 1000, 2000, 5000, 10000], value=2000)

# ----------------------------------------------------------------------------- step 3: run
st.subheader("3 · Convert")
if st.button("Translate archive to PDF", type="primary", disabled=not selected):
    job = OUTPUT_DIR / f"{zip_path.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    job.mkdir(parents=True)
    (job / "selection.json").write_text(json.dumps(selected))
    (job / "status.json").write_text(json.dumps({"state": "starting"}))
    cmd = [sys.executable, str(HERE / "converter.py"), str(zip_path), "--out", str(job),
           "--chunk", str(chunk), "--only-file", str(job / "selection.json")]
    if date_from:
        cmd += ["--from", date_from.isoformat(), "--to", date_to.isoformat()]
    log = open(job / "converter.log", "w")
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=str(HERE), start_new_session=True)
    threading.Thread(target=proc.wait, daemon=True).start()
    st.session_state["job"] = str(job)
    st.rerun()

# ----------------------------------------------------------------------------- cleanup
with st.expander("🧹 Clean up"):
    st.caption("Deletes exports in `input` and all results in `output`.")
    if st.checkbox("Yes, delete them") and st.button("Delete now"):
        for d in (INPUT_DIR, OUTPUT_DIR):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(exist_ok=True)
        st.session_state.pop("job", None)
        st.success("Deleted.")
