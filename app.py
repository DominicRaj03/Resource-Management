import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- Plotly Integration ---
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- Page Configuration ---
st.set_page_config(page_title="Resource Management V13.6", layout="wide")

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
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- AUTOMATED SYSTEM REPAIR ---
def auto_repair():
    try:
        m_df = get_data("Master_List")
        m_req = ["Resource Name", "Project", "Goal", "Year", "Month"]
        m_missing = [c for c in m_req if c not in m_df.columns]
        
        p_df = get_data("Performance_Log")
        p_req = ["Project", "Resource Name", "MM/YYYY", "Goal", "Status", "Rating", "Comments", "Recommended for Recognition", "Recognition Comments", "Timestamp"]
        p_missing = [c for c in p_req if c not in p_df.columns]

        if m_missing or p_missing:
            for col in m_missing: m_df[col] = ""
            conn.update(worksheet="Master_List", data=m_df)
            for col in p_missing: p_df[col] = ""
            conn.update(worksheet="Performance_Log", data=p_df)
            st.toast("System Repair: Columns synchronized.", icon="🛠️")
    except Exception:
        pass

auto_repair()

# --- Navigation ---
st.sidebar.title("Resource Management V13.6")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Analytics Dashboard"])

years_list = ["2024", "2025", "2026", "2027"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View (History)"])
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")

    with tab1:
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        with st.form("goal_v13_6", clear_on_submit=True):
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
            if not log_df.empty:
                log_df['Timestamp'] = log_df.get('Timestamp', "2000-01-01 00:00:00")
                log_clean = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last')
                unified_df = pd.merge(master_prep, log_clean[['Resource Name', 'Goal', 'Status', 'Rating']], on=['Resource Name', 'Goal'], how='left')
            else:
                unified_df = master_prep.copy()
            
            unified_df['Status'] = unified_df.get('Status', pd.Series(dtype=str)).fillna('Yet to Mark')
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
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        p_sel = st.sidebar.selectbox("Project", sorted(master_df["Project"].unique()))
        r_sel = st.selectbox("Resource", sorted(master_df[master_df["Project"] == p_sel]["Resource Name"].unique()))
        avail = master_df[(master_df["Resource Name"] == r_sel) & (master_df["Project"] == p_sel)]
        if not avail.empty:
            g_opts = avail.apply(lambda x: f"{x['Goal']} ({x['Month']} {x['Year']})", axis=1).tolist()
            sel_g = st.selectbox("Select Goal", g_opts)
            res_info = avail.iloc[g_opts.index(sel_g)]
            with st.form("cap_v13_6"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                rating = st.feedback("stars")
                if st.form_submit_button("💾 Save"):
                    new_e = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "Goal": res_info['Goal'], "Status": status,
                        "Rating": (rating+1 if rating is not None else 0), "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Saved!"); st.rerun()

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    if not master_df.empty:
        log_latest = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last') if not log_df.empty else pd.DataFrame(columns=['Resource Name', 'Goal', 'Status'])
        df = pd.merge(master_df, log_latest[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
        df['Status'] = df['Status'].fillna('Yet to Mark')

        # --- 🏆 LEADERBOARD LOGIC ---
        points_map = {'Achieved': 5, 'Partially Achieved': 3, 'Not Completed': 0, 'Yet to Mark': 0}
        df['Points'] = df['Status'].map(points_map)
        leaderboard = df.groupby('Resource Name')['Points'].sum().reset_index().sort_values('Points', ascending=False)

        st.subheader("🏆 Resource Leaderboard")
        if HAS_PLOTLY:
            fig_lead = px.bar(leaderboard, x='Points', y='Resource Name', orientation='h', color='Points', color_continuous_scale='Greens', text_auto=True)
            fig_lead.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_lead, use_container_width=True)

        st.divider()
        # Summary & Heatmap
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Goals", len(df))
        m2.metric("Achievement Rate", f"{(len(df[df['Status']=='Achieved'])/len(df)*100):.1f}%")
        m3.metric("Top Scorer", leaderboard.iloc[0]['Resource Name'] if not leaderboard.empty else "N/A")

        if HAS_PLOTLY:
            st.subheader("🔥 Goal Distribution Heatmap")
            heat_data = df.groupby(['Month', 'Status']).size().unstack(fill_value=0)
            for s in ['Achieved', 'Partially Achieved', 'Not Completed', 'Yet to Mark']:
                if s not in heat_data.columns: heat_data[s] = 0
            fig_heat = px.imshow(heat_data.T, labels=dict(x="Month", y="Status", color="Count"), color_continuous_scale='RdYlGn', text_auto=True)
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.warning("No data found for analytics.")
