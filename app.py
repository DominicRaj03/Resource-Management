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

st.set_page_config(page_title="Resource Management V15.0", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "Rating" in df.columns:
                df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def ensure_columns(df, required_cols):
    """Prevents KeyError by ensuring all expected columns exist in the dataframe."""
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    return df

# --- Navigation ---
st.sidebar.title("Resource Management V15.0")
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
        with st.form("goal_v15_0", clear_on_submit=True):
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
            f1, f2, f3, f4 = st.columns(4)
            sel_proj = f1.selectbox("Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            sel_res = f2.selectbox("Resource", ["All"] + sorted(master_df["Resource Name"].unique().tolist()))
            sel_year = f3.selectbox("Year", ["All"] + sorted(master_df["Year"].unique().astype(str).tolist()))
            sel_month = f4.selectbox("Month", ["All"] + months_list)

            # Defensive Column Handling for Log
            log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Timestamp'])
            
            log_latest = log_df.sort_values('Timestamp').drop_duplicates(subset=['Resource Name', 'Goal'], keep='last') if not log_df.empty else pd.DataFrame(columns=['Resource Name', 'Goal', 'Status'])

            display_df = pd.merge(master_df, log_latest[['Resource Name', 'Goal', 'Status']], on=['Resource Name', 'Goal'], how='left')
            display_df['Status'] = display_df['Status'].fillna('Assigned')

            filtered_df = display_df.copy()
            if sel_proj != "All": filtered_df = filtered_df[filtered_df["Project"] == sel_proj]
            if sel_res != "All": filtered_df = filtered_df[filtered_df["Resource Name"] == sel_res]
            if sel_year != "All": filtered_df = filtered_df[filtered_df["Year"].astype(str) == sel_year]
            if sel_month != "All": filtered_df = filtered_df[filtered_df["Month"] == sel_month]

            edited_df = st.data_editor(
                filtered_df,
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"], required=True),
                    "Resource Name": st.column_config.TextColumn(disabled=True),
                    "Project": st.column_config.TextColumn(disabled=True),
                },
                use_container_width=True, hide_index=True, key="goal_editor_v15_0"
            )

            a1, a2 = st.columns([1, 2])
            if a1.button("💾 Save Changes"):
                conn.update(worksheet="Master_List", data=edited_df.drop(columns=['Status'], errors='ignore'))
                new_entries = []
                for _, row in edited_df.iterrows():
                    new_entries.append({"Resource Name": row["Resource Name"], "Goal": row["Goal"], "Status": row["Status"], "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, pd.DataFrame(new_entries)], ignore_index=True))
                st.success("Saved!"); st.rerun()
            a2.download_button("📥 Export CSV", data=edited_df.to_csv(index=False).encode('utf-8'), file_name='goals.csv', mime='text/csv')

# --- SCREEN: PERFORMANCE CAPTURE (With State Reset) ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    if not master_df.empty:
        # Cascading Filters with Session State to allow resetting
        p_list = sorted(master_df["Project"].unique().tolist())
        sel_p = st.selectbox("1. Choose Project", p_list, key="cap_p")
        
        r_list = sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist())
        sel_r = st.selectbox("2. Choose Resource", r_list, key="cap_r")
        
        g_rows = master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]
        g_list = g_rows["Goal"].tolist()
        sel_g = st.selectbox("3. Select Goal", g_list, key="cap_g")
        
        with st.form("cap_v15_0", clear_on_submit=True):
            status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
            rating = st.feedback("stars") 
            comments = st.text_area("Comments*")
            st.divider()
            is_rec = st.checkbox("Recommend for Recognition?")
            just = st.text_area("Justification (Required if recommended)")
            
            if st.form_submit_button("💾 Save Entry"):
                if comments:
                    new_e = pd.DataFrame([{
                        "Resource Name": sel_r, "Goal": sel_g, "Status": status,
                        "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                        "Recommended": "Yes" if is_rec else "No", "Justification": just,
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    # Ensure Log sheet has all columns before update
                    log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Rating', 'Comments', 'Recommended', 'Justification', 'Timestamp'])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Performance Captured!"); st.rerun()
                else:
                    st.error("Comments are required.")
    else:
        st.warning("Please add goals in the Master List first.")

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Insights")
    master_df, log_df = get_data("Master_List"), get_data("Performance_Log")
    
    if not log_df.empty and not master_df.empty:
        log_df = ensure_columns(log_df, ['Resource Name', 'Goal', 'Status', 'Rating', 'Recommended', 'Justification'])
        df = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Project']], on=['Resource Name', 'Goal'], how='left')
        
        tab_a, tab_b = st.tabs(["📈 General Analytics", "🌟 Recognition Hall"])
        
        with tab_a:
            p_filter = st.selectbox("Project Filter", ["All"] + sorted(master_df["Project"].unique().tolist()))
            if p_filter != "All": df = df[df["Project"] == p_filter]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Evaluations", len(df))
            c2.metric("Achievement Rate", f"{(len(df[df['Status']=='Achieved'])/len(df)*100):.1f}%" if len(df)>0 else "0%")
            c3.metric("Avg Stars", f"{df['Rating'].mean():.1f} ⭐")

            if HAS_PLOTLY:
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🏆 Leaderboard")
                    lb = df.groupby("Resource Name")["Rating"].sum().reset_index().sort_values("Rating", ascending=False)
                    st.plotly_chart(px.bar(lb.head(10), x="Rating", y="Resource Name", orientation='h', color="Rating", color_continuous_scale='Greens'), use_container_width=True)
                with col2:
                    st.subheader("🎯 Goal Status")
                    st.plotly_chart(px.pie(df, names="Status", color="Status"), use_container_width=True)

        with tab_b:
            st.subheader("Recommended for Recognition")
            rec_df = df[df["Recommended"] == "Yes"][["Resource Name", "Project", "Goal", "Justification", "Timestamp"]]
            if not rec_df.empty:
                st.table(rec_df.sort_values("Timestamp", ascending=False))
            else:
                st.info("No recommendations recorded yet.")
