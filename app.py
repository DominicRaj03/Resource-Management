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

st.set_page_config(page_title="Resource Management V19.1", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

CURRENT_YEAR = str(datetime.now().year)

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
st.sidebar.title("Resource Management V19.1")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard", "Audit Section"])

years_list = ["2024", "2025", "2026", "2027", "2028"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2, tab3 = st.tabs(["🆕 Register Goal", "📤 Bulk Import", "📋 Filtered View"])
    master_df = get_data("Master_List")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v19_1", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                r_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = c1.selectbox("Resource*", r_names)
                existing_proj = master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0]
                res_proj = c2.text_input("Project", value=existing_proj, disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            
            default_year_idx = years_list.index(CURRENT_YEAR) if CURRENT_YEAR in years_list else 0
            y = st.selectbox("Year", years_list, index=default_year_idx)
            m = st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": str(y), "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab2:
        st.subheader("📤 Bulk Goal Upload")
        template_df = pd.DataFrame(columns=["Resource Name", "Project", "Goal", "Year", "Month"])
        template_csv = template_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Template", data=template_csv, file_name="goal_template.csv", mime="text/csv")
        
        st.divider()
        uploaded_file = st.file_uploader("Choose CSV/Excel File", type=['csv', 'xlsx'])
        if uploaded_file:
            try:
                import_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                required_fields = ["Resource Name", "Project", "Goal", "Year", "Month"]
                missing_cols = [col for col in required_fields if col not in import_df.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                elif import_df[required_fields].isnull().values.any():
                    st.error("❌ Validation Error: Required cells are empty.")
                else:
                    st.success(f"✅ Validated {len(import_df)} rows.")
                    if st.button("🚀 Confirm & Insert All"):
                        conn.update(worksheet="Master_List", data=pd.concat([master_df, import_df], ignore_index=True))
                        st.success("Bulk Upload Completed!"); st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")

    with tab3:
        if not master_df.empty:
            st.data_editor(master_df, use_container_width=True, hide_index=True)

# --- SCREEN: PERFORMANCE CAPTURE (Recognition Restored) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    if not master_df.empty:
        col1, col2 = st.columns(2)
        p_list = sorted(master_df["Project"].unique().tolist())
        sel_p = col1.selectbox("1. Choose Project", p_list)
        r_list = sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist())
        sel_r = col2.selectbox("2. Choose Resource", r_list)
        g_list = master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist()
        sel_g = st.selectbox("3. Select Goal", g_list)
        
        record_exists = False
        if not log_df.empty:
            record_exists = not log_df[(log_df["Resource Name"] == sel_r) & (log_df["Goal"] == sel_g)].empty

        can_edit = True
        if record_exists:
            st.warning("⚠️ Goal already captured.")
            override = st.checkbox("Would you like to override previous entry?")
            can_edit = override

        if can_edit:
            with st.form("cap_v19_1", clear_on_submit=True):
                status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
                rating = st.feedback("stars") 
                comments = st.text_area("Comments*")
                
                # --- RESTORED FIELDS ---
                st.divider()
                is_rec = st.checkbox("Recommend for Recognition?")
                just = st.text_area("Justification (Required if recommended)")
                
                if st.form_submit_button("💾 Save Entry"):
                    if not comments:
                        st.error("Comments are required.")
                    elif is_rec and not just:
                        st.error("Justification is required for recognition.")
                    else:
                        new_e = pd.DataFrame([{
                            "Resource Name": sel_r, "Goal": sel_g, "Status": status,
                            "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                            "Recommended": "Yes" if is_rec else "No", "Justification": just,
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Rating', 'Comments', 'Recommended', 'Justification', 'Timestamp'])
                        conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                        st.success("Entry Saved Successfully!"); st.rerun()
        else:
            st.info("Check override box above to edit.")

# --- ANALYTICS DASHBOARD ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty and not master_df.empty:
        full_df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project', 'Year', 'Month']], on=['Resource Name', 'Goal'], how='left')
        kpi_df = full_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Evaluations", len(kpi_df))
        c2.metric("Achievement Rate", f"{(len(kpi_df[kpi_df['Status']=='Achieved'])/len(kpi_df)*100):.1f}%" if len(kpi_df)>0 else "0%")
        c3.metric("Avg Rating", f"{kpi_df['Rating'].mean():.1f} ⭐")

        if HAS_PLOTLY:
            st.divider()
            st.subheader("📈 Performance Trend")
            trend_data = full_df.groupby(['Month'])['Rating'].mean().reindex(months_list).dropna().reset_index()
            st.plotly_chart(px.line(trend_data, x='Month', y='Rating', markers=True), use_container_width=True)

# --- AUDIT SECTION ---
else:
    st.title("🛡️ Performance Audit Section")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty:
        log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Rating', 'Comments', 'Recommended', 'Justification', 'Timestamp'])
        audit_df = pd.merge(log_df.sort_values('Timestamp', ascending=False), master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
