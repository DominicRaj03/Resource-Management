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
st.set_page_config(page_title="Jarvis Performance V3.8", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            # Clean strings to remove .0 decimal issues from Google Sheets
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V3.8")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: PERFORMANCE CAPTURE (FIXED) ---
if page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        proj_list = sorted(master_df["Project"].unique())
        proj_filter = st.sidebar.selectbox("Filter Project", proj_list)
        res_options = sorted(master_df[master_df["Project"] == proj_filter]["Resource Name"].unique())
        sel_res = st.selectbox("Select Resource", res_options)
        
        matched = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)]
        
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Current Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            
            # FIXED: KeyError 'Timestamp' safety check (image_b8f87e.png)
            if not log_df.empty and "Timestamp" in log_df.columns:
                history = log_df[log_df["Resource Name"] == sel_res].sort_values("Timestamp", ascending=False).head(3)
                if not history.empty:
                    with st.expander("🔍 View Goal History (Last 3 Months)"):
                        st.table(history[["MM/YYYY", "Goal", "Status", "Rating"]])
            
            with st.form("capture_form"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                feedback = st.text_area("Overall Feedback")
                
                # --- RESTORED EVIDENCE ATTACHMENT ---
                uploaded_file = st.
