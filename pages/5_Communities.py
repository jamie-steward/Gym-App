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
from components.navigation import remember_current_page
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
remember_current_page("communities")
st.markdown(
    """
    <style>
    div[class*="st-key-follow_"] button,
    div[class*="st-key-follow-"] button {
        min-height: 3rem !important;
        padding: 0.55rem 0.9rem !important;
        border-radius: 20px !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 0 12px rgba(102, 240, 95, 0.28) !important;
    }

    div[class*="st-key-follow_"] button:hover,
    div[class*="st-key-follow-"] button:hover {
        transform: scale(1.03) !important;
        filter: brightness(1.08) !important;
        box-shadow: 0 0 16px rgba(102, 240, 95, 0.45) !important;
    }

    div[class*="st-key-follow_"] button:active,
    div[class*="st-key-follow-"] button:active {
        transform: scale(0.97) !important;
        transition: all 0.1s ease !important;
    }

    div[class*="st-key-following_action"] button,
    div[class*="st-key-following-action"] button {
        min-height: 3rem !important;
        padding: 0.55rem 0.9rem !important;
        border-radius: 20px !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: relative !important;
        text-align: center !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }

    div[class*="st-key-following_action"] button:hover,
    div[class*="st-key-following-action"] button:hover {
        background: linear-gradient(135deg, #ef4444, #f87171) !important;
        border-color: rgba(248, 113, 113, 0.85) !important;
        color: transparent !important;
        outline: none !important;
        transform: scale(1.03) !important;
        filter: brightness(1.08) !important;
        box-shadow: 0 0 16px rgba(255, 80, 80, 0.45) !important;
    }

    div[class*="st-key-following_action"] button:focus,
    div[class*="st-key-following-action"] button:focus,
    div[class*="st-key-following_action"] button:focus-visible,
    div[class*="st-key-following-action"] button:focus-visible {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(102, 240, 95, 0.25), 0 0 16px rgba(102, 240, 95, 0.3) !important;
    }

    div[class*="st-key-following_action"] button:active,
    div[class*="st-key-following-action"] button:active {
        transform: scale(0.97) !important;
        transition: all 0.1s ease !important;
    }

    div[class*="st-key-following_action"] button:hover::after,
    div[class*="st-key-following-action"] button:hover::after {
        content: "Unfollow";
        color: #ffffff;
        font-size: 0.92rem;
        font-weight: 600;
        line-height: 1;
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def visible_people(people, current_user_id):
    return [
        person for person in people
        if str(person.get("user_id")) != str(current_user_id)
    ]


def render_person_card(current_user_id, person, following_ids, section_key, idx):
    display_name = get_public_display_name(person)
    username_label = get_username_label(person)
    avatar_html = render_avatar_html(display_name, person.get("avatar_url"), "feed-avatar")
    person_id = str(person["user_id"])
    is_following = person_id in [str(following_id) for following_id in following_ids]
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
        button_key = f"follow_{section_key}_{idx}_{person_id}"
        button_container = st.container(key=f"following_action_{section_key}_{idx}_{person_id}") if is_following else st.container()

        with button_container:
            clicked = st.button(button_label, key=button_key, use_container_width=True)

        if clicked:
            if person_id == str(current_user_id):
                st.warning("You cannot follow yourself.")
                return

            if is_following:
                unfollow_user(current_user_id, person_id)
            else:
                follow_user(current_user_id, person_id)

            st.rerun()


user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
display_name = get_public_display_name(profile, email)

render_app_header(display_name, profile.get("avatar_url") if profile else None)
render_page_heading("Communities", "Find people and follow their fitness progress.")
render_spacer("md")

following_ids = load_following_ids(user_id)
following_profiles = visible_people(load_following_profiles(user_id), user_id)
public_profiles = visible_people(load_public_profiles(user_id), user_id)

st.markdown('<div class="card-label">Following</div>', unsafe_allow_html=True)
if following_profiles:
    for idx, person in enumerate(following_profiles):
        render_person_card(user_id, person, following_ids, "following", idx)
        render_spacer("sm")
else:
    st.info("Follow people to start shaping your future feed.")

render_spacer("section")
st.markdown('<div class="card-label">Suggested users</div>', unsafe_allow_html=True)

if public_profiles:
    for idx, person in enumerate(public_profiles):
        render_person_card(user_id, person, following_ids, "suggested", idx)
        render_spacer("sm")
else:
    st.info("No other public profiles yet.")

render_spacer("section")
render_community_feed()
