
#!/usr/bin/env python3
import pandas as pd
import os

# --- Validate inputs ---
required = ["FTE.csv", "groups.csv", "members.csv"]
missing = [f for f in required if not os.path.exists(f)]
if missing:
    raise FileNotFoundError(f"Missing files: {', '.join(missing)}")

# --- Load FTEs (prefer 'profile.email' if present; else use first column) ---
fte_df = pd.read_csv("FTE.csv")
fte_col = "profile.email" if "profile.email" in fte_df.columns else fte_df.columns[0]
fte_emails = set(str(e).strip().lower() for e in fte_df[fte_col].dropna().astype(str))

# --- Load groups & members ---
groups_df = pd.read_csv("groups.csv")
members_df = pd.read_csv("members.csv")

def norm(s): return str(s).strip().lower()

# --- Groups: expect email,name,(aliases optional) ---
for col in ("email", "name"):
    if col not in groups_df.columns:
        raise ValueError("groups.csv must contain 'email' and 'name' headers.")
groups_df["email_norm"] = groups_df["email"].apply(norm)
groups_df["name"] = groups_df["name"].astype(str)
groups_df["aliases"] = groups_df["aliases"] if "aliases" in groups_df.columns else ""

# --- Members: your headers are group,type,role,status,email ---
for col in ("group", "type", "role", "status", "email"):
    if col not in members_df.columns:
        raise ValueError("members.csv must contain headers: group,type,role,status,email")

members_df["groupEmail_norm"] = members_df["group"].apply(norm)
members_df["memberEmail_norm"] = members_df["email"].apply(norm)
members_df["role"] = members_df["role"].astype(str)
members_df["type"] = members_df["type"].astype(str)

rows = []

for _, g in groups_df.iterrows():
    g_name = g["name"]
    g_email = g["email"]
    g_aliases = g.get("aliases", "")
    g_key = g["email_norm"]

    # All memberships for this group
    g_members = members_df[members_df["groupEmail_norm"] == g_key]
    member_emails = sorted(set(g_members["memberEmail_norm"].tolist()))
    members_list = ";".join(member_emails)

    # Existing FTE owners (USER type)
    existing_fte_owners = [
        m["memberEmail_norm"]
        for _, m in g_members.iterrows()
        if m["role"].strip().upper() == "OWNER"
           and m["type"].strip().upper() == "USER"
           and m["memberEmail_norm"] in fte_emails
    ]

    # All FTE members (USER type)
    fte_members = [
        m["memberEmail_norm"]
        for _, m in g_members.iterrows()
        if m["type"].strip().upper() == "USER"
           and m["memberEmail_norm"] in fte_emails
    ]

    # Choose Owner 1/Owner 2: prefer existing FTE owners, then fill from other FTE members
    chosen = []
    for e in existing_fte_owners:
        if e not in chosen:
            chosen.append(e)
            if len(chosen) == 2:
                break
    if len(chosen) < 2:
        for e in fte_members:
            if e not in chosen:
                chosen.append(e)
                if len(chosen) == 2:
                    break

    # Status + flag reason
    if len(chosen) >= 2:
        status, reason = "OK", ""
    else:
        status = "FLAGGED"
        if len(fte_members) == 0:
            reason = "No FTE in group"
        elif len(fte_members) == 1:
            reason = "Only 1 FTE in group"
        elif g_members.empty:
            reason = "No members in group"
        else:
            reason = "Unable to assign 2 FTE owners"

    rows.append({
        "Google Group Display Name": g_name,
        "Google Group Email": g_email,
        "Google Group Aliases": g_aliases,
        "Google Group Members": members_list,
        "Owner 1": chosen[0] if len(chosen) > 0 else "",
        "Owner 2": chosen[1] if len(chosen) > 1 else "",
        "Status": status,
        "Flag Reason": reason
    })

## --- Output CSV ---
out = pd.DataFrame(rows)
cols = [
    "Google Group Display Name", "Google Group Email", "Google Group Aliases",
    "Google Group Members", "Owner 1", "Owner 2", "Status", "Flag Reason"
]
out = out[cols]
out.to_csv("group_fte_owner_audit.csv", index=False)
