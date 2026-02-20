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
st.set_page_config(page_title="Resource Management V12.1", layout="wide")

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
st.sidebar.title("Resource Management V12.1")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST (Includes Integrated History/Goal List) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v12_1", clear_on_submit=True):
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

            # Filters for History View
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

            # Status Highlighting
            def color_status(val):
                color = '#90EE90' if val == 'Achieved' else '#FFCCCB' if val == 'Not Completed' else '#FFFFE0' if val == 'Partially Achieved' else 'white'
                return f'background-color: {color}; color: black'

            st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']].style.applymap(color_status, subset=['Status']), use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: final_df.to_excel(writer, index=False)
            st.download_button("📥 Export Goal History", data=buf.getvalue(), file_name="Master_History.xlsx")

# --- SCREEN: PERFORMANCE CAPTURE (Evaluation) ---
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
            with st.form("cap_v12_1"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save Evaluation"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") BurnedIn: True}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Evaluation Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not log_df.empty and HAS_PLOTLY:
        # Leaderboard
        st.subheader("🏆 Leaderboard")
        leaderboard = log_df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        l_cols = st.columns(len(leaderboard))
        for i, (name, score) in enumerate(leaderboard.items()):
            l_cols[i].metric(label=f"#{i+1} {name}", value=f"{score:.2f} ⭐")
        st.divider()

        # Pending Evaluation Alert
        st.subheader("⚠️ Unevaluated Goals")
        master_prep = master_df.copy()
        merged_audit = pd.merge(master_prep, log_df[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
        pending = merged_audit[merged_audit['Status'].isna()]
        if not pending.empty:
            st.warning(f"Total Pending: {len(pending)}")
            st.dataframe(pending[['Resource Name', 'Project', 'Month', 'Year', 'Goal']], use_container_width=True)
        else:
            st.success("All goals evaluated! ✅")
        st.divider()

        # Visualizations
        log_df['Date_Sort'] = pd.to_datetime(log_df['MM/YYYY'], format='%b/%Y', errors='coerce')
        log_df = log_df.sort_values('Date_Sort')

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.line(log_df.groupby("MM/YYYY")["Rating"].mean().reset_index(), x="MM/YYYY", y="Rating", markers=True, title="Team Monthly Trend"), use_container_width=True)
        with c2:
            proj_comp = log_df.groupby("Project")["Status"].value_counts(normalize=True).unstack().fillna(0) * 100
            st.plotly_chart(px.bar(proj_comp, barmode="group", title="Project Status %"), use_container_width=True)

        st.divider()
        sel_res = st.selectbox("Individual Deep Dive", sorted(log_df["Resource Name"].unique()))
        id1, id2 = st.columns(2)
        res_data = log_df[log_df["Resource Name"] == sel_res]
        with id1:
            st.plotly_chart(px.bar(res_data.groupby("MM/YYYY")["Rating"].mean().reset_index(), x="MM/YYYY", y="Rating", title=f"Rating Trend: {sel_res}"), use_container_width=True)
        with id2:
            st.plotly_chart(px.pie(res_data, names="Status", hole=0.4, title=f"Goal Distribution: {sel_res}"), use_container_width=True)
    else:
        st.warning("Insufficient performance data.")
