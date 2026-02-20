import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V9.8", layout="wide")

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
st.sidebar.title("Resource Management V9.8")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# Constants
years = ["2025", "2026", "2027"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST (PRESERVED) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        st.subheader("Assign Goals to Resource")
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v9_8"):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                res_name = c1.selectbox("Resource Name*", sorted(master_df["Resource Name"].unique().tolist()))
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            y, m = st.selectbox("Year", years), st.selectbox("Month", months)
            g = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name, "Project": res_proj, "Goal": g, "Year": y, "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal added!"); st.rerun()

    with tab2:
        if not master_df.empty:
            for i, row in master_df.iterrows():
                st.expander(f"{row['Resource Name']} - {row['Goal'][:30]}").write(row)

# --- SCREEN: PERFORMANCE CAPTURE (PRESERVED) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        avail = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        if not avail.empty:
            g_opts = avail.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
            sel_g = st.selectbox("Select Goal", g_opts)
            res_info = avail.iloc[g_opts.index(sel_g)]
            with st.form("cap_v9_8"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: HISTORICAL VIEW (FIXED AUDIT LOGIC) ---
elif page == "Historical View":
    st.title("📅 Unified Historical Audit")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        master_prep = master_df.copy()
        master_prep['MM/YYYY'] = master_prep['Month'].astype(str) + "/" + master_prep['Year'].astype(str)
        
        # --- FIXED LOGIC START ---
        # 1. Identify which columns actually exist in the log sheet to avoid KeyError
        available_cols = log_df.columns.tolist() if not log_df.empty else []
        required_data = ['Resource Name', 'Goal', 'Status', 'Rating', 'Comments', 'Timestamp']
        existing_data_cols = [c for c in required_data if c in available_cols]
        
        # 2. Perform merge only if we have at least the keys
        if not log_df.empty and 'Resource Name' in available_cols and 'Goal' in available_cols:
            # We use log_df[existing_data_cols] to only pull what exists
            unified_df = pd.merge(master_prep, log_df[existing_data_cols], on=['Resource Name', 'Goal'], how='left')
        else:
            # Fallback if log is empty or columns missing
            unified_df = master_prep.copy()
            for col in ['Status', 'Rating', 'Comments', 'Timestamp']:
                unified_df[col] = None
        
        # 3. Handle Status Display Correctly
        # If 'Status' is null, it means it was never evaluated in Performance Capture
        unified_df['Status'] = unified_df['Status'].fillna('⏳ Pending Evaluation')
        unified_df['Timestamp'] = unified_df['Timestamp'].fillna('N/A')
        unified_df['Rating'] = unified_df['Rating'].fillna('None')
        # --- FIXED LOGIC END ---
        
        f_p = st.selectbox("Filter Project", ["All"] + sorted(unified_df["Project"].unique().tolist()))
        final_df = unified_df[unified_df["Project"] == f_p] if f_p != "All" else unified_df
        
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False)
        st.download_button("📥 Export Audit Excel", data=buf.getvalue(), file_name="Unified_Audit.xlsx")
        
        # Display prioritized columns for visibility
        display_cols = ['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']
        st.dataframe(final_df[display_cols], use_container_width=True)
    else:
        st.warning("Master List is empty. Please add resources first.")

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        st.write("Analytics dashboard active. Filter by year/quarter to view trends.")
