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

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V11", layout="wide")

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
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V11")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# Constants
years = ["2025", "2026", "2027"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
q_map = {
    "Q1 (Jan-Mar)": ["Jan", "Feb", "Mar"],
    "Q2 (Apr-Jun)": ["Apr", "May", "Jun"],
    "Q3 (Jul-Sep)": ["Jul", "Aug", "Sep"],
    "Q4 (Oct-Dec)": ["Oct", "Nov", "Dec"]
}

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    master_df = get_data("Master_List")

    with tab1:
        st.subheader("Assign Goals to Resource")
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v11", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                res_name = c1.selectbox("Resource*", sorted(master_df["Resource Name"].unique().tolist()))
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            cd1, cd2 = st.columns(2)
            y, m = cd1.selectbox("Year", years), cd2.selectbox("Month", months)
            g = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": y, "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab2:
        if not master_df.empty:
            f1 = st.selectbox("Project Filter", ["All"] + sorted(master_df["Project"].unique().tolist()))
            v_df = master_df[master_df["Project"] == f1] if f1 != "All" else master_df
            st.dataframe(v_df, use_container_width=True)

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
            with st.form("capture_v11"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Comments*")
                rating = st.feedback("stars")
                if st.form_submit_button("💾 Save Performance"):
                    new_e = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", 
                        "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), 
                        "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: HISTORICAL VIEW (UNIFIED AUDIT) ---
elif page == "Historical View":
    st.title("📅 Unified Historical Audit")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        master_prep = master_df.copy()
        master_prep['MM/YYYY'] = master_prep['Month'] + "/" + master_prep['Year']
        
        req_cols = ['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp']
        if not log_df.empty:
            existing_log_cols = [c for c in req_cols if c in log_df.columns]
            log_subset = log_df[existing_log_cols].copy()
            log_subset = log_subset.drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
            unified_df = pd.merge(master_prep, log_subset, on=['Resource Name', 'Goal'], how='left')
        else:
            unified_df = master_prep.copy()
            for col in ['Status', 'Rating', 'Timestamp']: unified_df[col] = None

        unified_df['Status'] = unified_df['Status'].fillna('⏳ Pending Evaluation')
        unified_df['Rating'] = unified_df['Rating'].fillna('None')
        unified_df['Timestamp'] = unified_df['Timestamp'].fillna('N/A')
        
        c1, c2 = st.columns(2)
        f_p = c1.selectbox("Filter Project", ["All"] + sorted(unified_df["Project"].unique().tolist()))
        f_v = c2.radio("View Mode", ["All Goals", "Evaluated Only", "Pending Only"], horizontal=True)
        
        final_df = unified_df.copy()
        if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
        if f_v == "Evaluated Only": final_df = final_df[final_df["Status"] != '⏳ Pending Evaluation']
        elif f_v == "Pending Only": final_df = final_df[final_df["Status"] == '⏳ Pending Evaluation']
        
        st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']], use_container_width=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: final_df.to_excel(writer, index=False)
        st.download_button("📥 Export Audit Excel", data=buf.getvalue(), file_name="Unified_Audit_V11.xlsx")

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        t1, t2 = st.columns(2)
        sel_y, sel_p = t1.selectbox("Filter Year", years), t2.selectbox("Filter Period", ["Full Year"] + list(q_map.keys()))
        f_df = df[df["MM/YYYY"].str.contains(sel_y)]
        if sel_p != "Full Year":
            f_df = f_df[f_df["MM/YYYY"].str.split('/').str[0].isin(q_map[sel_p])]

        if not f_df.empty:
            st.subheader("🌟 Top 3 Performers")
            top_3 = f_df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
            cols = st.columns(3)
            for i, (name, rating) in enumerate(top_3.items()):
                cols[i].metric(label=name, value=f"{rating:.2f} ⭐")
            
            st.divider(); st.subheader("🏥 Project Health Index")
            health = f_df.groupby("Project").agg(
                Total_Goals=('Goal', 'count'),
                Success_Rate=('Status', lambda x: f"{(x=='Achieved').sum()/len(x)*100:.1f}%"),
                Avg_Rating=('Rating', 'mean')
            ).reset_index()
            st.table(health)

            if HAS_PLOTLY:
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.pie(f_df, names='Status', hole=0.4, title="Overall Status Ratio"), use_container_width=True)
                with c2:
                    trend = f_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
                    trend['Date_Sort'] = pd.to_datetime(trend['MM/YYYY'], format='%b/%Y')
                    trend = trend.sort_values('Date_Sort')
                    st.plotly_chart(px.line(trend, x="MM/YYYY", y="Rating", markers=True, title="Rating Trend"), use_container_width=True)
