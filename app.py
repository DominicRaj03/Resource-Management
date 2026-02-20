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
st.set_page_config(page_title="Resource Management V5.0", layout="wide")

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
st.sidebar.title("Resource Management V5.0")
page = st.sidebar.radio("Navigation", ["App User Guide", "Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN 1: APP USER GUIDE (SPOTLIGHT & WARNINGS) ---
if page == "App User Guide":
    st.title("🛠️ Resource Management")
    st.header("Application Overview & Spotlight")
    
    df_log = get_data("Performance_Log")
    
    if not df_log.empty:
        # 1. Top 3 Performers Spotlight
        st.subheader("🌟 Top 3 Performers (Current Year)")
        top_3 = df_log.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        cols = st.columns(3)
        icons = ["🥇", "🥈", "🥉"]
        for i, (name, rating) in enumerate(top_3.items()):
            cols[i].metric(label=f"{icons[i]} {name}", value=f"{rating:.2f} Stars")
        
        st.divider()

        # 2. Performance Warning Section (Ratings <= 2)
        st.subheader("⚠️ Performance Warnings")
        warnings = df_log[df_log["Rating"] <= 2].sort_values("Timestamp", ascending=False)
        if not warnings.empty:
            st.warning("The following resources require immediate attention due to low ratings:")
            st.dataframe(warnings[["Resource Name", "Project", "MM/YYYY", "Rating", "Comments"]], use_container_width=True)
        else:
            st.success("No critical performance warnings at this time.")

    st.markdown("""
    ---
    ### **System Modules**
    * **User Guide**: View the Yearly Spotlight and critical Performance Warnings.
    * **Master List**: Onboard resources and define monthly goals.
    * **Performance Capture**: Evaluates goals, star ratings, and **evidence upload**.
    * **Analytics**: Full data visualization including Team Trends and Leaderboards.
    """)

# --- SCREEN 5: ANALYTICS DASHBOARD ---
elif page == "Analytics Dashboard":
    st.header("📊 Performance Analytics")
    df = get_data("Performance_Log")
    
    if not df.empty and HAS_PLOTLY:
        # Leaderboard
        st.subheader("🏆 Yearly Leaderboard")
        leaderboard = df.groupby("Resource Name")["Rating"].mean().reset_index().sort_values(by="Rating", ascending=False).reset_index(drop=True)
        leaderboard.index += 1
        
        c1, c2 = st.columns([1, 2])
        with c1: st.dataframe(leaderboard)
        with c2: st.plotly_chart(px.bar(leaderboard, x="Resource Name", y="Rating", color="Rating", color_continuous_scale='Greens'), use_container_width=True)

        st.divider()

        # Team & Individual Trends
        sel_p = st.selectbox("Select Project", sorted(df["Project"].unique()))
        p_df = df[df["Project"] == sel_p]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌐 Team Monthly Trend")
            team_trend = p_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
            st.plotly_chart(px.line(team_trend, x="MM/YYYY", y="Rating", markers=True), use_container_width=True)
        
        with col2:
            st.markdown("#### 👤 Individual Benchmarking")
            sel_user = st.selectbox("Select Individual", sorted(p_df["Resource Name"].unique()))
            user_trend = p_df[p_df["Resource Name"] == sel_user][["MM/YYYY", "Rating"]]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=team_trend["MM/YYYY"], y=team_trend["Rating"], name="Team Avg", line=dict(dash='dash')))
            fig.add_trace(go.Scatter(x=user_trend["MM/YYYY"], y=user_trend["Rating"], name=sel_user, mode='markers+lines'))
            st.plotly_chart(fig, use_container_width=True)

        # Goal Status Breakdown
        st.divider()
        st.subheader(f"🎯 Status Distribution: {sel_user}")
        user_stats = p_df[p_df["Resource Name"] == sel_user]["Status"].value_counts().reset_index()
        st.plotly_chart(px.pie(user_stats, names='Status', values='count', hole=0.4, 
                               color_discrete_map={"Achieved": "green", "Partially Achieved": "orange", "Not Completed": "red"}), use_container_width=True)
    else:
        st.warning("Data sync required for analytics.")

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        res_list = sorted(master_df[master_df["Project"] == proj_filter]["Resource Name"].unique())
        sel_res = st.selectbox("Resource", res_list)
        matched = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)]
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            with st.form("cap_form"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
                rating = st.feedback("stars")
                if st.form_submit_button("💾 Save Record"):
                    period = f"{res_info['Month']}/{res_info['Year']}"
                    new_entry = pd.DataFrame([{
                        "Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": period,
                        "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                        "Comments": comments, "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                    st.success("Record Saved!")

# --- SCREEN: MASTER LIST ---
elif page == "Master List":
    st.header("👤 Master List")
    with st.form("m_form"):
        n, p = st.text_input("Name"), st.text_input("Project")
        g = st.text_area("Goal")
        y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        if st.form_submit_button("Save"):
            new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
            conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_r], ignore_index=True))
            st.success("Resource Added!")

# --- SCREEN: HISTORICAL VIEW ---
else: 
    st.header("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
