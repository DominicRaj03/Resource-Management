import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Plotly Integration ---
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(page_title="Resource Management V20.0", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

CURRENT_YEAR = str(datetime.now().year)
years_list = ["2024", "2025", "2026", "2027", "2028"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V20.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Resource Utilisation", "Analytics Dashboard", "Audit Section"])

# --- SCREEN: MASTER LIST (Same as V19.3) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2, tab3 = st.tabs(["🆕 Register Goal", "📤 Bulk Import", "📋 Filtered View"])
    master_df = get_data("Master_List")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v20", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                r_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = c1.selectbox("Resource*", r_names)
                existing_proj = master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0]
                res_proj = c2.text_input("Project", value=existing_proj, disabled=True)
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

    with tab2:
        st.subheader("📤 Bulk Goal Upload")
        template_csv = pd.DataFrame(columns=["Resource Name", "Project", "Goal", "Year", "Month"]).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Template", data=template_csv, file_name="template.csv")
        uploaded_file = st.file_uploader("Upload File", type=['csv', 'xlsx'])
        if uploaded_file:
            import_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            if all(col in import_df.columns for col in ["Resource Name", "Project", "Goal", "Year", "Month"]):
                if st.button("🚀 Import All"):
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, import_df], ignore_index=True))
                    st.success("Imported!"); st.rerun()

    with tab3:
        if not master_df.empty:
            f1, f2, f3 = st.columns(3)
            m_proj = f1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            m_year = f2.selectbox("Filter Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
            m_month = f3.selectbox("Filter Month", ["All"] + months_list)
            f_master = master_df.copy()
            if m_proj != "All": f_master = f_master[f_master["Project"] == m_proj]
            st.data_editor(f_master, use_container_width=True, hide_index=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        c1, c2 = st.columns(2)
        sel_p = c1.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        sel_r = c2.selectbox("Resource", sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist()))
        sel_g = st.selectbox("Goal", master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist())
        with st.form("cap_v20"):
            status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            is_rec = st.checkbox("Recommend for Recognition?")
            just = st.text_area("Justification")
            if st.form_submit_button("💾 Save"):
                new_e = pd.DataFrame([{"Resource Name": sel_r, "Goal": sel_g, "Status": status, "Rating": (rating+1 if rating is not None else 0), "Comments": comments, "Recommended": "Yes" if is_rec else "No", "Justification": just, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                st.success("Saved!"); st.rerun()

# --- NEW MODULE: RESOURCE UTILISATION ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation Tracking")
    master_df = get_data("Master_List")
    util_df = get_data("Utilisation_Log")

    # 1. Global Statistics (KPIs)
    st.subheader("📊 Team Overview")
    if not master_df.empty:
        total_team = master_df["Resource Name"].nunique()
        billable_count = 0
        non_billable_count = 0
        
        if not util_df.empty:
            # Filter for current month/year to get active counts
            latest_util = util_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name'], keep='last')
            billable_count = len(latest_util[latest_util["Type"] == "Billable"])
            non_billable_count = len(latest_util[latest_util["Type"] == "Non-Billable"])
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Team Size", total_team)
        k2.metric("Billable Resources", billable_count)
        k3.metric("Non-Billable Resources", non_billable_count)
        k4.metric("Utilisation %", f"{(billable_count/total_team*100):.1f}%" if total_team > 0 else "0%")

    st.divider()

    # 2. Entry Form
    if not master_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 Log Utilisation")
            with st.form("util_form", clear_on_submit=True):
                u_res = st.selectbox("Select Resource", sorted(master_df["Resource Name"].unique().tolist()))
                # Auto-detect project from Master List
                u_proj = master_df[master_df["Resource Name"] == u_res]["Project"].iloc[0]
                st.info(f"Assigned Project: {u_proj}")
                
                u_year = st.selectbox("Year", years_list, index=years_list.index(CURRENT_YEAR))
                u_month = st.selectbox("Month", months_list)
                u_type = st.radio("Allocation Type", ["Billable", "Non-Billable"], horizontal=True)
                
                if st.form_submit_button("📝 Update Utilisation"):
                    new_u = pd.DataFrame([{
                        "Resource Name": u_res, "Project": u_proj, "Year": u_year, 
                        "Month": u_month, "Type": u_type, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Utilisation_Log", data=pd.concat([util_df, new_u], ignore_index=True))
                    st.success("Utilisation updated!"); st.rerun()

        with col2:
            st.subheader("📈 Resource Trend Analysis")
            if not util_df.empty:
                t_res = st.selectbox("View Trend for Resource", sorted(util_df["Resource Name"].unique().tolist()))
                t_year = st.selectbox("Select Year for Graph", years_list, index=years_list.index(CURRENT_YEAR))
                
                res_trend = util_df[(util_df["Resource Name"] == t_res) & (util_df["Year"] == t_year)].copy()
                if not res_trend.empty:
                    m_map = {m: i+1 for i, m in enumerate(months_list)}
                    res_trend['m_idx'] = res_trend['Month'].map(m_map)
                    res_trend = res_trend.sort_values('m_idx')
                    
                    fig = px.line(res_trend, x='Month', y='Type', markers=True, 
                                  title=f"{t_res} Allocation Trend - {t_year}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data for selected year.")

# --- ANALYTICS & AUDIT (Same as V19.3) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty and not master_df.empty:
        full_df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project', 'Year', 'Month']], on=['Resource Name', 'Goal'], how='left')
        af1, af2, af3 = st.columns(3)
        ap_filt = af1.selectbox("Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
        ay_filt = af2.selectbox("Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
        am_filt = af3.selectbox("Month", ["All"] + months_list)
        df = full_df.copy()
        if ap_filt != "All": df = df[df["Project"] == ap_filt]
        kpi_df = df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
        m1, m2, m3 = st.columns(3)
        m1.metric("Evaluations", len(kpi_df)); m2.metric("Achievement Rate", f"{(len(kpi_df[kpi_df['Status']=='Achieved'])/len(kpi_df)*100):.1f}%"); m3.metric("Avg Rating", f"{kpi_df['Rating'].mean():.1f} ⭐")
        if HAS_PLOTLY:
            lb = kpi_df.groupby("Resource Name")["Rating"].mean().reset_index().sort_values("Rating", ascending=False)
            st.plotly_chart(px.bar(lb.head(10), x="Rating", y="Resource Name", orientation='h', title="Top Performers"), use_container_width=True)

else:
    st.title("🛡️ Audit Section")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty:
        audit_df = pd.merge(log_df.sort_values('Timestamp', ascending=False), master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
