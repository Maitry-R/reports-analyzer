import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import numpy as np
import re

# Set page configuration
st.set_page_config(
    page_title="User Access Analyzer",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    footer:before {
        content:''; 
        display:block;
        height: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    .metric-card {
        background-color: #E3F2FD;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1565C0;
    }
    .metric-label {
        font-size: 1rem;
        color: #424242;
    }
    .info-text {
        background-color: #E1F5FE;
        border-left: 5px solid #03A9F4;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .warning-text {
        background-color: #FFF8E1;
        border-left: 5px solid #FFC107;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .expander-header {
        font-weight: bold;
        color: #0D47A1;
    }
</style>
""", unsafe_allow_html=True)


# Load CSV file
def load_csv(uploaded_file):
    if uploaded_file is not None:
        try:
            # Try to detect the delimiter
            content = uploaded_file.getvalue().decode("utf-8")
            sample_line = content.split('\n')[0]
            
            if '\t' in sample_line:
                delimiter = '\t'
            elif ',' in sample_line:
                delimiter = ','
            else:
                delimiter = None  # Let pandas try to infer
            
            df = pd.read_csv(io.StringIO(content), delimiter=delimiter)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.replace('"', '')
            
            return df
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    return None

# Extract user groups from the user_groups file
def get_user_groups(df):
    required_columns = ['USER_NAME', 'MAIN_GROUP', 'ADDL_GROUP']
    for col in required_columns:
        if col not in df.columns:
            st.error(f"Missing required column: {col}. Please check your file.")
            return {}

    user_groups = {}
    for _, row in df.iterrows():
        groups = [row['MAIN_GROUP']] if pd.notna(row['MAIN_GROUP']) else []
        if pd.notna(row['ADDL_GROUP']):
            # Split by any whitespace or comma
            additional_groups = re.split(r'[,\s]+', str(row['ADDL_GROUP']))
            groups.extend([g for g in additional_groups if g])
        user_groups[row['USER_NAME']] = set(groups)
    return user_groups

# Extract group-to-access mappings from master_users_groups file
def get_group_accesses(df):
    group_accesses = {}
    # Filter rows where JNUSER starts with "GR"
    group_rows = df[df['JNUSER'].str.startswith('GR', na=False)]
    
    for _, row in group_rows.iterrows():
        group = row['JNUSER']
        access = row['VHFROM'] if pd.notna(row['VHFROM']) else None
        if group not in group_accesses:
            group_accesses[group] = set()
        if access:
            group_accesses[group].add(access)
    return group_accesses

# Get public accesses (default for all users)
def get_public_accesses(df):
    public_accesses = set()
    public_rows = df[df['JNUSER'] == '*PUBLIC']
    
    for _, row in public_rows.iterrows():
        access = row['VHFROM'] if pd.notna(row['VHFROM']) else None
        if access:
            public_accesses.add(access)
    
    return public_accesses

# Extract all accesses for users and groups from master_users_groups file
def get_user_accesses(df):
    user_accesses = {}
    for _, row in df.iterrows():
        user = row['JNUSER']
        access = row['VHFROM'] if pd.notna(row['VHFROM']) else None
        
        # Skip *PUBLIC entries as they're handled separately
        if user == '*PUBLIC':
            continue
            
        if user not in user_accesses:
            user_accesses[user] = set()
        if access:
            user_accesses[user].add(access)
    return user_accesses

# Find extra accesses for users (beyond their group permissions and public access)
def find_extra_accesses(user_groups, user_accesses, group_accesses, public_accesses):
    extra_accesses = {}
    for user, groups in user_groups.items():
        # Start with public accesses that everyone has
        all_expected_accesses = set(public_accesses)
        
        # Add group-based accesses
        for group in groups:
            if group in group_accesses:
                all_expected_accesses.update(group_accesses[group])
        
        # Get actual user accesses
        actual_accesses = user_accesses.get(user, set())
        
        # Find extra accesses
        extra = actual_accesses - all_expected_accesses
        if extra:
            extra_accesses[user] = extra
    
    return extra_accesses

# Generate summary statistics
def generate_summary_stats(user_groups, user_accesses, group_accesses, extra_accesses, public_accesses):
    stats = {
        'total_users': len(user_groups),
        'total_groups': len(group_accesses),
        'users_with_extra_access': len(extra_accesses),
        'total_unique_accesses': len(set().union(*[accesses for accesses in user_accesses.values()])),
        'public_accesses': len(public_accesses),
        'avg_group_per_user': sum(len(groups) for groups in user_groups.values()) / len(user_groups) if user_groups else 0,
        'avg_access_per_user': sum(len(accesses) for accesses in user_accesses.values()) / len(user_accesses) if user_accesses else 0,
        'avg_access_per_group': sum(len(accesses) for accesses in group_accesses.values()) / len(group_accesses) if group_accesses else 0,
    }
    
    # Most common groups
    all_groups = [group for groups in user_groups.values() for group in groups]
    stats['most_common_groups'] = Counter(all_groups).most_common(5)
    
    # Most common accesses
    all_accesses = [access for accesses in user_accesses.values() for access in accesses]
    stats['most_common_accesses'] = Counter(all_accesses).most_common(5)
    
    return stats

# Create visualizations
def create_visualizations(user_groups, user_accesses, group_accesses, extra_accesses, public_accesses, stats):
    visualizations = {}
    
    # 1. Distribution of group counts per user
    group_counts = [len(groups) for groups in user_groups.values()]
    visualizations['group_distribution'] = px.histogram(
        x=group_counts,
        nbins=max(10, max(group_counts) if group_counts else 1),
        labels={'x': 'Number of Groups', 'y': 'Number of Users'},
        title='Distribution of Group Membership per User',
        color_discrete_sequence=['#1E88E5']
    )
    visualizations['group_distribution'].update_layout(bargap=0.1)
    
    # 2. Distribution of access counts per user
    access_counts = [len(accesses) for accesses in user_accesses.values()]
    visualizations['access_distribution'] = px.histogram(
        x=access_counts,
        nbins=max(10, max(access_counts) if access_counts else 1),
        labels={'x': 'Number of Accesses', 'y': 'Number of Users'},
        title='Distribution of Access Rights per User',
        color_discrete_sequence=['#43A047']
    )
    visualizations['access_distribution'].update_layout(bargap=0.1)
    
    # 3. Top 10 groups by number of users
    group_user_counts = Counter([group for groups in user_groups.values() for group in groups])
    top_groups = group_user_counts.most_common(10)
    if top_groups:
        group_names, group_counts = zip(*top_groups)
        visualizations['top_groups'] = px.bar(
            x=group_names, 
            y=group_counts,
            labels={'x': 'Group', 'y': 'Number of Users'},
            title='Top 10 Groups by User Count',
            color_discrete_sequence=['#7E57C2']
        )
    
    # 4. Top 10 accesses
    access_counts = Counter([access for accesses in user_accesses.values() for access in accesses])
    top_accesses = access_counts.most_common(10)
    if top_accesses:
        access_names, access_counts = zip(*top_accesses)
        visualizations['top_accesses'] = px.bar(
            x=access_names, 
            y=access_counts,
            labels={'x': 'Access', 'y': 'Number of Users'},
            title='Top 10 Most Common Access Rights',
            color_discrete_sequence=['#EF6C00']
        )
    
    # 5. Pie chart of users with extra access vs standard access
    users_with_extra = len(extra_accesses)
    users_with_standard = len(user_groups) - users_with_extra
    visualizations['extra_access_pie'] = px.pie(
        values=[users_with_standard, users_with_extra],
        names=['Standard Access', 'Extra Access'],
        title='Users with Extra Access vs. Standard Access',
        color_discrete_sequence=['#4CAF50', '#F44336']
    )
    
    return visualizations

# Main Streamlit app logic
def main():
    st.markdown('<h1 class="main-header">🔐 User Access Analyzer</h1>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="info-text">This tool analyzes user access rights, comparing assigned group permissions with actual access rights to identify discrepancies.</div>', unsafe_allow_html=True)
    
    # Sidebar for uploading files
    with st.sidebar:
        st.header("Upload Files")
        
        st.markdown("### User Groups File")
        st.markdown("This file should contain columns: `USER_NAME`, `MAIN_GROUP`, and `ADDL_GROUP`")
        user_groups_file = st.file_uploader("Upload user_groups file", type=["csv", "txt"])
        
        st.markdown("### Master Users Groups File")
        st.markdown("This file should contain columns including: `JNUSER`, `VHFROM`, etc.")
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

    # Main content
    if user_groups_file and master_users_groups_file:
        with st.spinner("Processing files..."):
            # Load files
            user_groups_df = load_csv(user_groups_file)
            master_users_groups_df = load_csv(master_users_groups_file)

            if user_groups_df is not None and master_users_groups_df is not None:
                st.success("Files loaded successfully!")
                
                # Extract data
                user_groups = get_user_groups(user_groups_df)
                group_accesses = get_group_accesses(master_users_groups_df)
                user_accesses = get_user_accesses(master_users_groups_df)
                public_accesses = get_public_accesses(master_users_groups_df)
                
                # Find extra accesses (considering public access)
                extra_accesses = find_extra_accesses(user_groups, user_accesses, group_accesses, public_accesses)
                
                # Generate statistics
                stats = generate_summary_stats(user_groups, user_accesses, group_accesses, extra_accesses, public_accesses)
                
                # Create visualizations
                visualizations = create_visualizations(user_groups, user_accesses, group_accesses, extra_accesses, public_accesses, stats)
                
                # Display dashboard
                st.markdown('<h2 class="sub-header">Dashboard Overview</h2>', unsafe_allow_html=True)
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Total Users</div></div>'.format(stats['total_users']), unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Total Groups</div></div>'.format(stats['total_groups']), unsafe_allow_html=True)
                with col3:
                    st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Users with Extra Access</div></div>'.format(stats['users_with_extra_access']), unsafe_allow_html=True)
                with col4:
                    st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Public Accesses</div></div>'.format(stats['public_accesses']), unsafe_allow_html=True)
                
                # Second row of metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown('<div class="metric-card"><div class="metric-value">{:.2f}</div><div class="metric-label">Avg Groups per User</div></div>'.format(stats['avg_group_per_user']), unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="metric-card"><div class="metric-value">{:.2f}</div><div class="metric-label">Avg Accesses per User</div></div>'.format(stats['avg_access_per_user']), unsafe_allow_html=True)
                with col3:
                    st.markdown('<div class="metric-card"><div class="metric-value">{:.2f}</div><div class="metric-label">Avg Accesses per Group</div></div>'.format(stats['avg_access_per_group']), unsafe_allow_html=True)
                
                # Visualizations
                st.markdown('<h2 class="sub-header">Visualizations</h2>', unsafe_allow_html=True)
                
                # First row of charts
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(visualizations['group_distribution'], use_container_width=True)
                with col2:
                    st.plotly_chart(visualizations['access_distribution'], use_container_width=True)
                
                # Second row of charts
                col1, col2 = st.columns(2)
                with col1:
                    if 'top_groups' in visualizations:
                        st.plotly_chart(visualizations['top_groups'], use_container_width=True)
                with col2:
                    if 'top_accesses' in visualizations:
                        st.plotly_chart(visualizations['top_accesses'], use_container_width=True)
                
                # Third row - pie chart
                st.plotly_chart(visualizations['extra_access_pie'], use_container_width=True)
                
                # Public accesses section
                st.markdown('<h2 class="sub-header">Public Access Rights (Default for All Users)</h2>', unsafe_allow_html=True)
                
                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if public_accesses:
                        st.markdown(f"**{len(public_accesses)} default access rights** are granted to all users via *PUBLIC:")
                        st.write(", ".join(sorted(public_accesses)))
                    else:
                        st.markdown("No public access rights found.")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Users with extra access section
                st.markdown('<h2 class="sub-header">Users with Extra Access Rights</h2>', unsafe_allow_html=True)
                
                with st.container():
                    if extra_accesses:
                        st.markdown('<div class="warning-text">The following users have access rights beyond what their assigned groups provide (excluding public access).</div>', unsafe_allow_html=True)
                        
                        # Create a dataframe for better display
                        extra_access_data = []
                        for user, extra in extra_accesses.items():
                            extra_access_data.append({
                                'User': user,
                                'Extra Accesses': ", ".join(sorted(extra)),
                                'Extra Access Count': len(extra),
                                'Assigned Groups': ", ".join(sorted(user_groups.get(user, []))),
                                'Group Count': len(user_groups.get(user, [])),
                                'Total Access Count': len(user_accesses.get(user, []))
                            })
                        
                        extra_df = pd.DataFrame(extra_access_data)
                        extra_df = extra_df.sort_values('Extra Access Count', ascending=False)
                        
                        # Display as an interactive table
                        st.dataframe(extra_df, use_container_width=True)
                        
                        # Detailed expanders for each user
                        for _, row in extra_df.iterrows():
                            with st.expander(f"{row['User']} - {row['Extra Access Count']} extra access(es)"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown("**Extra Accesses:**")
                                    st.markdown(row['Extra Accesses'])
                                    
                                    st.markdown("**Assigned Groups:**")
                                    st.markdown(row['Assigned Groups'])
                                
                                with col2:
                                    st.markdown("**All Actual Accesses:**")
                                    all_accesses = ", ".join(sorted(user_accesses.get(row['User'], [])))
                                    st.markdown(all_accesses)
                                    
                                    # Show public accesses for reference
                                    st.markdown("**Public Accesses (Available to All):**")
                                    st.markdown(", ".join(sorted(public_accesses)))
                    else:
                        st.markdown('<div class="info-text">No users found with extra access rights beyond their group permissions and public access.</div>', unsafe_allow_html=True)
                
                # Group-to-Access mapping section
                st.markdown('<h2 class="sub-header">Group-to-Access Mapping</h2>', unsafe_allow_html=True)
                
                # Create a dataframe for better display
                group_access_data = []
                for group, accesses in group_accesses.items():
                    group_access_data.append({
                        'Group': group,
                        'Access Count': len(accesses),
                        'Users in Group': sum(1 for user_group in user_groups.values() if group in user_group)
                    })
                
                group_df = pd.DataFrame(group_access_data)
                group_df = group_df.sort_values(['Users in Group', 'Access Count'], ascending=False)
                
                # Display as an interactive table
                st.dataframe(group_df, use_container_width=True)
                
                # Detailed expanders for each group
                for group, accesses in group_accesses.items():
                    users_in_group = sum(1 for user_group in user_groups.values() if group in user_group)
                    with st.expander(f"{group} - {len(accesses)} access(es), {users_in_group} user(s)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Access List:**")
                            st.markdown(", ".join(sorted(accesses)))
                        
                        with col2:
                            st.markdown("**Users in this Group:**")
                            users_list = [user for user, groups in user_groups.items() if group in groups]
                            st.markdown(", ".join(sorted(users_list)) if users_list else "No users assigned to this group")
                
                # User Access Analysis section
                st.markdown('<h2 class="sub-header">User Access Analysis</h2>', unsafe_allow_html=True)
                
                # Create search functionality
                search_user = st.text_input("Search for a specific user:")
                
                # Filter users based on search
                filtered_users = [user for user in user_groups.keys() if search_user.lower() in user.lower()] if search_user else list(user_groups.keys())
                
                if filtered_users:
                    # Create a dataframe for better display
                    user_data = []
                    for user in filtered_users:
                        user_data.append({
                            'User': user,
                            'Group Count': len(user_groups.get(user, [])),
                            'Access Count': len(user_accesses.get(user, [])),
                            'Has Extra Access': user in extra_accesses,
                            'Extra Access Count': len(extra_accesses.get(user, []))
                        })
                    
                    user_df = pd.DataFrame(user_data)
                    user_df = user_df.sort_values(['Has Extra Access', 'Access Count'], ascending=[False, False])
                    
                    # Display as an interactive table
                    st.dataframe(user_df, use_container_width=True)
                    
                    # Detailed expanders for each user
                    for user in user_df['User']:
                        groups = user_groups.get(user, [])
                        accesses = user_accesses.get(user, [])
                        extra = extra_accesses.get(user, [])
                        
                        with st.expander(f"{user} - {len(groups)} group(s), {len(accesses)} access(es)"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Assigned Groups:**")
                                st.markdown(", ".join(sorted(groups)) if groups else "No groups assigned")
                                
                                st.markdown("**Access Rights:**")
                                st.markdown(", ".join(sorted(accesses)) if accesses else "No access rights")
                            
                            with col2:
                                if user in extra_accesses:
                                    st.markdown("**Extra Access Rights:**")
                                    st.markdown(", ".join(sorted(extra)) if extra else "No extra access rights")
                                
                                # Calculate expected access from groups
                                expected_access = set(public_accesses)  # Start with public access
                                for group in groups:
                                    if group in group_accesses:
                                        expected_access.update(group_accesses[group])
                                
                                st.markdown("**Expected Access from Groups + Public:**")
                                st.markdown(", ".join(sorted(expected_access)) if expected_access else "No expected access rights")
                else:
                    st.write("No users found matching your search criteria.")
                
                # Download section
                st.markdown('<h2 class="sub-header">Export Results</h2>', unsafe_allow_html=True)
                
                # Prepare data for export
                export_data = io.StringIO()
                
                # Extra accesses report
                if extra_access_data:
                    extra_df.to_csv(export_data, index=False)
                    extra_csv = export_data.getvalue()
                    st.download_button(
                        label="Download Extra Access Report (CSV)",
                        data=extra_csv,
                        file_name="extra_access_report.csv",
                        mime="text/csv"
                    )
            else:
                st.error("Error loading CSV files. Please check the file format and try again.")
    else:
        # Welcome screen
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        ## Welcome to the User Access Analyzer
        
        This application helps you analyze user access rights and identify potential security issues:
        
        1. **Upload the required files** using the sidebar
        2. **Analyze access patterns** across your organization
        3. **Identify users with extra access** beyond their assigned groups
        4. **Visualize access distribution** with interactive charts
        
        ### Key Features:
        - Identifies extra access rights beyond group permissions
        - Accounts for *PUBLIC access as default for all users
        - Provides detailed visualizations of access patterns
        - Allows searching and filtering of users
        - Exports results for further analysis
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 0.8em;'><p>Developed with ❤️ by Maitry Rawal</p></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
