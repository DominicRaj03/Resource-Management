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

st.set_page_config(page_title="Resource Management V18.0", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

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
st.sidebar.title("Resource Management V18.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard", "Audit Section"])

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
        with st.form("goal_v18", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                r_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = c1.selectbox("Resource*", r_names)
                existing_proj = master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0]
                res_proj = c2.text_input("Project", value=existing_proj, disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            
            y, m = st.selectbox("Year", years_list), st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": str(y), "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab2:
        if not master_df.empty:
            f1, f2, f3, f4 = st.columns(4)
            sel_proj = f1.selectbox("Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            sel_res = f2.selectbox("Resource", ["All"] + sorted(master_df["Resource Name"].unique().tolist()))
            sel_year = f3.selectbox("Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
            sel_month = f4.selectbox("Month", ["All"] + months_list)

            log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Timestamp'])
            log_latest = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last') if not log_df.empty else pd.DataFrame(columns=['Resource Name', 'Goal', 'Status'])
            
            display_df = pd.merge(master_df, log_latest[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
            display_df['Status'] = display_df['Status'].fillna('Assigned')

            filtered_df = display_df.copy()
            if sel_proj != "All": filtered_df = filtered_df[filtered_df["Project"] == sel_proj]
            if sel_res != "All": filtered_df = filtered_df[filtered_df["Resource Name"] == sel_res]
            if sel_year != "All": filtered_df = filtered_df[filtered_df["Year"].astype(str) == sel_year]
            if sel_month != "All": filtered_df = filtered_df[filtered_df["Month"] == sel_month]

            st.data_editor(filtered_df, use_container_width=True, hide_index=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    if not master_df.empty:
        col1, col2 = st.columns(2)
        p_list = sorted(master_df["Project"].unique().tolist())
        sel_p = col1.selectbox("1. Choose Project", p_list, key="cap_p")
        r_list = sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist())
        sel_r = col2.selectbox("2. Choose Resource", r_list, key="cap_r")
        g_list = master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist()
        sel_g = st.selectbox("3. Select Goal", g_list, key="cap_g")
        
        record_exists = False
        if not log_df.empty:
            record_exists = not log_df[(log_df["Resource Name"] == sel_r) & (log_df["Goal"] == sel_g)].empty

        can_edit = True
        if record_exists:
            st.warning("⚠️ Goal already captured for this resource.")
            override = st.checkbox("Would you like to override previous entry?")
            can_edit = override

        if can_edit:
            with st.form("cap_v18", clear_on_submit=True):
                status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
                rating = st.feedback("stars") 
                comments = st.text_area("Comments*")
                st.divider()
                is_rec = st.checkbox("Recommend for Recognition?")
                just = st.text_area("Justification (Required if recommended)")
                
                if st.form_submit_button("💾 Save Entry"):
                    if not comments:
                        st.error("Comments are required.")
                    else:
                        new_e = pd.DataFrame([{
                            "Resource Name": sel_r, "Goal": sel_g, "Status": status,
                            "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                            "Recommended": "Yes" if is_rec else "No", "Justification": just,
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                        st.success("Entry Updated Successfully!"); st.rerun()
        else:
            st.info("Check override box above to edit.")

# --- SCREEN: ANALYTICS DASHBOARD (Dynamic Trend Graphs) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not log_df.empty and not master_df.empty:
        # Merge for full context
        log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp'])
        full_df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project', 'Year', 'Month']], on=['Resource Name', 'Goal'], how='left')
        
        # --- Filters ---
        c1, c2, c3 = st.columns(3)
        f_proj = c1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
        f_year = c2.selectbox("Filter Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
        f_month = c3.selectbox("Filter Month", ["All"] + months_list)

        filtered_df = full_df.copy()
        if f_proj != "All": filtered_df = filtered_df[filtered_df["Project"] == f_proj]
        if f_year != "All": filtered_df = filtered_df[filtered_df["Year"].astype(str) == f_year]
        if f_month != "All": filtered_df = filtered_df[filtered_df["Month"] == f_month]

        # Latest choice override for KPIs
        kpi_df = filtered_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')

        m1, m2, m3 = st.columns(3)
        m1.metric("Unique Evaluations", len(kpi_df))
        m2.metric("Achievement Rate", f"{(len(kpi_df[kpi_df['Status']=='Achieved'])/len(kpi_df)*100):.1f}%" if len(kpi_df)>0 else "0%")
        m3.metric("Avg Rating", f"{kpi_df['Rating'].mean():.1f} ⭐")

        if HAS_PLOTLY:
            st.divider()
            
            # 1. Performance Trend (Shown when "All" months or many months exist)
            if f_month == "All":
                st.subheader("📈 Performance Trend (Monthly Rating Average)")
                # Map months to numbers for sorting
                m_map = {m: i+1 for i, m in enumerate(months_list)}
                trend_df = filtered_df.copy()
                trend_df['MonthNum'] = trend_df['Month'].map(m_map)
                trend_data = trend_df.groupby(['Year', 'MonthNum', 'Month'])['Rating'].mean().reset_index().sort_values(['Year', 'MonthNum'])
                
                fig_trend = px.line(trend_data, x='Month', y='Rating', color='Year', markers=True, 
                                   title="Average Star Rating over Time", labels={'Rating': 'Avg Stars'})
                st.plotly_chart(fig_trend, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Top Performers")
                lb = kpi_df.groupby("Resource Name")["Rating"].mean().reset_index().sort_values("Rating", ascending=False)
                st.plotly_chart(px.bar(lb.head(10), x="Rating", y="Resource Name", orientation='h', color="Rating"), use_container_width=True)
            with col2:
                st.subheader("🎯 Goal Status Distribution")
                st.plotly_chart(px.pie(kpi_df, names="Status"), use_container_width=True)

# --- SCREEN: AUDIT SECTION ---
else:
    st.title("🛡️ Performance Audit Section")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not log_df.empty:
        log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Rating', 'Comments', 'Recommended', 'Justification', 'Timestamp'])
        clean_log = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
        audit_df = pd.merge(clean_log, master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        st.dataframe(audit_df.sort_values("Timestamp", ascending=False), use_container_width=True, hide_index=True)
