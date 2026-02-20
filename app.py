import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V2.4", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V2.4")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN 4: ANALYTICS & LEADERBOARD ---
if page == "Analytics Dashboard":
    st.header("📊 Performance Analytics & Leaderboard")
    df = get_data("Performance_Log")
    
    if not df.empty:
        # --- NEW: LEADERBOARD SECTION ---
        st.subheader("🏆 Monthly Top Performers")
        current_month = st.selectbox("Select Month for Leaderboard", df["MM/YYYY"].unique())
        
        # Calculate Top 3 based on Rating
        top_df = df[df["MM/YYYY"] == current_month].sort_values(by="Rating", ascending=False).head(3)
        
        cols = st.columns(3)
        podium = ["🥇 1st Place", "🥈 2nd Place", "🥉 3rd Place"]
        
        for i, (index, row) in enumerate(top_df.iterrows()):
            with cols[i]:
                st.metric(label=podium[i], value=row["Resource Name"], delta=f"Rating: {row['Rating']}")
                st.caption(f"Project: {row['Project']}")
        
        st.divider()

        # 1. Team Overall Graph
        st.subheader("📈 Team Monthly Rating Trend")
        team_trend = df.groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig1 = px.line(team_trend, x="MM/YYYY", y="Rating", markers=True, title="Team Average Performance")
        st.plotly_chart(fig1, use_container_width=True)

        # 2. Individual Overall Graph
        st.subheader("👤 Individual Growth Tracker")
        sel_user = st.selectbox("Select Resource for Analysis", df["Resource Name"].unique())
        user_df = df[df["Resource Name"] == sel_user].sort_values("Timestamp")
        fig2 = px.bar(user_df, x="MM/YYYY", y="Rating", color="Status", title=f"Performance History: {sel_user}")
        st.plotly_chart(fig2, use_container_width=True)

        # 3. Goal Achievement Breakdown
        st.subheader("🎯 Achievement Summary")
        status_counts = user_df["Status"].value_counts().reset_index()
        fig3 = px.pie(status_counts, values='count', names='Status', hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("No data found. Please capture performance first.")

# --- OTHER SCREENS (LOGIC INHERITED FROM V2.3) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Project", master_df["Project"].unique())
        res_list = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Resource", res_list)
        
        res_info = master_df[(master_df["Resource Name"] == sel_res)].iloc[-1]
        st.info(f"**Goal:** {res_info['Goal']}")
        
        status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
        comments = st.text_area("Justification / Comments*")
        uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg'])
        rating = st.feedback("stars")
        
        if st.button("💾 Save Record"):
            if status != "Achieved" and not comments.strip():
                st.error("Comments mandatory for non-achieved goals!")
            else:
                log_df = get_data("Performance_Log")
                new_entry = pd.DataFrame([{
                    "Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}",
                    "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                    "Comments": comments, "Evidence_Filename": (uploaded_file.name if uploaded_file else "None"),
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                st.success("Entry Saved!")

elif page == "Master List":
    st.header("👤 Resource Master List")
    with st.form("master_form"):
        n, p = st.text_input("Name"), st.text_input("Project")
        g, a = st.text_area("Goal"), st.text_area("Action Items")
        y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        if st.form_submit_button("Save"):
            new_m = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Action Items": a, "Year": y, "Month": m}])
            conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_m], ignore_index=True))
            st.success("Resource Saved!")

else: # Historical View
    st.header("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        search = st.text_input("Search Name")
        display_df = df[df["Resource Name"].str.contains(search, case=False)] if search else df
        st.dataframe(display_df, use_container_width=True)
