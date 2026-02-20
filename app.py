import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# Robust Plotly Import
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V3.3", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            # FIX: Force Years/Months to clean strings to remove .0 decimal issue
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V3.3")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN 4: ANALYTICS DASHBOARD ---
if page == "Analytics Dashboard":
    st.header("📊 Advanced Performance Analytics")
    df = get_data("Performance_Log")
    
    if not df.empty:
        # 1. Project Summary & Team Stats
        st.subheader("👥 Project Overview")
        summary_df = df.groupby("Project")["Resource Name"].nunique().reset_index()
        summary_df.columns = ["Project Name", "Headcount"]
        st.table(summary_df)

        st.divider()

        # 2. Comparison Analytics
        st.subheader("📈 Individual vs. Project Average")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_proj_comp = st.selectbox("Select Project", df["Project"].unique())
        with col_f2:
            res_options = df[df["Project"] == sel_proj_comp]["Resource Name"].unique()
            sel_res_comp = st.selectbox("Select Resource to Compare", res_options)

        if HAS_PLOTLY:
            # Data Processing for Comparison
            proj_data = df[df["Project"] == sel_proj_comp]
            team_avg = proj_data.groupby("MM/YYYY")["Rating"].mean().reset_index()
            team_avg.columns = ["MM/YYYY", "Team Average"]

            indiv_data = proj_data[proj_data["Resource Name"] == sel_res_comp][["MM/YYYY", "Rating"]]
            indiv_data.columns = ["MM/YYYY", f"{sel_res_comp}'s Rating"]

            # Merge for Charting
            comp_df = pd.merge(team_avg, indiv_data, on="MM/YYYY", how="left")
            
            fig_comp = px.line(comp_df, x="MM/YYYY", y=["Team Average", f"{sel_res_comp}'s Rating"],
                              markers=True, title=f"Performance Benchmarking: {sel_res_comp} vs. {sel_proj_comp}")
            st.plotly_chart(fig_comp, use_container_width=True)

        st.divider()

        # 3. Goal Distribution Stats
        st.subheader("🎯 Goal Status Distribution")
        proj_stats_df = df[df["Project"] == sel_proj_comp]
        total_goals = len(proj_stats_df)
        achieved = len(proj_stats_df[proj_stats_df["Status"] == "Achieved"])
        
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("Total Goals", total_goals)
        c2.metric("Achievement Rate", f"{int(achieved/total_goals*100)}%" if total_goals > 0 else "0%")
        
        if HAS_PLOTLY:
            status_counts = proj_stats_df["Status"].value_counts().reset_index()
            fig_pie = px.pie(status_counts, values='count', names='Status', hole=0.4,
                            color_discrete_map={"Achieved": "green", "Partially Achieved": "orange", "Not Completed": "red"})
            c3.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("Log your first performance entry to unlock analytics.")

# --- OTHER SCREENS (STABLE LOGIC) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Project", master_df["Project"].unique())
        res_list = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Resource", res_list)
        matched = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)]
        
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            with st.form("cap_form"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                rating = st.feedback("stars")
                if st.form_submit_button("💾 Save Record"):
                    if status != "Achieved" and not comments.strip(): st.error("Comments mandatory!")
                    else:
                        log_df = get_data("Performance_Log")
                        period = f"{res_info['Month']}/{res_info['Year']}"
                        if not log_df.empty: log_df = log_df[~((log_df["Resource Name"] == sel_res) & (log_df["MM/YYYY"] == period))]
                        new_entry = pd.DataFrame([{"Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": period, "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                        conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                        st.success("Saved!")

elif page == "Master List":
    st.header("👤 Master List")
    with st.form("m_form"):
        n, p = st.text_input("Name"), st.text_input("Project")
        g = st.text_area("Goal")
        y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        if st.form_submit_button("Save"):
            new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
            conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_r], ignore_index=True))
            st.success("Resource Saved!")

else: # Historical View
    st.header("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
