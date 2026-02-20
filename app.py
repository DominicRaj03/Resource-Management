import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# Robust Plotly Import
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Config ---
st.set_page_config(page_title="Resource Management V7.0", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V7.0")
page = st.sidebar.radio("Navigation", ["App User Guide", "Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: ANALYTICS DASHBOARD (UPDATED REPORTS) ---
if page == "Analytics Dashboard":
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    
    if not df.empty and HAS_PLOTLY:
        # Global Filters for Reports
        all_projects = sorted(df["Project"].unique().tolist())
        sel_p = st.selectbox("Select Project for Analysis", all_projects)
        
        p_df = df[df["Project"] == sel_p]
        all_resources = sorted(p_df["Resource Name"].unique().tolist())
        sel_res = st.selectbox("Select Individual Resource", all_resources)
        
        st.divider()

        # 1. Team's Overall Graph for each month (ratings-based)
        st.subheader("🌐 Team Monthly Performance Trend")
        # Ensure MM/YYYY is treated as a chronological sequence
        team_monthly = p_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig_team = px.line(team_monthly, x="MM/YYYY", y="Rating", markers=True, 
                          title=f"Average Team Rating for {sel_p}",
                          labels={"Rating": "Average Rating", "MM/YYYY": "Month/Year"})
        fig_team.update_layout(yaxis_range=[0, 5.5])
        st.plotly_chart(fig_team, use_container_width=True)

        st.divider()

        # 2. Individual Overall Graph for each month (ratings-based)
        st.subheader(f"👤 Individual Monthly Trend: {sel_res}")
        ind_monthly = p_df[p_df["Resource Name"] == sel_res].groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig_ind = px.bar(ind_monthly, x="MM/YYYY", y="Rating", 
                        title=f"Monthly Ratings for {sel_res}",
                        color="Rating", color_continuous_scale='Blues')
        fig_ind.update_layout(yaxis_range=[0, 5.5])
        st.plotly_chart(fig_ind, use_container_width=True)

        st.divider()

        # 3. Goal Achieved vs Partially Achieved vs Not Completed (Individual-based)
        st.subheader(f"🎯 Goal Completion Breakdown: {sel_res}")
        status_counts = p_df[p_df["Resource Name"] == sel_res]["Status"].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        # Color mapping for consistency
        color_map = {
            "Achieved": "#28a745", 
            "Partially Achieved": "#ffc107", 
            "Not Completed": "#dc3545"
        }
        
        fig_pie = px.pie(status_counts, names='Status', values='Count', hole=0.4,
                         title=f"Status Distribution for {sel_res}",
                         color='Status', color_discrete_map=color_map)
        st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.warning("No performance data found. Please log ratings in 'Performance Capture' first.")

# --- SCREEN: APP USER GUIDE (Preserved) ---
elif page == "App User Guide":
    st.title("🛠️ Resource Management Guide")
    df_log = get_data("Performance_Log")
    if not df_log.empty:
        st.subheader("🌟 Top 3 Performers")
        top_3 = df_log.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        cols = st.columns(3)
        for i, (name, rating) in enumerate(top_3.items()):
            cols[i].metric(label=name, value=f"{rating:.2f} Stars")

# --- SCREEN: MASTER LIST (Preserved V6.1 CRUD Logic) ---
elif page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 New Entry", "📋 List View"])
    master_df = get_data("Master_List")
    with tab1:
        with st.form("new_entry_form", clear_on_submit=True):
            n, p = st.text_input("Full Name*"), st.text_input("Project Name*")
            g = st.text_area("Primary Goal")
            y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            if st.form_submit_button("➕ Save"):
                new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
                conn.update(worksheet="Master_List", data=pd.concat([master_df, new_r], ignore_index=True))
                st.rerun()
    with tab2:
        if not master_df.empty:
            for index, row in master_df.iterrows():
                with st.expander(f"{row['Resource Name']} ({row['Project']})"):
                    with st.form(key=f"edit_{index}"):
                        en = st.text_input("Name", value=row['Resource Name'])
                        ep = st.text_input("Project", value=row['Project'])
                        if st.form_submit_button("Update"):
                            master_df.at[index, 'Resource Name'], master_df.at[index, 'Project'] = en, ep
                            conn.update(worksheet="Master_List", data=master_df)
                            st.rerun()

# --- SCREEN: PERFORMANCE CAPTURE (Preserved V6.1 Logic) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        res_info = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)].iloc[-1]
        with st.form("cap_v7"):
            status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
            comments = st.text_area("Comments*")
            rating = st.feedback("stars")
            if st.form_submit_button("💾 Save"):
                new_entry = pd.DataFrame([{
                    "Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}",
                    "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                    "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                st.success("Saved!")

# --- SCREEN: HISTORICAL VIEW (Preserved) ---
else:
    st.header("📅 History")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
