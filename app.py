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
st.set_page_config(page_title="Resource Management V11.7", layout="wide")

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
st.sidebar.title("Resource Management V11.7")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST (Includes History & Entire Goal List) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (Goal History)"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v11_7", clear_on_submit=True):
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
            # 1. Merge logic to show status for EVERY goal
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

            # 2. Filters
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

            # 3. Coloring
            def color_status(val):
                color = '#90EE90' if val == 'Achieved' else '#FFCCCB' if val == 'Not Completed' else '#FFFFE0' if val == 'Partially Achieved' else 'white'
                return f'background-color: {color}; color: black'

            st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']].style.applymap(color_status, subset=['Status']), use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: final_df.to_excel(writer, index=False)
            st.download_button("📥 Export History", data=buf.getvalue(), file_name="Goal_History.xlsx")

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
            with st.form("cap_v11_7"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    
    if not df.empty and HAS_PLOTLY:
        # Pre-processing for time-series
        df['Date_Sort'] = pd.to_datetime(df['MM/YYYY'], format='%b/%Y', errors='coerce')
        df = df.sort_values('Date_Sort')

        # 1. Team Overall Graph (Monthly Ratings)
        st.subheader("📈 Team Monthly Performance Trend")
        team_trend = df.groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig1 = px.line(team_trend, x="MM/YYYY", y="Rating", markers=True, title="Team Average Rating per Month")
        st.plotly_chart(fig1, use_container_width=True)

        # 2. Individual Overall Graph (Monthly Ratings)
        st.divider()
        st.subheader("👤 Individual Monthly Trends")
        sel_res = st.selectbox("Filter Individual", sorted(df["Resource Name"].unique()))
        ind_trend = df[df["Resource Name"] == sel_res].groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig2 = px.bar(ind_trend, x="MM/YYYY", y="Rating", color="Rating", title=f"Rating Trend for {sel_res}")
        st.plotly_chart(fig2, use_container_width=True)

        # 3. Goal Status (Achieved vs Partial vs Not Completed)
        st.divider()
        st.subheader("🎯 Goal Completion Analysis (Individual)")
        status_dist = df[df["Resource Name"] == sel_res]["Status"].value_counts().reset_index()
        status_dist.columns = ['Status', 'Count']
        fig3 = px.pie(status_dist, values='Count', names='Status', hole=0.4, title=f"Goal Distribution for {sel_res}")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("No performance data available for analytics yet.")
