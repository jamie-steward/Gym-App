from datetime import date, datetime
from html import escape

import streamlit as st

from components.auth import require_login, show_logout_button
from components.charts import calculate_weight_summary, show_recent_weight_chart
from components.database import load_last_finished_workout, load_logs, load_profile, save_log_entry
from components.ui import (
    add_dashboard_styles,
    render_app_header,
    render_community_feed,
    get_public_display_name,
    render_section_title,
    render_section_card_start,
    render_spacer,
    render_stat_card,
    render_status_card,
    render_weight_card,
    show_profile_setup,
)


st.set_page_config(page_title="Home", layout="wide")
add_dashboard_styles()


user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)

if profile is None:
    show_profile_setup(user_id, email)
    st.stop()

logs = load_logs(user_id)
last_workout = load_last_finished_workout(user_id)
user_logs = logs[logs["user_id"] == str(user_id)].copy().sort_values("date")
weight_logs = user_logs.dropna(subset=["weight"]).copy()
summary = calculate_weight_summary(weight_logs)


def get_status_detail(status_label):
    if status_label == "Building baseline":
        return "Building baseline", "info", "Log 14 days to unlock trend feedback."

    if profile["goal"] == "Cut":
        if status_label == "On track":
            return status_label, "good", "Your cut trend is in the target range."
        if status_label == "Dropping fast":
            return "Dropping fast", "warn", "Keep an eye on recovery and training performance."
        return "Needs momentum", "warn", "The trend is not dropping much yet."

    if profile["goal"] == "Lean bulk":
        if status_label == "On track":
            return status_label, "good", "Your lean bulk trend is in the target range."
        if status_label == "Rising fast":
            return "Rising fast", "warn", "You may be gaining faster than needed."
        return "Needs fuel", "warn", "The trend is not rising much yet."

    if status_label == "On track":
        return status_label, "good", "Your recomp trend is nicely stable."

    return "Watch trend", "info", "Recomp usually works best with a stable weight trend."


def get_default_weight(entry_date):
    user_previous_logs = user_logs[user_logs["date"] <= entry_date].sort_values("date")
    user_previous_weight_logs = user_previous_logs.dropna(subset=["weight"])
    existing_entry = user_previous_logs[user_previous_logs["date"] == entry_date]

    if not existing_entry.empty:
        return float(existing_entry.iloc[-1]["weight"]), "Existing entry found for this date - fields pre-filled"

    if not user_previous_weight_logs.empty:
        return (
            float(user_previous_weight_logs.iloc[-1]["weight"]),
            "Using your most recent previous entry as a starting point",
        )

    return float(profile["weight_kg"]), ""


def show_log_weight_fields():
    entry_date = st.date_input("Date", date.today(), key="dialog_log_date")
    default_weight, prefill_message = get_default_weight(entry_date)

    if prefill_message:
        st.info(prefill_message)

    weight = st.number_input(
        "Weight (kg)",
        min_value=0.0,
        step=0.1,
        value=default_weight,
        key="dialog_log_weight",
    )

    if st.button("Save entry", use_container_width=True, key="dialog_save_entry"):
        save_log_entry(
            user_id=user_id,
            entry_date=entry_date,
            goal=profile["goal"],
            weight=weight,
        )

        st.success("Entry saved")
        st.rerun()


def format_workout_datetime(value):
    if not value:
        return ""

    try:
        workout_time = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return workout_time.strftime("%d %b %Y · %H:%M")
    except Exception:
        return value


def get_workout_title(summary):
    workout_type = summary.get("workout_type") or "Workout"
    subtype = summary.get("subtype")

    if subtype:
        return f"{workout_type} · {subtype}"

    return workout_type


def show_last_workout_card(summary):
    render_section_card_start("Last Workout")

    if summary is None:
        st.markdown(
            """
            <div class="dashboard-card">
                <div class="card-label">No workouts logged yet</div>
                <p class="stat-value">Ready when you are</p>
                <p class="subtle-text">Start your first session from the Log Workout page.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cta_label = "Log your first workout"
    else:
        pr_text = f"{summary['pr_count']} PRs" if summary["pr_count"] else "No PRs yet"
        st.markdown(
            f"""
            <div class="dashboard-card">
                <div class="card-label">{escape(format_workout_datetime(summary.get("ended_at")))}</div>
                <p class="stat-value">{escape(get_workout_title(summary))}</p>
                <p class="subtle-text">
                    {summary["duration_minutes"]} min · {summary["total_sets"]} sets ·
                    {summary["exercise_count"]} exercises · {pr_text}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cta_label = "View workouts"

    if st.button(cta_label, use_container_width=True, key="home_last_workout_cta"):
        try:
            if summary is None:
                st.switch_page("pages/2_Log_Workout.py")
            else:
                st.switch_page("pages/3_Workout_History.py")
        except Exception:
            st.info("Open Workout History from the sidebar.")


if hasattr(st, "dialog"):
    @st.dialog("Log Weight")
    def show_log_weight_dialog():
        show_log_weight_fields()
else:
    def show_log_weight_dialog():
        st.session_state["show_inline_log_weight"] = True


name = get_public_display_name(profile, email)
current_weight = summary["current_weight"]
if current_weight is None:
    current_weight = float(profile["weight_kg"])
weekly_change = summary["weekly_change"]
status_text, status_kind, status_detail = get_status_detail(summary["goal_status_label"])
streak = summary["streak"]
weekly_value = "Need 14 days" if weekly_change is None else f"{weekly_change:+.2f} kg"
weekly_detail = "Latest 7 logged entries vs previous 7"

render_app_header(name, profile.get("avatar_url"))

render_weight_card(name, current_weight, weekly_value, status_text, status_kind, streak, profile["goal"])

render_spacer("md")

stat_left, stat_mid, stat_right = st.columns(3)

with stat_left:
    render_stat_card("Weekly change", weekly_value, weekly_detail, "v")

with stat_mid:
    render_stat_card("Streak", f"{streak} days", "Consecutive days logged through today", "#")

with stat_right:
    render_status_card(status_text, status_kind, status_detail, profile["goal"])

render_spacer("section")
render_section_title("Dashboard")

chart_col, action_col = st.columns([65, 35], gap="large")

with chart_col:
    render_section_card_start("Recent Weight")
    show_recent_weight_chart(weight_logs)

with action_col:
    render_section_card_start("Quick Actions")
    if st.button("⚖️\nLog Weight", use_container_width=True):
        show_log_weight_dialog()

    if st.button("🏋️\nLog Workout", use_container_width=True):
        try:
            st.switch_page("pages/2_Log_Workout.py")
        except Exception:
            st.info("Open the Log Workout page from the sidebar.")

    if st.button("🎯\nSet Goal", use_container_width=True):
        try:
            st.switch_page("pages/4_Profile.py")
        except Exception:
            st.info("Open the Profile page to update your goal.")

    if st.session_state.get("show_inline_log_weight"):
        show_log_weight_fields()

render_spacer("section")
show_last_workout_card(last_workout)

render_spacer("lg")
render_community_feed()

with st.expander("See raw data"):
    st.write(user_logs)
