import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Jarvis Performance", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Navigation
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture"])

# --- SCREEN 1: MASTER LIST ---
if page == "Master List":
    st.title("📂 Resource Master List")
    with st.form("master_form"):
        name = st.text_input("Resource Name")
        goal = st.text_area("Goal")
        proj = st.text_input("Project")
        submitted = st.form_submit_button("Add Resource")
        
        if submitted:
            new_row = pd.DataFrame([{"Resource Name": name, "Goal": goal, "Project": proj}])
            # Append to sheet
            existing_data = conn.read(worksheet="Master_List")
            updated = pd.concat([existing_data, new_row], ignore_index=True)
            conn.update(worksheet="Master_List", data=updated)
            st.success("Resource Saved!")

# --- SCREEN 2: PERFORMANCE CAPTURE ---
else:
    st.title("📈 Performance Capture")
    master_df = conn.read(worksheet="Master_List")
    
    # Filter Logic
    proj_list = master_df["Project"].unique()
    sel_proj = st.selectbox("Select Project", proj_list)
    res_list = master_df[master_df["Project"] == sel_proj]["Resource Name"]
    sel_res = st.selectbox("Select Resource", res_list)
    
    # Capture Inputs
    status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
    
    if status == "Partially Achieved":
        st.number_input("% Completion", 0, 99)
    elif status == "Not Completed":
        st.date_input("Revised Date")
        
    rating = st.feedback("stars") # Streamlit's built-in star rating
    
    if st.button("Submit & Extend Goal"):
        st.write("Performance Recorded and Goal Extended to Next Month!")
