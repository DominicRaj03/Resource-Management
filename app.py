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
st.set_page_config(page_title="Resource Management V7.3", layout="wide")

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
st.sidebar.title("Resource Management V7.3")
page = st.sidebar.radio("Navigation", ["App User Guide", "Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: PERFORMANCE CAPTURE (FIXED LOGIC) ---
if page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        p_list = sorted(master_df["Project"].unique())
        p_sel = st.sidebar.selectbox("Project", p_list)
        r_list = sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique())
        r_sel = st.selectbox("Resource", r_list)
        
        matched = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            
            # FIX: KeyError on line 57
            # We verify the column exists and the dataframe is not empty before sorting
            if not log_df.empty and "Timestamp" in log_df.columns:
                history = log_df[log_df["Resource Name"] == r_sel].sort_values("Timestamp", ascending=False).head(3)
                if not history.empty:
                    with st.expander("🔍 View Recent History"):
                        st.table(history[["MM/YYYY", "Status", "Rating"]])

            with st.form("capture_v7_3"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                
                # FIX: SyntaxError on line 68
                # Completing the missing 'st.file_uploader' call
                uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
                
                rating = st.feedback("stars")
                
                if st.form_submit_button("💾 Save Record"):
                    period = f"{res_info['Month']}/{res_info['Year']}"
                    new_entry = pd.DataFrame([{
                        "Project": p_sel, 
                        "Resource Name": r_sel, 
                        "MM/YYYY": period,
                        "Goal": res_info['Goal'], 
                        "Status": status, 
                        "Rating": (rating+1 if rating else 0),
                        "Comments": comments, 
                        "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    # Safe update: concat with existing logs
                    updated_logs = pd.concat([log_df, new_entry], ignore_index=True)
                    conn.update(worksheet="Performance_Log", data=updated_logs)
                    st.success("Record successfully captured!")

# --- SCREEN: ANALYTICS DASHBOARD (PRESERVED V7.2) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty and HAS_PLOTLY:
        sel_p = st.selectbox("Select Project", sorted(df["Project"].unique().tolist()))
        p_df = df[df["Project"] == sel_p]
        
        # Project Health Summary
        total = len(p_df)
        achieved = len(p_df[p_df["Status"] == "Achieved"])
        h_col1, h_col2 = st.columns(2)
        h_col1.metric("Project Goal Success Rate", f"{(achieved/total*100):.1f}%" if total > 0 else "0%")
        h_col2.metric("Team Avg Rating", f"{p_df['Rating'].mean():.2f} ⭐")
        
        st.divider()
        # Monthly Comparison
        sel_res = st.selectbox("Select Resource", sorted(p_df["Resource Name"].unique().tolist()))
        team_m = p_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
        ind_m = p_df[p_df["Resource Name"] == sel_res].groupby("MM/YYYY")["Rating"].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=team_m["MM/YYYY"], y=team_m["Rating"], name="Team Avg", line=dict(dash='dash')))
        fig.add_trace(go.Scatter(x=ind_m["MM/YYYY"], y=ind_m["Rating"], name=sel_res, mode='lines+markers'))
        st.plotly_chart(fig, use_container_width=True)

# --- SCREEN: MASTER LIST (PRESERVED CRUD) ---
elif page == "Master List":
    st.title("👤 Master List")
    tab1, tab2 = st.tabs(["🆕 New Entry", "📋 List View"])
    master_df = get_data("Master_List")
    with tab1:
        with st.form("m_new"):
            n, p = st.text_input("Name"), st.text_input("Project")
            g = st.text_area("Goal")
            y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar"])
            if st.form_submit_button("Save"):
                new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
                conn.update(worksheet="Master_List", data=pd.concat([master_df, new_r], ignore_index=True))
                st.rerun()
    with tab2:
        if not master_df.empty:
            for i, row in master_df.iterrows():
                with st.expander(f"{row['Resource Name']}"):
                    st.write(f"Goal: {row['Goal']}")

# --- SCREEN: APP USER GUIDE & HISTORY ---
elif page == "App User Guide":
    st.title("🛠️ Resource Management Guide")
    st.info("Top Performers and Warnings summarized here.")
else:
    st.header("📅 History")
    df = get_data("Performance_Log")
    if not df.empty: st.dataframe(df, use_container_width=True)
