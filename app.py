import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- Plotly Integration ---
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V13.2", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
            for col in ["Resource Name", "Goal"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            if "Rating" in df.columns:
                df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce').fillna(0)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- System Repair Utility ---
def run_system_repair():
    st.sidebar.subheader("🛠️ System Health")
    if st.sidebar.button("Scan & Repair Database"):
        try:
            m_df = get_data("Master_List")
            m_required = ["Resource Name", "Project", "Goal", "Year", "Month"]
            for col in m_required:
                if col not in m_df.columns: m_df[col] = ""
            conn.update(worksheet="Master_List", data=m_df)
            
            p_df = get_data("Performance_Log")
            p_required = ["Project", "Resource Name", "MM/YYYY", "Goal", "Status", "Rating", "Comments", "Recommended for Recognition", "Recognition Comments", "Timestamp"]
            for col in p_required:
                if col not in p_df.columns: p_df[col] = ""
            conn.update(worksheet="Performance_Log", data=p_df)
            st.sidebar.success("Database Repaired!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Repair failed: {e}")

run_system_repair()

# --- Navigation ---
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2024", "2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v13_2", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                res_name = c1.selectbox("Resource*", sorted(master_df["Resource Name"].unique().tolist()))
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            y, m = st.selectbox("Year", years_list), st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": y, "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab2:
        if not master_df.empty:
            master_prep = master_df.copy()
            if not log_df.empty:
                # Deduplicate logs to get latest evaluation per goal
                log_clean = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
                unified_df = pd.merge(master_prep, log_clean[['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp']], on=['Resource Name', 'Goal'], how='left')
            else:
                unified_df = master_prep.copy()
                unified_df['Status'] = 'Yet to Mark'

            unified_df['Status'] = unified_df['Status'].fillna('Yet to Mark')
            
            # Filters
            c1, c2, c3, c4 = st.columns(4)
            f_p = c1.selectbox("Project", ["All"] + sorted(unified_df["Project"].unique().tolist()))
            f_r = c2.selectbox("Resource", ["All"] + sorted(unified_df["Resource Name"].unique().tolist()))
            f_y = f_y = c3.selectbox("Year", ["All"] + years_list)
            f_m = c4.selectbox("Month", ["All"] + months_list)

            final_df = unified_df.copy()
            if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
            if f_r != "All": final_df = final_df[final_df["Resource Name"] == f_r]
            if f_y != "All": final_df = final_df[final_df["Year"] == f_y]
            if f_m != "All": final_df = final_df[final_df["Month"] == f_m]

            def color_status(val):
                colors = {'Achieved': '#2E7D32', 'Not Completed': '#C62828', 'Partially Achieved': '#F9A825', 'Yet to Mark': '#757575'}
                return f'background-color: {colors.get(val, "none")}; color: white'

            st.dataframe(final_df.style.applymap(color_status, subset=['Status']), use_container_width=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        avail = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        
        if not avail.empty:
            g_opts = avail.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
            sel_g = st.selectbox("Select Goal", g_opts)
            res_info = avail.iloc[g_opts.index(sel_g)]
            
            with st.form("cap_v13_2"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                rating = st.feedback("stars")
                is_rec = st.checkbox("Recommend for Recognition?")
                if st.form_submit_button("💾 Save"):
                    new_entry = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "Goal": res_info['Goal'], "Status": status,
                        "Rating": (rating+1 if rating is not None else 0), "Recommended for Recognition": "Yes" if is_rec else "No",
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not master_df.empty:
        # --- FIX: ROBUST KPI CALCULATION ---
        log_latest = pd.DataFrame()
        if not log_df.empty:
            log_latest = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
        
        analytics_df = pd.merge(master_df, log_latest[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
        analytics_df['Status'] = analytics_df['Status'].fillna('Yet to Mark')
        
        # Metrics
        total = len(analytics_df)
        pending = len(analytics_df[analytics_df['Status'] == 'Yet to Mark'])
        achieved = len(analytics_df[analytics_df['Status'] == 'Achieved'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Goals", total)
        c2.metric("Pending (Yet to Mark)", pending)
        c3.metric("Achievement Rate", f"{(achieved/total*100):.1f}%" if total > 0 else "0%")
        
        if HAS_PLOTLY:
            st.divider()
            # Project Progress Chart
            st.subheader("🔥 Completion by Project")
            proj_chart = analytics_df.groupby(['Project', 'Status']).size().unstack(fill_value=0).reset_index()
            fig = px.bar(proj_chart, x='Project', y=proj_chart.columns[1:], barmode='group')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data found.")
