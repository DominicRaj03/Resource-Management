import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# Robust Plotly Import for Analytics
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V4.0", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V4.0")
page = st.sidebar.radio("Navigation", ["App User Guide", "Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN 1: APP USER GUIDE (NEW) ---
if page == "App User Guide":
    st.header("📖 Application Overview & Guide")
    st.markdown("""
    ### **What is this App?**
    This is a centralized Performance Management System designed to track resource goals, monthly achievements, and visual growth trends.
    
    ### **How to use it:**
    1.  **Master List**: Register new team members, assign them to projects, and set their primary goals for specific months.
    2.  **Performance Capture**: This is the evaluation screen. Select a resource, view their current and historical goals, provide a rating (1-5 stars), and **upload evidence** for their work.
    3.  **Historical View**: A tabular log of every submission. You can download the entire history as an Excel file here.
    4.  **Analytics Dashboard**: Visualized trends showing how individuals compare against the team average and their goal completion distribution.
    
    ### **Latest Fixes (V4.0):**
    * Restored **Evidence Attachment** field in the Capture screen.
    * Fixed **Timestamp KeyError** which caused crashes on new datasets.
    * Added **Comparative Month-on-Month Graphs** for Teams and Individuals.
    """)

# --- SCREEN 2: MASTER LIST ---
elif page == "Master List":
    st.header("👤 Resource Master List")
    with st.form("m_form", clear_on_submit=True):
        n, p = st.text_input("Name*"), st.text_input("Project*")
        g = st.text_area("Goal")
        y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        if st.form_submit_button("Save Resource"):
            if n and p:
                new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
                conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_r], ignore_index=True))
                st.success(f"Resource {n} registered successfully!")

# --- SCREEN 3: PERFORMANCE CAPTURE (RESTORED EVIDENCE) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Filter Project", sorted(master_df["Project"].unique()))
        res_options = sorted(master_df[master_df["Project"] == proj_filter]["Resource Name"].unique())
        sel_res = st.selectbox("Select Resource", res_options)
        matched = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)]
        
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Current Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            
            # FIXED: Timestamp KeyError check
            if not log_df.empty and "Timestamp" in log_df.columns:
                history = log_df[log_df["Resource Name"] == sel_res].sort_values("Timestamp", ascending=False).head(3)
                if not history.empty:
                    with st.expander("🔍 View Goal History (Last 3 Months)"):
                        st.table(history[["MM/YYYY", "Goal", "Status", "Rating"]])

            with st.form("capture_form"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                feedback = st.text_area("Overall Feedback")
                # RESTORED: Evidence Attachment Field
                uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
                rating = st.feedback("stars")
                
                if st.form_submit_button("💾 Save Record"):
                    if status != "Achieved" and not comments.strip():
                        st.error("Justification is mandatory for non-achieved goals!")
                    else:
                        period = f"{res_info['Month']}/{res_info['Year']}"
                        save_df = log_df.copy()
                        if not save_df.empty:
                            save_df = save_df[~((save_df["Resource Name"] == sel_res) & (save_df["MM/YYYY"] == period))]

                        # FIXED SyntaxErrors
                        new_entry = pd.DataFrame([{
                            "Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": period,
                            "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                            "Comments": comments, "Feedback": feedback, 
                            "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        conn.update(worksheet="Performance_Log", data=pd.concat([save_df, new_entry], ignore_index=True))
                        st.success("Record Saved!")

# --- SCREEN 5: ANALYTICS DASHBOARD (EXPANDED) ---
elif page == "Analytics Dashboard":
    st.header("📊 Performance Analytics")
    df = get_data("Performance_Log")
    
    if not df.empty and HAS_PLOTLY:
        st.caption(f"🔄 Last Synced: {datetime.now().strftime('%H:%M:%S')}")
        
        # Select for Filtering
        sel_p = st.selectbox("Select Project for Analytics", sorted(df["Project"].unique()))
        p_df = df[df["Project"] == sel_p]
        
        # 1. Team's Overall Graph (Monthly)
        st.subheader("🌐 Team Monthly Performance Trend")
        team_trend = df[df["Project"] == sel_p].groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig_team = px.line(team_trend, x="MM/YYYY", y="Rating", markers=True, title="Average Team Rating by Month")
        st.plotly_chart(fig_team, use_container_width=True)

        st.divider()

        # 2. Individual Overall Graph (Monthly)
        st.subheader("👤 Individual Performance Benchmarking")
        sel_user = st.selectbox("Select Individual", sorted(p_df["Resource Name"].unique()))
        user_trend = p_df[p_df["Resource Name"] == sel_user][["MM/YYYY", "Rating"]]
        
        fig_indiv = go.Figure()
        fig_indiv.add_trace(go.Scatter(x=team_trend["MM/YYYY"], y=team_trend["Rating"], name="Team Avg", line=dict(dash='dash', color='gray')))
        fig_indiv.add_trace(go.Scatter(x=user_trend["MM/YYYY"], y=user_trend["Rating"], name=sel_user, mode='lines+markers', line=dict(color='blue')))
        st.plotly_chart(fig_indiv, use_container_width=True)

        st.divider()

        # 3. Goal Achieved vs Partial vs Not Completed (Individual)
        st.subheader(f"🎯 Goal Breakdown: {sel_user}")
        user_stats = p_df[p_df["Resource Name"] == sel_user]["Status"].value_counts().reset_index()
        fig_pie = px.pie(user_stats, names='Status', values='count', hole=0.4, 
                         color_discrete_map={"Achieved": "green", "Partially Achieved": "orange", "Not Completed": "red"})
        st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.warning("Please log performance data to view charts.")

# --- SCREEN 4: HISTORICAL VIEW ---
else: 
    st.header("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Download Excel", buffer.getvalue(), "Performance.xlsx")
