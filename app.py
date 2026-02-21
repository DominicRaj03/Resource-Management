import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- Plotly Integration ---
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(page_title="Resource Management V22.1", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

CURRENT_YEAR = str(datetime.now().year)
years_list = ["2024", "2025", "2026", "2027", "2028"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def get_data(sheet_name):
    """Robust data fetcher with auto-initialization for missing columns."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass # Fallback to empty DF with correct headers below
    
    # Pre-defined headers to prevent KeyError
    if sheet_name == "Performance_Log":
        return pd.DataFrame(columns=["Resource Name", "Goal", "Status", "Rating", "Comments", "Recommended", "Justification", "Timestamp"])
    if sheet_name == "Utilisation_Log":
        return pd.DataFrame(columns=["Resource Name", "Project", "Year", "Month", "Type", "Timestamp"])
    if sheet_name == "Master_List":
        return pd.DataFrame(columns=["Resource Name", "Project", "Goal", "Year", "Month"])
    return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V22.1")
page = st.sidebar.radio("Navigation", [
    "Master List", "Performance Capture", "Resource Utilisation", 
    "Resource Profile", "Analytics Dashboard", "Audit Section"
])

# Load Data once per page load
master_df = get_data("Master_List")
log_df = get_data("Performance_Log")
util_df = get_data("Utilisation_Log")

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2, tab3 = st.tabs(["🆕 Register Goal", "📤 Bulk Import", "📋 Filtered View"])

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v22_1", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                r_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = c1.selectbox("Resource*", r_names)
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            
            y = st.selectbox("Year", years_list, index=years_list.index(CURRENT_YEAR))
            m = st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": str(y), "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab3:
        if not master_df.empty:
            f1, f2, f3 = st.columns(3)
            m_proj = f1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            m_year = f2.selectbox("Filter Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
            m_month = f3.selectbox("Filter Month", ["All"] + months_list)
            f_master = master_df.copy()
            if m_proj != "All": f_master = f_master[f_master["Project"] == m_proj]
            if m_year != "All": f_master = f_master[f_master["Year"].astype(str) == m_year]
            if m_month != "All": f_master = f_master[f_master["Month"] == m_month]
            st.data_editor(f_master, use_container_width=True, hide_index=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    if not master_df.empty:
        c1, c2 = st.columns(2)
        sel_p = c1.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        sel_r = c2.selectbox("Resource", sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist()))
        goals = master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist()
        sel_g = st.selectbox("Goal", goals)
        
        if not log_df.empty and not log_df[(log_df["Resource Name"] == sel_r) & (log_df["Goal"] == sel_g)].empty:
            st.warning("⚠️ Goal already captured.")
            if not st.checkbox("Override?"): st.stop()

        with st.form("cap_v22_1"):
            status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            if st.form_submit_button("💾 Save"):
                new_e = pd.DataFrame([{
                    "Resource Name": sel_r, "Goal": sel_g, "Status": status, 
                    "Rating": (rating+1 if rating is not None else 0), "Comments": comments, 
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                st.success("Saved!"); st.rerun()

# --- SCREEN: RESOURCE UTILISATION ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    if not master_df.empty:
        with st.form("util_v22_1"):
            u_res = st.selectbox("Resource", sorted(master_df["Resource Name"].unique().tolist()))
            u_proj = master_df[master_df["Resource Name"] == u_res]["Project"].iloc[0]
            st.info(f"Project: {u_proj}")
            u_year = st.selectbox("Year", years_list, index=years_list.index(CURRENT_YEAR))
            u_month = st.selectbox("Month", months_list)
            u_type = st.radio("Type", ["Billable", "Non-Billable"], horizontal=True)
            if st.form_submit_button("Update Utilisation"):
                new_u = pd.DataFrame([{"Resource Name": u_res, "Project": u_proj, "Year": u_year, "Month": u_month, "Type": u_type, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                # Robust Update
                try:
                    conn.update(worksheet="Utilisation_Log", data=pd.concat([util_df, new_u], ignore_index=True))
                    st.success("Utilisation Updated!"); st.rerun()
                except Exception as e:
                    st.error(f"Error: Worksheet 'Utilisation_Log' not found. Please create it in your Google Sheet.")

# --- SCREEN: RESOURCE PROFILE ---
elif page == "Resource Profile":
    st.title("👤 Resource Profile")
    if not master_df.empty:
        sel_name = st.selectbox("Select Resource", sorted(master_df["Resource Name"].unique().tolist()))
        
        # Safe filtering
        p_logs = log_df[log_df["Resource Name"] == sel_name] if not log_df.empty else pd.DataFrame()
        p_utils = util_df[util_df["Resource Name"] == sel_name] if not util_df.empty else pd.DataFrame()
        
        c1, c2 = st.columns(2)
        c1.metric("Evaluations", len(p_logs))
        c2.metric("Latest Status", p_utils.iloc[-1]['Type'] if not p_utils.empty else "N/A")
        
        if not p_logs.empty:
            st.subheader("Performance History")
            st.table(p_logs[['Goal', 'Status', 'Rating', 'Timestamp']])

# --- ANALYTICS & AUDIT (Standard Views) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    if not log_df.empty and not master_df.empty:
        full_df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.metric("Total Evaluations", len(full_df))
        if HAS_PLOTLY:
            st.plotly_chart(px.pie(full_df, names="Status", title="Team Progress"))

else:
    st.title("🛡️ Audit Section")
    if not log_df.empty:
        st.dataframe(log_df.sort_values('Timestamp', ascending=False), use_container_width=True)
