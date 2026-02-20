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
st.set_page_config(page_title="Jarvis Performance V3.9", layout="wide")

# --- Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            # Clean strings to remove .0 decimal issues from Google Sheets
            for col in ["Year", "Month", "MM/YYYY"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True)
        return df
    except Exception:
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title("Jarvis V3.9")
page = st.sidebar.radio("Navigation", ["Master List", "Performance Capture", "Historical View", "Analytics Dashboard"])

# --- SCREEN: PERFORMANCE CAPTURE (RESTORED & FIXED) ---
if page == "Performance Capture":
    st.header("📈 Performance Capture")
    master_df = get_data("Master_List")
    log_df = get_data("Performance_Log")
    
    if not master_df.empty:
        proj_list = sorted(master_df["Project"].unique())
        proj_filter = st.sidebar.selectbox("Filter Project", proj_list)
        res_options = sorted(master_df[master_df["Project"] == proj_filter]["Resource Name"].unique())
        sel_res = st.selectbox("Select Resource", res_options)
        
        matched = master_df[(master_df["Resource Name"] == sel_res) & (master_df["Project"] == proj_filter)]
        
        if not matched.empty:
            res_info = matched.iloc[-1]
            st.info(f"**Current Goal:** {res_info['Goal']} ({res_info['Month']} {res_info['Year']})")
            
            # FIXED: KeyError 'Timestamp' safety check (image_b8f87e.png)
            if not log_df.empty and "Timestamp" in log_df.columns:
                history = log_df[log_df["Resource Name"] == sel_res].sort_values("Timestamp", ascending=False).head(3)
                if not history.empty:
                    with st.expander("🔍 View Goal History (Last 3 Months)"):
                        st.table(history[["MM/YYYY", "Goal", "Status", "Rating"]])
            
            with st.form("capture_form"):
                status = st.selectbox("Status", ["Achieved", "Partially Achieved", "Not Completed"])
                comments = st.text_area("Justification / Comments*")
                feedback = st.text_area("Overall Feedback")
                
                # --- RESTORED EVIDENCE ATTACHMENT (image_b88f22.png) ---
                uploaded_file = st.file_uploader("Evidence Attachment (Optional)", type=['pdf', 'png', 'jpg', 'docx'])
                
                rating = st.feedback("stars")
                
                if st.form_submit_button("💾 Save Record"):
                    if status != "Achieved" and not comments.strip():
                        st.error("Justification is mandatory for non-achieved goals!")
                    else:
                        period = f"{res_info['Month']}/{res_info['Year']}"
                        
                        # Prevent Duplicates
                        save_df = log_df.copy()
                        if not save_df.empty:
                            save_df = save_df[~((save_df["Resource Name"] == sel_res) & (save_df["MM/YYYY"] == period))]

                        # FIXED: SyntaxErrors for new_entry and uploaded_file (image_b54aa1.png, image_b8fbfc.png)
                        new_entry = pd.DataFrame([{
                            "Project": proj_filter, 
                            "Resource Name": sel_res, 
                            "MM/YYYY": period,
                            "Goal": res_info['Goal'], 
                            "Status": status, 
                            "Rating": (rating+1 if rating else 0),
                            "Comments": comments, 
                            "Feedback": feedback, 
                            "Evidence_Filename": (uploaded_file.name if uploaded_file else "No Attachment"),
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        conn.update(worksheet="Performance_Log", data=pd.concat([save_df, new_entry], ignore_index=True))
                        st.success("Entry Saved Successfully!")

# --- SCREEN: ANALYTICS DASHBOARD ---
elif page == "Analytics Dashboard":
    st.header("📊 Performance Analytics")
    df = get_data("Performance_Log")
    st.caption(f"🔄 **System Last Synced:** {datetime.now().strftime('%H:%M:%S')}")
    
    if not df.empty and HAS_PLOTLY:
        # Comparative Chart logic (benchmarking individual vs team)
        sel_p = st.selectbox("Select Project", sorted(df["Project"].unique()))
        team_avg = df[df["Project"] == sel_p].groupby("MM/YYYY")["Rating"].mean().reset_index()
        st.line_chart(team_avg.set_index("MM/YYYY"))
    else:
        st.info("Log data and ensure plotly is installed to see charts.")

# --- OTHER SCREENS (MASTER & HISTORICAL) ---
elif page == "Master List":
    st.header("👤 Master List Registration")
    with st.form("m_form"):
        n, p = st.text_input("Name"), st.text_input("Project")
        g = st.text_area("Goal")
        y, m = st.selectbox("Year", ["2025", "2026"]), st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        if st.form_submit_button("Save"):
            new_r = pd.DataFrame([{"Resource Name": n, "Project": p, "Goal": g, "Year": y, "Month": m}])
            conn.update(worksheet="Master_List", data=pd.concat([get_data("Master_List"), new_r], ignore_index=True))
            st.success("Resource Added!")

else: # Historical View
    st.header("📅 Historical Logs")
    df = get_data("Performance_Log")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
