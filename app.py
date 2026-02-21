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

st.set_page_config(page_title="Resource Management V21.0", layout="wide")
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
        if sheet_name == "Performance_Log":
            return pd.DataFrame(columns=["Resource Name", "Goal", "Status", "Rating", "Comments", "Recommended", "Justification", "Timestamp"])
        if sheet_name == "Utilisation_Log":
            return pd.DataFrame(columns=["Resource Name", "Project", "Year", "Month", "Type", "Timestamp"])
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V21.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Resource Utilisation", "Analytics Dashboard", "Audit Section"])

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2, tab3 = st.tabs(["🆕 Register Goal", "📤 Bulk Import", "📋 Filtered View"])
    master_df = get_data("Master_List")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v21", clear_on_submit=True):
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
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        c1, c2 = st.columns(2)
        sel_p = c1.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        sel_r = c2.selectbox("Resource", sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist()))
        sel_g = st.selectbox("Goal", master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist())
        with st.form("cap_v21"):
            status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            is_rec = st.checkbox("Recommend for Recognition?")
            just = st.text_area("Justification")
            if st.form_submit_button("💾 Save"):
                new_e = pd.DataFrame([{"Resource Name": sel_r, "Goal": sel_g, "Status": status, "Rating": (rating+1 if rating is not None else 0), "Comments": comments, "Recommended": "Yes" if is_rec else "No", "Justification": just, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                st.success("Saved!"); st.rerun()

# --- SCREEN: RESOURCE UTILISATION ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    master_df, util_df = get_data("Master_List"), get_data("Utilisation_Log")
    tab_log, tab_bulk = st.tabs(["📝 Individual Update", "📤 Bulk Utilisation Import"])

    with tab_log:
        if not master_df.empty:
            total_team = master_df["Resource Name"].nunique()
            bill_c = len(util_df[util_df["Type"] == "Billable"]["Resource Name"].unique()) if not util_df.empty else 0
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Team", total_team); k2.metric("Billable", bill_c); k3.metric("Non-Billable", total_team - bill_c)

            with st.form("util_v21"):
                u_res = st.selectbox("Resource", sorted(master_df["Resource Name"].unique().tolist()))
                u_proj = master_df[master_df["Resource Name"] == u_res]["Project"].iloc[0]
                u_year = st.selectbox("Year", years_list, index=years_list.index(CURRENT_YEAR))
                u_month = st.selectbox("Month", months_list)
                u_type = st.radio("Type", ["Billable", "Non-Billable"], horizontal=True)
                if st.form_submit_button("Update"):
                    new_u = pd.DataFrame([{"Resource Name": u_res, "Project": u_proj, "Year": u_year, "Month": u_month, "Type": u_type, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Utilisation_Log", data=pd.concat([util_df, new_u], ignore_index=True))
                    st.success("Updated!"); st.rerun()

    with tab_bulk:
        st.subheader("📤 Bulk Upload Utilisation")
        u_template = pd.DataFrame(columns=["Resource Name", "Project", "Year", "Month", "Type"]).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Utilisation Template", data=u_template, file_name="util_template.csv")
        u_file = st.file_uploader("Upload Utilisation File", type=['csv', 'xlsx'])
        if u_file:
            u_import_df = pd.read_csv(u_file) if u_file.name.endswith('.csv') else pd.read_excel(u_file)
            if all(col in u_import_df.columns for col in ["Resource Name", "Project", "Year", "Month", "Type"]):
                if st.button("🚀 Import Utilisation"):
                    u_import_df["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.update(worksheet="Utilisation_Log", data=pd.concat([util_df, u_import_df], ignore_index=True))
                    st.success("Import Successful!"); st.rerun()

# --- ANALYTICS DASHBOARD ---
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
        m1.metric("Evaluations", len(kpi_df)); m2.metric("Achievement Rate", f"{(len(kpi_df[kpi_df['Status']=='Achieved'])/len(kpi_df)*100):.1f}%" if len(kpi_df)>0 else "0%"); m3.metric("Avg Stars", f"{kpi_df['Rating'].mean():.1f} ⭐")
        if HAS_PLOTLY and not kpi_df.empty:
            st.plotly_chart(px.pie(kpi_df, names="Status", title="Status Distribution"), use_container_width=True)

# --- AUDIT SECTION ---
else:
    st.title("🛡️ Audit Section")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty:
        audit_df = pd.merge(log_df.sort_values('Timestamp', ascending=False), master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
