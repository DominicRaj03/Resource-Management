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
st.set_page_config(page_title="Resource Management V14.1", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_valid_data(sheet_name):
    """Fetches data and ensures critical columns exist to prevent blank screens."""
    required_cols = {
        "Master_List": ["Resource Name", "Project", "Goal", "Year", "Month"],
        "Performance_Log": ["Project", "Resource Name", "Goal", "Status", "Rating", "Comments", 
                            "Recommended for Recognition", "Recognition Justification", "Timestamp"]
    }
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=required_cols[sheet_name])
        
        for col in required_cols[sheet_name]:
            if col not in df.columns:
                df[col] = ""
        
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce').fillna(pd.Timestamp('2000-01-01'))
        if "Rating" in df.columns:
            df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce').fillna(0)
            
        return df
    except Exception:
        return pd.DataFrame(columns=required_cols[sheet_name])

# --- Navigation ---
st.sidebar.title("Resource Management V14.1")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2024", "2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    master_df = get_valid_data("Master_List")
    log_df = get_valid_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v14_1", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty and master_df["Resource Name"].dropna().any():
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
                    new_g = pd.DataFrame([{"Resource Name": res_name.strip(), "Project": res_proj.strip(), "Goal": g.strip(), "Year": y, "Month": m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal Saved!"); st.rerun()

    with tab2:
        if not master_df.empty:
            log_clean = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
            unified_df = pd.merge(master_df, log_clean[['Resource Name', 'Goal', 'Status', 'Rating']], on=['Resource Name', 'Goal'], how='left')
            unified_df['Status'] = unified_df['Status'].fillna('Yet to Mark')
            
            c1, c2, c3, c4 = st.columns(4)
            f_p = c1.selectbox("Project Filter", ["All"] + sorted(unified_df["Project"].unique().tolist()))
            f_r = c2.selectbox("Resource Filter", ["All"] + sorted(unified_df["Resource Name"].unique().tolist()))
            f_y = c3.selectbox("Year Filter", ["All"] + years_list)
            f_m = c4.selectbox("Month Filter", ["All"] + months_list)

            final_df = unified_df.copy()
            if f_p != "All": final_df = final_df[final_df["Project"] == f_p]
            if f_r != "All": final_df = final_df[final_df["Resource Name"] == f_r]
            if f_y != "All": final_df = final_df[final_df["Year"] == f_y]
            if f_m != "All": final_df = final_df[final_df["Month"] == f_m]

            def color_status(val):
                colors = {'Achieved': '#2E7D32', 'Not Completed': '#C62828', 'Partially Achieved': '#F9A825', 'Yet to Mark': '#757575'}
                return f'background-color: {colors.get(val, "none")}; color: white'
            st.dataframe(final_df.style.applymap(color_status, subset=['Status']), use_container_width=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df, log_df = get_valid_data("Master_List"), get_valid_data("Performance_Log")
    
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        r_list = sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique().tolist())
        r_sel = st.selectbox("Resource", r_list)
        
        avail = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        if not avail.empty:
            g_opts = avail.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
            sel_g = st.selectbox("Select Goal", g_opts)
            res_info = avail.iloc[g_opts.index(sel_g)]
            
            with st.form("cap_v14_1"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                rating = st.feedback("stars")
                comments = st.text_area("Evaluation Comments*")
                is_rec = st.checkbox("Recommend for Recognition?")
                just = st.text_area("Recognition Justification (Optional)")
                
                if st.form_submit_button("💾 Save Entry"):
                    new_e = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "Goal": res_info['Goal'], 
                        "Status": status, "Rating": (rating+1 if rating is not None else 0), 
                        "Comments": comments, "Recommended for Recognition": "Yes" if is_rec else "No",
                        "Recognition Justification": just if is_rec else "",
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Insights")
    master_df, log_df = get_valid_data("Master_List"), get_valid_data("Performance_Log")
    
    if not master_df.empty:
        col_f1, col_f2 = st.columns(2)
        p_filter = col_f1.selectbox("Project Filter", ["All Projects"] + sorted(master_df["Project"].unique().tolist()))
        
        log_clean = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
        df = pd.merge(master_df, log_clean[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
        df['Status'] = df['Status'].fillna('Yet to Mark')

        if p_filter != "All Projects":
            df = df[df['Project'] == p_filter]
        
        r_filter = col_f2.selectbox("Resource Trend Filter", ["All Resources"] + sorted(df["Resource Name"].unique().tolist()))

        # KPIs
        pts = {'Achieved': 5, 'Partially Achieved': 3, 'Not Completed': 0, 'Yet to Mark': 0}
        df['Pts'] = df['Status'].map(pts)
        leaderboard = df.groupby('Resource Name')['Pts'].sum().reset_index().sort_values('Pts', ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Goals", len(df))
        c2.metric("Achievement %", f"{(len(df[df['Status']=='Achieved'])/len(df)*100):.1f}%" if len(df)>0 else "0%")
        c3.metric("Top Score", f"{leaderboard.iloc[0]['Pts']} pts" if not leaderboard.empty else "0 pts")

        if HAS_PLOTLY:
            st.divider()
            if r_filter != "All Resources":
                st.subheader(f"📈 Performance Trend: {r_filter}")
                res_df = df[df["Resource Name"] == r_filter]
                # Map status to numeric for plotting trend
                status_num = {'Achieved': 3, 'Partially Achieved': 2, 'Not Completed': 1, 'Yet to Mark': 0}
                res_df['Status_Score'] = res_df['Status'].map(status_num)
                fig_trend = px.line(res_df, x='Month', y='Status_Score', markers=True, 
                                    category_orders={"Month": months_list}, title="Status Progression")
                fig_trend.update_layout(yaxis=dict(tickvals=[0,1,2,3], ticktext=['Pending', 'Not Comp', 'Partial', 'Achieved']))
                st.plotly_chart(fig_trend, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Leaderboard")
                st.plotly_chart(px.bar(leaderboard.head(10), x='Pts', y='Resource Name', orientation='h', color='Pts', color_continuous_scale='Greens'), use_container_width=True)
            with col2:
                st.subheader("🎯 Goal Status")
                st.plotly_chart(px.pie(df, names='Status', color='Status', color_discrete_map={'Achieved':'#2E7D32', 'Partially Achieved':'#F9A825', 'Not Completed':'#C62828', 'Yet to Mark':'#757575'}), use_container_width=True)
    else:
        st.info("No data available.")
