import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V1.4", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0)

# --- Navigation ---
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View"])

# --- SCREEN 1: MASTER LIST ---
if page == "Master List":
    st.header("👤 Resource Master List")
    with st.form("master_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Resource Name*")
        proj = col2.text_input("Project Name*")
        goal = st.text_area("Primary Goal")
        year = st.selectbox("Year", ["2025", "2026", "2027"])
        month = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        if st.form_submit_button("Save Resource"):
            if name and proj:
                new_row = pd.DataFrame([{"Resource Name": name, "Goal": goal, "Month": month, "Year": year, "Project": proj}])
                df = get_data("Master_List")
                conn.update(worksheet="Master_List", data=pd.concat([df, new_row], ignore_index=True))
                st.success(f"Saved {name} for {month} {year}!")

# --- SCREEN 2: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Filter Project", master_df["Project"].unique())
        res_options = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Select Resource", res_options)
        
        res_info = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)].iloc[-1]
        st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")

        status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
        rating = st.feedback("stars")
        
        if st.button("💾 Save & Prevent Duplicates"):
            curr_period = f"{res_info['Month']}/{res_info['Year']}"
            log_df = get_data("Performance_Log")
            
            duplicate_mask = (log_df["Resource Name"] == sel_res) & \
                             (log_df["Project"] == proj_filter) & \
                             (log_df["MM/YYYY"] == curr_period)
            
            if not log_df[duplicate_mask].empty:
                st.warning("Previous entry found for this month. Overwriting...")
                log_df = log_df[~duplicate_mask]

            new_log = pd.DataFrame([{
                "Project": proj_filter, "Resource Name": sel_res,
                "MM/YYYY": curr_period, "Goal": res_info['Goal'],
                "Status": status, "Rating": (rating + 1) if rating is not None else 0
            }])
            
            conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_log], ignore_index=True))
            st.success("Record Saved Successfully!")

# --- SCREEN 3: HISTORICAL VIEW ---
else:
    st.header("📅 Monthly Performance Overview")
    log_df = get_data("Performance_Log")
    
    if not log_df.empty:
        # --- NEW: PROJECT METRICS ---
        proj_list = log_df["Project"].unique()
        sel_proj_stat = st.selectbox("Select Project for Summary", proj_list)
        proj_subset = log_df[log_df["Project"] == sel_proj_stat]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Average Rating", f"{proj_subset['Rating'].mean():.1f} / 5")
        m2.metric("Total Reviews", len(proj_subset))
        m3.metric("Achievement Rate", f"{(len(proj_subset[proj_subset['Status'] == 'Achieved']) / len(proj_subset) * 100):.1f}%")
        
        st.divider()
        
        # Table View
        cols = ["Project", "Resource Name", "MM/YYYY", "Goal", "Status", "Rating"]
        st.dataframe(log_df[cols], use_container_width=True)
        
        # Trend Chart
        st.subheader("📊 Performance Trends")
        chart_res = st.selectbox("Select Resource to View Trend", log_df["Resource Name"].unique())
        trend_data = log_df[log_df["Resource Name"] == chart_res].sort_values(by="MM/YYYY")
        st.line_chart(data=trend_data, x="MM/YYYY", y="Rating")
        
        # Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            log_df.to_excel(writer, index=False, sheet_name='Performance')
        st.download_button("📥 Download Excel", buffer.getvalue(), "Performance_Report.xlsx")
