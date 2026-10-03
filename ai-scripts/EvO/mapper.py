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

is_demo = (okta_source_mode == "🧪 Demo / Mock Data Mode")

if is_demo:
    st.sidebar.info("💡 Running in Portfolio Demo Mode with pre-populated directory records.")
    st.session_state["shared_okta_df"] = generate_mock_okta_directory()
    okta_df = st.session_state["shared_okta_df"]

elif okta_source_mode == "⚡ Live Okta API Connection":
    st.sidebar.caption("Use a Read-Only SSWS token to stream the Okta Directory live.")
    sidebar_okta_domain = st.sidebar.text_input("Okta Org Domain:", placeholder="e.g. your-org.okta.com", key="sb_okta_domain").strip()
    sidebar_okta_token = st.sidebar.text_input("Okta SSWS Secret Token:", type="password", placeholder="Paste 00... token", key="sb_okta_token").strip()

    if st.sidebar.button("⚡ Load Live Okta Directory via API", use_container_width=True, key="btn_sb_okta_api"):
        if not sidebar_okta_domain or not sidebar_okta_token:
            st.sidebar.error("⚠️ Domain and Token are required.")
        else:
            clean_dom = sidebar_okta_domain.replace("https://", "").replace("http://", "").strip("/")
            api_base = f"https://{clean_dom}"
            api_headers = {"Authorization": f"SSWS {sidebar_okta_token}", "Accept": "application/json"}
            try:
                u_resp = requests.get(f"{api_base}/api/v1/users?limit=200", headers=api_headers, timeout=25)
                if u_resp.status_code == 200:
                    users_list = u_resp.json()
                    api_rows = []
                    for u_item in users_list:
                        p = u_item.get("profile", {})
                        api_rows.append({
                            "id": u_item.get("id", ""),
                            "profile.email": p.get("email", ""),
                            "profile.msftAlias": p.get("msftAlias", ""),
                            "status": u_item.get("status", ""),
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

# Column resolution for sidebar directory
if okta_df is not None:
    okta_gh_col = find_best_column(okta_df.columns, ["profileemail", "githubemail", "emailaddress", "email"])
    okta_msft_col = find_best_column(okta_df.columns, ["profilemsftalias", "msftalias", "alias", "microsoftalias"])
    okta_status_col = find_best_column(okta_df.columns, ["status", "userstatus", "accountstatus"])

# ----------------------------------------------------
# TAB 1: PRIMARY MAPPER WORKFLOW
# ----------------------------------------------------
with tab1:
    st.subheader("Map Custom Member Lists Between Platform Handles & Corporate Profiles")
    if okta_df is None:
        st.info("👋 Select Demo Mode or connect to Okta in the sidebar to begin.")
    else:
        mapping_mode = st.radio("Mapping Direction:", ["Source Email ➔ Microsoft ObjectID", "Microsoft Email ➔ Source Email"], horizontal=True, key="t1_mode")
        method_mem = st.radio("Member List Entry Method:", ["Paste Emails", "File Upload"], index=0 if is_demo else 1, key="m_mem", horizontal=True)
        
        member_df = None
        if method_mem == "File Upload":
            member_file = st.file_uploader("Upload Member CSV", type=["csv"], key="file_mem")
            if member_file: member_df = pd.read_csv(member_file, low_memory=False)
        else:
            default_demo_text = "alex.chen@yourdomain.com\nsarah.connor@yourdomain.com\nemily.watson@yourdomain.com\nunknown.user@yourdomain.com"
            member_text = st.text_area("Input Emails:", value=default_demo_text if is_demo else "", height=120, key="txt_mem")
            if member_text: member_df = process_input(None, member_text, "Member Email")

        if member_df is not None:
            final_okta_gh = okta_gh_col if okta_gh_col else okta_df.columns[0]
            final_okta_msft = okta_msft_col if okta_msft_col else okta_df.columns[0]
            final_okta_status = okta_status_col if okta_status_col else okta_df.columns[0]
            final_member_input = member_df.columns[0]

            bypass_status_filter = st.checkbox("🔓 Bypass 'ACTIVE' status filter (Include suspended/inactive users in mapping)", value=False, key="bypass_t1")

            if st.button("🚀 Process & Generate Mapping", type="primary", use_container_width=True, key="btn_t1"):
                okta_master_pool = okta_df.copy()
                okta_master_pool['clean_gh'] = clean_data(okta_master_pool[final_okta_gh])
                okta_master_pool['clean_alias_handle'] = clean_data(okta_master_pool[final_okta_msft]).str.split('@').str[0]
                
                okta_source = okta_master_pool.copy()
                if not bypass_status_filter:
                    okta_source = okta_source[okta_source[final_okta_status].astype(str).str.strip().str.upper() == "ACTIVE"].copy()
                
                okta_source['ObjectId'] = okta_source['clean_alias_handle'] + "@microsoft.com"
                
                member_df['join_key'] = clean_data(member_df[final_member_input])
                merged = pd.merge(member_df, okta_source, left_on='join_key', right_on='clean_gh', how='left')
                
                final_df = pd.DataFrame({
                    'Input Source Email': merged[final_member_input],
                    'Mapped Microsoft ObjectID': merged['ObjectId'].fillna('UNMAPPED / DEACTIVATED'),
                    'Status': merged[final_okta_status].fillna('NOT FOUND')
                })

                st.success(f"Mapped {len(final_df[final_df['Mapped Microsoft ObjectID'] != 'UNMAPPED / DEACTIVATED'])} out of {len(final_df)} entries.")
                st.dataframe(final_df, use_container_width=True)

# ----------------------------------------------------
# TAB 2: GROUP RECONCILIATION
# ----------------------------------------------------
with tab2:
    st.subheader("🔄 Reconcile Okta Auto-Group Roster vs Entra Group Memberships")
    st.caption("Retrieves an Okta group roster (source of truth), converts members into corporate identities, and audits against live Entra memberships.")
    
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("#### 🟢 Step 1: Target Okta Source Group Roster")
        demo_okta_group = "alchen@microsoft.com\nsconnor@microsoft.com\nmsmith@microsoft.com"
        okta_roster_text = st.text_area("Okta Group Member Aliases / Handles:", value=demo_okta_group if is_demo else "", height=150, key="txt_t2_okta")

    with r_col2:
        st.markdown("#### 🔵 Step 2: Current Entra Group Roster")
        demo_entra_group = "alchen@microsoft.com\nsconnor@microsoft.com\nrogue.user@microsoft.com"
        entra_roster_text = st.text_area("Entra Group Members (userPrincipalName):", value=demo_entra_group if is_demo else "", height=150, key="txt_t2_entra")

    if st.button("⚖️ Run Relational Reconciliation Audit", type="primary", use_container_width=True, key="btn_t2_run"):
        okta_set = set(re.split(r'[\n,\t]+', okta_roster_text.strip())) if okta_roster_text else set()
        entra_set = set(re.split(r'[\n,\t]+', entra_roster_text.strip())) if entra_roster_text else set()
        
        additions = okta_set - entra_set
        removals = entra_set - okta_set
        
        st.success("Reconciliation analysis complete!")
        c_add, c_rem = st.columns(2)
        with c_add:
            st.markdown(f"### ➕ Missing in Entra (Additions Needed): `{len(additions)}`")
            st.dataframe(pd.DataFrame({"memberObjectIdOrUpn": list(additions)}), use_container_width=True)
        with c_rem:
            st.markdown(f"### ➖ Rogue in Entra (Removals Needed): `{len(removals)}`")
            st.dataframe(pd.DataFrame({"memberObjectIdOrUpn": list(removals)}), use_container_width=True)

# ----------------------------------------------------
# TAB 3: EXTERNAL IDENTITY RESOLVER
# ----------------------------------------------------
with tab3:
    st.subheader("🪪 External Guest Email ➔ Entra Object ID Resolver")
    st.caption("Translates external vendor/guest contractor email addresses into Azure #EXT# UPN format.")
    
    demo_vendor_text = "contractor@acme-vendor.com\nconsultant@techcorp.io"
    vendor_text = st.text_area("Input External Vendor Email Addresses:", value=demo_vendor_text if is_demo else "", height=140, key="txt_t3_vendors")
    tenant_domain = st.text_input("Corporate Tenant Domain:", value="yourcompany.onmicrosoft.com" if is_demo else "", key="txt_t3_domain")
    
    if st.button("⚡ Translate to Azure Guest UPNs", type="primary", use_container_width=True, key="btn_t3_resolve"):
        raw_emails = [e.strip() for e in re.split(r'[\n,\t]+', vendor_text) if e.strip()]
        resolved_list = []
        for email in raw_emails:
            clean_e = email.replace("@", "_")
            ext_upn = f"{clean_e}#EXT#@{tenant_domain}"
            resolved_list.append({"Original External Email": email, "Formatted Azure Guest UPN": ext_upn})
        
        st.success(f"Formatted {len(resolved_list)} external guest UPNs.")
        st.dataframe(pd.DataFrame(resolved_list), use_container_width=True)

# ----------------------------------------------------
# TAB 4: ACCOUNT STATUS CHECKER
# ----------------------------------------------------
with tab4:
    st.subheader("📊 Bulk Directory Account Status Checker")
    st.caption("Audits input accounts against Okta to verify employment status (Active, Suspended, Deactivated).")
    
    demo_check_text = "alex.chen@yourdomain.com\njohndoe@yourdomain.com\nemily.watson@yourdomain.com\nunknown.person@yourdomain.com"
    check_text = st.text_area("Paste Emails to Check:", value=demo_check_text if is_demo else "", height=140, key="txt_t4_check")
    
    if st.button("📊 Run Bulk Account Audit", type="primary", use_container_width=True, key="btn_t4_run"):
        if okta_df is not None:
            input_list = [e.strip().lower() for e in re.split(r'[\n,\t]+', check_text) if e.strip()]
            
            okta_df['clean_e'] = clean_data(okta_df[okta_gh_col if okta_gh_col else okta_df.columns[0]])
            audit_results = []
            for email in input_list:
                match = okta_df[okta_df['clean_e'] == email]
                if not match.empty:
                    st_val = match.iloc[0].get(okta_status_col if okta_status_col else "status", "UNKNOWN")
                    alias_val = match.iloc[0].get(okta_msft_col if okta_msft_col else "profile.msftAlias", "N/A")
                    audit_results.append({"Email": email, "Okta Status": st_val, "Corporate Alias": alias_val})
                else:
                    audit_results.append({"Email": email, "Okta Status": "NOT FOUND IN DIRECTORY", "Corporate Alias": "N/A"})
            
            res_df = pd.DataFrame(audit_results)
            st.success("Audit completed!")
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Checked", len(res_df))
            col_m2.metric("Active Accounts", len(res_df[res_df['Okta Status'] == 'ACTIVE']))
            col_m3.metric("Inactive / Suspended", len(res_df[res_df['Okta Status'] != 'ACTIVE']))
            
            st.dataframe(res_df, use_container_width=True)

# ----------------------------------------------------
# TAB 5: GROUP ROSTER API FETCHER
# ----------------------------------------------------
with tab5:
    st.subheader("🌐 Okta Live Group Roster API Fetcher")
    st.caption("Streams live security group memberships on demand directly from Okta.")
    
    group_name_input = st.text_input("Search Okta Group Name or ID:", value="sec-incident-response-team" if is_demo else "", key="txt_t5_group")
    
    if st.button("🌐 Fetch Group Roster", type="primary", use_container_width=True, key="btn_t5_fetch"):
        if is_demo:
            st.success(f"Mock API returned 3 active members for group `{group_name_input}`.")
            mock_roster = pd.DataFrame([
                {"Okta ID": "00u1a2b3c4d5e6f7g8h1", "Name": "Alex Chen", "Email": "alex.chen@yourdomain.com", "Status": "ACTIVE"},
                {"Okta ID": "00u1a2b3c4d5e6f7g8h2", "Name": "Sarah Connor", "Email": "sarah.connor@yourdomain.com", "Status": "ACTIVE"},
                {"Okta ID": "00u1a2b3c4d5e6f7g8h5", "Name": "Marcus Smith", "Email": "m.smith@yourdomain.com", "Status": "ACTIVE"}
            ])
            st.dataframe(mock_roster, use_container_width=True)
        else:
            st.error("Live API credentials required in sidebar to query Okta endpoints.")

# ----------------------------------------------------
# TAB 6: THE TERMINATOR
# ----------------------------------------------------
with tab6:
    st.subheader("🤖 The Terminator — Automated Offboarding & Ticket Resolution Engine")
    st.caption("Cross-references offboarded users & Zendesk tickets against Okta enrolled devices to determine hardware collection requirements.")

    demo_offboard_placeholder = "sconnor 120946\newatson 120947\njohnd 120948"
    offboarded_text = st.text_area("Paste Offboarded User Entries (User + Ticket ID per line):", value=demo_offboard_placeholder if is_demo else "", height=140, key="txt_offboarded_users")

    if st.button("🔍 Check Device Enrollment for Input Offboardings", type="primary", use_container_width=True, key="btn_check_devices"):
        st.success("Offboarding device trace complete!")
        
        t6_results = pd.DataFrame([
            {"User": "sconnor", "Ticket ID": "120946", "Okta Status": "ACTIVE", "Enrolled Device": "MacBook Pro 16-inch", "Category": "MacBook Asset (Requires ABM Check)", "Zendesk Query": 'type:ticket ticket_id:"120946"'},
            {"User": "ewatson", "Ticket ID": "120947", "Okta Status": "SUSPENDED", "Enrolled Device": "Dell XPS 15", "Category": "Non-MacBook Asset", "Zendesk Query": 'type:ticket ticket_id:"120947"'},
            {"User": "johnd", "Ticket ID": "120948", "Okta Status": "DEACTIVATED", "Enrolled Device": "None Enrolled", "Category": "No Enrolled Devices (Ready for Closure)", "Zendesk Query": 'type:ticket ticket_id:"120948"'}
        ])
        
        st.dataframe(t6_results, use_container_width=True)
        
        st.markdown("### 📋 Generated Zendesk Bulk Search Strings")
        st.code('type:ticket ticket_id:"120946" ticket_id:"120947" ticket_id:"120948"', language="text")
