import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- Page Config ---
st.set_page_config(page_title="Resource Management V9.2", layout="wide")

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
st.sidebar.title("Resource Management V9.2")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# Global Constants
years = ["2025", "2026", "2027"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- SCREEN: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    tab1, tab2 = st.tabs(["🆕 Register & Add Goals", "📋 Filtered List View"])
    
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")

    with tab1:
        st.subheader("Assign Goals to Resource")
        # Resource Type Toggle
        res_type = st.radio("Resource Type", ["Existing Resource", "New Resource"], horizontal=True)
        
        with st.form("new_goal_form", clear_on_submit=True):
            col_id1, col_id2 = st.columns(2)
            
            if res_type == "Existing Resource" and not master_df.empty:
                existing_names = sorted(master_df["Resource Name"].unique().tolist())
                res_name = col_id1.selectbox("Select Resource Name*", existing_names)
                # Auto-fill project based on selection
                current_proj = master_df[master_df["Resource Name"] == res_name]["Project"].iloc[0]
                res_proj = col_id2.text_input("Project", value=current_proj, disabled=True)
            else:
                res_name = col_id1.text_input("Resource Name*")
                res_proj = col_id2.text_input("Assign to Project*")
            
            col_dt1, col_dt2 = st.columns(2)
            sel_y = col_dt1.selectbox("Target Year", years)
            sel_m = col_dt2.selectbox("Target Month", months)
            goal_text = st.text_area("Enter Goal Details*")
            
            if st.form_submit_button("🎯 Add Goal"):
                if res_name and res_proj and goal_text:
                    new_goal = pd.DataFrame([{"Resource Name": res_name, "Project": res_proj, "Goal": goal_text, "Year": sel_y, "Month": sel_m}])
                    conn.update(worksheet="Master_List", data=pd.concat([master_df, new_goal], ignore_index=True))
                    st.success(f"Goal added for {res_name}!")
                    st.rerun()

    with tab2:
        if not master_df.empty:
            st.subheader("🔍 Goal Management")
            # 4-Tier Filter
            f1, f2, f3, f4 = st.columns(4)
            fp = f1.selectbox("Filter Project", ["All"] + sorted(master_df["Project"].unique().tolist()))
            res_opts = master_df[master_df["Project"] == fp] if fp != "All" else master_df
            fn = f2.selectbox("Filter Name", ["All"] + sorted(res_opts["Resource Name"].unique().tolist()))
            fy = f3.selectbox("Filter Year", ["All"] + years)
            fm = f4.selectbox("Filter Month", ["All"] + months)

            v_df = master_df.copy()
            if fp != "All": v_df = v_df[v_df["Project"] == fp]
            if fn != "All": v_df = v_df[v_df["Resource Name"] == fn]
            if fy != "All": v_df = v_df[v_df["Year"] == fy]
            if fm != "All": v_df = v_df[v_df["Month"] == fm]

            for i, row in v_df.iterrows():
                # Status Badge Logic
                is_eval = not log_df[(log_df["Resource Name"] == row["Resource Name"]) & (log_df["Goal"] == row["Goal"])].empty if not log_df.empty else False
                badge = "✅ Evaluated" if is_eval else "⏳ Pending"
                
                with st.expander(f"{badge} | {row['Resource Name']} - {row['Goal'][:40]}..."):
                    with st.form(key=f"edit_{i}"):
                        un = st.text_input("Name", value=row['Resource Name'])
                        up = st.text_input("Project", value=row['Project'])
                        ug = st.text_area("Goal Details", value=row['Goal'])
                        uy = st.selectbox("Year", years, index=years.index(row['Year']) if row['Year'] in years else 0)
                        um = st.selectbox("Month", months, index=months.index(row['Month']) if row['Month'] in months else 0)
                        
                        b1, b2 = st.columns([1, 4])
                        if b1.form_submit_button("💾 Update"):
                            master_df.at[i, 'Resource Name'], master_df.at[i, 'Project'] = un, up
                            master_df.at[i, 'Goal'], master_df.at[i, 'Year'], master_df.at[i, 'Month'] = ug, uy, um
                            conn.update(worksheet="Master_List", data=master_df)
                            st.rerun()
                        if b2.form_submit_button("🗑️ Delete"):
                            conn.update(worksheet="Master_List", data=master_df.drop(i))
                            st.rerun()

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
            sel_g = st.selectbox("Select Goal to Evaluate", g_opts)
            res_info = avail.iloc[g_opts.index(sel_g)]
            
            with st.form("capture_form"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                uploaded_file = st.file_uploader("Evidence Attachment", type=['pdf', 'png', 'jpg', 'docx'])
                rating = st.feedback("stars")
                
                if st.form_submit_button("💾 Save Record"):
                    new_e = pd.DataFrame([{
                        "Project": p_sel, "Resource Name": r_sel, "MM/YYYY": f"{res_info['Month']}/{res_info['Year']}",
                        "Goal": res_info['Goal'], "Status": status, "Rating": (rating+1 if rating else 0),
                        "Comments": comments, "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                    st.success("Evaluation Saved!")

# --- SCREEN: HISTORICAL VIEW ---
elif page == "Historical View":
    st.title("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        pf, mf = st.selectbox("Project", ["All"] + sorted(df["Project"].unique().tolist())), st.selectbox("Month", ["All"] + sorted(df["MM/YYYY"].unique().tolist()))
        v_df = df.copy()
        if pf != "All": v_df = v_df[v_df["Project"] == pf]
        if mf != "All": v_df = v_df[v_df["MM/YYYY"] == mf]
        
        # Excel Export
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            v_df.to_excel(writer, index=False)
        st.download_button("📥 Export to Excel", data=buf.getvalue(), file_name="Performance_Log.xlsx")
        st.dataframe(v_df, use_container_width=True)

# --- SCREEN: ANALYTICS DASHBOARD ---
else:
    st.title("📊 Performance Analytics")
    df = get_data("Performance_Log")
    if not df.empty:
        # Top 3 spotlight
        top_3 = df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(3)
        cols = st.columns(3)
        for i, (name, rating) in enumerate(top_3.items()):
            cols[i].metric(label=f"⭐ {name}", value=f"{rating:.2f}")
        st.divider()
        st.info("Additional project trends and charts can be added here.")
