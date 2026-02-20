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
st.set_page_config(page_title="Resource Management V6.1", layout="wide")

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
st.sidebar.title("Resource Management V6.1")
page = st.sidebar.radio("Navigation", ["App User Guide", "Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: MASTER LIST (WITH EDIT & DELETE) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 New Entry", "📋 List View"])
    
    master_df = get_data("Master_List")

    # SECTION 1: NEW ENTRY
    with tab1:
        st.subheader("Register New Resource")
        with st.form("new_entry_form", clear_on_submit=True):
            n, p = st.text_input("Full Name*"), st.text_input("Project Name*")
            g = st.text_area("Primary Goal")
            y, m = st.selectbox("Year", ["2025", "2026", "2027"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            
            if st.form_submit_button("➕ Save Resource"):
                if n and p:
                    new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
                    updated_master = pd.concat([master_df, new_r], ignore_index=True)
                    conn.update(worksheet="Master_List", data=updated_master)
                    st.success(f"Resource '{n}' has been added!")
                    st.rerun()
                else:
                    st.error("Name and Project are mandatory.")

    # SECTION 2: LIST VIEW (EDIT/DELETE)
    with tab2:
        st.subheader("Manage Resources")
        if not master_df.empty:
            p_filter = st.selectbox("Project Filter", ["All"] + sorted(master_df["Project"].unique().tolist()))
            
            view_df = master_df.copy()
            if p_filter != "All":
                view_df = view_df[view_df["Project"] == p_filter]

            for index, row in view_df.iterrows():
                with st.expander(f"👤 {row['Resource Name']} ({row['Project']})"):
                    # Edit Form inside Expander
                    with st.form(key=f"edit_form_{index}"):
                        new_n = st.text_input("Name", value=row['Resource Name'])
                        new_p = st.text_input("Project", value=row['Project'])
                        new_g = st.text_area("Goal", value=row['Goal'])
                        
                        col_a, col_b = st.columns(2)
                        if col_a.form_submit_button("💾 Update Details"):
                            master_df.at[index, 'Resource Name'] = new_n
                            master_df.at[index, 'Project'] = new_p
                            master_df.at[index, 'Goal'] = new_g
                            conn.update(worksheet="Master_List", data=master_df)
                            st.success("Updated!")
                            st.rerun()
                            
                        if col_b.form_submit_button("🗑️ Delete Resource"):
                            master_df = master_df.drop(index)
                            conn.update(worksheet="Master_List", data=master_df)
                            st.warning("Deleted!")
                            st.rerun()
        else:
            st.info("No records found.")

# --- SCREEN: APP USER GUIDE ---
elif page == "App User Guide":
    st.title("🛠️ Resource Management")
    df_log = get_data("Performance_Log")
    if not df_log.empty:
        st.subheader("🥇 Top 3 Performers")
        top_3 = df_log.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        cols = st.columns(3)
        for i, (name, rating) in enumerate(top_3.items()):
            cols[i].metric(label=name, value=f"{rating:.2f} Stars")
        st.divider()
        st.subheader("⚠️ Performance Warnings")
        warnings = df_log[df_log["Rating"] <= 2].sort_values("Timestamp", ascending=False)
        if not warnings.empty:
            st.dataframe(warnings[["Resource Name", "Rating", "Comments"]], use_container_width=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        
        matched = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Goal:** {res_info['Goal']}")
            
            with st.form("capture_v6_1"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Comments*")
                uploaded_file = st.file_uploader("Evidence", type=['pdf', 'png', 'jpg', 'docx'])
                rating = st.feedback("stars")
                
                if st.form_submit_button("💾 Save"):
                    new_entry = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}",
                        "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                        "Comments": comments, "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_entry], ignore_index=True))
                    st.success("Saved!")

# --- SCREEN: ANALYTICS ---
elif page == "Analytics Dashboard":
    st.header("📊 Analytics")
    df = get_data("Performance_Log")
    if not df.empty and HAS_PLOTLY:
        st.plotly_chart(px.bar(df.groupby("Resource Name")["Rating"].mean().reset_index(), x="Resource Name", y="Rating"), use_container_width=True)

# --- SCREEN: HISTORICAL VIEW ---
else:
    st.header("📅 History")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
