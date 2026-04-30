from datetime import datetime, timezone

import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import (
    create_workout,
    delete_workout_set,
    finish_workout,
    load_profile,
    load_workout_sets,
    save_workout_preset,
    save_workout_set,
)
from components.ui import add_dashboard_styles, render_app_header, render_page_heading, render_section_card_start
from components.database import load_workout_presets


st.set_page_config(page_title="Workouts", layout="wide")
add_dashboard_styles()


EXERCISES = [
    "Incline DB Press",
    "Bench Press",
    "Overhead Press",
    "Lat Pulldown",
    "Pull Up",
    "Seated Row",
    "Squat",
    "Leg Press",
    "Romanian Deadlift",
    "Deadlift",
    "Bicep Curl",
    "Tricep Pushdown",
    "Lateral Raise",
]


def get_active_workout():
    return st.session_state.get("active_workout")


def clear_active_workout():
    st.session_state.pop("active_workout", None)
    st.session_state.pop("cardio_distance_km", None)
    st.session_state.pop("cardio_duration_minutes", None)
    st.session_state.pop("cardio_estimated_calories", None)
    st.session_state.pop("preset_exercises", None)


def estimate_cardio_calories(workout_type, weight_kg, distance_km):
    if workout_type == "Run":
        return weight_kg * distance_km

    if workout_type == "Walk":
        return weight_kg * distance_km * 0.5

    return weight_kg * distance_km * 0.35


def show_start_workout(user_id):

    # --- PRESET LOADING ---
    presets = load_workout_presets(user_id)

    if presets:
        st.markdown("### Start from preset")

        preset_names = [p["name"] for p in presets]
        selected_preset_name = st.selectbox("Choose preset", preset_names)

        selected_preset = next(
            p for p in presets if p["name"] == selected_preset_name
        )

        if st.button("Start preset workout", use_container_width=True):
            preset_data = selected_preset["preset_data"]

            started_at = datetime.now(timezone.utc)

            try:
                workout = create_workout(
                    user_id=user_id,
                    workout_type=preset_data["workout_type"],
                    started_at=started_at,
                    subtype=preset_data.get("subtype"),
                )

                st.session_state["active_workout"] = {
                    "id": workout["id"],
                    "workout_type": preset_data["workout_type"],
                    "subtype": preset_data.get("subtype"),
                    "started_at": started_at.isoformat(),
                }

                # 👇 THIS IS THE IMPORTANT BIT
                st.session_state["preset_exercises"] = preset_data.get("exercises", [])

                st.rerun()

            except Exception as e:
                st.error(f"Could not start preset workout: {e}")

    render_section_card_start("Start Workout")

    workout_type = st.selectbox(
        "Workout type",
        ["Weight training", "Run", "Walk", "Cycle"],
    )

    subtype = None
    if workout_type == "Weight training":
        subtype = st.selectbox("Training type", ["Push", "Pull", "Legs", "Mixed"])

    if st.button("Start workout", use_container_width=True):
        started_at = datetime.now(timezone.utc)
        st.session_state.pop("workout_message", None)
        st.session_state.pop("cardio_distance_km", None)
        st.session_state.pop("cardio_duration_minutes", None)
        st.session_state.pop("cardio_estimated_calories", None)

        try:
            workout = create_workout(
                user_id=user_id,
                workout_type=workout_type,
                started_at=started_at,
                subtype=subtype,
            )
            st.session_state["active_workout"] = {
                "id": workout["id"],
                "workout_type": workout_type,
                "subtype": subtype,
                "started_at": started_at.isoformat(),
            }
            st.rerun()
        except Exception as e:
            st.error(f"Could not start workout. If tables are not created yet, run the SQL below. Error: {e}")


