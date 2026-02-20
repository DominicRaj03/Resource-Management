import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- Plotly Integration ---
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V12.7", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            if "Rating" in df.columns:
                df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V12.7")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2024", "2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    master_df = get_data("Master_List")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v12_7", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                r_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = c1.selectbox("Resource*", r_names)
                existing_proj = master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0]
                res_proj = c2.text_input("Project", value=existing_proj, disabled=True)
            else:
                res_name, res_proj = c1.text_input("Name*"), c2.text_input("Project*")
            
            y, m = st.selectbox("Year", years_list), st.selectbox("Month", months_list)
            g = st.text_area("Goal Details*")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and g:
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": str(y), "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab2:
        if not master_df.empty:
            c1, c2 = st.columns(2)
            f_p = c1.selectbox("Project Filter", ["All"] + sorted(master_df["Project"].unique().tolist()))
            f_r = c2.selectbox("Resource Filter", ["All"] + sorted(master_df["Resource Name"].unique().tolist()))
            
            final_df = master_df.copy()
            if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
            if f_r != "All": final_df = final_df[final_df["Resource Name"] == f_r]
            st.dataframe(final_df, use_container_width=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not master_df.empty:
        r_list = sorted(master_df["Resource Name"].unique().tolist())
        r_sel = st.selectbox("Resource", r_list)
        
        avail_goals = master_df[master_df["Resource Name"] == r_sel]
        g_opts = avail_goals.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
        sel_g_raw = st.selectbox("Select Goal", g_opts)
        
        actual_goal = avail_goals.iloc[g_opts.index(sel_g_raw)]['Goal']
        
        with st.form("cap_v12_7"):
            status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            st.divider()
            is_rec = st.checkbox("Recommend for Recognition?")
            just = st.text_area("Justification (Optional)")
            
            if st.form_submit_button("💾 Save Entry"):
                new_e = pd.DataFrame([{
                    "Resource Name": r_sel, "Goal": actual_goal, "Status": status,
                    "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                    "Recommended": "Yes" if is_rec else "No", "Justification": just,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                st.success("Entry Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not log_df.empty and not master_df.empty:
        df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        p_filter = st.selectbox("Project Filter", ["All Projects"] + sorted(master_df["Project"].unique().tolist()))
        if p_filter != "All Projects":
            df = df[df["Project"] == p_filter]

        c1, c2, c3 = st.columns(3)
        c1.metric("Evaluations", len(df))
        c2.metric("Achievement Rate", f"{(len(df[df['Status']=='Achieved'])/len(df)*100):.1f}%" if len(df)>0 else "0%")
        
        # Safe check for Recommended column
        rec_count = len(df[df["Recommended"] == "Yes"]) if "Recommended" in df.columns else 0
        c3.metric("Recognitions", rec_count)

        if HAS_PLOTLY:
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Leaderboard (Star Totals)")
                leaderboard = df.groupby("Resource Name")["Rating"].sum().reset_index().sort_values("Rating", ascending=False)
                st.plotly_chart(px.bar(leaderboard.head(10), x="Rating", y="Resource Name", orientation='h', color="Rating", color_continuous_scale='Greens'), use_container_width=True)
            with col2:
                st.subheader("🎯 Achievement Status")
                st.plotly_chart(px.pie(df, names="Status", color="Status", color_discrete_map={'Achieved':'#2E7D32', 'Partially Achieved':'#F9A825', 'Not Completed':'#C62828'}), use_container_width=True)
    else:
        st.info("Awaiting evaluation data.")
