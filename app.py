import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V1.8", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

# --- Admin: Database Repair Logic ---
def repair_db():
    master_df = pd.DataFrame(columns=["Resource Name", "Goal", "Month", "Year", "Project", "Experience", "Designation"])
    log_df = pd.DataFrame(columns=["Project", "Resource Name", "MM/YYYY", "Goal", "Status", "Rating", "Comments", "Feedback", "Evidence_Link"])
    try:
        conn.update(worksheet="Master_List", data=master_df)
        conn.update(worksheet="Performance_Log", data=log_df)
        st.sidebar.success("Database Repaired!")
    except Exception:
        st.sidebar.error("Repair Failed: Ensure Service Account is 'Editor'.")

# --- Navigation ---
st.sidebar.title("Jarvis V1.8")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View"])

st.sidebar.divider()
if st.sidebar.button("🛠️ Repair Database"):
    repair_db()

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
                st.success(f"Saved {name}!")

# --- SCREEN 2: PERFORMANCE CAPTURE (WITH VALIDATION) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    
    if not master_df.empty and "Resource Name" in master_df.columns:
        proj_filter = st.sidebar.selectbox("Filter Project", master_df["Project"].unique())
        res_options = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Select Resource", res_options)
        
        res_info = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)].iloc[-1]
        st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")

        status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
        
        # New UI Fields
        comments = st.text_area("Justification / Comments*", help="Mandatory if status is not 'Achieved'")
        feedback = st.text_area("Overall Feedback", placeholder="Suggestions for the resource...")
        evidence = st.text_input("Evidence Link (Optional)", placeholder="URL to Jira/Drive/Docs")
        
        rating = st.feedback("stars")
        
        if st.button("💾 Save & Prevent Duplicates"):
            # --- VALIDATION CHECK ---
            if status in ["Partially Achieved", "Not Completed"] and not comments.strip():
                st.error(f"Error: Comments/Justification is mandatory when status is '{status}'.")
            else:
                curr_period = f"{res_info['Month']}/{res_info['Year']}"
                log_df = get_data("Performance_Log")
                
                if not log_df.empty and "Resource Name" in log_df.columns:
                    mask = (log_df["Resource Name"] == sel_res) & (log_df["Project"] == proj_filter) & (log_df["MM/YYYY"] == curr_period)
                    log_df = log_df[~mask]

                new_log = pd.DataFrame([{
                    "Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": curr_period,
                    "Goal": res_info['Goal'], "Status": status, "Rating": (rating + 1) if rating is not None else 0,
                    "Comments": comments, "Feedback": feedback, "Evidence_Link": evidence
                }])
                
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_log], ignore_index=True))
                st.success("Record Saved!")
    else:
        st.warning("Master List empty. Add resources first.")

# --- SCREEN 3: HISTORICAL VIEW ---
else:
    st.header("📅 Monthly Performance Overview")
    log_df = get_data("Performance_Log")
    
    if not log_df.empty:
        view_cols = ["Project", "Resource Name", "MM/YYYY", "Goal", "Status", "Rating", "Comments", "Feedback", "Evidence_Link"]
        available_cols = [c for c in view_cols if c in log_df.columns]
        st.dataframe(log_df[available_cols], use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            log_df.to_excel(writer, index=False, sheet_name='Performance')
        st.download_button("📥 Download Excel Report", buffer.getvalue(), "Performance_Export.xlsx")
