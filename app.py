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

st.set_page_config(page_title="Resource Management V24.0", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

CURRENT_YEAR = str(datetime.now().year)
years_list = ["2024", "2025", "2026", "2027", "2028"]
months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def get_data(sheet_name):
    """Robust data fetcher with auto-initialization."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    
    if sheet_name == "Performance_Log":
        return pd.DataFrame(columns=["Resource Name", "Goal", "Status", "Rating", "Comments", "Recommended", "Justification", "Timestamp"])
    if sheet_name == "Utilisation_Log":
        return pd.DataFrame(columns=["Resource Name", "Project", "Year", "Month", "Type", "Timestamp"])
    if sheet_name == "Master_List":
        return pd.DataFrame(columns=["Resource Name", "Project", "Goal", "Year", "Month"])
    return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Resource Management V24.0")
page = st.sidebar.radio("Navigation", [
    "Master List", "Performance Capture", "Resource Utilisation", 
    "Resource Profile", "Analytics Dashboard", "Audit Section"
])

master_df = get_data("Master_List")
log_df = get_data("Performance_Log")
util_df = get_data("Utilisation_Log")

# --- SCREEN: RESOURCE PROFILE ---
if page == "Resource Profile":
    st.title("👤 Resource Profile & Recognition")
    if not master_df.empty:
        sel_name = st.selectbox("Select Resource", sorted(master_df["Resource Name"].unique().tolist()))
        
        # Filter data safely
        p_logs = log_df[log_df["Resource Name"] == sel_name] if not log_df.empty else pd.DataFrame()
        
        # --- NEW: Recognition Banner ---
        if not p_logs.empty and "Recommended" in p_logs.columns:
            rec_logs = p_logs[p_logs["Recommended"] == "Yes"]
            if not rec_logs.empty:
                st.balloons()
                st.success(f"🌟 **Recognition Alert:** {sel_name} has been recommended for recognition in {len(rec_logs)} goal(s)!")
                with st.expander("View Recognition Details"):
                    for _, row in rec_logs.iterrows():
                        st.write(f"🏆 **Goal:** {row['Goal']}")
                        st.write(f"📝 **Justification:** {row.get('Justification', 'No justification provided')}")
                        st.divider()

        c1, c2, c3 = st.columns(3)
        c1.metric("Goals Logged", len(p_logs))
        c2.metric("Avg Rating", f"{p_logs['Rating'].mean():.1f} ⭐" if not p_logs.empty else "0.0")
        
        st.subheader("Performance History")
        st.dataframe(p_logs, use_container_width=True, hide_index=True)

# --- SCREEN: PERFORMANCE CAPTURE ---
elif page == "Performance Capture":
    st.header("📈 Performance Capture")
    if not master_df.empty:
        c1, c2 = st.columns(2)
        sel_p = c1.selectbox("Project", sorted(master_df["Project"].unique().tolist()))
        sel_r = c2.selectbox("Resource", sorted(master_df[master_df["Project"] == sel_p]["Resource Name"].unique().tolist()))
        goals = master_df[(master_df["Project"] == sel_p) & (master_df["Resource Name"] == sel_r)]["Goal"].tolist()
        sel_g = st.selectbox("Goal", goals)
        
        # Check for existing entries to allow overrides
        if not log_df.empty and not log_df[(log_df["Resource Name"] == sel_r) & (log_df["Goal"] == sel_g)].empty:
            st.warning("⚠️ This goal has already been captured.")
            if not st.checkbox("Would you like to override?"): st.stop()

        with st.form("cap_v24"):
            status = st.selectbox("Status", ["In-Progress", "Assigned", "Achieved", "Partially achieved", "Not completed"])
            rating = st.feedback("stars")
            comments = st.text_area("Comments*")
            is_rec = st.checkbox("Recommend for Recognition?")
            just = st.text_area("Justification (Required if recommended)")
            
            if st.form_submit_button("💾 Save Entry"):
                new_e = pd.DataFrame([{
                    "Resource Name": sel_r, "Goal": sel_g, "Status": status, 
                    "Rating": (rating+1 if rating is not None else 0), "Comments": comments,
                    "Recommended": "Yes" if is_rec else "No", "Justification": just,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="Performance_Log", data=pd.concat([log_df, new_e], ignore_index=True))
                st.success("Performance Saved!"); st.rerun()

# --- OTHER SCREENS (Truncated for space, identical to V23.0) ---
elif page == "Master List":
    st.title("👤 Resource Master List")
    # ... (Master List Logic)
elif page == "Resource Utilisation":
    st.title("💼 Resource Utilisation")
    # ... (Utilisation Logic)
elif page == "Analytics Dashboard":
    st.title("📊 Performance Insights")
    # ... (Analytics Logic)
else:
    st.title("🛡️ Audit Section")
    # ... (Audit Logic)
