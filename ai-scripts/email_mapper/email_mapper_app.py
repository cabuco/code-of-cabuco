import subprocess
import sys
import os
import io

# --- AUTOMATIC DEPENDENCY CHECK ---
def prepare_environment():
    """Ensures all required libraries are installed before starting the app."""
    required_libraries = ["streamlit", "pandas"]
    for lib in required_libraries:
        try:
            __import__(lib)
        except ImportError:
            print(f"[{lib}] not found. Installing now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

# Run the check
prepare_environment()

# Now that we know they are installed, we can import them
import streamlit as st
import pandas as pd

# --- HELPER FUNCTIONS ---
def clean_data(series):
    """Consistent formatting for matching."""
    return series.astype(str).str.strip().str.lower()

# --- STREAMLIT UI ---
def run_app():
    st.set_page_config(page_title="Email Mapper Pro", layout="wide")

    st.title("📧 GitHub to Microsoft Email Mapper")
    st.info("Instructions: Just upload your two CSV files below. The tool handles deduplication and formatting automatically.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1️⃣ Source of Truth")
        okta_file = st.file_uploader("Upload Okta File", type=["csv"], help="Expected: 'profile.email' and 'profile.msftAlias'")

    with col2:
        st.subheader("2️⃣ Member List")
        member_file = st.file_uploader("Upload Member List", type=["csv"], help="Expected: 'Member Email'")

    if okta_file and member_file:
        try:
            df_okta = pd.read_csv(okta_file)
            df_members = pd.read_csv(member_file)

            # Column validation
            okta_req = ['profile.email', 'profile.msftAlias']
            member_req = ['Member Email']

            if not all(c in df_okta.columns for c in okta_req) or not all(c in df_members.columns for c in member_req):
                st.error("❌ Column mismatch detected. Ensure headers match the expected names exactly.")
                return

            # --- CLEANING & DEDUPLICATION ---
            # Prepare keys
            df_okta['join_key'] = clean_data(df_okta['profile.email'])
            df_members['join_key'] = clean_data(df_members['Member Email'])

            # Count duplicates for the report
            okta_dupes = df_okta.duplicated(subset=['join_key']).sum()
            member_dupes = df_members.duplicated(subset=['join_key']).sum()

            # Drop duplicates
            df_okta = df_okta.drop_duplicates(subset=['join_key'], keep='first')
            df_members = df_members.drop_duplicates(subset=['join_key'], keep='first')

            # Build Microsoft Email
            df_okta = df_okta.dropna(subset=['profile.msftAlias'])
            df_okta['ObjectId'] = df_okta['profile.msftAlias'].astype(str).str.strip() + "@microsoft.com"

            # --- MAPPING ---
            merged = pd.merge(df_members, df_okta[['join_key', 'ObjectId']], on='join_key', how='inner')

            # Format final output
            final_df = pd.DataFrame({
                'ObjectId': merged['ObjectId'],
                'GitHub Email': merged['Member Email']
            })

            # --- RESULTS ---
            st.divider()
            if okta_dupes > 0 or member_dupes > 0:
                st.warning(f"🧹 Deduplication: Removed {okta_dupes} rows from Okta and {member_dupes} rows from Member list.")

            st.success(f"Successfully matched {len(final_df)} unique records.")
            st.dataframe(final_df, use_container_width=True)

            csv_buffer = io.StringIO()
            final_df.to_csv(csv_buffer, index=False)
            st.download_button("📥 Download Mapped CSV", data=csv_buffer.getvalue(), file_name="mapped_emails.csv", mime="text/csv")

        except Exception as e:
            st.error(f"Critical Error: {e}")

# --- EXECUTION ---
if __name__ == "__main__":
    # Streamlit requires a specific way to be called if run from within a script
    if "_HEROKU_STATS_REPORT_STATE" not in os.environ: 
        # This part handles the "Fool Proof" execution
        # If the user runs 'python run_mapper.py', it re-runs itself through streamlit
        try:
            import streamlit.web.cli as stcli
            if not st._is_running_with_streamlit:
                sys.argv = ["streamlit", "run", sys.argv[0]]
                sys.exit(stcli.main())
        except Exception:
            pass
    run_app()
