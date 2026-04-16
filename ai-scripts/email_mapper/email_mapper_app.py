import streamlit as st
import pandas as pd
import io

def clean_data(series):
    """Helper to ensure data is stripped and lowercase for consistent matching."""
    return series.astype(str).str.strip().str.lower()

# --- Page Setup ---
st.set_page_config(page_title="GitHub to Microsoft Email Mapper", layout="wide")

st.title("📧 GitHub to Microsoft Email Mapper")
st.markdown("""
### Instructions:
1.  **Upload the Okta Source of Truth:** This file provides the mapping between GitHub addresses (`profile.email`) and Microsoft aliases (`profile.msftAlias`).
2.  **Upload the Member List:** A CSV containing the list of `Member Email` addresses you need to map.
3.  **Automatic Deduplication:** The tool will automatically remove duplicate email entries from both files to ensure a clean result.
4.  **Download the Result:** Get a CSV with unique **ObjectId** and **GitHub Email** pairs.
""")

st.divider()

# --- Upload Controls ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 Step 1: Source of Truth")
    okta_file = st.file_uploader("Upload Okta File (e.g., okta_data_users.csv)", type=["csv"], key="okta")

with col2:
    st.subheader("📁 Step 2: Member List")
    member_file = st.file_uploader("Upload Member List (GitHub Emails)", type=["csv"], key="member")

# --- Processing Engine ---
if okta_file and member_file:
    try:
        # Load Data
        df_okta = pd.read_csv(okta_file)
        df_members = pd.read_csv(member_file)

        # Validate Columns
        required_okta = ['profile.email', 'profile.msftAlias']
        required_member = ['Member Email']

        okta_missing = [c for c in required_okta if c not in df_okta.columns]
        member_missing = [c for c in required_member if c not in df_members.columns]

        if okta_missing or member_missing:
            if okta_missing:
                st.error(f"❌ Okta file is missing columns: {', '.join(okta_missing)}")
            if member_missing:
                st.error(f"❌ Member list is missing column: {', '.join(member_missing)}")
        else:
            # --- Logic Starts Here ---
            
            # 1. Prepare Join Keys (Case-insensitive)
            df_okta['join_key'] = clean_data(df_okta['profile.email'])
            df_members['join_key'] = clean_data(df_members['Member Email'])

            # 2. DEDUPLICATION
            # Remove duplicates from the source of truth based on the github email
            okta_dupes = df_okta.duplicated(subset=['join_key']).sum()
            df_okta = df_okta.drop_duplicates(subset=['join_key'], keep='first')

            # Remove duplicates from the member list
            member_dupes = df_members.duplicated(subset=['join_key']).sum()
            df_members = df_members.drop_duplicates(subset=['join_key'], keep='first')

            # 3. Create the Microsoft Email (ObjectId)
            # Remove rows with empty aliases
            df_okta = df_okta.dropna(subset=['profile.msftAlias'])
            df_okta['ObjectId'] = df_okta['profile.msftAlias'].astype(str).str.strip() + "@microsoft.com"

            # 4. Perform the Merge
            merged_df = pd.merge(
                df_members,
                df_okta[['join_key', 'ObjectId']],
                on='join_key',
                how='inner'
            )

            # 5. Final Formatting
            final_output = pd.DataFrame({
                'ObjectId': merged_df['ObjectId'],
                'GitHub Email': merged_df['Member Email']
            })

            # --- UI Results ---
            st.divider()
            st.subheader("✅ Mapping Complete")
            
            # Display Deduplication Info
            if okta_dupes > 0 or member_dupes > 0:
                with st.expander("🔍 Deduplication Summary"):
                    if okta_dupes > 0:
                        st.info(f"Removed {okta_dupes} duplicate entries from the Okta Source file.")
                    if member_dupes > 0:
                        st.info(f"Removed {member_dupes} duplicate entries from the Member List.")

            # Show stats
            col_a, col_b = st.columns(2)
            col_a.metric("Unique Members Found", len(df_members))
            col_b.metric("Successful Matches", len(final_output))

            if not final_output.empty:
                # Preview Table
                st.write("### Preview of Results")
                st.dataframe(final_output.head(15), use_container_width=True)

                # CSV Download Button
                csv_buffer = io.StringIO()
                final_output.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="📥 Download Cleaned CSV",
                    data=csv_buffer.getvalue(),
                    file_name="mapped_microsoft_emails.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No matches were found. Ensure the GitHub emails in your Member List appear in the Okta file.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please upload both CSV files to proceed.")
