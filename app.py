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

st.set_page_config(page_title="Resource Management V19.2", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

CURRENT_YEAR = str(datetime.now().year)
years_list = ["2024", "2025", "2026", "2027", "2028"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "Rating" in df.columns:
                df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def ensure_columns(df, required_cols):
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    return df

# --- Navigation ---
st.sidebar.title("Resource Management V19.2")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard", "Audit Section"])

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2, tab3 = st.tabs(["🆕 Register Goal", "📤 Bulk Import", "📋 Filtered View"])
    master_df = get_data("Master_List")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v19_2", clear_on_submit=True):
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
                st.success("File Validated."); 
                if st.button("🚀 Import All"):
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, import_df], ignore_index=True))
                    st.success("Imported!"); st.rerun()
            else:
                st.error("Invalid Columns.")

    with tab3:
        if not master_df.empty: st.data_editor(master_df, use_container_width=True, hide_index=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        c1, c2 = st.columns(2)
        sel_p = c1.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        sel_r = c2.selectbox("Resource", sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist()))
        sel_g = st.selectbox("Goal", master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist())
        
        can_edit = True
        if not log_df.empty and not log_df[(log_df["Resource Name"] == sel_r) & (log_df["Goal"] == sel_g)].empty:
            st.warning("⚠️ Already captured.")
            can_edit = st.checkbox("Override?")

        if can_edit:
            with st.form("cap_v19_2"):
                status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
                rating = st.feedback("stars")
                comments = st.text_area("Comments*")
                is_rec = st.checkbox("Recommend for Recognition?")
                just = st.text_area("Justification (Required if recommended)")
                if st.form_submit_button("💾 Save"):
                    if comments and (not is_rec or just):
                        new_e = pd.DataFrame([{"Resource Name": sel_r, "Goal": sel_g, "Status": status, "Rating": (rating+1 if rating is not None else 0), "Comments": comments, "Recommended": "Yes" if is_rec else "No", "Justification": just, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                        conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                        st.success("Saved!"); st.rerun()
                    else: st.error("Please fill required fields.")

# --- SCREEN: ANALYTICS DASHBOARD (Restored & Fixed) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty and not master_df.empty:
        full_df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project', 'Year', 'Month']], on=['Resource Name', 'Goal'], how='left')
        
        # Filters
        f1, f2, f3 = st.columns(3)
        p_filt = f1.selectbox("Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
        y_filt = f2.selectbox("Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
        m_filt = f3.selectbox("Month", ["All"] + months_list)

        df = full_df.copy()
        if p_filt != "All": df = df[df["Project"] == p_filt]
        if y_filt != "All": df = df[df["Year"].astype(str) == y_filt]
        if m_filt != "All": df = df[df["Month"] == m_filt]

        kpi_df = df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
        m1, m2, m3 = st.columns(3)
        m1.metric("Evaluations", len(kpi_df))
        m2.metric("Achievement Rate", f"{(len(kpi_df[kpi_df['Status']=='Achieved'])/len(kpi_df)*100):.1f}%" if len(kpi_df)>0 else "0%")
        m3.metric("Avg Rating", f"{kpi_df['Rating'].mean():.1f} ⭐")

        if HAS_PLOTLY:
            if m_filt == "All":
                st.subheader("📈 Monthly Performance Trend")
                m_map = {m: i+1 for i, m in enumerate(months_list)}
                df['m_idx'] = df['Month'].map(m_map)
                t_data = df.groupby(['Month', 'm_idx'])['Rating'].mean().reset_index().sort_values('m_idx')
                st.plotly_chart(px.line(t_data, x='Month', y='Rating', markers=True), use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                lb = kpi_df.groupby("Resource Name")["Rating"].mean().reset_index().sort_values("Rating", ascending=False)
                st.plotly_chart(px.bar(lb.head(10), x="Rating", y="Resource Name", orientation='h', title="Top Performers"), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(kpi_df, names="Status", title="Status Distribution"), use_container_width=True)

# --- AUDIT SECTION ---
else:
    st.title("🛡️ Audit Section")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty:
        audit_df = pd.merge(log_df.sort_values('Timestamp', ascending=False), master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
