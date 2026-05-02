import streamlit as st
import uuid

from components.auth import get_current_user, restore_session_from_cookie, show_logout_button
from components.navigation import restore_page_from_query
from components.ui import add_dashboard_styles

st.set_page_config(page_title="ShapeUp", layout="wide")
st.session_state["supabase_client_created_this_run"] = False
st.session_state["_auth_current_run_id"] = uuid.uuid4().hex
add_dashboard_styles()
restore_session_from_cookie(rerun_after_restore=True)
current_user = get_current_user()
if current_user:
    show_logout_button(current_user["email"], source="app.py/app shell")

current_page = restore_page_from_query()

pages = {
    "": [
        st.Page("pages/0_Home.py", title="Home", default=current_page == "home"),
        st.Page("pages/1_Progress.py", title="Progress", default=current_page == "progress"),
        st.Page("pages/2_Log_Workout.py", title="Log Workout", default=current_page == "log_workout"),
        st.Page("pages/3_Workout_History.py", title="Workout History", default=current_page == "workout_history"),
        st.Page("pages/4_Profile.py", title="Profile", default=current_page == "profile"),
        st.Page("pages/5_Communities.py", title="Communities", default=current_page == "communities"),
    ]
}

pg = st.navigation(pages)
pg.run()
