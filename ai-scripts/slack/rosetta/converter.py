#!/usr/bin/env python3
"""
Rosetta conversion engine: Slack export .zip -> readable PDFs.
"""
import argparse
import html
import json
import os
import re
import signal
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DAY_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
TOKEN = re.compile(r"<([^<>]+)>")
SYSTEM_SUBTYPES = {
    "channel_join", "channel_leave", "channel_topic", "channel_purpose", "channel_name",
    "channel_archive", "channel_unarchive", "group_join", "group_leave", "group_topic",
    "group_purpose", "group_name", "group_archive", "group_unarchive", "pinned_item",
    "unpinned_item", "reminder_add", "reminder_delete",
}

CSS = """
@page { size: A4; margin: 1.8cm 1.6cm 2cm;
        @bottom-right { content: counter(page) " / " counter(pages); font-size: 8pt; color: #888; } }
body { font-family: "DejaVu Sans", "Noto Sans", sans-serif; color: #111; font-size: 9pt; line-height: 1.4; }
h1 { font-size: 17pt; border-bottom: 2px solid #222; padding-bottom: 6px; margin: 0 0 4px; }
.range { color: #666; font-size: 8.5pt; margin: 0 0 14px; }
h3 { font-size: 10pt; color: #1264a3; margin: 18px 0 6px; border-bottom: 1px solid #e0e0e0;
     padding-bottom: 3px; break-after: avoid; }
.msg { margin: 0 0 7px; padding-bottom: 5px; border-bottom: 1px solid #f1f1f1; break-inside: avoid; }
.msg.reply { margin-left: 18px; border-left: 2px solid #d0d7de; padding-left: 8px; }
.msg.sys { color: #777; font-style: italic; }
.meta { font-weight: bold; font-size: 9pt; }
.ts { font-weight: normal; color: #777; font-size: 7.5pt; margin-left: 8px; }
.text { margin-top: 2px; white-space: pre-wrap; overflow-wrap: anywhere; }
.mention { color: #1264a3; background: #e8f1fa; }
.extra { margin-top: 2px; font-size: 8pt; color: #555; overflow-wrap: anywhere; }
"""

def _clean(names):
    return [n for n in names
            if not n.startswith("__MACOSX/") and not Path(n).name.startswith("._") and not n.endswith("/")]

def _load_json(z, name):
    try:
        return json.loads(z.read(name).decode("utf-8"))
    except Exception:
        return None

def load_metadata(z, names):
    meta = {k: [] for k in ("users", "channels", "groups", "dms", "mpims")}
    for n in names:
        base = Path(n).name
        key = base[:-5] if base.endswith(".json") else None
        if key in meta:
            data = _load_json(z, n)
            if isinstance(data, list):
                meta[key].extend(d for d in data if isinstance(d, dict))
    return meta

def build_user_map(users):
    m = {"USLACKBOT": "Slackbot (Bot)"}
    for u in users:
        uid = u.get("id")
        if not uid:
            continue
        p = u.get("profile") or {}
        name = (u.get("real_name") or p.get("real_name") or p.get("display_name")
                or u.get("name") or f"User {uid}")
        if u.get("deleted"):
            tag = " (Deactivated)"
        elif u.get("is_bot") or uid == "USLACKBOT":
            tag = " (Bot)"
        else:
            tag = ""
        m[uid] = f"{name}{tag}"
    return m

def build_labels(meta, user_map):
    labels, chan_names = {}, {}
    for kind, prefix in (("channels", "#"), ("groups", "Private: #")):
        for c in meta[kind]:
            name = c.get("name") or c.get("id")
            if name:
                labels[name] = f"{prefix}{name}"
                if c.get("id"):
                    chan_names[c["id"]] = name
    for d in meta["dms"]:
        if d.get("id"):
            members = ", ".join(user_map.get(m, m) for m in d.get("members", []))
            labels[d["id"]] = f"DM: {members}" if members else f"DM {d['id']}"
    for g in meta["mpims"]:
        members = ", ".join(user_map.get(m, m) for m in g.get("members", []))
        lab = f"Group DM: {members}" if members else f"Group DM {g.get('name') or g.get('id')}"
        for key in (g.get("name"), g.get("id")):
            if key:
                labels[key] = lab
    return labels, chan_names

def group_day_files(names):
    groups = {}
    for n in names:
        parts = n.split("/")
        if len(parts) >= 2 and DAY_FILE.match(parts[-1]):
            groups.setdefault(parts[-2], []).append((parts[-1][:-5], n))
    for v in groups.values():
        v.sort()
    return groups

