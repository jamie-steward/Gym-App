import streamlit as st
from components.ui import add_dashboard_styles

st.set_page_config(page_title="ShapeUp", layout="wide")
add_dashboard_styles()

pages = {
    "": [
        st.Page("pages/0_Home.py", title="Home"),
        st.Page("pages/1_Progress.py", title="Progress"),
        st.Page("pages/2_Log_Workout.py", title="Log Workout"),
        st.Page("pages/3_Workout_History.py", title="Workout History"),
        st.Page("pages/4_Profile.py", title="Profile"),
        st.Page("pages/5_Communities.py", title="Communities"),
    ]
}

pg = st.navigation(pages)
pg.run()
