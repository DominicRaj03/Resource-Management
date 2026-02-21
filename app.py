import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- Plotly Integration ---
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- App Config ---
st.set_page_config(page_title="Jarvis Resource Management V26.0", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Constants ---
CURRENT_YEAR = str(datetime.now().year)
YEARS = ["2024", "2025", "2026", "2027", "2028"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- Helper Functions ---
def get_data(sheet_name):
    """Fetches data with auto-initialization to prevent KeyErrors."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    
    # Pre-defined schemas for missing sheets
    schemas = {
        "Master_List": ["Resource Name", "Project", "Goal", "Year", "Month"],
        "Performance_Log": ["Resource Name", "Goal", "Status", "Rating", "Comments", "Recommended", "Justification", "Timestamp"],
        "Utilisation_Log": ["Resource Name", "Project", "Year", "Month", "Type", "Timestamp"]
    }
    return pd.DataFrame(columns=schemas.get(sheet_name, []))

def save_data(sheet_name, updated_df):
    """Universal save function with loader."""
    with st.spinner(f"Synchronizing {sheet_name}..."):
        try:
            conn.update(worksheet=sheet_name, data=updated_df)
            st.toast(f"✅ {sheet_name} updated!")
            time.sleep(1)
            return True
        except Exception:
            st.error(f"Sheet '{sheet_name}' not found. Please create it in your Google Sheet.")
            return False

# --- Global Data Loading ---
master_df = get_data("Master_List")
log_df = get_data("Performance_Log")
util_df = get_data("Utilisation_Log")

# --- Navigation ---
st.sidebar.title("Jarvis V26.0")
page = st.sidebar.radio("Navigation", [
    "Master List", "Performance Capture", "Resource Utilisation", 
    "Resource Profile", "Analytics Dashboard", "Audit Section"
])

# --- MODULE 1: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    t1, t2, t3 = st.tabs(["🆕 Add Goal", "📤 Bulk Import", "📋 Filtered View"])
    
    with t1:
        res_type = st.radio("Type", ["Existing", "New"], horizontal=True)
        with st.form("m_form"):
            c1, c2 = st.columns(2)
            if res_type == "Existing" and not master_df.empty:
                r_name = c1.selectbox("Resource", sorted(master_df["Resource Name"].unique()))
                r_proj = c2.text_input("Project", value=master_df[master_df["Resource Name"]==r_name]["Project"].iloc[0], disabled=True)
            else:
                r_name, r_proj = c1.text_input("Resource Name*"), c2.text_input("Project Name*")
            
            y, m = st.selectbox("Year", YEARS, index=YEARS.index(CURRENT_YEAR)), st.selectbox("Month", MONTHS)
            goal = st.text_area("Goal Details*")
            if st.form_submit_button("🎯 Register"):
                if r_name and r_proj and goal:
                    new_r = pd.DataFrame([{"Resource Name": r_name, "Project": r_proj, "Goal": goal, "Year": y, "Month": m}])
                    if save_data("Master_List", pd.concat([master_df, new_r], ignore_index=True)): st.rerun()

    with t3:
        # Added Year/Month Filtering
        f1, f2 = st.columns(2)
        fy = f1.selectbox("Filter Year", ["All"] + YEARS)
        fm = f2.selectbox("Filter Month", ["All"] + MONTHS)
        view_df = master_df.copy()
        if fy != "All": view_df = view_df[view_df["Year"] == fy]
        if fm != "All": view_df = view_df[view_df["Month"] == fm]
        st.dataframe(view_df, use_container_width=True, hide_index=True)

# --- MODULE 2: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.title("📈 Performance Capture")
    if not master_df.empty:
        # Added Year/Month Filtering to find specific goals
        f1, f2 = st.columns(2)
        sy = f1.selectbox("Goal Year", YEARS, index=YEARS.index(CURRENT_YEAR))
        sm = f2.selectbox("Goal Month", MONTHS)
        
        filtered_master = master_df[(master_df["Year"] == sy) & (master_df["Month"] == sm)]
        
        if not filtered_master.empty:
            c1, c2 = st.columns(2)
            p_sel = c1.selectbox("Project", sorted(filtered_master["Project"].unique()))
            r_sel = c2.selectbox("Resource", sorted(filtered_master[filtered_master["Project"]==p_sel]["Resource Name"].unique()))
            g_sel = st.selectbox("Goal", filtered_master[(filtered_master["Project"]==p_sel) & (filtered_master["Resource Name"]==r_sel)]["Goal"].tolist())
            
            with st.form("p_form"):
                status = st.selectbox("Status", ["Achieved", "In-Progress", "Partially achieved", "Not completed"])
                rating = st.feedback("stars")
                comments = st.text_area("Comments*")
                rec = st.checkbox("Recommend for Recognition?")
                just = st.text_area("Justification")
                if st.form_submit_button("💾 Save"):
                    new_p = pd.DataFrame([{
                        "Resource Name": r_sel, "Goal": g_sel, "Status": status, 
                        "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                        "Recommended": "Yes" if rec else "No", "Justification": just,
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    if save_data("Performance_Log", pd.concat([log_df, new_p], ignore_index=True)): st.rerun()
        else: st.info(f"No goals found for {sm} {sy}.")

# --- MODULE 3: UTILISATION ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    if not master_df.empty:
        with st.form("u_form"):
            u_r = st.selectbox("Resource", sorted(master_df["Resource Name"].unique()))
            u_p = master_df[master_df["Resource Name"]==u_r]["Project"].iloc[0]
            u_y, u_m = st.selectbox("Year", YEARS, index=YEARS.index(CURRENT_YEAR)), st.selectbox("Month", MONTHS)
            u_t = st.radio("Allocation", ["Billable", "Non-Billable"], horizontal=True)
            if st.form_submit_button("🚀 Update"):
                new_u = pd.DataFrame([{"Resource Name": u_r, "Project": u_p, "Year": u_y, "Month": u_m, "Type": u_t, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                if save_data("Utilisation_Log", pd.concat([util_df, new_u], ignore_index=True)): st.rerun()

# --- MODULE 4: RESOURCE PROFILE (With Export) ---
elif page == "Resource Profile":
    st.title("👤 Resource Profile")
    if not master_df.empty:
        sel = st.selectbox("Select Employee", sorted(master_df["Resource Name"].unique()))
        
        # Banner & Metrics
        p_data = log_df[log_df["Resource Name"] == sel] if not log_df.empty else pd.DataFrame()
        if not p_data.empty and "Yes" in p_data["Recommended"].values:
            st.success(f"🌟 **Award Nominee:** {sel} has been recommended for recognition!")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Stars", f"{p_data['Rating'].mean():.1f} ⭐" if not p_data.empty else "N/A")
        u_data = util_df[util_df["Resource Name"] == sel] if not util_df.empty else pd.DataFrame()
        c2.metric("Latest Status", u_data.iloc[-1]['Type'] if not u_data.empty else "N/A")
        
        # --- PDF/CSV Download ---
        if not p_data.empty:
            csv = p_data.to_csv(index=False).encode('utf-8')
            c3.download_button("📥 Download Profile (CSV)", data=csv, file_name=f"{sel}_Profile.csv", mime='text/csv')

        st.subheader("Goal Achievement History")
        st.dataframe(p_data, use_container_width=True, hide_index=True)

# --- MODULE 5: ANALYTICS ---
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    # Year/Month Global Filters for Analytics
    af1, af2 = st.columns(2)
    ay = af1.selectbox("Analysis Year", ["All"] + YEARS)
    am = af2.selectbox("Analysis Month", ["All"] + MONTHS)
    
    # Logic to merge logs with master for date-based analytics
    if not log_df.empty and not master_df.empty:
        merged = pd.merge(log_df, master_df[['Resource Name', 'Goal', 'Year', 'Month']], on=['Resource Name', 'Goal'], how='left')
        if ay != "All": merged = merged[merged["Year"] == ay]
        if am != "All": merged = merged[merged["Month"] == am]
        
        m1, m2 = st.columns(2)
        m1.metric("Evaluations", len(merged))
        m2.metric("Avg Rating", f"{merged['Rating'].mean():.1f} ⭐" if not merged.empty else "0.0")
        
        if HAS_PLOTLY and not merged.empty:
            st.plotly_chart(px.bar(merged, x="Resource Name", y="Rating", color="Status", barmode="group"))

# --- MODULE 6: AUDIT ---
else:
    st.title("🛡️ Audit Log")
    st.dataframe(log_df.sort_values("Timestamp", ascending=False), use_container_width=True)
