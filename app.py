import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V13.0", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V13.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2024", "2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_form_v13", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                res_name = c1.selectbox("Resource*", sorted(master_df["Resource Name"].unique().tolist()))
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name = c1.text_input("Name*")
                res_proj = c2.text_input("Project*")
            
            y = st.selectbox("Year", years_list)
            m = st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_goal = pd.DataFrame([{
                        "Resource Name": res_name.strip(),
                        "Project": res_proj.strip(),
                        "Goal": g.strip(),
                        "Year": str(y),
                        "Month": m
                    }])
                    updated_df = pd.concat([master_df, new_goal], ignore_index=True)
                    conn.update(worksheet="Master_List", data=updated_df)
                    st.success("Goal successfully added!"); st.rerun()

    with tab2:
        if not master_df.empty:
            # Merge logic for status display
            if not log_df.empty:
                # Latest status per goal
                log_clean = log_df.drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
                display_df = pd.merge(master_df, log_clean[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
            else:
                display_df = master_df.copy()
                display_df['Status'] = 'Yet to Mark'
            
            display_df['Status'] = display_df['Status'].fillna('Yet to Mark')
            
            # Filters
            c1, c2 = st.columns(2)
            f_p = c1.selectbox("Project Filter", ["All"] + sorted(display_df["Project"].unique().tolist()))
            f_r = c2.selectbox("Resource Filter", ["All"] + sorted(display_df["Resource Name"].unique().tolist()))
            
            final_df = display_df.copy()
            if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
            if f_r != "All": final_df = final_df[final_df["Resource Name"] == f_r]
            
            st.dataframe(final_df, use_container_width=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        r_list = sorted(master_df["Resource Name"].unique().tolist())
        r_sel = st.selectbox("Select Resource", r_list)
        
        # Get specific goals for selected resource
        res_goals = master_df[master_df["Resource Name"] == r_sel]
        goal_list = res_goals.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
        g_sel_raw = st.selectbox("Select Goal", goal_list)
        
        # Extract the actual goal text
        actual_goal = res_goals.iloc[goal_list.index(g_sel_raw)]['Goal']
        
        with st.form("perf_form_v13"):
            status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
            rating = st.select_slider("Rating", options=[1, 2, 3, 4, 5])
            comments = st.text_area("Comments")
            
            if st.form_submit_button("💾 Save Performance"):
                new_entry = pd.DataFrame([{
                    "Resource Name": r_sel,
                    "Goal": actual_goal,
                    "Status": status,
                    "Rating": rating,
                    "Comments": comments,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                updated_log = pd.concat([log_df, new_entry], ignore_index=True)
                conn.update(worksheet="Performance_Log", data=updated_log)
                st.success("Performance recorded!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        total_goals = len(master_df)
        achieved = len(log_df[log_df["Status"] == "Achieved"]) if not log_df.empty else 0
        
        c1, c2 = st.columns(2)
        c1.metric("Total Goals", total_goals)
        c2.metric("Achievement Rate", f"{(achieved/total_goals*100):.1f}%" if total_goals > 0 else "0%")
        
        if not log_df.empty:
            st.subheader("Performance Breakdown")
            st.bar_chart(log_df["Status"].value_counts())
    else:
        st.info("No data found in Master List.")