def show_weight_training(user_id, active_workout):
    workout_sets = load_workout_sets(user_id, active_workout["id"])
    exercises_in_workout = sorted({row["exercise_name"] for row in workout_sets})

    render_section_card_start("Add Set")

    preset_exercises = st.session_state.get("preset_exercises", [])

    exercise_options = preset_exercises + [
        ex for ex in EXERCISES if ex not in preset_exercises
    ]

    exercise_choice = st.selectbox(
        "Exercise",
        exercise_options + ["Custom exercise"],
        help="Open the menu and type to search.",
    )

    if exercise_choice == "Custom exercise":
        exercise_name = st.text_input("Exercise name")
    else:
        exercise_name = exercise_choice

    previous_sets = [
        row for row in workout_sets
        if row["exercise_name"] == exercise_name
    ]
    next_set_number = len(previous_sets) + 1
    st.caption(f"Next set: {next_set_number}")

    weight = st.number_input("Weight", min_value=0.0, value=0.0, step=2.5)
    reps = st.number_input("Reps", min_value=1, value=8, step=1)

    if st.button("Save set", use_container_width=True):
        if not exercise_name.strip():
            st.error("Choose or enter an exercise first.")
        else:
            try:
                _, is_pr = save_workout_set(
                    user_id=user_id,
                    workout_id=active_workout["id"],
                    exercise_name=exercise_name.strip(),
                    set_number=next_set_number,
                    weight=weight,
                    reps=reps,
                )

                if is_pr:
                    st.session_state["workout_message"] = f"New PR for {exercise_name}! 🎉"
                else:
                    st.session_state["workout_message"] = "Set saved"

                st.rerun()
            except Exception as e:
                st.error(f"Could not save set: {e}")

    show_current_sets(user_id, workout_sets)

    render_section_card_start("Preset")
    preset_name = st.text_input("Preset name", value=f"{active_workout.get('subtype') or 'Workout'} preset")

    if st.button("Save as preset", use_container_width=True):
        preset_data = {
            "workout_type": active_workout["workout_type"],
            "subtype": active_workout.get("subtype"),
            "exercises": exercises_in_workout,
        }

        try:
            save_workout_preset(user_id, preset_name, preset_data)
            st.success("Preset saved")
        except Exception as e:
            st.error(f"Could not save preset: {e}")


def show_current_sets(user_id, workout_sets):
    render_section_card_start("Current Sets")

    if not workout_sets:
        st.info("No sets logged yet.")
        return

    grouped_sets = {}
    for row in workout_sets:
        grouped_sets.setdefault(row["exercise_name"], []).append(row)

    for exercise_name, rows in grouped_sets.items():
        st.markdown(f"**{exercise_name}**")

        for row in sorted(rows, key=lambda item: item["set_number"]):
            set_col, delete_col = st.columns([5, 1])

            with set_col:
                weight_label = f"{float(row['weight']):g}kg"
                st.write(f"- Set {row['set_number']}: {weight_label} x {row['reps']}")

            with delete_col:
                if st.button("Remove", key=f"delete_set_{row['id']}"):
                    try:
                        delete_workout_set(user_id, row["id"])
                        st.session_state["workout_message"] = "Set removed"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not remove set: {e}")


def show_cardio(active_workout, profile):
    render_section_card_start(f"{active_workout['workout_type']} Details")

    distance_km = st.number_input("Distance km", min_value=0.0, value=0.0, step=0.1)
    cardio_duration = st.number_input("Time minutes", min_value=0, value=30, step=1)
    weight_kg = float(profile["weight_kg"]) if profile else 70.0
    estimated = estimate_cardio_calories(active_workout["workout_type"], weight_kg, distance_km)

    st.write(f"Estimated calories: **{round(estimated)} kcal**")
    st.session_state["cardio_distance_km"] = distance_km
    st.session_state["cardio_duration_minutes"] = cardio_duration
    st.session_state["cardio_estimated_calories"] = estimated


def show_finish_workout(user_id, active_workout):
    if st.button("Finish Workout", use_container_width=True):
        ended_at = datetime.now(timezone.utc)
        started_at = datetime.fromisoformat(active_workout["started_at"])
        duration_minutes = (ended_at - started_at).total_seconds() / 60

        try:
            workout = finish_workout(
                user_id=user_id,
                workout_id=active_workout["id"],
                ended_at=ended_at,
                duration_minutes=duration_minutes,
                distance_km=st.session_state.get("cardio_distance_km"),
                cardio_duration_minutes=st.session_state.get("cardio_duration_minutes"),
                estimated_calories=st.session_state.get("cardio_estimated_calories"),
            )
            clear_active_workout()

            st.success("Workout finished")
            st.write(f"Duration: **{int(round(duration_minutes))} minutes**")

            if workout and workout.get("estimated_calories") is not None:
                st.write(f"Estimated calories: **{workout['estimated_calories']} kcal**")
        except Exception as e:
            st.error(f"Could not finish workout: {e}")


user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
render_app_header(profile["name"] if profile else "ShapeUp")
render_page_heading("Workouts", "Log strength sessions and simple cardio.")

active_workout = get_active_workout()

if st.session_state.get("workout_message"):
    st.success(st.session_state.pop("workout_message"))

if active_workout is None:
    show_start_workout(user_id)
else:
    started_at = datetime.fromisoformat(active_workout["started_at"])
    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="card-label">Active workout</div>
            <p class="stat-value">{active_workout['workout_type']}</p>
            <p class="subtle-text">Started {started_at.strftime('%H:%M')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_workout["workout_type"] == "Weight training":
        show_weight_training(user_id, active_workout)
    else:
        show_cardio(active_workout, profile)

    show_finish_workout(user_id, active_workout)
