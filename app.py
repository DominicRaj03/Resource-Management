import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Plotly Integration ---
try:
    import plotly.express as px
    import plotly.graph_objects as go
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
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
            for col in ["Resource Name", "Goal"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            if "Rating" in df.columns:
                df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce').fillna(0)
        return df if df is not None else pd.DataFrame()
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
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v12_7", clear_on_submit=True):
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
            master_prep = master_df.copy()
            master_prep['MM/YYYY'] = master_prep['Month'] + "/" + master_prep['Year']
            req_cols = ['Resource Name', 'Goal', 'Status', 'Rating', 'Timestamp']
            if not log_df.empty:
                existing_cols = [c for c in req_cols if c in log_df.columns]
                log_subset = log_df[existing_cols].copy().drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
                unified_df = pd.merge(master_prep, log_subset, on=['Resource Name', 'Goal'], how='left')
            else:
                unified_df = master_prep.copy()
                for col in ['Status', 'Rating', 'Timestamp']: unified_df[col] = None
            unified_df['Status'] = unified_df['Status'].fillna('⏳ Pending Evaluation')

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

            def color_status(val):
                color = '#90EE90' if val == 'Achieved' else '#FFCCCB' if val == 'Not Completed' else '#FFFFE0' if val == 'Partially Achieved' else 'white'
                return f'background-color: {color}; color: black'

            st.dataframe(final_df[['Project', 'Resource Name', 'MM/YYYY', 'Goal', 'Status', 'Rating', 'Timestamp']].style.applymap(color_status, subset=['Status']), use_container_width=True)

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
            with st.form("cap_v12_7"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments, rating = st.text_area("Comments*"), st.feedback("stars")
                if st.form_submit_button("💾 Save Evaluation"):
                    new_e = pd.DataFrame([{"Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}", "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0), "Comments": comments, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not master_df.empty:
        # --- YoY COMPARISON TOGGLE ---
        with st.expander("🔄 Year-over-Year (YoY) Comparison Tools"):
            mode = st.toggle("Enable Comparison Mode")
            if mode:
                y1, y2 = st.columns(2)
                base_year = y1.selectbox("Base Year", years_list, index=1)
                comp_year = y2.selectbox("Comparison Year", years_list, index=2)
                
                # Logic for YoY overlay
                def get_yoy_data(df, year):
                    return df[df['Year'] == year].groupby('Month')['Goal'].count().reindex(months_list).fillna(0).reset_index()

                base_data = get_yoy_data(master_df, base_year)
                comp_data = get_yoy_data(master_df, comp_year)
                
                fig_yoy = go.Figure()
                fig_yoy.add_trace(go.Scatter(x=months_list, y=base_data['Goal'], name=f"{base_year} Velocity", line=dict(dash='dash')))
                fig_yoy.add_trace(go.Scatter(x=months_list, y=comp_data['Goal'], name=f"{comp_year} Velocity"))
                st.plotly_chart(fig_yoy, use_container_width=True)

        # Main Stats Ribbon
        st.divider()
        audit_full = pd.merge(master_df, log_df[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
        audit_full['Status'] = audit_full['Status'].fillna('Pending')
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Lifetime Goals", len(audit_full))
        k2.metric("Achieved", len(audit_full[audit_full['Status'] == 'Achieved']))
        k3.metric("Pending Eval", len(audit_full[audit_full['Status'] == 'Pending']))

        if HAS_PLOTLY:
            # Monthly Planning Volume
            st.divider()
            st.subheader("📈 Planning Volume (All Years)")
            v_df = master_df.copy()
            v_df['MM/YYYY'] = v_df['Month'] + "/" + v_df['Year']
            v_plot = v_df.groupby("MM/YYYY")["Goal"].count().reset_index()
            st.plotly_chart(px.line(v_plot, x="MM/YYYY", y="Goal", markers=True), use_container_width=True)

            # Project Burn-down
            st.divider()
            st.subheader("🔥 Project Progress (%)")
            proj_stats = audit_full.groupby(['Project', 'Status']).size().unstack(fill_value=0)
            if 'Achieved' not in proj_stats.columns: proj_stats['Achieved'] = 0
            proj_stats['Total'] = proj_stats.sum(axis=1)
            proj_stats['Completion %'] = (proj_stats['Achieved'] / proj_stats['Total'] * 100).round(1)
            st.plotly_chart(px.bar(proj_stats.reset_index(), x="Project", y="Completion %", color="Completion %", color_continuous_scale="RdYlGn"), use_container_width=True)
    else:
        st.warning("No data found.")
