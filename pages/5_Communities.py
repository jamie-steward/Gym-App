import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import (
    follow_user,
    load_following_ids,
    load_following_profiles,
    load_profile,
    load_public_profiles,
    unfollow_user,
)
from components.ui import (
    add_dashboard_styles,
    get_public_display_name,
    get_username_label,
    render_app_header,
    render_avatar_html,
    render_community_feed,
    render_goal_badge,
    render_page_heading,
    render_spacer,
)


st.set_page_config(page_title="Communities", layout="wide")
add_dashboard_styles()


def render_person_card(current_user_id, person, following_ids):
    display_name = get_public_display_name(person)
    username_label = get_username_label(person)
    avatar_html = render_avatar_html(display_name, person.get("avatar_url"), "feed-avatar")
    is_following = person["user_id"] in following_ids
    button_label = "Following" if is_following else "Follow"

    card_col, action_col = st.columns([4, 1])

    with card_col:
        st.markdown(
            f"""
            <div class="dashboard-card" style="padding: 0.9rem 1rem;">
                <div class="feed-head">
                    {avatar_html}
                    <div>
                        <div class="feed-name">{display_name}</div>
                        <div class="feed-meta">{username_label}</div>
                    </div>
                    {render_goal_badge(person.get("goal", "recomp"))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_col:
        if st.button(button_label, key=f"follow_{person['user_id']}", use_container_width=True):
            if is_following:
                unfollow_user(current_user_id, person["user_id"])
            else:
                follow_user(current_user_id, person["user_id"])

            st.rerun()


user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
display_name = get_public_display_name(profile, email)

render_app_header(display_name, profile.get("avatar_url") if profile else None)
render_page_heading("Communities", "Find people and follow their fitness progress.")
render_spacer("md")

following_ids = load_following_ids(user_id)
following_profiles = load_following_profiles(user_id)
public_profiles = load_public_profiles(user_id)

st.markdown('<div class="card-label">Following</div>', unsafe_allow_html=True)
if following_profiles:
    for person in following_profiles:
        render_person_card(user_id, person, following_ids)
        render_spacer("sm")
else:
    st.info("Follow people to start shaping your future feed.")

render_spacer("section")
st.markdown('<div class="card-label">Suggested users</div>', unsafe_allow_html=True)

if public_profiles:
    for person in public_profiles:
        render_person_card(user_id, person, following_ids)
        render_spacer("sm")
else:
    st.info("No other public profiles yet.")

render_spacer("section")
render_community_feed()
