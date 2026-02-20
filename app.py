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
st.set_page_config(page_title="Resource Management V9.0", layout="wide")

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
st.sidebar.title("Resource Management V9.0")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: MASTER LIST (V9.0 MULTI-GOAL) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    
    master_df = get_data("Master_List")
    years = ["2025", "2026", "2027"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # TAB 1: NEW ENTRY (LINKED NAME/PROJECT + MULTI-GOAL)
    with tab1:
        st.subheader("Assign Goals to Resource")
        with st.form("new_goal_v9", clear_on_submit=True):
            col_id1, col_id2 = st.columns(2)
            res_name = col_id1.text_input("Resource Name*")
            res_proj = col_id2.text_input("Assign to Project*")
            
            col_dt1, col_dt2 = st.columns(2)
            sel_y = col_dt1.selectbox("Target Year", years)
            sel_m = col_dt2.selectbox("Target Month", months)
            
            goal_text = st.text_area("Enter Goal Details*")
            st.info("To add multiple goals for the same month, simply submit this form again with the same Name/Project/Date.")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and goal_text:
                    new_goal = pd.DataFrame([{
                        "Resource Name": res_name, 
                        "Project": res_proj, 
                        "Goal": goal_text, 
                        "Year": sel_y, 
                        "Month": sel_m
                    }])
                    updated_master = pd.concat([master_df, new_goal], ignore_index=True)
                    conn.update(worksheet="Master_List", data=updated_master)
                    st.success(f"Goal added for {res_name} in {sel_m} {sel_y}")
                    st.rerun()
                else:
                    st.error("Please fill in all mandatory fields.")

    # TAB 2: LIST VIEW (4-TIER FILTERING & EDIT/DELETE)
    with tab2:
        if not master_df.empty:
            st.subheader("🔍 Goal Management")
            
            # 4-Tier Filter Logic
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            f_proj = f_col1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            
            # Chain Resource Name filter based on Project
            res_options = master_df.copy()
            if f_proj != "All":
                res_options = res_options[res_options["Project"] == f_proj]
            f_name = f_col2.selectbox("Filter Name", ["All"] + sorted(res_options["Resource Name"].unique().tolist()))
            
            f_year = f_col3.selectbox("Filter Year", ["All"] + years)
            f_month = f_col4.selectbox("Filter Month", ["All"] + months)

            # Applying Filters
            view_df = master_df.copy()
            if f_proj != "All": view_df = view_df[view_df["Project"] == f_proj]
            if f_name != "All": view_df = view_df[view_df["Resource Name"] == f_name]
            if f_year != "All": view_df = view_df[view_df["Year"] == f_year]
            if f_month != "All": view_df = view_df[view_df["Month"] == f_month]

            st.divider()
            
            if view_df.empty:
                st.warning("No goals found for the selected filters.")
            else:
                for index, row in view_df.iterrows():
                    with st.expander(f"🎯 Goal: {row['Goal'][:50]}... ({row['Month']} {row['Year']})"):
                        with st.form(key=f"edit_v9_{index}"):
                            # Display all editable fields mirroring the entry screen
                            e_n = st.text_input("Name", value=row['Resource Name'])
                            e_p = st.text_input("Project", value=row['Project'])
                            e_g = st.text_area("Goal Details", value=row['Goal'])
                            
                            c_y, c_m = st.columns(2)
                            y_idx = years.index(row['Year']) if row['Year'] in years else 0
                            m_idx = months.index(row['Month']) if row['Month'] in months else 0
                            e_y = c_y.selectbox("Year", years, index=y_idx)
                            e_m = c_m.selectbox("Month", months, index=m_idx)
                            
                            b1, b2 = st.columns([1, 4])
                            if b1.form_submit_button("💾 Update"):
                                master_df.at[index, 'Resource Name'] = e_n
                                master_df.at[index, 'Project'] = e_p
                                master_df.at[index, 'Goal'] = e_g
                                master_df.at[index, 'Year'] = e_y
                                master_df.at[index, 'Month'] = e_m
                                conn.update(worksheet="Master_List", data=master_df)
                                st.rerun()
                            if b2.form_submit_button("🗑️ Delete"):
                                master_df = master_df.drop(index)
                                conn.update(worksheet="Master_List", data=master_df)
                                st.rerun()
        else:
            st.info("The Master List is currently empty.")

# --- PRESERVED PERFORMANCE CAPTURE (UPDATED FOR MULTI-GOAL) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        
        # Filter goals available for this resource
        available_goals = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        
        if not available_goals.empty:
            # Dropdown to select which specific goal to evaluate
            goal_options = available_goals.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
            sel_goal_str = st.selectbox("Select Goal to Evaluate", goal_options)
            
            # Retrieve specific row data
            goal_idx = goal_options.index(sel_goal_str)
            res_info = available_goals.iloc[goal_idx]
            
            # Logic Fix: History check
            if not log_df.empty and "Timestamp" in log_df.columns:
                history = log_df[(log_df["Resource Name"] == r_sel) & (log_df["Goal"] == res_info['Goal'])].sort_values("Timestamp", ascending=False).head(2)
                if not history.empty:
                    with st.expander("🔍 Goal History"):
                        st.table(history[["MM/YYYY", "Status", "Rating"]])

            with st.form("cap_v9"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                # Logic Fix: Proper file uploader
                uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
                rating = st.feedback("stars")
                
                if st.form_submit_button("💾 Save Record"):
                    new_entry = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}",
                        "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                        "Comments": comments, "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                    st.success("Record Saved!")

# --- PRESERVED HISTORICAL & ANALYTICS ---
elif page == "Historical View":
    st.title("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        p_filter = st.selectbox("Filter Project", ["All"] + sorted(df["Project"].unique().tolist()))
        m_filter = st.selectbox("Filter Month", ["All"] + sorted(df["MM/YYYY"].unique().tolist()))
        filtered_df = df.copy()
        if p_filter != "All": filtered_df = filtered_df[filtered_df["Project"] == p_filter]
        if m_filter != "All": filtered_df = filtered_df[filtered_df["MM/YYYY"] == m_filter]
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, index=False)
        st.download_button("📥 Export to Excel", data=buffer.getvalue(), file_name="Performance_Log.xlsx")
        st.dataframe(filtered_df, use_container_width=True)

else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        top_3 = df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        cols = st.columns(3)
        for i, (name, rating) in enumerate(top_3.items()):
            cols[i].metric(label=name, value=f"{rating:.2f} Stars")
