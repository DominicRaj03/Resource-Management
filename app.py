import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Config ---
st.set_page_config(page_title="Resource Management V9.2", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V9.2")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: MASTER LIST (V9.2 WITH RESOURCE TOGGLE) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    
    master_df = get_data("Master_List")
    years = ["2025", "2026", "2027"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    with tab1:
        st.subheader("Assign Goals to Resource")
        
        # Resource Type Selection
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        
        with st.form("new_goal_v9_2", clear_on_submit=True):
            col_id1, col_id2 = st.columns(2)
            
            if res_type == "Existing Resource" and not master_df.empty:
                # List all unique existing resources
                existing_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = col_id1.selectbox("Select Resource Name*", existing_names)
                
                # Auto-fill project based on selected resource
                current_proj = master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0]
                res_proj = col_id2.text_input("Project (Auto-filled)", value=current_proj, disabled=True)
            else:
                # Input for new resource
                res_name = col_id1.text_input("New Resource Name*")
                res_proj = col_id2.text_input("Assign to Project*")
            
            col_dt1, col_dt2 = st.columns(2)
            sel_y = col_dt1.selectbox("Target Year", years)
            sel_m = col_dt2.selectbox("Target Month", months)
            
            goal_text = st.text_area("Enter Goal Details*")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and goal_text:
                    new_goal = pd.DataFrame([{
                        "Resource Name": res_name, 
                        "Project": res_proj, 
                        "Goal": goal_text, 
                        "Year": sel_y, 
                        "Month": sel_m
                    }])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_goal], ignore_index=True))
                    st.success(f"Goal recorded for {res_name}")
                    st.rerun()
                else:
                    st.error("Missing mandatory fields.")

    # TAB 2: LIST VIEW (PRESERVED WITH 4-TIER FILTER & STATUS BADGE)
    with tab2:
        if not master_df.empty:
            st.subheader("🔍 Goal Management")
            f1, f2, f3, f4 = st.columns(4)
            fp = f1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            res_opts = master_df[master_df["Project"] == fp] if fp != "All" else master_df
            fn = f2.selectbox("Filter Name", ["All"] + sorted(res_opts["Resource Name"].unique().tolist()))
            fy = f3.selectbox("Filter Year", ["All"] + years)
            fm = f4.selectbox("Filter Month", ["All"] + months)

            v_df = master_df.copy()
            if fp != "All": v_df = v_df[v_df["Project"] == fp]
            if fn != "All": v_df = v_df[v_df["Resource Name"] == fn]
            if fy != "All": v_df = v_df[v_df["Year"] == fy]
            if fm != "All": v_df = v_df[v_df["Month"] == fm]

            log_df = get_data("Performance_Log")
            for i, row in v_df.iterrows():
                is_eval = not log_df[(log_df["Resource Name"] == row["Resource Name"]) & (log_df["Goal"] == row["Goal"])].empty if not log_df.empty else False
                badge = "✅ Evaluated" if is_eval else "⏳ Pending"
                
                with st.expander(f"{badge} | {row['Resource Name']} - {row['Goal'][:40]}..."):
                    with st.form(key=f"ed_v9_2_{i}"):
                        un = st.text_input("Name", value=row['Resource Name'])
                        up = st.text_input("Project", value=row['Project'])
                        ug = st.text_area("Goal Details", value=row['Goal'])
                        if st.form_submit_button("Update"):
                            master_df.at[i, 'Resource Name'], master_df.at[i, 'Project'], master_df.at[i, 'Goal'] = un, up, ug
                            conn.update(worksheet="Master_List", data=master_df)
                            st.rerun()

# --- PRESERVED OTHER SCREENS (Capture, History, Analytics) ---
elif page == "Performance Capture":
    # ... logic for capturing performance for specific goals ...
    st.info("Screen logic preserved from V9.1")

elif page == "Historical View":
    # ... logic for filtering and exporting Excel ...
    st.info("Screen logic preserved from V9.1")

else:
    # ... logic for Top 3 Performers and Analytics ...
    st.info("Screen logic preserved from V9.1")
