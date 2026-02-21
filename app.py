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
st.set_page_config(page_title="Jarvis Resource Management V25.0", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Constants ---
CURRENT_YEAR = str(datetime.now().year)
YEARS = ["2024", "2025", "2026", "2027", "2028"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- Helper Functions ---
def get_data(sheet_name):
    """Fetches data with auto-initialization of schemas to prevent KeyErrors."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    
    # Schema definitions for missing sheets
    schemas = {
        "Master_List": ["Resource Name", "Project", "Goal", "Year", "Month"],
        "Performance_Log": ["Resource Name", "Goal", "Status", "Rating", "Comments", "Recommended", "Justification", "Timestamp"],
        "Utilisation_Log": ["Resource Name", "Project", "Year", "Month", "Type", "Timestamp"]
    }
    return pd.DataFrame(columns=schemas.get(sheet_name, []))

def save_data(sheet_name, updated_df):
    """Universal save function with loader and error catching."""
    with st.spinner(f"Synchronizing with {sheet_name}..."):
        try:
            conn.update(worksheet=sheet_name, data=updated_df)
            st.toast(f"✅ {sheet_name} updated successfully!")
            time.sleep(1)
            return True
        except Exception as e:
            st.error(f"Failed to update {sheet_name}. Ensure the worksheet exists in your Google Sheet.")
            return False

# --- Global Data Loading ---
master_df = get_data("Master_List")
log_df = get_data("Performance_Log")
util_df = get_data("Utilisation_Log")

# --- Navigation Sidebar ---
st.sidebar.title("Jarvis V25.0")
page = st.sidebar.radio("Navigation", [
    "Master List", "Performance Capture", "Resource Utilisation", 
    "Resource Profile", "Analytics Dashboard", "Audit Section"
])

# --- MODULE 1: MASTER LIST ---
if page == "Master List":
    st.title("👤 Resource Master List")
    t1, t2, t3 = st.tabs(["🆕 Add Goal", "📤 Bulk Import", "📋 View All"])
    
    with t1:
        res_type = st.radio("Type", ["Existing", "New"], horizontal=True)
        with st.form("master_form"):
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
                    new_row = pd.DataFrame([{"Resource Name": r_name, "Project": r_proj, "Goal": goal, "Year": y, "Month": m}])
                    if save_data("Master_List", pd.concat([master_df, new_row], ignore_index=True)): st.rerun()

    with t2:
        u_file = st.file_uploader("Upload CSV/Excel Template", type=['csv','xlsx'])
        if u_file:
            import_df = pd.read_csv(u_file) if u_file.name.endswith('.csv') else pd.read_excel(u_file)
            if st.button("🚀 Confirm Bulk Import"):
                if save_data("Master_List", pd.concat([master_df, import_df], ignore_index=True)): st.rerun()

    with t3:
        st.dataframe(master_df, use_container_width=True, hide_index=True)

# --- MODULE 2: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.title("📈 Performance Capture")
    if not master_df.empty:
        c1, c2 = st.columns(2)
        p_filt = c1.selectbox("Select Project", sorted(master_df["Project"].unique()))
        r_filt = c2.selectbox("Select Resource", sorted(master_df[master_df["Project"]==p_filt]["Resource Name"].unique()))
        g_filt = st.selectbox("Select Goal", master_df[(master_df["Project"]==p_filt) & (master_df["Resource Name"]==r_filt)]["Goal"].tolist())
        
        # Override Logic
        is_dup = not log_df.empty and not log_df[(log_df["Resource Name"]==r_filt) & (log_df["Goal"]==g_filt)].empty
        if is_dup:
            st.warning("⚠️ Goal already captured.")
            if not st.checkbox("Enable Override?"): st.stop()

        with st.form("perf_form"):
            status = st.selectbox("Status", ["Achieved", "In-Progress", "Partially achieved", "Not completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            rec = st.checkbox("Recommend for Recognition?")
            just = st.text_area("Justification")
            if st.form_submit_button("💾 Save Performance"):
                new_p = pd.DataFrame([{
                    "Resource Name": r_filt, "Goal": g_filt, "Status": status, 
                    "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                    "Recommended": "Yes" if rec else "No", "Justification": just,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                if save_data("Performance_Log", pd.concat([log_df, new_p], ignore_index=True)): st.rerun()

# --- MODULE 3: UTILISATION ---
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    if not master_df.empty:
        with st.form("util_form"):
            u_r = st.selectbox("Resource", sorted(master_df["Resource Name"].unique()))
            u_p = master_df[master_df["Resource Name"]==u_r]["Project"].iloc[0]
            st.caption(f"Assigned Project: {u_p}")
            u_y, u_m = st.selectbox("Year", YEARS, index=YEARS.index(CURRENT_YEAR)), st.selectbox("Month", MONTHS)
            u_t = st.radio("Allocation", ["Billable", "Non-Billable"], horizontal=True)
            if st.form_submit_button("🚀 Update Allocation"):
                new_u = pd.DataFrame([{"Resource Name": u_r, "Project": u_p, "Year": u_y, "Month": u_m, "Type": u_t, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                if save_data("Utilisation_Log", pd.concat([util_df, new_u], ignore_index=True)): st.rerun()

# --- MODULE 4: RESOURCE PROFILE ---
elif page == "Resource Profile":
    st.title("👤 Resource Profile")
    if not master_df.empty:
        sel = st.selectbox("Select Employee", sorted(master_df["Resource Name"].unique()))
        
        # Recognition Banner
        p_data = log_df[log_df["Resource Name"] == sel] if not log_df.empty else pd.DataFrame()
        if not p_data.empty and "Yes" in p_data["Recommended"].values:
            st.success(f"🌟 **Award Nominee:** {sel} has been recommended for recognition!")
            st.balloons()
            
        m1, m2 = st.columns(2)
        m1.metric("Avg Stars", f"{p_data['Rating'].mean():.1f} ⭐" if not p_data.empty else "N/A")
        u_data = util_df[util_df["Resource Name"] == sel] if not util_df.empty else pd.DataFrame()
        m2.metric("Current Utilisation", u_data.iloc[-1]['Type'] if not u_data.empty else "Unknown")
        
        st.subheader("Goal Achievement History")
        st.dataframe(p_data, use_container_width=True, hide_index=True)

# --- MODULE 5: ANALYTICS ---
elif page == "Analytics Dashboard":
    st.title("📊 Insights")
    if not log_df.empty:
        # Leaderboard Logic
        leaderboard = log_df.groupby("Resource Name")["Rating"].mean().sort_values(ascending=False).head(5)
        st.subheader("Top 5 Performers (Avg Stars)")
        st.table(leaderboard)
        if HAS_PLOTLY:
            st.plotly_chart(px.pie(log_df, names="Status", title="Team Status Distribution"))

# --- MODULE 6: AUDIT ---
else:
    st.title("🛡️ Audit Log")
    if not log_df.empty:
        st.dataframe(log_df.sort_values("Timestamp", ascending=False), use_container_width=True)
