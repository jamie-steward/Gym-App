import re

import streamlit as st

from components.database import (
    calculate_targets,
    create_profile,
    is_username_available,
    update_full_profile,
    update_public_profile,
    upload_avatar,
)


GOALS = ["Cut", "Lean bulk", "Recomp"]
ACTIVITY_LEVELS = ["Sedentary", "Light", "Moderate", "Very active"]
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,20}$")


def normalize_goal(goal):
    goal_key = str(goal).strip().lower().replace("-", " ").replace("_", " ")

    if goal_key == "cut":
        return "cut"

    if goal_key in ["lean bulk", "bulk"]:
        return "lean_bulk"

    return "recomp"


def get_goal_label(goal):
    goal_key = normalize_goal(goal)

    if goal_key == "cut":
        return "Cut"

    if goal_key == "lean_bulk":
        return "Lean bulk"

    return "Recomp"


def get_goal_color(goal):
    goal_key = normalize_goal(goal)

    if goal_key == "cut":
        return "#4dabf7"

    if goal_key == "lean_bulk":
        return "#51cf66"

    return "#ffd43b"


def get_goal_class(goal):
    goal_key = normalize_goal(goal)

    if goal_key == "cut":
        return "goal-cut"

    if goal_key == "lean_bulk":
        return "goal-bulk"

    return "goal-recomp"


def render_goal_badge(goal):
    return f'<div class="status-pill {get_goal_class(goal)}">{get_goal_label(goal)}</div>'


def get_public_display_name(profile, fallback_email=""):
    if profile and profile.get("display_name"):
        return profile["display_name"]

    if profile and profile.get("username"):
        return profile["username"]

    if profile and profile.get("name"):
        return profile["name"]

    if fallback_email:
        return fallback_email.split("@")[0]

    return "ShapeUp user"


def get_username_label(profile):
    username = (profile or {}).get("username")
    return f"@{username}" if username else "No username yet"


def get_initials(name):
    parts = str(name or "S").split()
    return "".join(part[0] for part in parts[:2]).upper() or "S"


def render_avatar_html(name, avatar_url=None, class_name="feed-avatar"):
    if avatar_url:
        return f'<div class="{class_name}"><img src="{avatar_url}" alt="{name} avatar"></div>'

    return f'<div class="{class_name}">{get_initials(name)}</div>'


def validate_username(username):
    username = str(username or "").strip().lower()

    if not username:
        return False, "Choose a username."

    if not USERNAME_PATTERN.match(username):
        return False, "Use 3-20 lowercase letters, numbers, or underscores."

    return True, ""


