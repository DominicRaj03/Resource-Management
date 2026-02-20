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
st.set_page_config(page_title="Resource Management V8.1", layout="wide")

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
st.sidebar.title("Resource Management V8.1")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: MASTER LIST (RECONFIGURED) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 New Entry", "📋 List View"])
    
    master_df = get_data("Master_List")
    years = ["2025", "2026", "2027"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # TAB 1: NEW ENTRY (Reference image_b90fdb.png)
    with tab1:
        st.subheader("Register New Resource")
        with st.form("new_entry_v8_1", clear_on_submit=True):
            n = st.text_input("Name")
            p = st.text_input("Project")
            g = st.text_area("Goal")
            y = st.selectbox("Year", years)
            m = st.selectbox("Month", months)
            
            if st.form_submit_button("Save"):
                if n and p:
                    new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
                    updated_master = pd.concat([master_df, new_r], ignore_index=True)
                    conn.update(worksheet="Master_List", data=updated_master)
                    st.success(f"Resource '{n}' added to project '{p}'")
                    st.rerun()
                else:
                    st.error("Name and Project are mandatory.")

    # TAB 2: LIST VIEW (NEW FILTERED & EDITABLE LOGIC)
    with tab2:
        if not master_df.empty:
            # Project Filter as requested
            st.subheader("Filter & Edit Resources")
            all_projects = sorted(master_df["Project"].unique().tolist())
            sel_p_filter = st.selectbox("Select Project to View", ["All"] + all_projects)
            
            # Filter the dataframe
            view_df = master_df.copy()
            if sel_p_filter != "All":
                view_df = view_df[view_df["Project"] == sel_p_filter]

            # Display Editable Expanders (Reference image_c31007.png)
            for index, row in view_df.iterrows():
                with st.expander(f"👤 {row['Resource Name']} | Project: {row['Project']}"):
                    with st.form(key=f"edit_v8_1_{index}"):
                        # Mirroring all inputs from the entry screen
                        up_n = st.text_input("Name", value=row['Resource Name'])
                        up_p = st.text_input("Project", value=row['Project'])
                        up_g = st.text_area("Goal", value=row['Goal'])
                        
                        col_y, col_m = st.columns(2)
                        # Handling index matching for selectboxes
                        y_idx = years.index(row['Year']) if row['Year'] in years else 0
                        m_idx = months.index(row['Month']) if row['Month'] in months else 0
                        
                        up_y = col_y.selectbox("Year", years, index=y_idx)
                        up_m = col_m.selectbox("Month", months, index=m_idx)
                        
                        col_btn1, col_btn2 = st.columns([1, 4])
                        if col_btn1.form_submit_button("💾 Update"):
                            master_df.at[index, 'Resource Name'] = up_n
                            master_df.at[index, 'Project'] = up_p
                            master_df.at[index, 'Goal'] = up_g
                            master_df.at[index, 'Year'] = up_y
                            master_df.at[index, 'Month'] = up_m
                            conn.update(worksheet="Master_List", data=master_df)
                            st.success("Changes saved!")
                            st.rerun()
                            
                        if col_btn2.form_submit_button("🗑️ Delete"):
                            master_df = master_df.drop(index)
                            conn.update(worksheet="Master_List", data=master_df)
                            st.warning("Resource deleted.")
                            st.rerun()
        else:
            st.info("No resources found. Please add one in the 'New Entry' tab.")

# --- PRESERVED SCREENS (Analytics, Capture, History) ---
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
            st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            if not log_df.empty and "Timestamp" in log_df.columns:
                history = log_df[log_df["Resource Name"] == r_sel].sort_values("Timestamp", ascending=False).head(3)
                if not history.empty:
                    with st.expander("🔍 Recent History"):
                        st.table(history[["MM/YYYY", "Status", "Rating"]])
            with st.form("cap_v8_1"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
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

elif page == "Historical View":
    st.title("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        p_filter = st.selectbox("Filter by Project", ["All"] + sorted(df["Project"].unique().tolist()))
        m_filter = st.selectbox("Filter by Month", ["All"] + sorted(df["MM/YYYY"].unique().tolist()))
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
        st.divider()
        sel_p = st.selectbox("Select Project", sorted(df["Project"].unique().tolist()))
        p_df = df[df["Project"] == sel_p]
        if HAS_PLOTLY:
            team_m = p_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
            st.plotly_chart(px.line(team_m, x="MM/YYYY", y="Rating", title=f"Team Trend: {sel_p}"), use_container_width=True)
