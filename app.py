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
st.set_page_config(page_title="Resource Management V7.5", layout="wide")

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
st.sidebar.title("Resource Management V7.5")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: ANALYTICS DASHBOARD (V7.5 WITH SPOTLIGHT) ---
if page == "Analytics Dashboard":
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    
    if not df.empty:
        # 1. TOP 3 PERFORMERS SPOTLIGHT (Relocated from Guide)
        st.subheader("🌟 Top 3 Performers (Overall)")
        top_3 = df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        s_col1, s_col2, s_col3 = st.columns(3)
        icons = ["🥇", "🥈", "🥉"]
        for i, (name, rating) in enumerate(top_3.items()):
            with [s_col1, s_col2, s_col3][i]:
                st.metric(label=f"{icons[i]} {name}", value=f"{rating:.2f} Stars")
        
        st.divider()

        # Selection Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_p = st.selectbox("Select Project", sorted(df["Project"].unique().tolist()))
        with col_f2:
            p_df = df[df["Project"] == sel_p]
            sel_res = st.selectbox("Select Resource", sorted(p_df["Resource Name"].unique().tolist()))
        
        # 2. Project Health Summary
        st.subheader(f"🏥 Project Health: {sel_p}")
        total = len(p_df)
        achieved = len(p_df[p_df["Status"] == "Achieved"])
        h1, h2, h3 = st.columns(3)
        h1.metric("Goal Achievement", f"{(achieved/total*100):.1f}%" if total > 0 else "0%")
        h2.metric("Avg Team Rating", f"{p_df['Rating'].mean():.2f} ⭐")
        h3.metric("Evaluations", total)
        
        st.divider()

        # 3. Comparative Trend
        if HAS_PLOTLY:
            st.subheader("📈 Performance Benchmark")
            team_m = p_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
            ind_m = p_df[p_df["Resource Name"] == sel_res].groupby("MM/YYYY")["Rating"].mean().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=team_m["MM/YYYY"], y=team_m["Rating"], name="Team Avg", line=dict(dash='dash', color='gray')))
            fig.add_trace(go.Scatter(x=ind_m["MM/YYYY"], y=ind_m["Rating"], name=sel_res, mode='lines+markers', line=dict(color='#00CC96', width=3)))
            fig.update_layout(yaxis_range=[0, 5.5])
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Insufficient data for analytics.")

# --- SCREEN: MASTER LIST (PRESERVED CRUD) ---
elif page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 New Entry", "📋 List View"])
    master_df = get_data("Master_List")
    with tab1:
        with st.form("new_v7_5", clear_on_submit=True):
            n, p = st.text_input("Full Name*"), st.text_input("Project Name*")
            g = st.text_area("Primary Goal")
            y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            if st.form_submit_button("➕ Save"):
                new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
                conn.update(worksheet="Master_List", data=pd.concat([master_df, new_r], ignore_index=True))
                st.rerun()
    with tab2:
        if not master_df.empty:
            for index, row in master_df.iterrows():
                with st.expander(f"{row['Resource Name']} ({row['Project']})"):
                    with st.form(key=f"ed_v7_5_{index}"):
                        en = st.text_input("Name", value=row['Resource Name'])
                        ep = st.text_input("Project", value=row['Project'])
                        if st.form_submit_button("Update"):
                            master_df.at[index, 'Resource Name'], master_df.at[index, 'Project'] = en, ep
                            conn.update(worksheet="Master_List", data=master_df)
                            st.rerun()

# --- SCREEN: PERFORMANCE CAPTURE (PRESERVED) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        res_info = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)].iloc[-1]
        
        if not log_df.empty and "Timestamp" in log_df.columns:
            history = log_df[log_df["Resource Name"] == r_sel].sort_values("Timestamp", ascending=False).head(3)
            if not history.empty:
                with st.expander("🔍 Recent History"):
                    st.table(history[["MM/YYYY", "Status", "Rating"]])

        with st.form("cap_v7_5"):
            status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
            comments = st.text_area("Justification / Comments*")
            uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
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

# --- SCREEN: HISTORICAL VIEW ---
else:
    st.header("📅 History")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