def add_dashboard_styles():
    st.markdown(
        """
        <style>
        :root {
            --shape-bg: #050708;
            --shape-panel: rgba(15, 19, 25, 0.76);
            --shape-panel-strong: rgba(18, 23, 30, 0.92);
            --shape-line: rgba(255, 255, 255, 0.12);
            --shape-muted: #9ca3b5;
            --shape-text: #f7f8fb;
            --shape-green: #66f05f;
            --shape-green-soft: rgba(102, 240, 95, 0.18);
            --shape-purple: #9b5cff;
        }

        .stApp {
            background:
                radial-gradient(circle at 18% 2%, rgba(102, 240, 95, 0.13), transparent 18rem),
                radial-gradient(circle at 92% 6%, rgba(102, 240, 95, 0.10), transparent 20rem),
                radial-gradient(circle at 78% 46%, rgba(155, 92, 255, 0.10), transparent 22rem),
                linear-gradient(180deg, #090d11 0%, #050708 55%, #030405 100%);
            color: var(--shape-text);
        }

        [data-testid="stHeader"] {
            background: rgba(9, 13, 18, 0);
        }

        section[data-testid="stSidebar"] {
            background: rgba(5, 7, 8, 0.92);
            border-right: 1px solid var(--shape-line);
        }

        section[data-testid="stSidebar"] a {
            border-radius: 18px;
            color: var(--shape-muted);
            font-weight: 750;
            margin: 0.16rem 0;
        }

        section[data-testid="stSidebar"] a[aria-current="page"] {
            background: var(--shape-green-soft);
            color: var(--shape-green);
        }

        .block-container {
            max-width: 960px;
            padding-top: 0.65rem;
            padding-bottom: 5rem;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.82rem;
        }

        h1, h2, h3, p, label, span, div {
            letter-spacing: 0;
        }

        h1, h2, h3 {
            color: var(--shape-text);
        }

        .account-bar {
            margin: 0 0 0.15rem 0;
        }

        .account-email {
            color: var(--shape-muted);
            font-size: 0.84rem;
            font-weight: 700;
            line-height: 2.55rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .account-email span {
            color: #dfe5ef;
            font-weight: 850;
        }

        .account-bar div.stButton > button {
            min-height: 2.4rem;
            border-radius: 999px;
            padding: 0.32rem 0.7rem;
            background: rgba(255, 255, 255, 0.055);
            border: 1px solid var(--shape-line);
            color: var(--shape-text);
            font-size: 0.82rem;
            font-weight: 850;
            box-shadow: none;
        }

        .shape-topbar {
            display: grid;
            grid-template-columns: 54px 1fr 54px;
            align-items: center;
            gap: 0.85rem;
            margin: 0.1rem 0 0.75rem 0;
        }

        .shape-avatar {
            width: 48px;
            height: 48px;
            border-radius: 18px;
            display: grid;
            place-items: center;
            color: #071007;
            font-weight: 900;
            font-size: 1.05rem;
            background: linear-gradient(135deg, #f7f8fb, #667085);
            position: relative;
            box-shadow: 0 18px 34px rgba(0, 0, 0, 0.28);
        }

        .shape-avatar img,
        .feed-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: inherit;
        }

        .shape-avatar::after {
            content: "";
            position: absolute;
            width: 11px;
            height: 11px;
            right: 1px;
            bottom: 3px;
            border-radius: 999px;
            background: var(--shape-green);
            border: 3px solid #050708;
        }

        .shape-brand {
            text-align: center;
        }

        .shape-brand-title {
            color: var(--shape-text);
            font-size: clamp(1.75rem, 6vw, 2.45rem);
            font-weight: 800;
            line-height: 1;
            margin: 0;
        }

        .shape-brand-title span {
            color: var(--shape-green);
        }

        .shape-brand-subtitle {
            color: var(--shape-muted);
            font-size: 0.92rem;
            font-weight: 650;
            margin: 0.3rem 0 0 0;
        }

        .shape-bell {
            justify-self: end;
            width: 42px;
            height: 42px;
            border-radius: 16px;
            display: grid;
            place-items: center;
            color: var(--shape-text);
            background: rgba(255, 255, 255, 0.055);
            border: 1px solid var(--shape-line);
            position: relative;
            font-size: 1.35rem;
        }

        .shape-bell::after {
            content: "";
            position: absolute;
            right: 7px;
            top: 6px;
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: var(--shape-green);
        }

        .dashboard-card {
            background:
                linear-gradient(145deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.028)),
                var(--shape-panel);
            border: 1px solid var(--shape-line);
            border-radius: 28px;
            padding: 1.15rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 24px 60px rgba(0, 0, 0, 0.33);
            backdrop-filter: blur(18px);
            min-height: 100%;
        }

        .weight-card {
            padding: clamp(1.15rem, 3.2vw, 1.65rem);
            background:
                radial-gradient(circle at 76% 34%, rgba(102, 240, 95, 0.18), transparent 15rem),
                linear-gradient(145deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.025)),
                var(--shape-panel-strong);
        }

        .hero-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }

        .hero-greeting {
            color: var(--shape-text);
            font-size: clamp(1.5rem, 5vw, 2rem);
            font-weight: 850;
            margin: 0;
        }

        .hero-subtitle {
            color: var(--shape-muted);
            font-size: 1.05rem;
            font-weight: 650;
            margin: 0.3rem 0 0 0;
        }

        .range-pill {
            color: #d8dde9;
            background: rgba(5, 7, 8, 0.44);
            border: 1px solid var(--shape-line);
            border-radius: 16px;
            padding: 0.58rem 0.8rem;
            font-weight: 760;
            white-space: nowrap;
        }

        .card-label {
            color: var(--shape-muted);
            font-size: 0.82rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.55rem;
        }

        .big-number {
            color: var(--shape-text);
            font-size: clamp(4.2rem, 16vw, 7.2rem);
            font-weight: 900;
            line-height: 0.95;
            margin: 0.95rem 0 0 0;
            text-shadow: 0 0 28px rgba(255, 255, 255, 0.14);
        }

        .big-number span {
            color: var(--shape-muted);
            font-size: clamp(1.4rem, 4vw, 2rem);
            font-weight: 850;
        }

        .hero-change {
            color: var(--shape-green);
            font-size: clamp(1.3rem, 4vw, 1.75rem);
            font-weight: 850;
            margin: 0.85rem 0 0.8rem 0;
        }

        .hero-change span {
            color: var(--shape-muted);
            font-size: 1rem;
            font-weight: 700;
            margin-left: 0.45rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.56rem 0.84rem;
            font-weight: 800;
            font-size: 0.92rem;
            margin: 0.25rem 0.35rem 0 0;
        }

        .status-good {
            background: var(--shape-green-soft);
            color: var(--shape-green);
            border: 1px solid rgba(102, 240, 95, 0.28);
        }

        .status-warn {
            background: rgba(251, 191, 36, 0.14);
            color: #fde68a;
            border: 1px solid rgba(253, 230, 138, 0.28);
        }

        .status-info {
            background: rgba(102, 240, 95, 0.12);
            color: var(--shape-green);
            border: 1px solid rgba(102, 240, 95, 0.22);
        }

        .goal-cut {
            background: rgba(77, 171, 247, 0.14);
            color: #4dabf7;
            border: 1px solid rgba(77, 171, 247, 0.28);
        }

        .goal-bulk {
            background: rgba(81, 207, 102, 0.14);
            color: #51cf66;
            border: 1px solid rgba(81, 207, 102, 0.28);
        }

        .goal-recomp {
            background: rgba(255, 212, 59, 0.14);
            color: #ffd43b;
            border: 1px solid rgba(255, 212, 59, 0.28);
        }

        .subtle-text {
            color: var(--shape-muted);
            margin: 0.35rem 0 0 0;
        }

        .stat-card {
            min-height: 220px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            overflow: visible;
            padding-top: 1.35rem;
            padding-bottom: 1.35rem;
        }

        .profile-stat-card {
            height: 220px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 1.35rem;
            border-radius: 24px;
            border: 1px solid var(--shape-line);
            overflow: hidden;
        }

        .profile-start-weight {
            color: rgba(255, 255, 255, 0.6);
            margin-top: 0.28rem;
        }

        .profile-targets-expander {
            margin-top: 20px;
        }

        .stat-value {
            color: var(--shape-text);
            font-size: clamp(1.55rem, 5vw, 2.3rem);
            font-weight: 900;
            line-height: 1.08;
            margin: 0 0 0.2rem 0;
            min-height: 2.55rem;
        }

        .stat-icon {
            width: 44px;
            height: 44px;
            border-radius: 18px;
            display: grid;
            place-items: center;
            margin-bottom: 0.9rem;
            color: #071007;
            background: linear-gradient(135deg, var(--shape-green), #8dfb67);
            font-weight: 900;
        }

        .gap-sm {
            height: 8px;
        }

        .gap-md {
            height: 16px;
        }

        .gap-lg {
            height: 24px;
        }

        .section-gap,
        .gap-section {
            height: 32px;
        }

        .profile-card-gap,
        .hero-stat-gap {
            height: 16px;
        }

        .section-label-card {
            min-height: 46px;
            padding: 0.62rem 1.05rem;
            display: flex;
            align-items: center;
        }

        .section-label-card > .card-label {
            margin: 0;
        }

        .section-content-gap {
            height: 24px;
        }

        .dashboard-card div[data-testid="stHorizontalBlock"] {
            gap: 1.15rem;
        }

        .dashboard-card div.stButton > button {
            min-height: 5.65rem;
            border-radius: 24px;
            padding: 0.95rem 1rem 0.95rem 1.15rem;
            background:
                radial-gradient(circle at 1.7rem 50%, rgba(102, 240, 95, 0.34), transparent 1.2rem),
                linear-gradient(145deg, rgba(102, 240, 95, 0.22), rgba(255, 255, 255, 0.055));
            border: 1px solid rgba(102, 240, 95, 0.24);
            color: var(--shape-text);
            font-weight: 900;
            line-height: 1.15;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 14px 30px rgba(0, 0, 0, 0.22);
            text-align: left;
            justify-content: flex-start;
            margin-bottom: 1rem;
            white-space: pre-line;
            transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, background 140ms ease;
        }

        .dashboard-card div.stButton > button p {
            white-space: pre-line;
            text-align: left;
        }

        .dashboard-card div.stButton > button:hover {
            border-color: rgba(102, 240, 95, 0.55);
            color: var(--shape-green);
            transform: translateY(-1px) scale(1.01);
            box-shadow: 0 0 24px rgba(102, 240, 95, 0.16), 0 16px 34px rgba(0, 0, 0, 0.24);
            background:
                radial-gradient(circle at 1.7rem 50%, rgba(102, 240, 95, 0.48), transparent 1.35rem),
                linear-gradient(145deg, rgba(102, 240, 95, 0.3), rgba(255, 255, 255, 0.065));
        }

        .action-card {
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-bottom: 1rem;
        }

        .action-icon {
            width: 64px;
            height: 64px;
            border-radius: 26px;
            display: grid;
            place-items: center;
            flex: 0 0 auto;
            color: #071007;
            background: linear-gradient(135deg, var(--shape-green), #8dfb67);
            box-shadow: 0 0 28px rgba(102, 240, 95, 0.28);
            font-weight: 900;
            font-size: 1.5rem;
        }

        .action-title {
            color: var(--shape-green);
            font-size: 1.45rem;
            font-weight: 900;
            margin: 0;
        }

        .section-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 1rem 0 0.65rem 0;
        }

        .section-title-row h3 {
            margin: 0;
            font-size: 1.5rem;
        }

        .section-title-row span {
            color: var(--shape-green);
            font-weight: 850;
        }

        .feed-post {
            background:
                radial-gradient(circle at 86% 38%, rgba(102, 240, 95, 0.10), transparent 11rem),
                linear-gradient(145deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.025)),
                var(--shape-panel);
            border: 1px solid var(--shape-line);
            border-radius: 28px;
            padding: 1.15rem;
            margin-bottom: 1rem;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.24);
        }

        .feed-head {
            display: grid;
            grid-template-columns: 54px 1fr auto;
            align-items: center;
            gap: 0.85rem;
        }

        .feed-avatar {
            width: 54px;
            height: 54px;
            border-radius: 22px;
            display: grid;
            place-items: center;
            color: #071007;
            background: linear-gradient(135deg, #f7f8fb, #758092);
            font-weight: 900;
        }

        .feed-name {
            color: var(--shape-text);
            font-weight: 900;
            font-size: 1.1rem;
            margin-bottom: 0.15rem;
        }

        .feed-meta {
            color: var(--shape-muted);
            font-size: 0.9rem;
            font-weight: 650;
        }

        .feed-body {
            color: var(--shape-text);
            font-size: 1.45rem;
            font-weight: 900;
            margin: 1rem 0 0.2rem 0;
        }

        .feed-subtext {
            color: var(--shape-muted);
            font-size: 1rem;
            margin: 0 0 1rem 0;
        }

        .feed-divider {
            height: 1px;
            background: var(--shape-line);
            margin: 0.85rem 0;
        }

        .feed-actions {
            color: var(--shape-muted);
            display: flex;
            gap: 1.25rem;
            font-weight: 800;
        }

        .feed-actions span:first-child {
            color: var(--shape-green);
        }

        .targets-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .target-cell {
            background: rgba(255, 255, 255, 0.045);
            border: 1px solid var(--shape-line);
            border-radius: 22px;
            padding: 1rem;
            min-height: 116px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .target-label {
            color: var(--shape-muted);
            font-size: 0.82rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.45rem;
        }

        .target-value {
            color: var(--shape-text);
            font-size: clamp(1.35rem, 4vw, 2rem);
            font-weight: 900;
            line-height: 1.1;
            margin: 0;
        }

        .targets-header {
            display: flex;
            align-items: baseline;
            gap: 0.55rem;
            flex-wrap: wrap;
        }

        .targets-context {
            opacity: 0.85
            color: var(--shape-muted);
            font-size: 0.86rem;
            font-weight: 500;
            letter-spacing: 0;
            text-transform: none;
        }

        .targets-context-value {
            font-weight: 850;
        }

        .targets-separator {
            color: var(--shape-muted);
            opacity: 0.72;
            margin-left: -0.15rem;
        }

        @media (max-width: 720px) {
            .targets-grid {
                grid-template-columns: 1fr;
            }
        }

        div[data-testid="stDateInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-baseweb="input"] input {
            background: rgba(255, 255, 255, 0.075);
            border-radius: 18px;
            border: 1px solid var(--shape-line);
            color: var(--shape-text);
        }

        label {
            color: #d7dce8 !important;
            font-weight: 760 !important;
        }

        div.stButton > button {
            border-radius: 20px;
            border: 1px solid rgba(102, 240, 95, 0.45);
            background: linear-gradient(135deg, var(--shape-green), #8dfb67);
            color: #06100e;
            font-weight: 600;
            min-height: 3rem;
            cursor: pointer;
            transition: all 0.15s ease;
            box-shadow: 0 0 12px rgba(102, 240, 95, 0.28);
        }

        .stApp div.stButton > button:hover {
            outline: none !important;
            border-color: rgba(102, 240, 95, 0.58) !important;
            transform: scale(1.03);
            filter: brightness(1.08);
            box-shadow: 0 0 16px rgba(102, 240, 95, 0.45) !important;
        }

        .stApp div.stButton > button:active {
            transform: scale(0.97);
            transition: all 0.1s ease;
        }

        .stApp div.stButton > button:focus,
        .stApp div.stButton > button:focus-visible {
            outline: none !important;
            border-color: rgba(102, 240, 95, 0.58) !important;
            box-shadow: 0 0 0 2px rgba(102, 240, 95, 0.25), 0 0 16px rgba(102, 240, 95, 0.3) !important;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--shape-line);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.035);
            box-shadow: none !important;
            outline: none !important;
            overflow: hidden;
        }

        div[data-testid="stExpander"] details,
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary:focus,
        div[data-testid="stExpander"] summary:focus-visible {
            border: 0 !important;
            box-shadow: none !important;
            outline: none !important;
        }

        @media (max-width: 720px) {
            .shape-topbar {
                grid-template-columns: 54px 1fr 54px;
            }

            .shape-avatar {
                width: 50px;
                height: 50px;
                border-radius: 19px;
            }

            .shape-bell {
                width: 44px;
                height: 44px;
            }

            .dashboard-card {
                border-radius: 24px;
            }

        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(name, avatar_url=None):
    avatar_html = render_avatar_html(name, avatar_url, "shape-avatar")
    st.markdown(
        f"""
        <div class="shape-topbar">
            {avatar_html}
            <div class="shape-brand">
                <div class="shape-brand-title">Shape<span>Up</span></div>
                <p class="shape-brand-subtitle">Stronger together.</p>
            </div>
            <div class="shape-bell">!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_weight_card(name, current_weight, weekly_value, status_text, status_kind, streak, goal=None):
    status_class = get_goal_class(goal) if goal is not None else f"status-{status_kind}"

    st.markdown(
        f"""
        <div class="dashboard-card weight-card">
            <div class="hero-row">
                <div>
                    <p class="hero-greeting">Hey {name}</p>
                    <p class="hero-subtitle">Here's your progress</p>
                </div>
                <div class="range-pill">7 Days</div>
            </div>
            <p class="big-number">{current_weight:.1f}<span> kg</span></p>
            <p class="hero-change">{weekly_value}<span>this week</span></p>
            <div>
                <div class="status-pill status-info">{streak} day streak</div>
                <div class="status-pill {status_class}">{status_text}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_card(label, value, detail="", icon="+", extra_class=""):
    detail_html = f'<p class="subtle-text">{detail}</p>' if detail else ""
    st.markdown(
        f"""
        <div class="dashboard-card stat-card {extra_class}">
            <div class="stat-icon">{icon}</div>
            <div class="card-label">{label}</div>
            <p class="stat-value">{value}</p>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_header(title, subtitle, icon="+"):
    st.markdown(
        f"""
        <div class="action-card">
            <div class="action-icon">{icon}</div>
            <div>
                <p class="action-title">{title}</p>
                <p class="subtle-text">{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(status_text, status_kind, detail, goal=None):
    status_class = get_goal_class(goal) if goal is not None else f"status-{status_kind}"

    st.markdown(
        f"""
        <div class="dashboard-card stat-card">
            <div class="stat-icon">✓</div>
            <div class="card-label">Goal status</div>
            <p class="stat-value"><span class="status-pill {status_class}" style="margin: 0;">{status_text}</span></p>
            <p class="subtle-text">{detail}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title, action_text=""):
    st.markdown(
        f"""
        <div class="section-title-row">
            <h3>{title}</h3>
            <span>{action_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_heading(title, subtitle=""):
    subtitle_html = f'<p class="shape-brand-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-title-row page-heading">
            <div>
                <h3>{title}</h3>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_spacer(size="md"):
    classes = {
        "sm": "gap-sm",
        "md": "gap-md",
        "lg": "gap-lg",
        "section": "gap-section",
    }
    spacer_class = classes.get(size, "gap-md")
    st.markdown(f'<div class="{spacer_class}"></div>', unsafe_allow_html=True)


def render_glass_card(title, body, icon="+"):
    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="action-card" style="margin-bottom: 0;">
                <div class="action-icon">{icon}</div>
                <div>
                    <p class="action-title">{title}</p>
                    <p class="subtle-text">{body}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_card_start(label):
    label_html = f'<div class="card-label">{label}</div>' if label else ""
    st.markdown(
        f"""
        <div class="dashboard-card section-label-card">
            {label_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-content-gap"></div>', unsafe_allow_html=True)


def render_card_end():
    st.markdown("</div>", unsafe_allow_html=True)


def render_card_start():
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)


def render_community_feed():
    render_section_title("Community Feed", "View all")

    posts = [
        {
            "name": "Tom",
            "meta": "2h ago",
            "body": "Bench PR: 100kg x 5",
            "subtext": "New personal best",
            "likes": 12,
            "comments": 3,
        },
        {
            "name": "Sarah",
            "meta": "4h ago",
            "body": "Lost 1.2kg this week",
            "subtext": "12 day streak",
            "likes": 15,
            "comments": 2,
        },
        {
            "name": "You",
            "meta": "1d ago",
            "body": "Weekly update",
            "subtext": "On track to hit my goal",
            "likes": 20,
            "comments": 6,
        },
    ]

    for post in posts:
        st.markdown(
            f"""
            <div class="feed-post">
                <div class="feed-head">
                    <div class="feed-avatar">{post['name'][0]}</div>
                    <div>
                        <div class="feed-name">{post['name']}</div>
                        <div class="feed-meta">{post['meta']}</div>
                    </div>
                    <div class="feed-meta">...</div>
                </div>
                <p class="feed-body">{post['body']}</p>
                <p class="feed-subtext">{post['subtext']}</p>
                <div class="feed-divider"></div>
                <div class="feed-actions">
                    <span>Heart {post['likes']}</span>
                    <span>Comment {post['comments']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_profile_summary(profile, followers_count=0, following_count=0, current_weight=None):
    goal = normalize_goal(profile["goal"])
    display_name = get_public_display_name(profile)
    username_label = get_username_label(profile)
    avatar_html = render_avatar_html(display_name, profile.get("avatar_url"), "feed-avatar")
    calorie_low = int(profile["calorie_low"])
    calorie_high = int(profile["calorie_high"])
    protein_target = int(profile["protein_target"])
    use_custom_targets = bool(profile.get("use_custom_targets"))
    custom_calorie_target = profile.get("custom_calorie_target")
    custom_protein_target = profile.get("custom_protein_target")
    display_calorie_target = f"{calorie_low}&ndash;{calorie_high} kcal"
    display_protein_target = f"{protein_target}g"
    custom_note = ""

    if use_custom_targets:
        if custom_calorie_target:
            display_calorie_target = f"{int(custom_calorie_target)} kcal"
        if custom_protein_target:
            display_protein_target = f"{int(custom_protein_target)}g"
        custom_note = '<p class="subtle-text" style="margin-top: 0.75rem;">Custom targets are enabled.</p>'

    if goal == "cut":
        target_label = "Cutting targets"
        maintenance = round(((calorie_low + 600) + (calorie_high + 400)) / 2)
        target_context = f"{maintenance - calorie_high}&ndash;{maintenance - calorie_low} kcal deficit"
    elif goal == "lean_bulk":
        target_label = "Bulking targets"
        maintenance = round(((calorie_low - 150) + (calorie_high - 300)) / 2)
        target_context = f"{calorie_low - maintenance}&ndash;{calorie_high - maintenance} kcal surplus"
    else:
        target_label = "Recomp targets"
        maintenance = round(((calorie_low + 150) + (calorie_high - 150)) / 2)
        target_context = "Around maintenance"

    target_context_color = get_goal_color(goal)
    goal_badge = render_goal_badge(goal)
    starting_weight = profile.get("starting_weight_kg") or profile.get("weight_kg")
    current_weight = float(current_weight if current_weight is not None else profile.get("weight_kg", 0))
    started_line = ""
    change_line = ""

    if starting_weight:
        weight_change = current_weight - float(starting_weight)
        change_arrow = "↓" if weight_change < 0 else "↑" if weight_change > 0 else ""
        started_line = f'<p class="subtle-text profile-start-weight">Started at {float(starting_weight):.1f} kg</p>'
        change_line = f'<p class="subtle-text" style="margin-top: 0.12rem; color: {target_context_color}; font-weight: 850;">{weight_change:+.1f} kg {change_arrow}</p>'

    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="card-label">Profile</div>
            <div class="feed-head">
                {avatar_html}
                <div>
                    <div class="feed-name">{display_name}</div>
                    <div class="feed-meta">{username_label}</div>
                    <div class="feed-meta" style="margin-top: 0.28rem;">
                        <strong>{followers_count}</strong> followers&nbsp;&nbsp;·&nbsp;&nbsp;<strong>{following_count}</strong> following
                    </div>
                </div>
                {goal_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_spacer("md")

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        render_stat_card("Age", profile["age"], "", "#", "profile-stat-card")

    with col2:
        render_stat_card("Height", f"{profile['height_cm']} cm", "", "H", "profile-stat-card")

    with col3:
        st.markdown(
            f"""
            <div class="dashboard-card stat-card profile-stat-card">
                <div class="stat-icon">W</div>
                <div class="card-label">Weight</div>
                <p class="stat-value">{current_weight:.1f} kg</p>
                {started_line}
                {change_line}
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_spacer("md")

    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="targets-header">
                <div class="card-label">{target_label}:</div>
                <div class="targets-context"> <span class="targets-context-value" style="color: {target_context_color};">{target_context}</span></div>
            </div>
            <div class="targets-grid">
                <div class="target-cell">
                    <div class="target-label">Estimated Maintenance</div>
                    <p class="target-value">{maintenance} kcal</p>
                </div>
                <div class="target-cell">
                    <div class="target-label">Daily Calorie Target</div>
                    <p class="target-value">{display_calorie_target}</p>
                </div>
                <div class="target-cell">
                    <div class="target-label">Daily Protein Target</div>
                    <p class="target-value">{display_protein_target}</p>
                </div>
            </div>
            {custom_note}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="profile-targets-expander">', unsafe_allow_html=True)
    with st.expander("How targets are calculated"):
        st.write("Maintenance is estimated from age, height, weight, and activity level.")
        st.write("Cut applies roughly a 400-600 kcal deficit.")
        st.write("Lean bulk applies roughly a 200-300 kcal surplus.")
        st.write("Recomp keeps calories around maintenance.")
        st.write("Protein is estimated from bodyweight, roughly around 2g/kg.")
    st.markdown("</div>", unsafe_allow_html=True)


def show_profile_setup(user_id, email):
    st.subheader("Complete your profile")

    pending_public_profile = st.session_state.get("pending_public_profile") or {}
    profile_name = st.text_input("Name", value=pending_public_profile.get("display_name", ""))
    profile_goal = st.selectbox("Goal", GOALS)
    profile_age = st.number_input("Age", min_value=10, max_value=100, value=32)
    profile_height = st.number_input("Height (cm)", min_value=100, max_value=230, value=183)
    profile_weight = st.number_input(
        "Current weight (kg)",
        min_value=30.0,
        max_value=200.0,
        value=72.0,
        step=0.1,
    )
    profile_activity = st.selectbox("Activity level", ACTIVITY_LEVELS, index=2)

    if st.button("Save profile", use_container_width=True):
        if profile_name.strip() == "":
            st.error("Enter your name first.")
        else:
            create_profile(
                user_id=user_id,
                email=email,
                name=profile_name,
                goal=profile_goal,
                age=profile_age,
                height_cm=profile_height,
                weight_kg=profile_weight,
                activity_level=profile_activity,
            )

            pending_username = pending_public_profile.get("username")
            pending_display_name = pending_public_profile.get("display_name")
            if pending_username:
                update_public_profile(
                    user_id=user_id,
                    username=pending_username,
                    display_name=pending_display_name or profile_name,
                )
                st.session_state.pop("pending_public_profile", None)

            st.success("Profile saved")
            st.rerun()


def show_profile_editor(user_id, profile, followers_count=0, following_count=0, current_weight=None):
    render_profile_summary(profile, followers_count, following_count, current_weight)

    render_spacer("md")

    if not profile.get("username"):
        st.markdown(
            """
            <div class="dashboard-card">
                <div class="card-label">Complete your public profile</div>
                <p class="subtle-text">Add a username and avatar so friends can find you in Communities.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_spacer("md")

    with st.expander("Public profile"):
        current_username = profile.get("username") or ""
        current_display_name = profile.get("display_name") or profile.get("name") or ""

        public_username = st.text_input("Username", value=current_username).strip().lower()
        public_display_name = st.text_input("Display name", value=current_display_name)
        avatar_file = st.file_uploader("Profile picture", type=["png", "jpg", "jpeg", "webp"])

        if profile.get("avatar_url"):
            st.image(profile["avatar_url"], width=96)

        if st.button("Update public profile", use_container_width=True):
            is_valid, error_message = validate_username(public_username)

            if not is_valid:
                st.error(error_message)
            elif not is_username_available(user_id, public_username):
                st.error("That username is already taken.")
            else:
                try:
                    avatar_url = None
                    if avatar_file is not None:
                        avatar_url = upload_avatar(user_id, avatar_file)

                    update_public_profile(
                        user_id=user_id,
                        username=public_username,
                        display_name=public_display_name,
                        avatar_url=avatar_url,
                    )
                    st.success("Public profile updated")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update public profile: {e}")

    render_spacer("md")

    with st.expander("Edit profile / recalculate targets"):
        edit_goal = st.selectbox(
            "Goal",
            GOALS,
            index=GOALS.index(profile["goal"]),
        )

        edit_age = st.number_input("Age", min_value=10, max_value=100, value=int(profile["age"]))
        edit_height = st.number_input(
            "Height (cm)",
            min_value=100,
            max_value=230,
            value=int(profile["height_cm"]),
        )
        edit_weight = st.number_input(
            "Current weight (kg)",
            min_value=30.0,
            max_value=200.0,
            value=float(profile["weight_kg"]),
            step=0.1,
        )
        edit_activity = st.selectbox(
            "Activity level",
            ACTIVITY_LEVELS,
            index=ACTIVITY_LEVELS.index(profile["activity_level"]),
        )

        new_low, new_high, new_protein = calculate_targets(
            edit_goal, edit_height, edit_weight, edit_age, edit_activity
        )

        st.write(f"Calculated calorie range: **{new_low}-{new_high} kcal**")
        st.write(f"Calculated protein target: **{new_protein}g**")

        use_custom_targets = st.checkbox(
            "Use custom targets",
            value=bool(profile.get("use_custom_targets")),
            help="Advanced: override the calculated calorie and protein targets.",
        )
        custom_calorie_target = None
        custom_protein_target = None

        if use_custom_targets:
            default_calories = int(profile.get("custom_calorie_target") or round((new_low + new_high) / 2))
            default_protein = int(profile.get("custom_protein_target") or new_protein)
            custom_calorie_target = st.number_input(
                "Custom daily calorie target",
                min_value=800,
                max_value=6000,
                value=default_calories,
                step=25,
            )
            custom_protein_target = st.number_input(
                "Custom daily protein target",
                min_value=40,
                max_value=400,
                value=default_protein,
                step=5,
            )

        if st.button("Update profile"):
            update_full_profile(
                user_id=user_id,
                goal=edit_goal,
                age=edit_age,
                height_cm=edit_height,
                weight_kg=edit_weight,
                activity_level=edit_activity,
                calorie_low=new_low,
                calorie_high=new_high,
                protein_target=new_protein,
                use_custom_targets=use_custom_targets,
                custom_calorie_target=custom_calorie_target,
                custom_protein_target=custom_protein_target,
            )

            st.success("Profile updated")
            st.rerun()
