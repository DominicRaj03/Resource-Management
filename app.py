import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- Plotly Integration ---
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(page_title="Jarvis Resource Management V27.0", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Constants ---
CURRENT_YEAR = str(datetime.now().year)
YEARS = ["2024", "2025", "2026", "2027", "2028"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- Data Engine ---
def get_data(sheet_name):
    """Robust fetcher with schema protection."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    schemas = {
        "Master_List": ["Resource Name", "Project", "Goal", "Year", "Month"],
        "Performance_Log": ["Resource Name", "Goal", "Status", "Rating", "Comments", "Recommended", "Justification", "Timestamp"],
        "Utilisation_Log": ["Resource Name", "Project", "Year", "Month", "Type", "Timestamp"]
    }
    return pd.DataFrame(columns=schemas.get(sheet_name, []))

def save_data(sheet_name, updated_df):
    """Save with loader screen."""
    with st.spinner(f"Updating {sheet_name}..."):
        try:
            conn.update(worksheet=sheet_name, data=updated_df)
            st.toast(f"✅ Data synced to {sheet_name}")
            return True
        except Exception:
            st.error(f"Error: Worksheet '{sheet_name}' not found.")
            return False

# --- Global Load ---
master_df = get_data("Master_List")
log_df = get_data("Performance_Log")
util_df = get_data("Utilisation_Log")

# --- Navigation ---
st.sidebar.title("Jarvis V27.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Resource Utilisation", "Resource Profile", "Analytics Dashboard", "Audit Section"])

# --- MODULE: PERFORMANCE CAPTURE (Project-First Filter) ---
if page == "Performance Capture":
    st.title("📈 Performance Capture")
    if not master_df.empty:
        # Primary Project Filter
        all_projs = sorted(master_df["Project"].unique().tolist())
        sel_proj = st.selectbox("1. Choose Project", all_projs)
        
        # Dependent Resource List
        proj_resources = sorted(master_df[master_df["Project"] == sel_proj]["Resource Name"].unique().tolist())
        sel_res = st.selectbox("2. Choose Resource", proj_resources)
        
        # Dependent Goal List
        res_goals = master_df[(master_df["Project"] == sel_proj) & (master_df["Resource Name"] == sel_res)]["Goal"].tolist()
        sel_goal = st.selectbox("3. Select Goal", res_goals)
        
        with st.form("perf_capture_v27"):
            status = st.selectbox("Status", ["Achieved", "In-Progress", "Not completed"])
            rating = st.feedback("stars")
            comm = st.text_area("Comments*")
            if st.form_submit_button("💾 Save Entry"):
                new_p = pd.DataFrame([{
                    "Resource Name": sel_res, "Goal": sel_goal, "Status": status, 
                    "Rating": (rating+1 if rating is not None else 0), "Comments": comm,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                if save_data("Performance_Log", pd.concat([log_df, new_p], ignore_index=True)): st.rerun()

# --- MODULE: RESOURCE UTILISATION ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    if not master_df.empty:
        # Project Filter First
        u_proj = st.selectbox("Select Project", sorted(master_df["Project"].unique().tolist()))
        u_res_list = sorted(master_df[master_df["Project"] == u_proj]["Resource Name"].unique().tolist())
        
        with st.form("util_v27"):
            u_res = st.selectbox("Resource", u_res_list)
            u_y, u_m = st.selectbox("Year", YEARS, index=YEARS.index(CURRENT_YEAR)), st.selectbox("Month", MONTHS)
            u_type = st.radio("Allocation Type", ["Billable", "Non-Billable"], horizontal=True)
            if st.form_submit_button("🚀 Update Utilisation"):
                new_u = pd.DataFrame([{"Resource Name": u_res, "Project": u_proj, "Year": u_y, "Month": u_m, "Type": u_type, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                if save_data("Utilisation_Log", pd.concat([util_df, new_u], ignore_index=True)): st.rerun()

# --- MODULE: ANALYTICS DASHBOARD (New Charts) ---
elif page == "Analytics Dashboard":
    st.title("📊 Project & Resource Analytics")
    if not util_df.empty:
        all_projs = ["All"] + sorted(util_df["Project"].unique().tolist())
        ana_proj = st.selectbox("Primary Project Filter", all_projs)
        
        filt_util = util_df if ana_proj == "All" else util_df[util_df["Project"] == ana_proj]
        
        if HAS_PLOTLY and not filt_util.empty:
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Resource Utilisation Mix")
                # Stacked bar for individual resource stats
                util_chart = px.bar(filt_util, x="Resource Name", color="Type", 
                                    title="Billable vs Non-Billable by Resource",
                                    color_discrete_map={"Billable": "#1f77b4", "Non-Billable": "#aec7e8"})
                st.plotly_chart(util_chart, use_container_width=True)
            
            with c2:
                st.subheader("Project Resource Stat")
                # Pie for overall project composition
                proj_mix = px.pie(filt_util, names="Type", hole=.4, title=f"Overall {ana_proj} Mix")
                st.plotly_chart(proj_mix, use_container_width=True)

# --- MODULE: MASTER LIST ---
elif page == "Master List":
    st.title("👤 Resource Master List")
    # ... (Standard logic with Project-first filtering for viewing)
    t1, t2 = st.tabs(["🆕 Add Goal", "📋 Filtered View"])
    with t2:
        view_p = st.selectbox("Filter by Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
        df_v = master_df if view_p == "All" else master_df[master_df["Project"] == view_p]
        st.dataframe(df_v, use_container_width=True, hide_index=True)

# --- MODULE: RESOURCE PROFILE ---
elif page == "Resource Profile":
    st.title("👤 Resource Profile")
    if not master_df.empty:
        p_sel = st.selectbox("Select Project", sorted(master_df["Project"].unique().tolist()))
        r_sel = st.selectbox("Select Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique().tolist()))
        # ... (Display Profile Logic)
        st.subheader(f"History for {r_sel}")
        st.dataframe(log_df[log_df["Resource Name"] == r_sel], use_container_width=True)

# --- AUDIT ---
else:
    st.title("🛡️ Audit Log")
    st.dataframe(log_df.sort_values("Timestamp", ascending=False), use_container_width=True)