def scan(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        names = _clean(z.namelist())
        meta = load_metadata(z, names)
    users = build_user_map(meta["users"])
    labels, _ = build_labels(meta, users)
    rows = []
    for folder, files in group_day_files(names).items():
        rows.append({"folder": folder, "label": labels.get(folder, folder), "days": len(files),
                     "first": files[0][0], "last": files[-1][0]})
    rows.sort(key=lambda r: r["label"].lower())
    return {"conversations": rows, "users": len(meta["users"]), "has_users_json": bool(meta["users"])}

class Ctx:
    def __init__(self, users, chans):
        self.users, self.chans, self.unresolved = users, chans, set()

def _esc(s):
    return html.escape(html.unescape(str(s)))

def _token(tok, ctx):
    target, _, label = tok.partition("|")
    if target.startswith("@"):
        uid = target[1:]
        name = label or ctx.users.get(uid)
        if not name:
            ctx.unresolved.add(uid)
            name = f"Unknown user ({uid})"
        return f'<span class="mention">@{_esc(name.lstrip("@"))}</span>'
    if target.startswith("#"):
        cid = target[1:]
        return f'<span class="mention">#{_esc(label or ctx.chans.get(cid) or cid)}</span>'
    if target.startswith("!"):
        base = target[1:].split("^")[0]
        if label:
            return _esc(label)
        return "@" + ("user-group" if base == "subteam" else _esc(base))
    if label and label != target:
        return _esc(f"{label} ({target})")
    return _esc(target)

def render_text(text, ctx):
    out, pos = [], 0
    for m in TOKEN.finditer(text):
        out.append(_esc(text[pos:m.start()]))
        out.append(_token(m.group(1), ctx))
        pos = m.end()
    out.append(_esc(text[pos:]))
    return "".join(out)

def speaker(msg, ctx):
    uid = msg.get("user")
    prof = msg.get("user_profile") or {}
    bot_name = (msg.get("bot_profile") or {}).get("name") or msg.get("username")
    bid = msg.get("bot_id")
    if uid:
        if uid in ctx.users:
            return ctx.users[uid]
        n = prof.get("real_name") or prof.get("display_name")
        if n:
            ctx.users[uid] = n
            return n
        if not bot_name:
            ctx.unresolved.add(uid)
            return f"Unknown user ({uid})"
    if bid and bid in ctx.users:
        return ctx.users[bid]
    if bot_name:
        label = f"{bot_name} (Bot)"
        if bid:
            ctx.users[bid] = label
        return label
    if bid:
        ctx.unresolved.add(bid)
        return f"Unknown bot ({bid})"
    return "Unknown sender"

def _ts(msg):
    try:
        return float(msg.get("ts") or 0)
    except (TypeError, ValueError):
        return 0.0

def render_message(msg, ctx):
    ts = _ts(msg)
    name = _esc(speaker(msg, ctx))
    when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S UTC")
    if msg.get("edited"):
        when += " (edited)"
    is_reply = bool(msg.get("thread_ts")) and msg.get("thread_ts") != msg.get("ts")
    classes = "msg" + (" reply" if is_reply else "") + (" sys" if msg.get("subtype") in SYSTEM_SUBTYPES else "")
    raw = msg.get("text") or ""
    extras = []
    for f in msg.get("files") or []:
        if isinstance(f, dict):
            extras.append("[File] " + _esc(f.get("title") or f.get("name") or "unnamed file"))
    for a in msg.get("attachments") or []:
        if isinstance(a, dict):
            t = str(a.get("title") or a.get("fallback") or a.get("text") or "")
            if t and t not in raw:
                extras.append("[Attachment] " + render_text(t[:500], ctx))
    rx = [f":{r.get('name')}: x{r.get('count', 1)}" for r in msg.get("reactions") or [] if isinstance(r, dict)]
    if rx:
        extras.append("Reactions: " + _esc(", ".join(rx)))
    if msg.get("reply_count") and not is_reply:
        extras.append(f"{_esc(msg['reply_count'])} replies in thread")
    body = render_text(raw, ctx)
    if not body and not extras:
        body = "<i>[no text]</i>"
    parts = [f'<div class="{classes}"><div class="meta">{name}<span class="ts">{when}</span></div>']
    if body:
        parts.append(f'<div class="text">{body}</div>')
    parts.extend(f'<div class="extra">{e}</div>' for e in extras)
    parts.append("</div>")
    return "".join(parts)

def _write_pdf(body, path):
    from weasyprint import HTML
    doc = ('<!doctype html><html><head><meta charset="utf-8"><style>' + CSS +
           "</style></head><body>" + body + "</body></html>")
    HTML(string=doc).write_pdf(str(path))

def _safe(label):
    return re.sub(r"[^\w.\-]+", "_", label).strip("_")[:80] or "conversation"

class ConvWriter:
    def __init__(self, label, stem, pdf_dir, chunk, ctx):
        self.label, self.stem, self.pdf_dir, self.chunk, self.ctx = label, stem, pdf_dir, chunk, ctx
        self.parts = []
        self._reset()

    def _reset(self):
        self.html, self.count, self.day, self.first, self.last = [], 0, None, None, None

    def add(self, msg):
        day = datetime.fromtimestamp(_ts(msg), tz=timezone.utc).strftime("%Y-%m-%d (%A)")
        if day != self.day:
            self.html.append(f"<h3>{day}</h3>")
            self.day = day
        self.first = self.first or day
        self.last = day
        self.html.append(render_message(msg, self.ctx))
        self.count += 1
        if self.count >= self.chunk:
            self.flush()

    def flush(self):
        if not self.count:
            return
        n = len(self.parts) + 1
        path = self.pdf_dir / f"{self.stem}__part{n:03d}.pdf"
        suffix = f" (part {n})" if n > 1 else ""
        head = (f"<h1>{_esc(self.label)}{suffix}</h1>"
                f'<p class="range">{_esc(self.first)} &rarr; {_esc(self.last)} &middot; {self.count} messages</p>')
        _write_pdf(head + "".join(self.html), path)
        self.parts.append(path)
        self._reset()

    def finish(self):
        self.flush()
        if len(self.parts) == 1:
            final = self.pdf_dir / f"{self.stem}.pdf"
            self.parts[0].replace(final)
            self.parts = [final]
        return self.parts

def convert(zip_path, out_dir, chunk=2000, only=None, date_from=None, date_to=None, on_progress=None):
    import weasyprint

    out_dir = Path(out_dir)
    pdf_dir = out_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdfs, errors, used = [], [], set()

    with zipfile.ZipFile(zip_path) as z:
        names = _clean(z.namelist())
        meta = load_metadata(z, names)
        users = build_user_map(meta["users"])
        labels, chans = build_labels(meta, users)
        ctx = Ctx(users, chans)

        selected = {}
        for folder, files in group_day_files(names).items():
            if only is not None and folder not in only:
                continue
            files = [(d, n) for d, n in files
                     if (not date_from or d >= date_from) and (not date_to or d <= date_to)]
            if files:
                selected[folder] = files

        total = sum(len(v) for v in selected.values())
        done = 0
        for folder in sorted(selected, key=lambda f: labels.get(f, f).lower()):
            label = labels.get(folder, folder)
            stem, i = _safe(label), 2
            while stem in used:
                stem, i = f"{_safe(label)}_{i}", i + 1
            used.add(stem)
            writer = ConvWriter(label, stem, pdf_dir, chunk, ctx)
            try:
                for _, member in selected[folder]:
                    data = _load_json(z, member)
                    if isinstance(data, list):
                        data = [m for m in data if isinstance(m, dict)]
                        data.sort(key=_ts)
                        for msg in data:
                            writer.add(msg)
                    else:
                        errors.append(f"Unreadable file: {member}")
                    done += 1
                    if on_progress:
                        on_progress(done, total, label, len(pdfs) + len(writer.parts))
                pdfs.extend(writer.finish())
            except Exception as e:
                errors.append(f"{label}: {type(e).__name__}: {e}")

    report = [f"Rosetta report for {Path(zip_path).name}",
              f"PDF files written: {len(pdfs)}",
              f"Errors: {len(errors)}",
              f"Unresolved IDs (not found in users.json or message metadata): {len(ctx.unresolved)}"]
    report += [f"  - {e}" for e in errors]
    report += ["Unresolved IDs: " + ", ".join(sorted(ctx.unresolved)[:300])] if ctx.unresolved else []
    (out_dir / "report.txt").write_text("\n".join(report), encoding="utf-8")

    zip_out = out_dir / f"{Path(zip_path).stem}_PDFs.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_STORED, allowZip64=True) as zo:
        for p in pdfs:
            zo.write(p, p.name)
        zo.write(out_dir / "report.txt", "report.txt")
    return {"pdf_count": len(pdfs), "error_count": len(errors), "unresolved": len(ctx.unresolved),
            "zip": str(zip_out)}

class Status:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {"state": "running", "pid": os.getpid(), "done": 0, "total": 0,
                     "current": "", "pdfs": 0, "started": time.time()}
        self._last = 0.0

    def update(self, force=False, **kw):
        self.data.update(kw)
        if force or time.time() - self._last > 0.5:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data))
            tmp.replace(self.path)
            self._last = time.time()

def main():
    ap = argparse.ArgumentParser(description="Slack export zip -> PDFs")
    ap.add_argument("zip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--only-file")
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    status = Status(out / "status.json")
    status.update(force=True)

    def _term(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _term)

    try:
        only = set(json.loads(Path(a.only_file).read_text())) if a.only_file else None
        result = convert(a.zip, out, a.chunk, only, a.date_from, a.date_to,
                         on_progress=lambda d, t, c, p: status.update(done=d, total=t, current=c, pdfs=p))
        status.update(force=True, state="done", finished=time.time(), **result)
    except KeyboardInterrupt:
        status.update(force=True, state="cancelled")
    except Exception as e:
        traceback.print_exc()
        status.update(force=True, state="error", error=f"{type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
