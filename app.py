import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance Capture", layout="wide", page_icon="🎯")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    # ttl=0 ensures we always get the freshest data from Google Sheets
    return conn.read(worksheet=sheet_name, ttl=0)

def get_next_month(current_month):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        idx = months.index(current_month)
        return months[(idx + 1) % 12]
    except:
        return "Jan"

# --- Navigation ---
st.sidebar.title("Jarvis Menu")
page = st.sidebar.radio("Navigate to:", ["1. Master List", "2. Performance Capture", "3. Analytics & Export"])

# --- SCREEN 1: MASTER LIST ---
if page == "1. Master List":
    st.header("👤 Resource Master List")
    st.subheader("Add New Resource & Goals")
    
    with st.form("master_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Resource Name*")
        proj = col2.text_input("Project Name*")
        desig = col1.selectbox("Designation", ["Developer", "Senior Developer", "Lead", "Manager", "QA", "Designer"])
        exp = col2.text_input("Experience (Years/Months)")
        
        goal = st.text_area("Primary Goal Description")
        month = st.selectbox("Target Completion Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        if st.form_submit_button("Save Resource to Master"):
            if name and proj:
                new_row = pd.DataFrame([{
                    "Resource Name": name, "Goal": goal, "Month": month, 
                    "Project": proj, "Experience": exp, "Designation": desig
                }])
                master_df = get_data("Master_List")
                updated_df = pd.concat([master_df, new_row], ignore_index=True)
                conn.update(worksheet="Master_List", data=updated_df)
                st.success(f"Resource {name} successfully added to {proj}!")
            else:
                st.error("Please fill in the required fields (*) to proceed.")

    st.divider()
    st.subheader("Current Master Database")
    st.dataframe(get_data("Master_List"), use_container_width=True)

# --- SCREEN 2: PERFORMANCE CAPTURE ---
elif page == "2. Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    
    if not master_df.empty:
        # Filtering logic
        st.sidebar.subheader("Filters")
        proj_filter = st.sidebar.selectbox("Filter by Project", master_df["Project"].unique())
        
        filtered_resources = master_df[master_df["Project"] == proj_filter]
        sel_res = st.selectbox("Select Resource to Evaluate", filtered_resources["Resource Name"].unique())
        
        # Pull Goal Data
        res_info = filtered_resources[filtered_resources["Resource Name"] == sel_res].iloc[0]
        st.info(f"**Assigned Goal for {res_info['Month']}:** {res_info['Goal']}")

        # Evaluation Form
        with st.container(border=True):
            status = st.selectbox("Goal Status", ["Achieved", "Partially Achieved", "Not Completed"])
            
            # Logic based on requirements
            perc, revised, justification = 100, "N/A", ""
            
            if status == "Achieved":
                justification = st.text_area("Justification (Comments & Attachment Links)")
                st.file_uploader("Upload Attachments for Justification")
                
            elif status == "Partially Achieved":
                perc = st.slider("Percentage of Completion (%)", 0, 99)
                justification = st.text_area("Justification for Partial Completion")
                
            elif status == "Not Completed":
                perc = 0
                justification = st.text_area("Reason for Non-Completion")
                revised = st.text_input("Revised Date/Month to Close")

            rating = st.feedback("stars") # 1 to 5 stars
            final_fb = st.text_area("Final Feedback / Suggestions")

            c1, c2 = st.columns(2)
            
            if c1.button("💾 Save Performance Record", use_container_width=True):
                log_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Resource Name": sel_res, "Project": proj_filter, "Status": status,
                    "Rating": (rating + 1) if rating is not None else 0,
                    "Comments": justification, "Completion %": perc, 
                    "Revised Date": revised, "Feedback": final_fb
                }])
                log_df = get_data("Performance_Log")
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, log_row], ignore_index=True))
                st.success(f"Performance for {sel_res} has been logged.")

            if c2.button("➕ Extend Goal to Next Month", use_container_width=True):
                next_mo = get_next_month(res_info['Month'])
                ext_row = pd.DataFrame([{
                    "Resource Name": sel_res, "Goal": res_info['Goal'], 
                    "Month": next_mo, "Project": proj_filter, 
                    "Experience": res_info['Experience'], "Designation": res_info['Designation']
                }])
                updated_master = pd.concat([master_df, ext_row], ignore_index=True)
                conn.update(worksheet="Master_List", data=updated_master)
                st.warning(f"Goal extended! {sel_res} now has a duplicate goal for {next_mo}.")
    else:
        st.warning("No resources found. Please populate the Master List first.")

# --- SCREEN 3: ANALYTICS & EXCEL EXPORT ---
else:
    st.header("📊 Performance Analytics & Export")
    perf_df = get_data("Performance_Log")
    
    if not perf_df.empty:
        st.dataframe(perf_df, use_container_width=True)
        
        # Prepare Excel file
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            perf_df.to_excel(writer, index=False, sheet_name='Performance_Report')
        
        st.download_button(
            label="📥 Export Full Report to Excel",
            data=buffer.getvalue(),
            file_name=f"Performance_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
    else:
        st.info("No performance records found to export.")
