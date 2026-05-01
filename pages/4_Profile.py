import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import count_followers, count_following, load_profile
from components.ui import (
    add_dashboard_styles,
    get_public_display_name,
    render_app_header,
    render_page_heading,
    render_spacer,
    show_profile_editor,
    show_profile_setup,
)


st.set_page_config(page_title="Profile", layout="wide")
add_dashboard_styles()

user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
followers_count = count_followers(user_id)
following_count = count_following(user_id)

if profile is None:
    show_profile_setup(user_id, email)
    st.stop()

render_app_header(get_public_display_name(profile, email), profile.get("avatar_url"))
render_page_heading("Profile", "View your details and update your targets.")
render_spacer("md")
show_profile_editor(user_id, profile, followers_count, following_count)
