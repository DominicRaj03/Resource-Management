import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Plotly Integration ---
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V12.5", layout="wide")

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

# --- Navigation ---
st.sidebar.title("Resource Management V12.5")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v12_5", clear_on_submit=True):
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
            master_prep['MM/YYYY'] = master_prep['Month'] + "/" + master_prep['Year']
            req_cols = ['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp']
            if not log_df.empty:
                existing_cols = [c for c in req_cols if c in log_df.columns]
                log_subset = log_df[existing_cols].copy().drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
                unified_df = pd.merge(master_prep, log_subset, on=['Resource Name', 'Goal'], how='left')
            else:
                unified_df = master_prep.copy()
                for col in ['Status', 'Rating', 'Timestamp']: unified_df[col] = None
            unified_df['Status'] = unified_df['Status'].fillna('⏳ Pending Evaluation')

            c1, c2, c3, c4 = st.columns(4)
            f_p = c1.selectbox("Project", ["All"] + sorted(unified_df["Project"].unique().tolist()))
            f_r = c2.selectbox("Resource", ["All"] + sorted(unified_df["Resource Name"].unique().tolist()))
            f_y = c3.selectbox("Year", ["All"] + years_list)
            f_m = c4.selectbox("Month", ["All"] + months_list)

            final_df = unified_df.copy()
            if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
            if f_r != "All": final_df = final_df[final_df["Resource Name"] == f_r]
            if f_y != "All": final_df = final_df[final_df["Year"] == f_y]
            if f_m != "All": final_df = final_df[final_df["Month"] == f_m]

            def color_status(val):
                color = '#90EE90' if val == 'Achieved' else '#FFCCCB' if val == 'Not Completed' else '#FFFFE0' if val == 'Partially Achieved' else 'white'
                return f'background-color: {color}; color: black'

            st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']].style.applymap(color_status, subset=['Status']), use_container_width=True)

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
            with st.form("cap_v12_5"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not master_df.empty:
        # --- 1. KPI SUMMARY RIBBON ---
        st.subheader("🏁 Executive Summary")
        audit_full = pd.merge(master_df, log_df[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
        audit_full['Status'] = audit_full['Status'].fillna('Pending Evaluation')
        
        total_g = len(audit_full)
        achieved_g = len(audit_full[audit_full['Status'] == 'Achieved'])
        pending_g = len(audit_full[audit_full['Status'] == 'Pending Evaluation'])
        success_rate = (achieved_g / total_g * 100) if total_g > 0 else 0
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Goals Set", total_g)
        kpi2.metric("Total Achieved", achieved_g, f"{success_rate:.1f}% Rate")
        kpi3.metric("Pending Eval", pending_g, delta=f"-{pending_g}", delta_color="inverse")
        kpi4.metric("Active Projects", master_df['Project'].nunique())
        st.divider()

        # --- 2. PROJECT BURN-DOWN ---
        if HAS_PLOTLY:
            st.subheader("🔥 Project Progress (%)")
            proj_stats = audit_full.groupby(['Project', 'Status']).size().unstack(fill_value=0)
            if 'Achieved' not in proj_stats.columns: proj_stats['Achieved'] = 0
            proj_stats['Total'] = proj_stats.sum(axis=1)
            proj_stats['Completion %'] = (proj_stats['Achieved'] / proj_stats['Total'] * 100).round(1)
            
            fig_burn = px.bar(proj_stats.reset_index(), x="Project", y="Completion %", text="Completion %", color="Completion %", color_continuous_scale="RdYlGn")
            st.plotly_chart(fig_burn, use_container_width=True)

        # --- 3. WORKLOAD UTILIZATION ---
        st.divider()
        st.subheader("⚖️ Resource Workload")
        util_df = master_df.groupby("Resource Name")["Goal"].count().reset_index(name="Goal Count")
        st.plotly_chart(px.bar(util_df, x="Resource Name", y="Goal Count", color="Goal Count", title="Goals per Resource"), use_container_width=True)

        # --- 4. INDIVIDUAL TRENDS ---
        if not log_df.empty:
            st.divider()
            sel_res = st.selectbox("Individual Deep Dive", sorted(log_df["Resource Name"].unique()))
            res_log = log_df[log_df["Resource Name"] == sel_res]
            st.plotly_chart(px.pie(res_log, names="Status", hole=0.4, title=f"Result Distribution: {sel_res}"), use_container_width=True)
    else:
        st.warning("No data found to analyze.")
