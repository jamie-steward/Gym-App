import streamlit as st

from components.auth import require_login, show_logout_button
from components.charts import calculate_weight_summary, show_goal_feedback, show_weight_chart
from components.database import load_logs, load_profile
from components.navigation import remember_current_page
from components.ui import (
    add_dashboard_styles,
    get_public_display_name,
    render_app_header,
    render_page_heading,
    render_spacer,
    show_profile_setup,
)


st.set_page_config(page_title="Progress", layout="wide")
add_dashboard_styles()
remember_current_page("progress")

user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)

if profile is None:
    show_profile_setup(user_id, email)
    st.stop()

render_app_header(get_public_display_name(profile, email), profile.get("avatar_url"))
render_page_heading("Progress", "Your full weight trend and coaching feedback.")
render_spacer("md")

user_logs = load_logs(user_id)
user_logs = user_logs[user_logs["user_id"] == str(user_id)].copy()
weight_summary = calculate_weight_summary(user_logs)

show_weight_chart(user_logs)

render_spacer("section")
show_goal_feedback(user_logs, profile, weight_summary)

with st.expander("See raw data"):
    st.write(user_logs)
