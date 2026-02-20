import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V2.0", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

# --- Admin: Database Repair Logic ---
def repair_db():
    master_df = pd.DataFrame(columns=["Resource Name", "Goal", "Action Items", "Month", "Year", "Project", "Experience", "Designation"])
    # Schema updated to include 'Evidence_Filename'
    log_df = pd.DataFrame(columns=["Project", "Resource Name", "MM/YYYY", "Goal", "Action Items", "Status", "Rating", "Comments", "Feedback", "Evidence_Filename"])
    try:
        conn.update(worksheet="Master_List", data=master_df)
        conn.update(worksheet="Performance_Log", data=log_df)
        st.sidebar.success("Database Repaired for V2.0!")
    except Exception:
        st.sidebar.error("Repair Failed: Ensure Service Account is 'Editor'.")

# --- Navigation ---
st.sidebar.title("Jarvis V2.0")
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
        actions = st.text_area("Specific Action Items")
        year = st.selectbox("Year", ["2025", "2026", "2027"])
        month = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        if st.form_submit_button("Save Resource"):
            if name and proj:
                new_row = pd.DataFrame([{
                    "Resource Name": name, "Goal": goal, "Action Items": actions,
                    "Month": month, "Year": year, "Project": proj
                }])
                df = get_data("Master_List")
                conn.update(worksheet="Master_List", data=pd.concat([df, new_row], ignore_index=True))
                st.success(f"Saved {name}!")

# --- SCREEN 2: PERFORMANCE CAPTURE (FIXED WITH FILE UPLOADER) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    
    if not master_df.empty and "Resource Name" in master_df.columns:
        proj_filter = st.sidebar.selectbox("Filter Project", master_df["Project"].unique())
        res_options = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Select Resource", res_options)
        
        res_info = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)].iloc[-1]
        
        st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
        st.warning(f"**Action Items:** {res_info.get('Action Items', 'None')}")

        status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
        
        # Capture Sections
        comments = st.text_area("Justification / Comments*")
        feedback = st.text_area("Overall Feedback")
        
        # FIXED: Replaced link field with Attachment field
        uploaded_file = st.file_uploader("Upload Evidence (Optional)", type=['pdf', 'png', 'jpg', 'docx'])
        
        rating = st.feedback("stars")
        
        if st.button("💾 Save & Prevent Duplicates"):
            if status in ["Partially Achieved", "Not Completed"] and not comments.strip():
                st.error(f"Comments are mandatory for '{status}' status.")
            else:
                curr_period = f"{res_info['Month']}/{res_info['Year']}"
                log_df = get_data("Performance_Log")
                
                if not log_df.empty and "Resource Name" in log_df.columns:
                    mask = (log_df["Resource Name"] == sel_res) & (log_df["Project"] == proj_filter) & (log_df["MM/YYYY"] == curr_period)
                    log_df = log_df[~mask]

                # Note: Streamlit Cloud does not store local files. 
                # We log the filename in the sheet for tracking.
                file_name = uploaded_file.name if uploaded_file else "No Attachment"

                new_log = pd.DataFrame([{
                    "Project": proj_filter, "Resource Name": sel_res, "MM/YYYY": curr_period,
                    "Goal": res_info['Goal'], "Action Items": res_info.get('Action Items', ''),
                    "Status": status, "Rating": (rating + 1) if rating is not None else 0,
                    "Comments": comments, "Feedback": feedback, 
                    "Evidence_Filename": file_name
                }])
                
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_log], ignore_index=True))
                st.success(f"Record Saved! Evidence tracked: {file_name}")
    else:
        st.warning("Master List empty.")

# --- SCREEN 3: HISTORICAL VIEW ---
else:
    st.header("📅 Monthly Performance Overview")
    log_df = get_data("Performance_Log")
    
    if not log_df.empty:
        view_cols = ["Project", "Resource Name", "MM/YYYY", "Goal", "Status", "Rating", "Comments", "Feedback", "Evidence_Filename"]
        available_cols = [c for c in view_cols if c in log_df.columns]
        st.dataframe(log_df[available_cols], use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            log_df.to_excel(writer, index=False, sheet_name='Performance')
        st.download_button("📥 Download Excel Report", buffer.getvalue(), "Performance_Export.xlsx")
