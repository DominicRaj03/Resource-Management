import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# Attempt to import plotly; provide a fallback if not installed yet
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ModuleNotFoundError:
    HAS_PLOTLY = False

# --- Page Config ---
st.set_page_config(page_title="Jarvis Performance V2.9", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        # Fix for the KeyError and .0 issue: Convert Year and Month to clean strings
        if not df.empty:
            if "Year" in df.columns:
                df["Year"] = df["Year"].astype(str).replace(r'\.0$', '', regex=True)
            if "Month" in df.columns:
                df["Month"] = df["Month"].astype(str)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V2.9")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard", "App User Guide"])

# --- USER GUIDE ---
if page == "App User Guide":
    st.header("📖 Application User Guide")
    st.info("To fix the 'ModuleNotFoundError', ensure 'plotly' is added to your requirements.txt file.")
    st.markdown("""
    * **Step 1**: Register in 'Master List'.
    * **Step 2**: Rate in 'Performance Capture'.
    * **Step 3**: View Trends in 'Analytics'.
    """)

# --- MASTER LIST ---
elif page == "Master List":
    st.header("👤 Resource Master List")
    with st.form("master_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name, proj = col1.text_input("Resource Name*"), col2.text_input("Project Name*")
        goal, actions = st.text_area("Primary Goal"), st.text_area("Specific Action Items")
        year = st.selectbox("Year", ["2025", "2026", "2027"])
        month = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        if st.form_submit_button("Save Resource"):
            if name and proj:
                new_row = pd.DataFrame([{"Resource Name": name, "Goal": goal, "Action Items": actions, "Month": month, "Year": year, "Project": proj}])
                conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_row], ignore_index=True))
                st.success("Resource Saved!")

# --- PERFORMANCE CAPTURE (FIXED) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    
    if not master_df.empty:
        proj_filter = st.sidebar.selectbox("Filter Project", master_df["Project"].unique())
        res_list = master_df[master_df["Project"] == proj_filter]["Resource Name"].unique()
        sel_res = st.selectbox("Select Resource", res_list)
        
        # Safe lookup for res_info to prevent KeyError
        matched_rows = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)]
        if not matched_rows.empty:
            res_info = matched_rows.iloc[-1]
            st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            
            status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
            comments = st.text_area("Justification / Comments*")
            feedback = st.text_area("Overall Feedback")
            uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg'])
            rating = st.feedback("stars")
            
            if st.button("💾 Save Record"):
                if status != "Achieved" and not comments.strip():
                    st.error("Comments mandatory for non-achieved goals!")
                else:
                    log_df = get_data("Performance_Log")
                    curr_period = f"{res_info['Month']}/{res_info['Year']}"
                    
                    new_entry = pd.DataFrame([{
