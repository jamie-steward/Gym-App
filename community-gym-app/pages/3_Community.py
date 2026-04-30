import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import load_profile
from components.ui import add_dashboard_styles, render_app_header, render_community_feed


st.set_page_config(page_title="Community", layout="wide")
add_dashboard_styles()

user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
render_app_header(profile["name"] if profile else "ShapeUp")
render_community_feed()
