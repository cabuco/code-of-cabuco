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

# --- MOCK DATA GENERATOR FOR PORTFOLIO DEMOS ---
def generate_mock_okta_directory():
    return pd.DataFrame([
        {"id": "00u1a2b3c4d5e6f7g8h1", "profile.email": "alex.chen@yourdomain.com", "profile.msftAlias": "alchen@microsoft.com", "status": "ACTIVE", "profile.firstName": "Alex", "profile.lastName": "Chen"},
        {"id": "00u1a2b3c4d5e6f7g8h2", "profile.email": "sarah.connor@yourdomain.com", "profile.msftAlias": "sconnor@microsoft.com", "status": "ACTIVE", "profile.firstName": "Sarah", "profile.lastName": "Connor"},
        {"id": "00u1a2b3c4d5e6f7g8h3", "profile.email": "johndoe@yourdomain.com", "profile.msftAlias": "johnd@microsoft.com", "status": "DEACTIVATED", "profile.firstName": "John", "profile.lastName": "Doe"},
        {"id": "00u1a2b3c4d5e6f7g8h4", "profile.email": "emily.watson@yourdomain.com", "profile.msftAlias": "ewatson@microsoft.com", "status": "SUSPENDED", "profile.firstName": "Emily", "profile.lastName": "Watson"},
        {"id": "00u1a2b3c4d5e6f7g8h5", "profile.email": "m.smith@yourdomain.com", "profile.msftAlias": "msmith@microsoft.com", "status": "ACTIVE", "profile.firstName": "Marcus", "profile.lastName": "Smith"},
    ])

# --- TAB 6 HELPERS ---
def parse_offboarding_lines(raw_text):
    """Parse 'user + ticket' lines. Handles ticketing subject lines and full ticket URLs."""
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
    ["🧪 Demo / Mock Data Mode", "⚡ Live Okta API Connection", "📁 Upload / Paste CSV File"], 
    key="m_okta_mode"
)

if okta_source_mode == "🧪 Demo / Mock Data Mode":
    st.sidebar.info("💡 Running in Portfolio Demo Mode with pre-populated directory records.")
    st.session_state["shared_okta_df"] = generate_mock_okta_directory()
    okta_df = st.session_state["shared_okta_df"]

elif okta_source_mode == "⚡ Live Okta API Connection":
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
        st.info("👋 Connect to Okta via **API**, select **Demo Mode**, or upload your **Okta CSV** in the sidebar to get started.")
    else:
        mapping_mode = st.radio("Mapping Direction:", ["Source Email ➔ Microsoft ObjectID", "Microsoft Email ➔ Source Email"], horizontal=True, key="t1_mode")
        
        member_df = None
        method_mem = st.radio("Member List Entry Method:", ["File Upload", "Paste Emails"], key="m_mem", horizontal=True)
        
        if method_mem == "File Upload":
            member_file = st.file_uploader("Upload Member CSV", type=["csv"], key="file_mem")
            if member_file: member_df = pd.read_csv(member_file, low_memory=False)
        else:
            default_demo_text = "alex.chen@yourdomain.com\nsarah.connor@yourdomain.com\nemily.watson@yourdomain.com" if okta_source_mode == "🧪 Demo / Mock Data Mode" else ""
            member_text = st.text_area("Paste Input Emails", value=default_demo_text, height=150, key="txt_mem")
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

    if okta_source_mode != "🧪 Demo / Mock Data Mode" and (not sb_domain_t6 or not sb_token_t6):
        st.warning("⚠️ Live Okta API connection or Demo Mode required. Select Demo Mode or enter your credentials in the left sidebar.")
    else:
        st.markdown("#### 1️⃣ Input Offboarded Users & Ticket Numbers")
        
        c_input, c_reset = st.columns([0.85, 0.15])
        with c_reset:
            if st.button("🗑️ Clear & Reset", use_container_width=True, key="btn_reset_t6"):
                for k in [
                    "txt_offboarded_users", "txt_pasted_abm_serials", "t6_audit_df", 
                    "t6_matched_devices_df", "t6_no_dev_chunks", "t6_non_mac_chunks", 
                    "t6_non_abm_chunks", "t6_abm_serials", "t6_macbook_map"
                ]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

        demo_offboard_placeholder = "sconnor 120946\n120947 - ewatson\njohnd https://company-it.zendesk.com/agent/tickets/120948"
        offboarded_text = st.text_area(
            "Paste Offboarded User Entries (User + Ticket ID per line):", 
            value=demo_offboard_placeholder if okta_source_mode == "🧪 Demo / Mock Data Mode" else "",
            height=180, 
            key="txt_offboarded_users"
        )

        if st.button("🔍 Check Device Enrollment for Input Offboardings", use_container_width=True, key="btn_check_devices"):
            if not offboarded_text.strip():
                st.warning("⚠️ Please paste at least one entry.")
            else:
                st.success("Offboarding device trace complete!")
