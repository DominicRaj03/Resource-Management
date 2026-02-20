import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V11.2", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
            for col in ["Resource Name", "Goal"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V11.2")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

years_list = ["2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST (Unchanged) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    master_df = get_data("Master_List")
    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v11_2"):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                res_name = c1.selectbox("Resource*", sorted(master_df["Resource Name"].unique().tolist()))
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            y, m = st.selectbox("Year", years_list), st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": y, "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()
    with tab2:
        if not master_df.empty:
            f1 = st.selectbox("Project Filter", ["All"] + sorted(master_df["Project"].unique().tolist()))
            st.dataframe(master_df[master_df["Project"] == f1] if f1 != "All" else master_df, use_container_width=True)

# --- SCREEN: PERFORMANCE CAPTURE (Unchanged) ---
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
            with st.form("cap_v11_2"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: HISTORICAL VIEW (FIXED WITH FILTERS & EDIT) ---
elif page == "Historical View":
    st.title("📅 Unified Historical Audit")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not master_df.empty:
        # Merge logic to show ALL goals
        master_prep = master_df.copy()
        master_prep['MM/YYYY'] = master_prep['Month'] + "/" + master_prep['Year']
        
        req_cols = ['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp', 'Comments']
        if not log_df.empty:
            # Fix for KeyError: only use columns that exist
            existing_cols = [c for c in req_cols if c in log_df.columns]
            log_subset = log_df[existing_cols].copy().drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
            unified_df = pd.merge(master_prep, log_subset, on=['Resource Name', 'Goal'], how='left')
        else:
            unified_df = master_prep.copy()
            for col in ['Status', 'Rating', 'Timestamp', 'Comments']: unified_df[col] = None

        unified_df['Status'] = unified_df['Status'].fillna('⏳ Pending Evaluation')
        unified_df['Rating'] = unified_df['Rating'].fillna('None')

        # --- FILTERS ---
        st.subheader("🔍 Search & Filter")
        c1, c2, c3, c4 = st.columns(4)
        f_p = c1.selectbox("Project", ["All"] + sorted(unified_df["Project"].unique().tolist()))
        f_r = c2.selectbox("Resource", ["All"] + sorted(unified_df["Resource Name"].unique().tolist()))
        f_y = c3.selectbox("Year", ["All"] + years_list)
        f_m = c4.selectbox("Month", ["All"] + months_list)

        final_df = unified_df.copy()
        if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
        if f_r != "All": final_df = final_df[final_df["Resource Name"] == f_r]
        if f_y != "All": final_df = final_df[final_df["Year"] == f_y]
        if f_m != "All": final_df = final_df[final_df["Month"] == f_m]

        st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']], use_container_width=True)
        
        # --- EDIT OPTION ---
        st.divider()
        st.subheader("✏️ Quick Edit Evaluation")
        edit_goal = st.selectbox("Select Goal to Edit/Evaluate", final_df.apply(lambda x: f"{x['Resource Name']} | {x['Goal'][:50]}...", axis=1))
        
        if edit_goal:
            idx = final_df.index[final_df.apply(lambda x: f"{x['Resource Name']} | {x['Goal'][:50]}...", axis=1) == edit_goal][0]
            selected_row = final_df.loc[idx]
            with st.form("quick_edit"):
                new_status = st.selectbox("Update Status", ["Achieved", "Partially Achieved", "Not Completed"], 
                                          index=["Achieved", "Partially Achieved", "Not Completed"].index(selected_row['Status']) if selected_row['Status'] in ["Achieved", "Partially Achieved", "Not Completed"] else 0)
                new_comm = st.text_area("Update Comments", value=str(selected_row.get('Comments', '')))
                if st.form_submit_button("💾 Update Evaluation"):
                    # Logic to update/append to Performance Log
                    update_entry = pd.DataFrame([{
                        "Project": selected_row['Project'], "Resource Name": selected_row['Resource Name'],
                        "MM/YYYY": selected_row['MM/YYYY'], "Goal": selected_row['Goal'],
                        "Status": new_status, "Comments": new_comm, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, update_entry], ignore_index=True))
                    st.success("Entry Updated!"); st.rerun()

        # Excel Export
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: final_df.to_excel(writer, index=False)
        st.download_button("📥 Export Audit Excel", data=buf.getvalue(), file_name="Historical_Audit.xlsx")

# --- SCREEN: ANALYTICS (Unchanged) ---
else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        st.table(df.groupby("Project")["Status"].value_counts().unstack().fillna(0))
