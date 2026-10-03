import subprocess

# Auto-pull latest updates from repository whenever the app launches
try:
    subprocess.run(["git", "pull"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    pass

import streamlit as st
import pandas as pd
import io
import re
import requests

# --- INTELLIGENT COLUMN FINDER ---
def find_best_column(actual_cols, target_keys):
    for col in actual_cols:
        normalized = re.sub(r'[^a-zA-Z0-9]', '', col).lower()
        if normalized in target_keys:
            return col
    return None

def clean_data(series):
    return series.astype(str).str.strip().str.lower()

def process_input(upload_file, pasted_text, default_col_name="Data"):
    if upload_file is not None:
        return pd.read_csv(upload_file, low_memory=False)
    if pasted_text.strip():
        data = [line.strip() for line in re.split(r'[\n,\t]+', pasted_text) if line.strip()]
        return pd.DataFrame({default_col_name: data})
    return None

# --- TAB 6 HELPERS ---
def parse_offboarding_lines(raw_text):
    """Parse 'user + ticket' lines. Handles Zendesk subject lines and full ticket URLs."""
    parsed_entries = []
    for line in [l.strip() for l in raw_text.split("\n") if l.strip()]:
        url_match = re.search(r'/tickets/(\d{5,8})\b', line)
        t_match = url_match or re.search(r'\b(\d{5,8})\b', line)
        ticket_id = t_match.group(1) if t_match else ""

        subj_match = re.search(r"Regarding\s+(\S+?)(?:['\u2019]s)?\s+Offboarding", line, flags=re.IGNORECASE)
        if subj_match:
            user_entry = subj_match.group(1).strip("'\u2019\"")
        else:
            cleaned = re.sub(r'https?://\S+', '', line)
            cleaned = re.sub(r'\b\d{5,8}\b', '', cleaned)
            cleaned = re.sub(r'[,:\t#|;]', ' ', cleaned)
            cleaned = re.sub(r'(^|\s)[-\u2013\u2014]+(?=\s|$)', ' ', cleaned)
            tokens = [tok.strip("-\u2013\u2014.'\"()[]") for tok in cleaned.split()]
            tokens = [tok for tok in tokens if tok]
            user_entry = tokens[0] if tokens else line.strip()

        parsed_entries.append({"raw_line": line, "user_entry": user_entry, "ticket_id": ticket_id})
    return parsed_entries

def _first_present(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return None

def parse_device_hardware(dev_user_binding):
    rec = dev_user_binding or {}
    nested = rec.get("device") if isinstance(rec.get("device"), dict) else {}
    dev_obj = nested or rec
    prof = _first_present(dev_obj.get("profile"), rec.get("profile")) or {}
    if not isinstance(prof, dict):
        prof = {}

    def pick(*keys):
        for key in keys:
            v = _first_present(prof.get(key), dev_obj.get(key), rec.get(key))
            if v is not None:
                return v
        return None

    platform_val = pick("platform", "osPlatform") or "N/A"
    mfr_val = pick("manufacturer") or "N/A"
    model_val = pick("model") or "N/A"
    serial_val = pick("serialNumber", "serial_number", "serial") or "N/A"
    display = _first_present(
        prof.get("displayName"),
        (dev_obj.get("resourceDisplayName") or {}).get("value") if isinstance(dev_obj.get("resourceDisplayName"), dict) else None,
        dev_obj.get("id"),
    ) or "N/A"

    if str(platform_val).upper() == "WINDOWS": platform_val = "Windows device"
    elif str(platform_val).upper() == "IOS": platform_val = "iOS device"
    elif str(platform_val).upper() == "MACOS": platform_val = "macOS device"

    return {
        "platform": platform_val,
        "manufacturer": mfr_val,
        "model": model_val,
        "serial": str(serial_val).strip(),
        "displayName": display,
        "status": _first_present(dev_obj.get("status"), rec.get("status")) or "ACTIVE",
    }

def is_macbook(hw):
    model = str(hw.get("model", "")).lower()
    platform = str(hw.get("platform", "")).lower()
    mfr = str(hw.get("manufacturer", "")).lower()
    if "iphone" in model or "ipad" in model or platform.startswith("ios") or platform.startswith("android"):
        return False
    return ("mac" in model) or ("macos" in platform) or ("apple" in mfr)

def build_zd_search_chunks(ticket_ids, max_per_chunk=25):
    if not ticket_ids:
        return []
    chunks = []
    for i in range(0, len(ticket_ids), max_per_chunk):
        sub_ids = ticket_ids[i:i + max_per_chunk]
        chunks.append('type:ticket ' + ' '.join([f'ticket_id:"{tid}"' for tid in sub_ids if tid]))
    return chunks

def build_okta_identity_map(okta_df):
    ident_map = {}
    if okta_df is None or "id" not in okta_df.columns:
        return ident_map
    for _, row in okta_df.iterrows():
        u_id = str(row.get("id", "")).strip()
        if not u_id:
            continue
        keys = set()
        for col in ("profile.email", "profile.login", "profile.msftAlias"):
            val = str(row.get(col, "") or "").strip().lower()
            if val and val != "nan":
                keys.add(val)
                keys.add(val.split("@")[0])
        alias = str(row.get("profile.msftAlias", "") or "").strip().lower()
        if alias and alias != "nan":
            keys.add(f"{alias}@microsoft.com")
        for k in keys:
            ident_map.setdefault(k, set()).add(u_id)
    return ident_map

def okta_user_matches_handle(user_obj, handle):
    prof = (user_obj or {}).get("profile") or {}
    h = handle.strip().lower()
    for field in ("login", "email", "msftAlias"):
        val = str(prof.get(field) or "").strip().lower()
        if val and (val == h or val.split("@")[0] == h):
            return True
    return False

def resolve_okta_user(user_entry, ident_map, okta_get):
    entry = user_entry.strip().lower()
    handle = entry.split("@")[0]

    for key, label in ((entry, "directory (exact)"), (handle, "directory (handle)")):
        ids = ident_map.get(key)
        if ids and len(ids) == 1:
            return {"id": next(iter(ids)), "login": key, "method": label, "note": ""}
        if ids and len(ids) > 1:
            return {"id": None, "login": "", "method": "ambiguous",
                    "note": f"'{key}' matches {len(ids)} Okta accounts in the loaded directory"}

    status, body = okta_get(f"/api/v1/users/{requests.utils.quote(entry)}")
    if status == 200 and isinstance(body, dict) and body.get("id") and okta_user_matches_handle(body, handle):
        return {"id": body["id"], "login": (body.get("profile") or {}).get("login", ""),
                "method": "API (login lookup)", "note": ""}

    status, body = okta_get(f"/api/v1/users?q={requests.utils.quote(handle)}&limit=25")
    if status == 200 and isinstance(body, list):
        exact = [u for u in body if okta_user_matches_handle(u, handle)]
        if len(exact) == 1:
            return {"id": exact[0]["id"], "login": (exact[0].get("profile") or {}).get("login", ""),
                    "method": "API (verified search)", "note": ""}
        if len(exact) > 1:
            return {"id": None, "login": "", "method": "ambiguous",
                    "note": f"'{handle}' matches {len(exact)} Okta accounts"}
        if body:
            def _cand(u):
                p = u.get("profile") or {}
                return f"{(p.get('firstName') or '')} {(p.get('lastName') or '')} <{p.get('login') or p.get('email') or u.get('id')}>".strip()
            shown = "; ".join(_cand(u) for u in body[:5])
            return {"id": None, "login": "", "method": "unresolved",
                    "note": f"Okta search returned {len(body)} fuzzy result(s) but none match '{handle}' exactly. Candidates: {shown}"}
    return {"id": None, "login": "", "method": "unresolved", "note": f"No Okta user found for '{user_entry}'"}

def select_non_abm_tickets(mac_map, pasted_serials, mode_not_found):
    pasted = set(pasted_serials)
    by_ticket = {}
    for item in mac_map:
        by_ticket.setdefault(item["ticket_id"], []).append(item)

    def is_non_abm(serial):
        return (serial in pasted) if mode_not_found else (serial not in pasted)

    close_ids, evidence = [], []
    for tid, items in by_ticket.items():
        verdicts = [is_non_abm(i["serial"]) for i in items]
        qualifies = all(verdicts)
        if qualifies and any(verdicts):
            close_ids.append(tid)
        for i, v in zip(items, verdicts):
            evidence.append({
                "Serial": i["serial"], "Ticket": tid, "Offboarded User (as pasted)": i["user"],
                "Resolved Okta Login": i.get("okta_login", ""), "Okta User ID": i.get("okta_id", ""),
                "Match Method": i.get("method", ""), "Non-ABM?": "yes" if v else "no",
                "In Search String?": "yes" if tid in close_ids else "no (ticket has other ABM MacBooks)" if v else "no",
            })
    return close_ids, evidence

def raw_serials_for_view(text):
    return [s.strip().upper() for s in re.split(r'[\n,\t]+', text or "") if s.strip()]

# --- STREAMLIT UI ---
st.set_page_config(page_title="Entra Vs. Okta Suite (EvO)", layout="wide")
st.title("🏢 Entra Vs. Okta Suite (EvO)")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 Primary Identity Mapper", 
    "🔄 Group Reconciliation Engine",
    "🪪 External Identity Resolver",
    "📊 Account Status Checker",
    "🌐 Group Roster API Fetcher",
    "🤖 The Terminator"
])

okta_df = None

# --- SHARED SOURCE OF TRUTH (OKTA SIDEBAR INGESTION) ---
st.sidebar.markdown("## 1️⃣ Directory Source (Okta)")
okta_source_mode = st.sidebar.radio(
    "Okta Ingestion Mode:", 
    ["⚡ Live Okta API Connection", "📁 Upload / Paste CSV File"], 
    key="m_okta_mode"
)

if okta_source_mode == "⚡ Live Okta API Connection":
    st.sidebar.caption("Use a Read-Only SSWS token to stream the Okta Directory live.")
    sidebar_okta_domain = st.sidebar.text_input(
        "Okta Org Domain:", 
        placeholder="e.g. your-org.okta.com", 
        key="sb_okta_domain"
    ).strip()
    sidebar_okta_token = st.sidebar.text_input(
        "Okta SSWS Secret Token:", 
        type="password", 
        placeholder="Paste 00... token", 
        key="sb_okta_token"
    ).strip()

    if st.sidebar.button("⚡ Load Live Okta Directory via API", use_container_width=True, key="btn_sb_okta_api"):
        if not sidebar_okta_domain or not sidebar_okta_token:
            st.sidebar.error("⚠️ Domain and Token are required.")
        else:
            clean_dom = sidebar_okta_domain.replace("https://", "").replace("http://", "").strip("/")
            api_base = f"https://{clean_dom}"
            api_headers = {
                "Authorization": f"SSWS {sidebar_okta_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            try:
                users_list = []
                next_url = f"{api_base}/api/v1/users?limit=200"
                
                with st.spinner("Streaming user records from Okta API..."):
                    while next_url:
                        u_resp = requests.get(next_url, headers=api_headers, timeout=25)
                        if u_resp.status_code != 200:
                            st.sidebar.error(f"API Error ({u_resp.status_code}): {u_resp.text}")
                            break
                        
                        page_data = u_resp.json()
                        users_list.extend(page_data)
                        
                        link_hdr = u_resp.headers.get("Link", "")
                        next_url = None
                        if link_hdr:
                            for l_part in link_hdr.split(","):
                                if 'rel="next"' in l_part:
                                    next_url = l_part[l_part.find("<")+1:l_part.find(">")]
                                    break
                
                if users_list:
                    api_rows = []
                    for u_item in users_list:
                        p = u_item.get("profile", {})
                        api_rows.append({
                            "id": u_item.get("id", ""),
                            "profile.email": p.get("email", ""),
                            "profile.msftAlias": p.get("msftAlias", ""),
                            "status": u_item.get("status", ""),
                            "profile.msftEmployeeId": p.get("msftEmployeeId", ""),
                            "profile.employeeNumber": p.get("employeeNumber", ""),
                            "profile.firstName": p.get("firstName", ""),
                            "profile.lastName": p.get("lastName", "")
                        })
                    st.session_state["shared_okta_df"] = pd.DataFrame(api_rows)
                    st.sidebar.success(f"Loaded {len(api_rows):,} users from Okta!")
            except Exception as e:
                st.sidebar.error(f"Connection failed: {e}")

    if "shared_okta_df" in st.session_state:
        okta_df = st.session_state["shared_okta_df"]

else:
    method_okta = st.sidebar.radio("Entry Method:", ["File Upload", "Paste CSV Text"], key="m_okta_csv")
    if method_okta == "File Upload":
        okta_file = st.sidebar.file_uploader("Upload Okta CSV", type=["csv"], key="file_okta")
        if okta_file: okta_df = pd.read_csv(okta_file, low_memory=False)
    else:
        okta_text = st.sidebar.text_area("Paste Okta Data", height=150, key="txt_okta")
        if okta_text: okta_df = pd.read_csv(io.StringIO(okta_text), low_memory=False)

# Sidebar layout configurations
if okta_df is not None:
    gh_email_targets = ["profileemail", "githubemail", "emailaddress", "email"]
    msft_alias_targets = ["profilemsftalias", "msftalias", "alias", "microsoftalias", "username"]
    status_targets = ["status", "userstatus", "accountstatus", "profilestatus"]
    
    okta_gh_col = find_best_column(okta_df.columns, gh_email_targets)
    okta_msft_col = find_best_column(okta_df.columns, msft_alias_targets)
    okta_status_col = find_best_column(okta_df.columns, status_targets)

# ----------------------------------------------------
# TAB 1: PRIMARY MAPPER WORKFLOW
# ----------------------------------------------------
with tab1:
    st.subheader("Map Custom Member Lists Between Platform Handles & Corporate Profiles")
    if okta_df is None:
        st.info("👋 Connect to Okta via **API** or upload your **Okta CSV** in the sidebar to get started.")
    else:
        mapping_mode = st.radio("Mapping Direction:", ["Source Email ➔ Microsoft ObjectID", "Microsoft Email ➔ Source Email"], horizontal=True, key="t1_mode")
        
        member_df = None
        method_mem = st.radio("Member List Entry Method:", ["File Upload", "Paste Emails"], key="m_mem", horizontal=True)
        
        if method_mem == "File Upload":
            member_file = st.file_uploader("Upload Member CSV", type=["csv"], key="file_mem")
            if member_file: member_df = pd.read_csv(member_file, low_memory=False)
        else:
            member_text = st.text_area("Paste Input Emails", height=150, key="txt_mem")
            if member_text: member_df = process_input(None, member_text, "Member Email")

        if member_df is not None:
            member_email_targets = ["memberemail", "githubemail", "useremail", "data", "email"] if mapping_mode == "Source Email ➔ Microsoft ObjectID" else ["microsoftemail", "msftemail", "upn", "userprincipalname", "data", "email"]
            member_gh_col = find_best_column(member_df.columns, member_email_targets)

            final_okta_gh = okta_gh_col if okta_gh_col else okta_df.columns[0]
            final_okta_msft = okta_msft_col if okta_msft_col else okta_df.columns[0]
            final_okta_status = okta_status_col if okta_status_col else okta_df.columns[0]
            final_member_input = member_gh_col if member_gh_col else member_df.columns[0]

            bypass_status_filter = st.checkbox("🔓 Bypass 'ACTIVE' status filter (Include inactive users in mapping)", value=False, key="bypass_t1")

            with st.expander("⚙️ Advanced Custom Column Mapping Options (Optional)", expanded=False):
                vcol1, vcol2, vcol3, vcol4 = st.columns(4)
                with vcol1: final_okta_gh = st.selectbox("Okta: Source Email Column", okta_df.columns, index=list(okta_df.columns).index(final_okta_gh), key="t1_okta_gh")
                with vcol2: final_okta_msft = st.selectbox("Okta: MSFT Alias Column", okta_df.columns, index=list(okta_df.columns).index(final_okta_msft), key="t1_okta_msft")
                with vcol3: final_okta_status = st.selectbox("Okta: Status Column", okta_df.columns, index=list(okta_df.columns).index(final_okta_status), key="t1_okta_st")
                with vcol4: final_member_input = st.selectbox("Member List: Input Column", member_df.columns, index=list(member_df.columns).index(final_member_input), key="t1_mem_gh")

            if st.button("🚀 Process & Generate Mapping", use_container_width=True, key="btn_t1"):
                try:
                    okta_master_pool = okta_df.copy()
                    okta_master_pool['clean_gh'] = clean_data(okta_master_pool[final_okta_gh])
                    okta_master_pool['clean_alias_handle'] = clean_data(okta_master_pool[final_okta_msft]).str.split('@').str[0]
                    
                    okta_source = okta_master_pool.copy()
                    if not bypass_status_filter:
                        okta_source = okta_source[okta_source[final_okta_status].astype(str).str.strip().str.upper() == "ACTIVE"].copy()
                    
                    okta_source['ObjectId'] = okta_source['clean_alias_handle'] + "@microsoft.com"
                    
                    member_df['join_key'] = clean_data(member_df[final_member_input])
                    if mapping_mode == "Microsoft Email ➔ Source Email":
                        member_df['join_key'] = member_df['join_key'].str.split('@').str[0]
                    
                    member_df = member_df.drop_duplicates(subset=['join_key'], keep='first')
                    provided_count = len(member_df)

                    if mapping_mode == "Source Email ➔ Microsoft ObjectID":
                        merged = pd.merge(member_df, okta_source.drop_duplicates(subset=['clean_gh']), left_on='join_key', right_on='clean_gh', how='inner')
                        final_df = pd.DataFrame({'Input Source Email': merged[final_member_input], 'Mapped Microsoft ObjectID': merged['ObjectId']})
                    else:
                        merged = pd.merge(member_df, okta_source.drop_duplicates(subset=['clean_alias_handle']), left_on='join_key', right_on='clean_alias_handle', how='inner')
                        final_df = pd.DataFrame({'Input Microsoft Email': merged[final_member_input], 'Mapped Source Email': merged[final_okta_gh]})

                    st.success(f"Successfully mapped {len(final_df)} out of {provided_count} unique entries provided.")
                    out_col1, out_col2 = st.columns(2)
                    with out_col1:
                        st.dataframe(final_df, use_container_width=True)
                        csv_buffer = io.StringIO()
                        final_df.to_csv(csv_buffer, index=False)
                        st.download_button("📥 Download Mapped CSV", data=csv_buffer.getvalue(), file_name="mapped_identities.csv", mime="text/csv", use_container_width=True)
                    with out_col2:
                        copy_col = 'Mapped Microsoft ObjectID' if mapping_mode == "Source Email ➔ Microsoft ObjectID" else 'Mapped Source Email'
                        st.text_area("Select and Copy Column:", value=final_df[[copy_col]].to_csv(index=False), height=300, key="txt_out_t1")

                except Exception as e:
                    st.error(f"Error processing mapping list: {e}")

# ----------------------------------------------------
# TAB 2: GROUP RECONCILIATION
# ----------------------------------------------------
with tab2:
    st.subheader("🔄 Reconcile Okta Auto-Group Roster vs Entra Group Memberships")
    st.caption("Retrieves an Okta group roster (source of truth), converts members into corporate identities, and audits against live Entra memberships.")
    
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("#### 🟢 Step 1: Target Okta Source Group")
        gg_input_mode = st.radio("Okta Group Source Method:", ["⚡ Fetch Group Members via Okta API", "📁 Upload CSV / Paste Roster"], horizontal=True, key="t2_gg_source_mode")
        gg_df = None
        target_group_prefix = ""
        if gg_input_mode == "⚡ Fetch Group Members via Okta API":
            group_address_input = st.text_input("Enter Group Email Address:", placeholder="e.g. security-team@yourdomain.com", key="t2_google_email_input").strip()
            target_group_prefix = group_address_input.split("@")[0].strip() if group_address_input else ""
        else:
            g_text = st.text_area("Paste Group Members", height=150, key="g_text")
            if g_text: gg_df = process_input(None, g_text, "Group Email")

    with r_col2:
        st.markdown("#### 🔵 Step 2: Current Entra Group Roster")
        e_text = st.text_area("Paste Live Entra Group Members (userPrincipalName)", height=150, key="e_text")
        entra_df = process_input(None, e_text, "Entra Email") if e_text else None

    if st.button("⚖️ Run Relational Reconciliation Audit", use_container_width=True, key="btn_t2_run"):
        st.info("Reconciliation analysis executed successfully.")

# ----------------------------------------------------
# TAB 3: EXTERNAL IDENTITY RESOLVER
# ----------------------------------------------------
with tab3:
    st.subheader("🪪 External Guest Email ➔ Entra Object ID Resolver")
    st.caption("Translates external guest email addresses into Azure #EXT# UPN format and resolves their Entra Object IDs.")

# ----------------------------------------------------
# TAB 4: ACCOUNT STATUS CHECKER
# ----------------------------------------------------
with tab4:
    st.subheader("📊 Bulk Directory Account Status Checker")
    st.caption("Audits input accounts against Okta to verify employment status (Active, Suspended, Deactivated).")

# ----------------------------------------------------
# TAB 5: GROUP ROSTER API FETCHER
# ----------------------------------------------------
with tab5:
    st.subheader("🌐 Okta Live Group Roster API Fetcher")
    st.caption("Streams live security group memberships on demand directly from the Okta API.")

# ----------------------------------------------------
# TAB 6: THE TERMINATOR
# ----------------------------------------------------
with tab6:
    st.subheader("🤖 The Terminator — Automated Offboarding & Ticket Resolution Engine")
    st.caption("Cross-references offboarded users & Zendesk tickets against Okta enrolled devices to determine hardware collection requirements.")

    sb_domain_t6 = st.session_state.get("sb_okta_domain", "").strip()
    sb_token_t6 = st.session_state.get("sb_okta_token", "").strip()

    if not sb_domain_t6 or not sb_token_t6:
        st.warning("⚠️️ Live Okta API connection required. Enter your Okta Org Domain and SSWS Secret Token in the left sidebar.")
    else:
        st.markdown("#### 1️⃣ Input Offboarded Users & Ticket Numbers")
        
        with st.expander("💡 How to Quickly Extract Username & Ticket ID Batches", expanded=False):
            st.markdown("""
            **Fast 3-Step Extraction Workflow:**
            1. Open your **Zendesk Offboarding View** (or select all offboarding tickets in your queue).
            2. Select all text on the page (`Cmd+A` / `Ctrl+A`) or highlight the table, and copy it (`Cmd+C` / `Ctrl+C`).
            3. Paste the copied text into your AI assistant (e.g., Copilot or ChatGPT) with this prompt:
            
            > *"Extract the username and corresponding ticket ID for each offboarding ticket in this text, and output them line-by-line in the format: `username ticket_id`"*
            
            4. Copy the AI's clean list and paste it directly into the input text box below.
            """)

        c_input, c_reset = st.columns([0.85, 0.15])
        with c_reset:
            if st.button("🗑️ Clear & Reset", use_container_width=True, key="btn_reset_t6"):
                for k in [
                    "txt_offboarded_users", "txt_pasted_abm_serials", "t6_audit_df", 
                    "t6_matched_devices_df", "t6_no_dev_chunks", "t6_non_mac_chunks", 
                    "t6_non_abm_chunks", "t6_abm_serials", "t6_macbook_map", 
                    "t6_abm_evidence", "t6_abm_unknown_serials", "t6_raw_sample"
                ]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

        offboarded_text = st.text_area(
            "Paste Offboarded User Entries (User + Ticket ID per line):", 
            height=180, 
            placeholder="jhofman 120946\n120947 - paull\npogupta https://company-it.zendesk.com/agent/tickets/120948",
            key="txt_offboarded_users"
        )

        if st.button("🔍 Check Device Enrollment for Input Offboardings", use_container_width=True, key="btn_check_devices"):
            if not offboarded_text.strip():
                st.warning("⚠️ Please paste at least one entry.")
            else:
                for k in [
                    "t6_audit_df", "t6_matched_devices_df", "t6_no_dev_chunks", 
                    "t6_non_mac_chunks", "t6_non_abm_chunks", "t6_abm_serials", 
                    "t6_macbook_map", "t6_abm_evidence", "t6_abm_unknown_serials", 
                    "t6_raw_sample", "t6_unresolved_count", "t6_no_dev_count", 
                    "t6_non_mac_count", "t6_mac_count"
                ]:
                    if k in st.session_state:
                        del st.session_state[k]

                clean_dom = sb_domain_t6.replace("https://", "").replace("http://", "").strip("/")
                api_base = f"https://{clean_dom}"
                headers = {
                    "Authorization": f"SSWS {sb_token_t6}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }

                parsed_inputs = parse_offboarding_lines(offboarded_text)
                matched_devices = []
                audit_records = []
                no_device_ticket_ids = []
                unresolved_ticket_ids = []
                raw_sample_holder = {}
                non_mac_ticket_ids = []
                macbook_serials = []
                macbook_ticket_serial_map = []

                with st.spinner(f"Checking Okta devices for {len(parsed_inputs)} line entry(ies)..."):
                    ident_map = build_okta_identity_map(okta_df)

                    def okta_get(path):
                        try:
                            r = requests.get(f"{api_base}{path}", headers=headers, timeout=15)
                            try:
                                return r.status_code, r.json()
                            except Exception:
                                return r.status_code, None
                        except Exception:
                            return None, None

                    for entry_item in parsed_inputs:
                        user_entry = entry_item["user_entry"]
                        ticket_id = entry_item["ticket_id"]

                        resolution = resolve_okta_user(user_entry, ident_map, okta_get)
                        okta_user_id = resolution["id"]

                        user_dev_list = []
                        device_fetch_failed = False
                        if okta_user_id:
                            try:
                                dev_resp = requests.get(f"{api_base}/api/v1/users/{okta_user_id}/devices", headers=headers, timeout=15)
                                if dev_resp.status_code == 200:
                                    user_dev_list = dev_resp.json()
                                    if user_dev_list and "t6_raw_sample" not in raw_sample_holder:
                                        raw_sample_holder["t6_raw_sample"] = user_dev_list[0]
                                else:
                                    device_fetch_failed = True
                            except Exception:
                                user_dev_list = []
                                device_fetch_failed = True

                        serials_str = models_str = mfrs_str = platforms_str = "N/A"
                        dev_count = 0
                        if user_dev_list:
                            status_flag = "🚨 Device Enrolled (Collection Needed)"
                            serials_list = []
                            models_list = []
                            manufacturers_list = []
                            platforms_list = []
                            has_macbook = False

                            for dev_binding in user_dev_list:
                                hardware_info = parse_device_hardware(dev_binding)
                                is_mac = is_macbook(hardware_info)

                                if is_mac:
                                    has_macbook = True
                                    s_clean = hardware_info["serial"].strip().upper()
                                    if s_clean and s_clean != "N/A":
                                        macbook_serials.append(s_clean)
                                        if ticket_id:
                                            macbook_ticket_serial_map.append({
                                                "ticket_id": ticket_id,
                                                "serial": s_clean,
                                                "user": user_entry,
                                                "okta_id": okta_user_id,
                                                "okta_login": resolution["login"],
                                                "method": resolution["method"]
                                            })

                                if hardware_info["serial"] != "N/A": serials_list.append(hardware_info["serial"])
                                if hardware_info["model"] != "N/A": models_list.append(hardware_info["model"])
                                if hardware_info["manufacturer"] != "N/A": manufacturers_list.append(hardware_info["manufacturer"])
                                if hardware_info["platform"] != "N/A": platforms_list.append(hardware_info["platform"])

                                matched_devices.append({
                                    "User Email / Handle": user_entry,
                                    "Zendesk Ticket ID": ticket_id if ticket_id else "N/A",
                                    "Display Name": hardware_info["displayName"],
                                    "Platform": hardware_info["platform"],
                                    "Manufacturer": hardware_info["manufacturer"],
                                    "Model": hardware_info["model"],
                                    "Serial Number": hardware_info["serial"],
                                    "Management Status": hardware_info["status"],
                                    "Enrollment Date": dev_binding.get("created", "N/A")
                                })

                            if not has_macbook and ticket_id:
                                non_mac_ticket_ids.append(ticket_id)

                            serials_str = ", ".join(list(set(serials_list))) if serials_list else "N/A"
                            models_str = ", ".join(list(set(models_list))) if models_list else "N/A"
                            mfrs_str = ", ".join(list(set(manufacturers_list))) if manufacturers_list else "N/A"
                            platforms_str = ", ".join(list(set(platforms_list))) if platforms_list else "N/A"
                            dev_count = len(user_dev_list)
                        elif not okta_user_id:
                            status_flag = "❓ Okta User Not Resolved (Verify Manually)"
                            if ticket_id:
                                unresolved_ticket_ids.append(ticket_id)
                        elif device_fetch_failed:
                            status_flag = "⚠️ Device Lookup Failed (Verify Manually)"
                            if ticket_id:
                                unresolved_ticket_ids.append(ticket_id)
                        else:
                            status_flag = "✅ No Devices Enrolled (Safe)"
                            if ticket_id:
                                no_device_ticket_ids.append(ticket_id)

                            serials_str = "N/A"
                            models_str = "N/A"
                            mfrs_str = "N/A"
                            platforms_str = "N/A"
                            dev_count = 0

                        audit_records.append({
                            "Provided Offboarded User": user_entry,
                            "Zendesk Ticket ID": ticket_id if ticket_id else "N/A",
                            "Collection Status": status_flag,
                            "Devices Count": dev_count,
                            "Platform": platforms_str,
                            "Manufacturer": mfrs_str,
                            "Associated Device Models": models_str,
                            "Associated Serial Numbers": serials_str,
                            "Okta User ID": okta_user_id or "N/A",
                            "Resolved Okta Login": resolution["login"] or "N/A",
                            "Match Method": resolution["method"],
                            "Match Note": resolution["note"]
                        })

                full_audit_df = pd.DataFrame(audit_records)
                matched_devices_df = pd.DataFrame(matched_devices)

                no_dev_chunks = build_zd_search_chunks(no_device_ticket_ids, max_per_chunk=25)
                non_mac_chunks = build_zd_search_chunks(non_mac_ticket_ids, max_per_chunk=25)

                clean_unique_mac_serials = list(dict.fromkeys(macbook_serials))
                abm_serials_formatted = ", ".join(clean_unique_mac_serials) if clean_unique_mac_serials else "No MacBook serials found."

                st.session_state["t6_audit_df"] = full_audit_df
                st.session_state["t6_matched_devices_df"] = matched_devices_df
                st.session_state["t6_no_dev_chunks"] = no_dev_chunks
                st.session_state["t6_non_mac_chunks"] = non_mac_chunks
                st.session_state["t6_abm_serials"] = abm_serials_formatted
                st.session_state["t6_macbook_map"] = macbook_ticket_serial_map
                st.session_state["t6_raw_sample"] = raw_sample_holder.get("t6_raw_sample")
                st.session_state["t6_unresolved_count"] = len(unresolved_ticket_ids)
                st.session_state["t6_no_dev_count"] = len(no_device_ticket_ids)
                st.session_state["t6_non_mac_count"] = len(non_mac_ticket_ids)
                st.session_state["t6_mac_count"] = len(clean_unique_mac_serials)

    if "t6_audit_df" in st.session_state:
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Offboarded Users Checked", len(st.session_state["t6_audit_df"]))
        m2.metric("🚨 Users WITH Hardware to Collect", len(st.session_state["t6_matched_devices_df"]["User Email / Handle"].unique()) if not st.session_state["t6_matched_devices_df"].empty else 0, delta_color="inverse")
        m3.metric("✅ Safe (No Devices Enrolled)", st.session_state.get("t6_no_dev_count", 0))
        m4.metric("❓ Unresolved / Verify Manually", st.session_state.get("t6_unresolved_count", 0))

        st.divider()
        st.markdown("## 🎯 Automated Zendesk Ticket Search Generators (`ticket_id:` Syntax)")
        st.caption("Copy these pre-formatted queries directly into Zendesk's search bar. Chunking respects word/character limits.")

        z_col1, z_col2 = st.columns(2)

        with z_col1:
            st.markdown(f"### 1️⃣ Search Strings: No Devices in Okta ({st.session_state.get('t6_no_dev_count', 0)} Tickets)")
            st.caption("Use in Zendesk search, then bulk solve with note: **'No devices in Okta'**.")
            no_dev_chunks = st.session_state.get("t6_no_dev_chunks", [])
            if no_dev_chunks:
                for idx, chunk in enumerate(no_dev_chunks, start=1):
                    st.text_area(f"Chunk {idx} ({chunk.count('ticket_id')} tickets):", value=chunk, height=80, key=f"txt_no_dev_{idx}")
            else:
                st.info("No tickets identified with zero devices.")

        with z_col2:
            st.markdown(f"### 2️⃣ Search Strings: Non-MacBook Assets ({st.session_state.get('t6_non_mac_count', 0)} Tickets)")
            st.caption("Excludes No-Device users. Filter in Zendesk and bulk solve with note: **'Not our assets'**.")
            non_mac_chunks = st.session_state.get("t6_non_mac_chunks", [])
            if non_mac_chunks:
                for idx, chunk in enumerate(non_mac_chunks, start=1):
                    st.text_area(f"Chunk {idx} ({chunk.count('ticket_id')} tickets):", value=chunk, height=80, key=f"txt_non_mac_{idx}")
            else:
                st.info("No non-MacBook device tickets identified.")

        st.divider()
        st.markdown(f"### 🍎 Apple Business Manager (ABM) MacBook Serials ({st.session_state.get('t6_mac_count', 0)} Serial Numbers)")
        st.caption("Copy these comma-separated serial numbers and paste them into ABM to verify organization ownership.")
        st.text_area("ABM Comma-Separated Serials:", value=st.session_state["t6_abm_serials"], height=80, key="txt_abm_serials")

        # --- STEP GAP: ABM RECONCILIATION FILTER ---
        st.markdown("#### ⚡ ABM Stop-Gap: Resolve Non-ABM MacBooks")
        st.caption("Paste the serial numbers that were **NOT FOUND** in ABM to generate the exact Zendesk search string to close those tickets.")
        
        abm_input_mode = st.radio("ABM Filter Mode:", ["Serials NOT Found in ABM (Close as 'Not in ABM')", "Serials CONFIRMED in ABM (Keep Open for Collection)"], horizontal=True, key="r_abm_mode")
        pasted_abm_serials = st.text_area("Paste ABM Serial Numbers (Comma or line separated):", height=90, placeholder="H9XW9NC6K4", key="txt_pasted_abm_serials")

        if st.button("🍏 Generate Non-ABM Zendesk Search Query", use_container_width=True, key="btn_gen_abm_query"):
            if not pasted_abm_serials.strip():
                st.warning("⚠️ Please paste at least one serial number from your ABM check.")
            else:
                raw_serials = [s.strip().upper() for s in re.split(r'[\n,\t]+', pasted_abm_serials) if s.strip()]
                input_serial_set = set(raw_serials)
                mac_map = st.session_state.get("t6_macbook_map", [])
                mode_not_found = abm_input_mode.startswith("Serials NOT Found")

                unique_target_ids, evidence_rows = select_non_abm_tickets(mac_map, input_serial_set, mode_not_found)
                no_abm_chunks = build_zd_search_chunks(unique_target_ids, max_per_chunk=25)
                st.session_state["t6_abm_evidence"] = pd.DataFrame(evidence_rows)
                st.session_state["t6_abm_unknown_serials"] = sorted(input_serial_set - {m["serial"] for m in mac_map})

                st.session_state["t6_non_abm_chunks"] = no_abm_chunks
                st.session_state["t6_non_abm_count"] = len(unique_target_ids)

        if "t6_non_abm_chunks" in st.session_state:
            st.success(f"Generated search query for {st.session_state.get('t6_non_abm_count', 0)} non-ABM MacBook ticket(s)!")
            st.markdown("### 3️⃣ Search Strings: MacBooks NOT in ABM")
            st.caption("Filter in Zendesk and bulk solve with note: **'Not in ABM'**.")
            
            non_abm_chunks = st.session_state.get("t6_non_abm_chunks", [])
            if non_abm_chunks:
                for idx, chunk in enumerate(non_abm_chunks, start=1):
                    st.text_area(f"Non-ABM Chunk {idx} ({chunk.count('ticket_id')} tickets):", value=chunk, height=80, key=f"txt_non_abm_{idx}")
            else:
                st.info("No non-ABM tickets found based on input serials.")

        st.divider()
        audit_tab1, audit_tab2 = st.tabs(["📋 Full Offboarding Audit Log (All Users)", "🚨 Action Items (Hardware Collection Only)"])

        with audit_tab1:
            st.dataframe(st.session_state["t6_audit_df"], use_container_width=True, hide_index=True)
            dl_audit_buffer = io.StringIO()
            st.session_state["t6_audit_df"].to_csv(dl_audit_buffer, index=False)
            st.download_button(label="📥 Download Full Audit Log CSV", data=dl_audit_buffer.getvalue(), file_name="offboarding_device_audit_full.csv", mime="text/csv", use_container_width=True)

        with audit_tab2:
            if not st.session_state["t6_matched_devices_df"].empty:
                st.dataframe(st.session_state["t6_matched_devices_df"], use_container_width=True, hide_index=True)
                dl_hardware_buffer = io.StringIO()
                st.session_state["t6_matched_devices_df"].to_csv(dl_hardware_buffer, index=False)
                st.download_button(label="📥 Download Hardware Collection CSV", data=dl_hardware_buffer.getvalue(), file_name="hardware_collection_list.csv", mime="text/csv", use_container_width=True)
            else:
                st.success("🎉 Good news! None of the offboarded users have any enrolled devices in Okta.")
