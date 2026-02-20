import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V2.7", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        # ttl=0 ensures real-time data fetching
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V2.7")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN 1: MASTER LIST ---
if page == "Master List":
    st.header("👤 Resource Master List")
    with st.form("master_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name, proj = col1.text_input("Resource Name*"), col2.text_input("Project Name*")
        goal, actions = st.text_area("Primary Goal"), st.text_area("Specific Action Items")
        year, month = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        if st.form_submit_button("Save Resource"):
            if name and proj:
                new_row = pd.DataFrame([{"Resource Name": name, "Goal": goal, "Action Items": actions, "Month": str(month), "Year": str(year), "Project": proj}])
                conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_row], ignore_index=True))
                st.success(f"Resource {name} Saved Successfully!")

# --- SCREEN 2: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Filter Project", master_df["Project"].unique())
        res_list = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Select Resource", res_list)
        res_info = master_df[(master_df["Resource Name"] == sel_res)].iloc[-1]
        
        st.info(f"**Current Goal:** {res_info['Goal']}")
        st.warning(f"**Action Items:** {res_info.get('Action Items', 'None')}")

        status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
        comments = st.text_area("Justification / Comments*")
        feedback = st.text_area("Overall Feedback")
        uploaded_file = st.file_uploader("Upload Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
        rating = st.feedback("stars")
        
        if st.button("💾 Save Performance Record"):
            if status != "Achieved" and not comments.strip():
                st.error("Justification is mandatory for non-achieved goals!")
            else:
                log_df = get_data("Performance_Log")
                # Remove duplicates for the same month/year/resource
                curr_period = f"{res_info['Month']}/{res_info['Year']}"
                if not log_df.empty:
                    mask = (log_df["Resource Name"] == sel_res) & (log_df["MM/YYYY"] == curr_period)
                    log_df = log_df[~mask]

                new_entry = pd.DataFrame([{
                    "Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": curr_period,
                    "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                    "Comments": comments, "Feedback": feedback, 
                    "Evidence_Filename": (uploaded_file.name if uploaded_file else "None"),
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                st.success("Performance Logged!")

# --- SCREEN 3: HISTORICAL VIEW (WITH FILTERS) ---
elif page == "Historical View":
    st.header("📅 Historical Logs & Auditing")
    df = get_data("Performance_Log")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_proj = st.selectbox("Project Filter", ["All"] + sorted(df["Project"].unique().tolist()))
        with c2:
            sel_stat = st.selectbox("Status Filter", ["All", "Achieved", "Partially Achieved", "Not Completed"])
        with c3:
            search = st.text_input("Search Name")
        
        display_df = df.copy()
        if sel_proj != "All": display_df = display_df[display_df["Project"] == sel_proj]
        if sel_stat != "All": display_df = display_df[display_df["Status"] == sel_stat]
        if search: display_df = display_df[display_df["Resource Name"].str.contains(search, case=False)]
            
        st.dataframe(display_df, use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Performance')
        st.download_button(f"📥 Download Excel", buffer.getvalue(), f"Performance_Audit.xlsx")

# --- SCREEN 4: ANALYTICS DASHBOARD ---
else:
    st.header("📊 Analytics & Project Health")
    df = get_data("Performance_Log")
    if not df.empty:
        col_gauge, col_lead = st.columns([1, 2])
        with col_gauge:
            sel_p = st.selectbox("Health Gauge Project", df["Project"].unique())
            p_df = df[df["Project"] == sel_p]
            h_pct = (len(p_df[p_df["Status"] == "Achieved"]) / len(p_df) * 100) if len(p_df) > 0 else 0
            fig = go.Figure(go.Indicator(mode="gauge+number", value=h_pct, title={'text': "Achievement %"},
                gauge={'axis': {'range': [0, 100]}, 'steps': [
                    {'range': [0, 50], 'color': "red"}, 
                    {'range': [50, 80], 'color': "yellow"}, 
                    {'range': [80, 100], 'color': "green"}]}))
            st.plotly_chart(fig, use_container_width=True)
        
        with col_lead:
            curr_m = st.selectbox("Leaderboard Month", df["MM/YYYY"].unique())
            top_df = df[df["MM/YYYY"] == curr_m].sort_values(by="Rating", ascending=False).head(3)
            l_cols = st.columns(3)
            podium = ["🥇 1st", "🥈 2nd", "🥉 3rd"]
            for i, (idx, row) in enumerate(top_df.iterrows()):
                with l_cols[i]: st.metric(podium[i], row["Resource Name"], f"Rating: {row['Rating']}")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Team Rating Trend")
            team_trend = df.groupby("MM/YYYY")["Rating"].mean().reset_index()
            st.plotly_chart(px.line(team_trend, x="MM/YYYY", y="Rating", markers=True), use_container_width=True)
        with c2:
            st.subheader("Individual Growth")
            sel_user = st.selectbox("Select Resource", df["Resource Name"].unique())
            user_df = df[df["Resource Name"] == sel_user].sort_values("Timestamp")
            st.plotly_chart(px.bar(user_df, x="MM/YYYY", y="Rating", color="Status"), use_container_width=True)
