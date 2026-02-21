import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- Plotly Integration ---
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(page_title="Jarvis Resource Management V28.0", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Constants ---
CURRENT_YEAR = str(datetime.now().year)
YEARS = ["2024", "2025", "2026", "2027", "2028"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- Repaired Data Engine ---
def get_data(sheet_name):
    """Auto-initializes missing columns to prevent KeyError crashes."""
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
    """Synchronizes data with a loader screen to prevent double-submissions."""
    with st.spinner(f"Writing to {sheet_name}..."):
        try:
            conn.update(worksheet=sheet_name, data=updated_df)
            st.toast(f"✅ {sheet_name} Updated")
            return True
        except Exception:
            st.error(f"Error: Worksheet '{sheet_name}' missing. Please create this tab in Google Sheets.")
            return False

# --- Global Load ---
master_df = get_data("Master_List")
log_df = get_data("Performance_Log")
util_df = get_data("Utilisation_Log")

# --- Navigation ---
st.sidebar.title("Jarvis V28.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Resource Utilisation", "Resource Profile", "Analytics Dashboard", "Audit Section"])

# --- MODULE: MASTER LIST (Repaired) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    t1, t2 = st.tabs(["🆕 Add Goal", "📋 Filtered View"])
    
    with t1:
        with st.form("m_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            r_name = c1.text_input("Resource Name*")
            r_proj = c2.text_input("Project Name*")
            y, m = st.selectbox("Year", YEARS, index=YEARS.index(CURRENT_YEAR)), st.selectbox("Month", MONTHS)
            goal = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Register"):
                if r_name and r_proj and goal:
                    new_r = pd.DataFrame([{"Resource Name": r_name, "Project": r_proj, "Goal": goal, "Year": y, "Month": m}])
                    if save_data("Master_List", pd.concat([master_df, new_r], ignore_index=True)): st.rerun()

    with t2:
        if not master_df.empty:
            f_proj = st.selectbox("Primary Project Filter", ["All"] + sorted(master_df["Project"].unique().tolist()))
            v_df = master_df if f_proj == "All" else master_df[master_df["Project"] == f_proj]
            st.dataframe(v_df, use_container_width=True, hide_index=True)

# --- MODULE: RESOURCE UTILISATION (Repaired) ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    if not master_df.empty:
        # Project-First Filter
        u_p = st.selectbox("1. Select Project", sorted(master_df["Project"].unique().tolist()))
        u_r_list = sorted(master_df[master_df["Project"] == u_p]["Resource Name"].unique().tolist())
        
        with st.form("u_form"):
            u_r = st.selectbox("2. Select Resource", u_r_list)
            u_y, u_m = st.selectbox("Year", YEARS), st.selectbox("Month", MONTHS)
            u_type = st.radio("Allocation", ["Billable", "Non-Billable"], horizontal=True)
            if st.form_submit_button("🚀 Update"):
                new_u = pd.DataFrame([{"Resource Name": u_r, "Project": u_p, "Year": u_y, "Month": u_m, "Type": u_type, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                if save_data("Utilisation_Log", pd.concat([util_df, new_u], ignore_index=True)): st.rerun()

# --- MODULE: ANALYTICS (Repaired) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance & Utilisation Insights")
    if not util_df.empty:
        ana_p = st.selectbox("Filter Analytics by Project", ["All"] + sorted(util_df["Project"].unique().tolist()))
        f_util = util_df if ana_p == "All" else util_df[util_df["Project"] == ana_p]
        
        if HAS_PLOTLY:
            c1, c2 = st.columns(2)
            with c1:
                # Utilisation Bar Chart
                fig1 = px.bar(f_util, x="Resource Name", color="Type", title="Resource Utilisation Mix", barmode="group")
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                # Project Overall Mix
                fig2 = px.pie(f_util, names="Type", title=f"Overall Project Stat: {ana_p}")
                st.plotly_chart(fig2, use_container_width=True)

# --- MODULE: AUDIT SECTION (Repaired) ---
elif page == "Audit Section":
    st.title("🛡️ Audit Log")
    if not log_df.empty:
        # Merging with Master to show Project info in Audit
        audit_view = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.dataframe(audit_view.sort_values("Timestamp", ascending=False), use_container_width=True, hide_index=True)
    else: st.info("No audit logs found.")

# --- MODULE: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.title("📈 Performance Capture")
    if not master_df.empty:
        sel_p = st.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        sel_r = st.selectbox("Resource", sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist()))
        sel_g = st.selectbox("Goal", master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist())
        
        with st.form("p_capture"):
            status = st.selectbox("Status", ["Achieved", "In-Progress", "Not completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            if st.form_submit_button("💾 Save"):
                new_p = pd.DataFrame([{
                    "Resource Name": sel_r, "Goal": sel_g, "Status": status, 
                    "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                if save_data("Performance_Log", pd.concat([log_df, new_p], ignore_index=True)): st.rerun()

# --- MODULE: RESOURCE PROFILE ---
else:
    st.title("👤 Resource Profile")
    if not master_df.empty:
        r_list = sorted(master_df["Resource Name"].unique().tolist())
        sel_res = st.selectbox("Select Resource", r_list)
        st.subheader(f"History for {sel_res}")
        st.dataframe(log_df[log_df["Resource Name"] == sel_res], use_container_width=True)
