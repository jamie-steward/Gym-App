import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import load_profile
from components.ui import add_dashboard_styles, render_app_header, render_page_heading, show_profile_editor, show_profile_setup


st.set_page_config(page_title="Profile", layout="wide")
add_dashboard_styles()

user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)

if profile is None:
    show_profile_setup(user_id, email)
    st.stop()

render_app_header(profile["name"])
render_page_heading("Profile", "View your details and update your targets.")
show_profile_editor(user_id, profile)
