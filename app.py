import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V11.4", layout="wide")

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
st.sidebar.title("Resource Management V11.4")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

years_list = ["2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    master_df = get_data("Master_List")
    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v11_4", clear_on_submit=True):
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

# --- SCREEN: PERFORMANCE CAPTURE ---
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
            with st.form("cap_v11_4"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: HISTORICAL VIEW (WITH COLOR HIGHLIGHTING) ---
elif page == "Historical View":
    st.title("📅 Unified Historical Audit")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not master_df.empty:
        master_prep = master_df.copy()
        master_prep['MM/YYYY'] = master_prep['Month'] + "/" + master_prep['Year']
        
        req_cols = ['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp', 'Comments']
        if not log_df.empty:
            existing_cols = [c for c in req_cols if c in log_df.columns]
            log_subset = log_df[existing_cols].copy().drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
            unified_df = pd.merge(master_prep, log_subset, on=['Resource Name', 'Goal'], how='left')
        else:
            unified_df = master_prep.copy()
            for col in ['Status', 'Rating', 'Timestamp', 'Comments']: unified_df[col] = None

        unified_df['Status'] = unified_df['Status'].fillna('⏳ Pending Evaluation')
        
        # --- FILTERS ---
        st.subheader("🔍 Filters")
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

        # Apply coloring to Status column
        def color_status(val):
            color = '#90EE90' if val == 'Achieved' else '#FFCCCB' if val == 'Not Completed' else '#FFFFE0' if val == 'Partially Achieved' else 'white'
            return f'background-color: {color}; color: black'

        st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']].style.applymap(color_status, subset=['Status']), use_container_width=True)
        
        # --- QUICK EDIT ---
        st.divider()
        st.subheader("✏️ Quick Evaluation")
        edit_goal = st.selectbox("Select Goal", final_df.apply(lambda x: f"{x['Resource Name']} | {x['Goal'][:40]}...", axis=1))
        
        if edit_goal:
            sel_idx = final_df.index[final_df.apply(lambda x: f"{x['Resource Name']} | {x['Goal'][:40]}...", axis=1) == edit_goal][0]
            row = final_df.loc[sel_idx]
            with st.form("historical_edit"):
                new_stat = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                new_comm = st.text_area("Evaluation Comments", value=str(row.get('Comments', '')))
                if st.form_submit_button("💾 Save Update"):
                    update_row = pd.DataFrame([{
                        "Project": row['Project'], "Resource Name": row['Resource Name'], "MM/YYYY": row['MM/YYYY'],
                        "Goal": row['Goal'], "Status": new_stat, "Comments": new_comm, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, update_row], ignore_index=True))
                    st.success("Updated!"); st.rerun()

        # Excel Export with formatting
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Audit')
            workbook  = writer.book
            worksheet = writer.sheets['Audit']
            green_fmt = workbook.add_format({'bg_color': '#C6EFCE'})
            worksheet.conditional_format('A1:Z100', {'type': 'text', 'criteria': 'containing', 'value': 'Achieved', 'format': green_fmt})
        st.download_button("📥 Export Audit Excel", data=buf.getvalue(), file_name="Historical_Audit.xlsx")

# --- SCREEN: ANALYTICS ---
else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        st.table(df.groupby("Project")["Status"].value_counts().unstack().fillna(0))
