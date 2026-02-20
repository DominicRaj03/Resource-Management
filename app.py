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
st.set_page_config(page_title="Resource Management V9.4", layout="wide")

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
st.sidebar.title("Resource Management V9.4")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# Global Constants
years = ["2025", "2026", "2027"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
q_map = {
    "Q1 (Jan-Mar)": ["Jan", "Feb", "Mar"],
    "Q2 (Apr-Jun)": ["Apr", "May", "Jun"],
    "Q3 (Jul-Sep)": ["Jul", "Aug", "Sep"],
    "Q4 (Oct-Dec)": ["Oct", "Nov", "Dec"]
}

# --- SCREEN: MASTER LIST (PRESERVED) ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        st.subheader("Assign Goals to Resource")
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_form_v9_4", clear_on_submit=True):
            c1, c2 = st.columns(2)
            if res_type == "Existing Resource" and not master_df.empty:
                res_name = c1.selectbox("Select Resource*", sorted(master_df["Resource Name"].unique().tolist()))
                res_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0], disabled=True)
            else:
                res_name, res_proj = c1.text_input("Resource Name*"), c2.text_input("Assign to Project*")
            cd1, cd2 = st.columns(2)
            sel_y, sel_m = cd1.selectbox("Year", years), cd2.selectbox("Month", months)
            goal_text = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and goal_text:
                    new_g = pd.DataFrame([{"Resource Name": res_name, "Project": res_proj, "Goal": goal_text, "Year": sel_y, "Month": sel_m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_g], ignore_index=True))
                    st.success("Goal added!")
                    st.rerun()

    with tab2:
        if not master_df.empty:
            f1, f2, f3, f4 = st.columns(4)
            fp = f1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            fn = f2.selectbox("Filter Name", ["All"] + sorted(master_df[master_df["Project"] == fp]["Resource Name"].unique().tolist() if fp != "All" else master_df["Resource Name"].unique().tolist()))
            fy, fm = f3.selectbox("Filter Year", ["All"] + years), f4.selectbox("Filter Month", ["All"] + months)
            v_df = master_df.copy()
            if fp != "All": v_df = v_df[v_df["Project"] == fp]
            if fn != "All": v_df = v_df[v_df["Resource Name"] == fn]
            if fy != "All": v_df = v_df[v_df["Year"] == fy]
            if fm != "All": v_df = v_df[v_df["Month"] == fm]
            for i, row in v_df.iterrows():
                is_eval = not log_df[(log_df["Resource Name"] == row["Resource Name"]) & (log_df["Goal"] == row["Goal"])].empty if not log_df.empty else False
                badge = "✅ Evaluated" if is_eval else "⏳ Pending"
                with st.expander(f"{badge} | {row['Resource Name']} - {row['Goal'][:30]}..."):
                    st.write(row)

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
            with st.form("cap_v9_4"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Comments*")
                rating = st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!")

# --- SCREEN: ANALYTICS DASHBOARD (V9.4 WITH ENHANCED CHARTS) ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        # Timeline Filters
        t_col1, t_col2 = st.columns(2)
        sel_year = t_col1.selectbox("Analytics Year", years)
        sel_period = t_col2.selectbox("Period", ["Full Year", "Q1 (Jan-Mar)", "Q2 (Apr-Jun)", "Q3 (Jul-Sep)", "Q4 (Oct-Dec)"])
        
        # Apply Filters
        f_df = df[df["MM/YYYY"].str.contains(sel_year)]
        if sel_period != "Full Year":
            f_df = f_df[f_df["MM/YYYY"].str.split('/').str[0].isin(q_map[sel_period])]

        if not f_df.empty:
            # 1. Top 3 Performers
            st.subheader("🌟 Top 3 Performers")
            top_3 = f_df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
            cols = st.columns(3)
            for i, (name, rating) in enumerate(top_3.items()):
                cols[i].metric(label=name, value=f"{rating:.2f} ⭐")
            
            st.divider()

            # 2. Key Charts Row
            if HAS_PLOTLY:
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("🎯 Goal Achievement Ratio")
                    pie_fig = px.pie(f_df, names='Status', hole=0.4, color='Status',
                                    color_discrete_map={'Achieved':'#00CC96', 'Partially Achieved':'#FFA15A', 'Not Completed':'#EF553B'})
                    st.plotly_chart(pie_fig, use_container_width=True)
                
                with c2:
                    st.subheader("📈 Monthly Performance Trend")
                    trend_df = f_df.groupby("MM/YYYY")["Rating"].mean().reset_index()
                    line_fig = px.line(trend_df, x="MM/YYYY", y="Rating", markers=True, 
                                      labels={"Rating": "Avg Rating"}, template="plotly_dark")
                    line_fig.update_layout(yaxis_range=[0, 5.5])
                    st.plotly_chart(line_fig, use_container_width=True)

                st.divider()
                
                # 3. Resource Comparison Chart
                st.subheader("👥 Resource Performance Benchmarking")
                res_avg = f_df.groupby("Resource Name")["Rating"].mean().reset_index().sort_values("Rating", ascending=True)
                bar_fig = px.bar(res_avg, x="Rating", y="Resource Name", orientation='h',
                                title="Average Star Rating by Individual", color="Rating", color_continuous_scale='Viridis')
                st.plotly_chart(bar_fig, use_container_width=True)
        else:
            st.warning("No data found for this selection.")

# --- SCREEN: HISTORICAL VIEW (PRESERVED) ---
else:
    st.title("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        pf = st.selectbox("Filter Project", ["All"] + sorted(df["Project"].unique().tolist()))
        v_df = df[df["Project"] == pf] if pf != "All" else df
        st.dataframe(v_df, use_container_width=True)
