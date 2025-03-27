import streamlit as st
import pandas as pd
import io
import re

# Set page configuration
st.set_page_config(
    page_title="Access Export",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #90CAF9;
        padding-bottom: 0.5rem;
    }
    .card {
        background-color: #F5F7FA;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .info-text {
        background-color: #E1F5FE;
        border-left: 5px solid #03A9F4;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Load CSV file
def load_csv(uploaded_file):
    if uploaded_file is not None:
        try:
            content = uploaded_file.getvalue().decode("utf-8")
            sample_line = content.split('\n')[0]
            
            if '\t' in sample_line:
                delimiter = '\t'
            elif ',' in sample_line:
                delimiter = ','
            else:
                delimiter = None  # Let pandas try to infer
                
            df = pd.read_csv(io.StringIO(content), delimiter=delimiter)
            df.columns = df.columns.str.strip().str.replace('"', '')
            return df
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    return None

# Extract user groups
def get_user_groups(df):
    required_columns = ['USER_NAME', 'MAIN_GROUP', 'ADDL_GROUP']
    for col in required_columns:
        if col not in df.columns:
            st.error(f"Missing required column: {col}. Please check your file.")
            return {}
    user_groups = {}
    for _, row in df.iterrows():
        groups = [row['USER_NAME'], row['MAIN_GROUP']] if pd.notna(row['MAIN_GROUP']) else [row['USER_NAME']]
        if pd.notna(row['ADDL_GROUP']):
            additional_groups = re.split(r'[,\s]+', str(row['ADDL_GROUP']))
            groups.extend([g for g in additional_groups if g])
        user_groups[row['USER_NAME']] = set(groups)
    return user_groups

# Extract user accesses
def get_user_accesses(df):
    user_accesses = {}
    for _, row in df.iterrows():
        user = row['JNUSER']
        access = row['VHFROM'] if pd.notna(row['VHFROM']) else None
        if user not in user_accesses:
            user_accesses[user] = set()
        if access:
            user_accesses[user].add(access)
    return user_accesses

# Main Streamlit app logic
def main():
    st.markdown('<h1 class="main-header">Access Export</h1>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("Upload Files")
        user_groups_file = st.file_uploader("Upload user_groups file", type=["csv", "txt"])
        master_users_groups_file = st.file_uploader("Upload master_users_groups file", type=["csv", "txt"])
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This tool identifies:
        - Users with extra access rights beyond their group permissions
        - Group-to-access mappings
        - Comprehensive access analysis

        Note: *PUBLIC access is treated as default access for all users.
        """)

    if user_groups_file and master_users_groups_file:
        with st.spinner("Processing files..."):
            user_groups_df = load_csv(user_groups_file)
            master_users_groups_df = load_csv(master_users_groups_file)

            if user_groups_df is not None and master_users_groups_df is not None:
                st.success("Files loaded successfully!")
                
                user_groups = get_user_groups(user_groups_df)
                user_accesses = get_user_accesses(master_users_groups_df)
                
                all_accesses = set()
                for accesses in user_accesses.values():
                    all_accesses.update(accesses)
                    
                selected_accesses = st.multiselect("Select Accesses to Filter:", sorted(list(all_accesses)))
                
                if selected_accesses:
                    filtered_data = []
                    for user, accesses in user_accesses.items():
                        if any(access in selected_accesses for access in accesses):
                            groups = user_groups.get(user, set())
                            filtered_data.append({
                                'User': user,
                                'Groups': ", ".join(sorted(groups)),
                                'Accesses': ", ".join(sorted(accesses)),
                            })
                    
                    filtered_df = pd.DataFrame(filtered_data)
                    st.dataframe(filtered_df)
                    
                    # Export data
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Filtered Access Report (CSV)",
                        data=csv,
                        file_name="filtered_access_report.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Please select at least one access to filter.")
            else:
                st.error("Error loading CSV files. Please check the file format and try again.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        ## Access Export Tool
        
        This tool helps you export users with specific access rights.
        
        1. **Upload the required files** using the sidebar.
        2. **Select the access rights** you want to filter.
        3. **View and download** the filtered results.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 0.8em;'><p>Developed with ❤️ by Maitry Rawal</p></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()