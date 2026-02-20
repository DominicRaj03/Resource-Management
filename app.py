import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Config ---
st.set_page_config(page_title="Resource Management System", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0)

# --- Navigation ---
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture"])

# --- SCREEN 1: MASTER LIST ---
if page == "Master List":
    st.title("📂 Resource Master List")
    
    with st.form("add_resource_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Resource Name*")
        desig = col2.text_input("Designation")
        exp = col1.text_input("Experience")
        proj = col2.text_input("Project Name*")
        goal = st.text_area("Goal Description")
        month = st.selectbox("Completion Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        if st.form_submit_button("Add to Master List"):
            if name and proj:
                new_data = pd.DataFrame([{
                    "Resource Name": name, "Goal": goal, "Month": month, 
                    "Project": proj, "Experience": exp, "Designation": desig
                }])
                master_df = get_data("Master_List")
                updated_df = pd.concat([master_df, new_data], ignore_index=True)
                conn.update(worksheet="Master_List", data=updated_df)
                st.success(f"Resource {name} added!")
            else:
                st.error("Please fill in Name and Project.")

    st.subheader("Current Resources")
    st.dataframe(get_data("Master_List"), use_container_width=True)

# --- SCREEN 2: PERFORMANCE CAPTURE ---
else:
    st.title("📈 Performance Capture")
    master_df = get_data("Master_List")
    
    if master_df.empty:
        st.warning("No resources found. Please add them in the Master List first.")
    else:
        # Filters
        proj_list = master_df["Project"].unique()
        selected_proj = st.sidebar.selectbox("Filter by Project", proj_list)
        
        res_list = master_df[master_df["Project"] == selected_proj]["Resource Name"].tolist()
        selected_res = st.selectbox("Select Resource", res_list)
        
        # Get selected resource's goal
        current_goal = master_df[(master_df["Resource Name"] == selected_res) & (master_df["Project"] == selected_proj)]["Goal"].values[0]
        st.info(f"**Target Goal:** {current_goal}")

        # Review Form
        with st.container(border=True):
            status = st.radio("Goal Status", ["Achieved", "Partially Achieved", "Not Completed"], horizontal=True)
            
            # Conditional Inputs
            perc_comp = 100
            revised_date = ""
            if status == "Partially Achieved":
                perc_comp = st.number_input("Percentage of Completion (%)", 0, 99)
                justification = st.text_area("Justification")
            elif status == "Not Completed":
                perc_comp = 0
                revised_date = st.date_input("Revised Date/Month to Close")
                justification = st.text_area("Comments")
            else:
                justification = st.text_area("Justification & Comments")
                st.file_uploader("Upload Attachments (Optional)")

            rating = st.feedback("stars") # Built-in 5-star rating (0-4 index)
            final_feedback = st.text_area("Final Feedback / Suggestions")

            col_a, col_b = st.columns(2)
            
            # Save Action
            if col_a.button("Submit Performance Log"):
                perf_row = pd.DataFrame([{
                    "Resource Name": selected_res, "Project": selected_proj, "Status": status,
                    "Rating": (rating + 1) if rating is not None else 0, "Comments": justification,
                    "Completion %": perc_comp, "Revised Date": str(revised_date), "Feedback": final_feedback
                }])
                log_df = get_data("Performance_Log")
                updated_log = pd.concat([log_df, perf_row], ignore_index=True)
                conn.update(worksheet="Performance_Log", data=updated_log)
                st.success("Performance recorded!")

            # Extend Goal Action
            if col_b.button("Extend Goal to Next Period"):
                new_row = master_df[master_df["Resource Name"] == selected_res].copy()
                # logic to move month could be added here
                updated_master = pd.concat([master_df, new_row], ignore_index=True)
                conn.update(worksheet="Master_List", data=updated_master)
                st.info("Goal extended in Master List.")

        # Export to Excel
        st.divider()
        if st.button("Generate Excel Report"):
            full_log = get_data("Performance_Log")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                full_log.to_excel(writer, index=False, sheet_name='Performance_Report')
            
            st.download_button(
                label="📥 Download Excel File",
                data=buffer.getvalue(),
                file_name=f"Performance_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
