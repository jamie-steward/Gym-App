from datetime import datetime
from html import escape

import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import delete_workout_log, load_finished_workouts, load_profile
from components.navigation import go_to_page, remember_current_page
from components.ui import add_dashboard_styles, get_public_display_name, render_app_header, render_page_heading, render_spacer


st.set_page_config(page_title="Workout History", layout="wide")
add_dashboard_styles()
remember_current_page("workout_history")


def parse_workout_datetime(value):
    if not value:
        return None

    try:
        workout_time = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return workout_time.astimezone()
    except Exception:
        return None


def workout_time_range(summary):
    started_at = parse_workout_datetime(summary.get("started_at"))
    ended_at = parse_workout_datetime(summary.get("ended_at"))

    if not started_at or not ended_at:
        return ""

    date_label = started_at.strftime("%a %-d %b")
    return f"{date_label} • {started_at.strftime('%H:%M')}-{ended_at.strftime('%H:%M')}"


def workout_title(summary):
    workout_type = summary.get("workout_type") or "Workout"
    subtype = summary.get("subtype")

    if subtype:
        return f"{subtype} session"

    return workout_type


def workout_detail(summary):
    workout_type = summary.get("workout_type") or "Workout"
    subtype = summary.get("subtype")

    if subtype:
        return f"{workout_type} • {subtype}"

    return workout_type


def set_label(row):
    weight = row.get("weight")
    reps = row.get("reps")
    load_mode = row.get("load_mode") or "external_weight"

    if reps is None:
        return ""

    if load_mode == "bodyweight":
        return f"BWx{reps}"

    if weight is None:
        return ""

    if load_mode == "weighted_bodyweight":
        return f"+{float(weight):g}kg x {reps}"

    if load_mode == "assisted_bodyweight":
        return f"assisted {float(weight):g}kg x {reps}"

    return f"{float(weight):g}x{reps}"


def render_workout_card(summary, user_id, is_latest=False):
    workout_id = summary.get("workout", {}).get("id")
    pr_text = f"{summary['pr_count']} PRs" if summary["pr_count"] else "No PRs"
    label = "Latest completed workout" if is_latest else "Completed workout"

    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="card-label">{label}</div>
            <p class="stat-value">{escape(workout_title(summary))}</p>
            <p class="subtle-text">{escape(workout_time_range(summary))}</p>
            <p class="subtle-text">{escape(workout_detail(summary))}</p>
            <p class="subtle-text">
                {summary["duration_minutes"]} min • {summary["total_sets"]} sets •
                {summary["exercise_count"]} exercises • {pr_text}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("View details"):
        exercise_summaries = summary.get("exercise_summaries", [])

        if not exercise_summaries:
            st.caption("No exercise sets logged for this workout.")

        for exercise in exercise_summaries:
            set_summary = " • ".join(
                label for label in [set_label(row) for row in exercise.get("sets", [])]
                if label
            )
            pr_label = "New PR" if exercise.get("is_pr") else ""
            pr_line = ""
            if pr_label:
                pr_line = f'<p class="subtle-text" style="margin-top: 0.1rem; color: var(--shape-green); font-weight: 900;">{pr_label}</p>'

            st.markdown(
                f"""
                <div style="
                    background: rgba(255, 255, 255, 0.045);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 18px;
                    padding: 0.75rem 0.9rem;
                    margin-bottom: 0.65rem;
                ">
                    <div style="display: flex; justify-content: space-between; gap: 1rem; align-items: center;">
                        <strong>{escape(exercise["exercise_name"])}</strong>
                        <span style="color: var(--shape-green); font-weight: 900;">{exercise["set_count"]} sets</span>
                    </div>
                    <p class="subtle-text" style="margin-top: 0.35rem;">{escape(set_summary or "No sets")}</p>
                    {pr_line}
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_delete_workout_controls(workout_id, user_id)


def render_delete_workout_controls(workout_id, user_id):
    if not workout_id:
        st.error("This workout is missing an ID, so it cannot be deleted.")
        return

    confirm_key = f"confirm_delete_workout_{workout_id}"

    if not st.session_state.get(confirm_key):
        if st.button("Delete workout", key=f"delete_workout_{workout_id}", type="secondary"):
            st.session_state[confirm_key] = True
            st.rerun()
        return

    st.warning("Are you sure you want to delete this workout? This cannot be undone.")
    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button("Yes, delete workout", key=f"confirm_delete_workout_button_{workout_id}", type="primary"):
            try:
                deleted_rows = delete_workout_log(workout_id, user_id)
                if deleted_rows:
                    st.session_state.pop(confirm_key, None)
                    st.success("Workout deleted.")
                    st.rerun()
                else:
                    st.error("Workout could not be deleted. It may already be gone, or you may not have permission.")
            except Exception as e:
                st.error(f"Workout delete failed: {e}")

    with cancel_col:
        if st.button("Cancel", key=f"cancel_delete_workout_{workout_id}"):
            st.session_state.pop(confirm_key, None)
            st.rerun()


user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
render_app_header(get_public_display_name(profile, email), profile.get("avatar_url") if profile else None)
render_page_heading("Workout History", "Review your completed sessions.")
render_spacer("md")

finished_workouts = load_finished_workouts(user_id)

if not finished_workouts:
    st.markdown(
        """
        <div class="dashboard-card">
            <div class="card-label">No workouts logged yet</div>
            <p class="stat-value">Your log starts here</p>
            <p class="subtle-text">Finish a workout to see it in your history.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Log your first workout", use_container_width=True):
        go_to_page("log_workout")

    st.stop()

render_workout_card(finished_workouts[0], user_id, is_latest=True)

render_spacer("section")

for workout in finished_workouts[1:]:
    render_workout_card(workout, user_id)
    render_spacer("lg")
