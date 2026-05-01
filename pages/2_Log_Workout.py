from datetime import datetime, timezone
from html import escape
import json

import streamlit as st

from components.auth import require_login, show_logout_button
from components.database import (
    create_workout,
    delete_workout_set,
    finish_workout,
    load_active_workout,
    load_profile,
    load_workout_presets,
    load_workout_sets,
    save_workout_preset,
    save_workout_set,
    summarize_workout,
    update_workout_plan,
    update_workout_preset,
)
from components.ui import (
    add_dashboard_styles,
    get_public_display_name,
    render_app_header,
    render_page_heading,
    render_section_card_start,
    render_spacer,
)


st.set_page_config(page_title="Log Workout", layout="wide")
add_dashboard_styles()
st.markdown(
    """
    <style>
    div[class*="st-key-log_set_action"] button,
    div[class*="st-key-log-set-action"] button {
        min-height: 1.95rem !important;
        padding: 0.32rem 0.68rem !important;
        font-size: 0.82rem !important;
    }

    div[class*="st-key-remove_last_action"] button,
    div[class*="st-key-remove-last-action"] button {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: #f87171 !important;
        min-height: 0.92rem !important;
        padding: 0 !important;
        margin-top: 0.18rem;
        font-size: 0.62rem !important;
        font-weight: 800 !important;
        text-align: center;
    }

    div[class*="st-key-remove_last_action"] button:hover,
    div[class*="st-key-remove-last-action"] button:hover {
        color: #fca5a5 !important;
        transform: none !important;
        text-decoration: underline;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


EXERCISES = [
    "Incline DB Press",
    "Bench Press",
    "Overhead Press",
    "Lat Pulldown",
    "Pull Up",
    "Pull Ups",
    "Chest Dips",
    "Dips",
    "Assisted Pull Up",
    "Assisted Dip",
    "Seated Row",
    "Squat",
    "Leg Press",
    "Romanian Deadlift",
    "Deadlift",
    "Bicep Curl",
    "Tricep Pushdown",
    "Lateral Raise",
]

WORKOUT_TYPES = ["Weight training", "Run", "Walk", "Cycle"]
TRAINING_SUBTYPES = ["Push", "Pull", "Legs", "Mixed"]
BODYWEIGHT_EXERCISES = [
    "Pull Up",
    "Pull Ups",
    "Chest Dips",
    "Dips",
    "Assisted Pull Up",
    "Assisted Dip",
]
LOAD_MODE_LABELS = {
    "Bodyweight": "bodyweight",
    "Weighted": "weighted_bodyweight",
    "Assisted": "assisted_bodyweight",
    "External weight": "external_weight",
}
LOAD_MODE_DISPLAY = {
    "bodyweight": "Bodyweight",
    "weighted_bodyweight": "Weighted",
    "assisted_bodyweight": "Assisted",
    "external_weight": "External weight",
}


def get_active_workout():
    return st.session_state.get("active_workout")


def workout_plan_key(workout_id):
    return f"planned_exercises_{workout_id}"


def remember_workout_plan(workout_id, exercises):
    plan = clean_exercise_list(exercises)
    st.session_state[workout_plan_key(workout_id)] = plan
    st.session_state["preset_exercises"] = plan
    return plan


def remembered_workout_plan(workout_id):
    return clean_exercise_list(st.session_state.get(workout_plan_key(workout_id)) or [])


def restore_active_workout(user_id):
    active_workout = get_active_workout()
    workout = load_active_workout(user_id)

    if not workout:
        return active_workout

    workout_sets = load_workout_sets(user_id, workout["id"])
    planned_exercises = restored_workout_plan(workout, workout_sets)
    session_plan = clean_exercise_list((active_workout or {}).get("planned_exercises", []))
    cached_plan = remembered_workout_plan(workout["id"])
    session_name = (active_workout or {}).get("preset_name")

    if not workout_planned_exercises(workout):
        # Immediately after starting/logging, Supabase may briefly return an
        # active row without planned_exercises. Do not collapse the full plan
        # down to logged sets; use the same-workout cached plan first.
        fallback_plan = cached_plan or session_plan
        if fallback_plan:
            planned_exercises = build_visible_exercises(fallback_plan, workout_sets)
        if planned_exercises:
            update_workout_plan(user_id, workout["id"], planned_exercises)

    st.session_state["active_workout"] = {
        "id": workout["id"],
        "workout_type": workout["workout_type"],
        "subtype": workout.get("subtype"),
        "started_at": workout["started_at"],
        "planned_exercises": planned_exercises,
    }
    if workout.get("workout_name"):
        st.session_state["active_workout"]["preset_name"] = workout["workout_name"]
    elif session_name and active_workout and active_workout.get("id") == workout["id"]:
        st.session_state["active_workout"]["preset_name"] = session_name
    remember_workout_plan(workout["id"], planned_exercises)

    return st.session_state["active_workout"]


def clear_active_workout():
    active_workout = get_active_workout()
    if active_workout:
        st.session_state.pop(workout_plan_key(active_workout["id"]), None)
    st.session_state.pop("active_workout", None)
    st.session_state.pop("cardio_distance_km", None)
    st.session_state.pop("cardio_duration_minutes", None)
    st.session_state.pop("cardio_estimated_calories", None)
    st.session_state.pop("preset_exercises", None)


def clean_exercise_list(exercises):
    cleaned = []

    for exercise in exercises:
        exercise_name = str(exercise).strip()
        if exercise_name and exercise_name not in cleaned:
            cleaned.append(exercise_name)

    return cleaned


def workout_planned_exercises(workout):
    planned = workout.get("planned_exercises") or []

    if isinstance(planned, list):
        return clean_exercise_list(planned)

    if isinstance(planned, str):
        try:
            return clean_exercise_list(json.loads(planned))
        except Exception:
            return []

    return []


def workout_set_exercises(workout_sets):
    return clean_exercise_list([
        row["exercise_name"]
        for row in workout_sets
        if row.get("exercise_name")
    ])


def restored_workout_plan(workout, workout_sets):
    # Supabase is the source of truth after refresh/logout.
    # Keep the saved preset/manual plan first, then append any logged exercises
    # that are missing so older or partially migrated workouts do not break.
    plan = workout_planned_exercises(workout)
    return build_visible_exercises(plan, workout_sets)


def build_visible_exercises(planned_exercises, workout_sets):
    plan = clean_exercise_list(planned_exercises)

    for exercise_name in workout_set_exercises(workout_sets):
        if exercise_name not in plan:
            plan.append(exercise_name)

    return plan


def exercise_text_to_list(exercise_text):
    return clean_exercise_list(exercise_text.splitlines())


def exercise_list_to_text(exercises):
    return "\n".join(clean_exercise_list(exercises))


def option_index(options, value):
    return options.index(value) if value in options else 0


def normalize_preset_data(preset):
    data = preset.get("preset_data") or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {}

    exercises = data.get("exercises") or []
    workout_type = data.get("workout_type", "Weight training")
    subtype = data.get("subtype") or "Mixed"

    return {
        "workout_type": workout_type if workout_type in WORKOUT_TYPES else "Weight training",
        "subtype": subtype if subtype in TRAINING_SUBTYPES else "Mixed",
        "exercises": clean_exercise_list(exercises),
    }


def build_preset_data(workout_type, subtype, exercises):
    return {
        "workout_type": workout_type,
        "subtype": subtype if workout_type == "Weight training" else None,
        "exercises": clean_exercise_list(exercises),
    }


def workout_title(active_workout):
    return active_workout.get("preset_name") or active_workout.get("workout_type", "Workout")


def workout_detail(summary):
    workout_type = summary.get("workout_type") or "Workout"
    subtype = summary.get("subtype")

    if subtype:
        return f"{workout_type} · {subtype}"

    return workout_type


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
    return f"{date_label} • {started_at.strftime('%H:%M')}–{ended_at.strftime('%H:%M')}"


def start_workout_from_template(user_id, preset_name, preset_data):
    started_at = datetime.now(timezone.utc)
    st.session_state.pop("workout_message", None)
    st.session_state.pop("cardio_distance_km", None)
    st.session_state.pop("cardio_duration_minutes", None)
    st.session_state.pop("cardio_estimated_calories", None)

    workout = create_workout(
        user_id=user_id,
        workout_type=preset_data["workout_type"],
        started_at=started_at,
        subtype=preset_data.get("subtype"),
        planned_exercises=clean_exercise_list(preset_data.get("exercises", [])),
        workout_name=preset_name,
    )

    planned_exercises = clean_exercise_list(preset_data.get("exercises", []))
    st.session_state["active_workout"] = {
        "id": workout["id"],
        "workout_type": preset_data["workout_type"],
        "subtype": preset_data.get("subtype"),
        "started_at": started_at.isoformat(),
        "preset_name": preset_name,
        "planned_exercises": planned_exercises,
    }
    remember_workout_plan(workout["id"], planned_exercises)


def format_exercise_preview(exercises, max_items=4):
    exercises = clean_exercise_list(exercises)

    if not exercises:
        return "No exercises in this preset yet."

    visible_exercises = exercises[:max_items]
    preview = ", ".join(visible_exercises)
    remaining_count = len(exercises) - len(visible_exercises)

    if remaining_count > 0:
        preview = f"{preview} +{remaining_count} more"

    return preview


def estimate_cardio_calories(workout_type, weight_kg, distance_km):
    if workout_type == "Run":
        return weight_kg * distance_km

    if workout_type == "Walk":
        return weight_kg * distance_km * 0.5

    return weight_kg * distance_km * 0.35


def sets_for_exercise(workout_sets, exercise_name):
    exercise_sets = [
        row for row in workout_sets
        if row["exercise_name"] == exercise_name
    ]
    return sorted(exercise_sets, key=lambda row: row["set_number"])


def widget_key(text):
    return "".join(character if character.isalnum() else "_" for character in text.lower())


def compact_set_label(row, include_unit=False):
    load_mode = row.get("load_mode") or "external_weight"
    reps = row["reps"]

    if load_mode == "bodyweight":
        return f"BW x {reps}" if include_unit else f"BWx{reps}"

    if load_mode == "weighted_bodyweight":
        weight_label = f"+{float(row['weight']):g}kg"
        return f"{weight_label} x {row['reps']}"

    if load_mode == "assisted_bodyweight":
        weight_label = f"assisted {float(row['weight']):g}kg"
        return f"{weight_label} x {row['reps']}"

    weight_label = f"{float(row['weight']):g}kg"
    return f"{weight_label} x {reps}" if include_unit else f"{float(row['weight']):g}x{reps}"


def last_set_label(exercise_sets):
    if not exercise_sets:
        return "No sets yet"

    return compact_set_label(exercise_sets[-1], include_unit=True)


def set_summary_label(exercise_sets):
    if not exercise_sets:
        return "Sets: none yet"

    set_labels = [compact_set_label(row) for row in exercise_sets]
    return f"Sets: {' • '.join(set_labels)}"


def is_known_bodyweight_exercise(exercise_name):
    return exercise_name.strip().lower() in [
        name.lower()
        for name in BODYWEIGHT_EXERCISES
    ]


def save_set_for_exercise(user_id, active_workout, exercise_name, weight, reps, load_mode):
    workout_sets = load_workout_sets(user_id, active_workout["id"])
    previous_sets = sets_for_exercise(workout_sets, exercise_name)
    next_set_number = len(previous_sets) + 1

    _, is_pr = save_workout_set(
        user_id=user_id,
        workout_id=active_workout["id"],
        exercise_name=exercise_name,
        set_number=next_set_number,
        weight=weight,
        reps=reps,
        load_mode=load_mode,
    )

    current_plan = remembered_workout_plan(active_workout["id"]) or workout_planned_exercises(active_workout)
    if exercise_name not in current_plan:
        current_plan.append(exercise_name)
        current_plan = remember_workout_plan(active_workout["id"], current_plan)
        active_workout["planned_exercises"] = current_plan
        update_workout_plan(user_id, active_workout["id"], current_plan)

    if is_pr:
        st.session_state["workout_message"] = f"New PR for {exercise_name}! 🎉"
    else:
        st.session_state["workout_message"] = f"{exercise_name} set saved"


def show_log_set_fields(user_id, active_workout, exercise_name):
    workout_sets = load_workout_sets(user_id, active_workout["id"])
    exercise_sets = sets_for_exercise(workout_sets, exercise_name)
    last_set = exercise_sets[-1] if exercise_sets else None
    default_load_mode = (last_set or {}).get("load_mode") or "external_weight"
    default_weight = float(last_set["weight"]) if last_set else 0.0
    default_reps = int(last_set["reps"]) if last_set else 8
    key_base = f"{widget_key(exercise_name)}_{len(exercise_sets)}"

    st.markdown(f"### {exercise_name}")

    if is_known_bodyweight_exercise(exercise_name):
        load_labels = ["Bodyweight", "Weighted", "Assisted"]
        default_label = LOAD_MODE_DISPLAY.get(default_load_mode, "Bodyweight")
        if default_label not in load_labels:
            default_label = "Bodyweight"

        load_label = st.selectbox(
            "Load mode",
            load_labels,
            index=load_labels.index(default_label),
            key=f"dialog_load_mode_{key_base}",
        )
        load_mode = LOAD_MODE_LABELS[load_label]
    else:
        load_mode = "external_weight"

    weight = 0.0
    if load_mode != "bodyweight":
        weight_label = "Weight"
        if load_mode == "weighted_bodyweight":
            weight_label = "Added weight"
        elif load_mode == "assisted_bodyweight":
            weight_label = "Assistance weight"

        weight = st.number_input(
            weight_label,
            min_value=0.0,
            value=default_weight,
            step=0.5,
            key=f"dialog_weight_{key_base}",
        )

    reps = st.number_input(
        "Reps",
        min_value=1,
        value=default_reps,
        step=1,
        key=f"dialog_reps_{key_base}",
    )

    if st.button("Save set", use_container_width=True, key=f"dialog_save_{key_base}", type="primary"):
        try:
            save_set_for_exercise(
                user_id=user_id,
                active_workout=active_workout,
                exercise_name=exercise_name,
                weight=weight,
                reps=reps,
                load_mode=load_mode,
            )
            st.session_state.pop("inline_log_set_exercise", None)
            st.rerun()
        except Exception as e:
            st.error(f"Could not save set: {e}")


if hasattr(st, "dialog"):
    @st.dialog("Log Set")
    def show_log_set_dialog(user_id, active_workout, exercise_name):
        show_log_set_fields(user_id, active_workout, exercise_name)
else:
    def show_log_set_dialog(user_id, active_workout, exercise_name):
        st.session_state["inline_log_set_exercise"] = exercise_name


def show_preset_manager(user_id):
    presets = load_workout_presets(user_id)
    selected_preset = None
    selected_data = None

    render_section_card_start("Workout Preset")

    if presets:
        preset_names = ["No preset"] + [p["name"] for p in presets]
        selected_name = st.selectbox(
            "Choose preset",
            preset_names,
            help="Optional. Pick a saved template or start empty.",
        )

        if selected_name != "No preset":
            selected_preset = next(p for p in presets if p["name"] == selected_name)
            selected_data = normalize_preset_data(selected_preset)

            render_spacer("md")
            st.markdown(
                f"""
                <div class="dashboard-card">
                    <div class="card-label">{selected_data["workout_type"]}</div>
                    <p class="stat-value">{selected_preset["name"]}</p>
                    <p class="subtle-text">{len(selected_data["exercises"])} exercises</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            render_spacer("md")
            st.caption(format_exercise_preview(selected_data["exercises"]))

        with st.expander("Edit selected preset"):
            if selected_preset is None:
                st.caption("Select a preset above to edit it.")
            else:
                with st.form("edit_preset_form"):
                    edit_name = st.text_input("Preset name", value=selected_preset["name"])
                    edit_type = st.selectbox(
                        "Workout type",
                        WORKOUT_TYPES,
                        index=option_index(WORKOUT_TYPES, selected_data["workout_type"]),
                        key=f"edit_preset_type_{selected_preset['id']}",
                    )

                    edit_subtype = None
                    if edit_type == "Weight training":
                        current_subtype = selected_data.get("subtype") or "Mixed"
                        edit_subtype = st.selectbox(
                            "Training type",
                            TRAINING_SUBTYPES,
                            index=option_index(TRAINING_SUBTYPES, current_subtype),
                            key=f"edit_preset_subtype_{selected_preset['id']}",
                        )

                    edit_exercises = st.text_area(
                        "Exercises, one per line",
                        value=exercise_list_to_text(selected_data["exercises"]),
                        height=180,
                    )
                    save_edit = st.form_submit_button("Save preset changes", use_container_width=True)

                    if save_edit:
                        exercises = exercise_text_to_list(edit_exercises)
                        preset_data = build_preset_data(edit_type, edit_subtype, exercises)

                        if not edit_name.strip():
                            st.error("Add a preset name first.")
                        elif edit_type == "Weight training" and not exercises:
                            st.error("Add at least one exercise.")
                        else:
                            try:
                                update_workout_preset(
                                    user_id=user_id,
                                    preset_id=selected_preset["id"],
                                    name=edit_name.strip(),
                                    preset_data=preset_data,
                                )
                                st.success("Preset updated")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not update preset: {e}")
    else:
        st.info("No presets yet. Create your first workout template below.")

    with st.expander("Create new preset"):
        with st.form("create_preset_form"):
            preset_name = st.text_input("Preset name", value="Push Day")
            workout_type = st.selectbox("Workout type", WORKOUT_TYPES, key="create_preset_type")

            subtype = None
            if workout_type == "Weight training":
                subtype = st.selectbox("Training type", TRAINING_SUBTYPES, key="create_preset_subtype")

            starter_text = "Incline DB Press\nBench Press\nOverhead Press\nTricep Pushdown\nLateral Raise"
            exercise_text = st.text_area(
                "Exercises, one per line",
                value=starter_text,
                height=180,
                help="The order here is the order shown when you start the preset.",
            )
            create_preset = st.form_submit_button("Create preset", use_container_width=True)

            if create_preset:
                exercises = exercise_text_to_list(exercise_text)

                if not preset_name.strip():
                    st.error("Add a preset name first.")
                elif workout_type == "Weight training" and not exercises:
                    st.error("Add at least one exercise.")
                else:
                    preset_data = build_preset_data(workout_type, subtype, exercises)

                    try:
                        save_workout_preset(user_id, preset_name.strip(), preset_data)
                        st.success("Preset created")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not create preset: {e}")

    return selected_preset, selected_data


def show_start_workout(user_id):
    selected_preset, selected_data = show_preset_manager(user_id)

    render_spacer("section")
    render_section_card_start("Workout Setup")

    default_workout_type = selected_data["workout_type"] if selected_data else "Weight training"
    default_subtype = (selected_data or {}).get("subtype") or "Mixed"

    workout_type = st.selectbox(
        "Workout type",
        WORKOUT_TYPES,
        index=option_index(WORKOUT_TYPES, default_workout_type),
    )

    subtype = None
    if workout_type == "Weight training":
        subtype = st.selectbox(
            "Training type",
            TRAINING_SUBTYPES,
            index=option_index(TRAINING_SUBTYPES, default_subtype),
        )

    render_spacer("lg")
    render_section_card_start("Start Workout")
    if st.button("Start workout", use_container_width=True, type="primary"):
        started_at = datetime.now(timezone.utc)
        st.session_state.pop("workout_message", None)
        st.session_state.pop("cardio_distance_km", None)
        st.session_state.pop("cardio_duration_minutes", None)
        st.session_state.pop("cardio_estimated_calories", None)
        preset_exercises = selected_data.get("exercises", []) if selected_data else []
        preset_exercises = clean_exercise_list(preset_exercises)
        workout_name = selected_preset["name"] if selected_preset else None

        try:
            workout = create_workout(
                user_id=user_id,
                workout_type=workout_type,
                started_at=started_at,
                subtype=subtype,
                planned_exercises=preset_exercises,
                workout_name=workout_name,
            )
            if preset_exercises:
                update_workout_plan(user_id, workout["id"], preset_exercises)

            st.session_state["active_workout"] = {
                "id": workout["id"],
                "workout_type": workout_type,
                "subtype": subtype,
                "started_at": started_at.isoformat(),
                "planned_exercises": preset_exercises,
            }
            if selected_preset:
                st.session_state["active_workout"]["preset_name"] = selected_preset["name"]
            remember_workout_plan(workout["id"], preset_exercises)
            restore_active_workout(user_id)
            st.rerun()
        except Exception as e:
            st.error(f"Could not start workout. If tables are not created yet, run the SQL below. Error: {e}")


def show_weight_training(user_id, active_workout):
    workout_sets = load_workout_sets(user_id, active_workout["id"])
    saved_plan = workout_planned_exercises(active_workout)
    cached_plan = remembered_workout_plan(active_workout["id"])
    active_exercises = build_visible_exercises(saved_plan or cached_plan, workout_sets)
    remember_workout_plan(active_workout["id"], active_exercises)

    if saved_plan and active_exercises != saved_plan:
        active_workout["planned_exercises"] = active_exercises
        update_workout_plan(user_id, active_workout["id"], active_workout["planned_exercises"])

    show_workout_plan(user_id, active_workout, workout_sets)
    render_spacer("lg")
    show_add_exercise(user_id, active_workout)
    render_spacer("lg")

    st.markdown(
        '<div class="card-label" style="margin: 0 0 8px 0;">Save workout template</div>',
        unsafe_allow_html=True,
    )
    preset_name = st.text_input("Preset name", value=f"{active_workout.get('subtype') or 'Workout'} preset")

    if st.button("Save as preset", use_container_width=True, type="primary"):
        exercise_names = st.session_state.get("preset_exercises") or workout_set_exercises(workout_sets)
        preset_data = {
            "workout_type": active_workout["workout_type"],
            "subtype": active_workout.get("subtype"),
            "exercises": clean_exercise_list(exercise_names),
        }

        try:
            save_workout_preset(user_id, preset_name, preset_data)
            st.success("Preset saved")
        except Exception as e:
            st.error(f"Could not save preset: {e}")

    render_spacer("lg")


def show_workout_plan(user_id, active_workout, workout_sets):
    render_section_card_start("Workout Plan")
    active_exercises = remembered_workout_plan(active_workout["id"])

    if not active_exercises:
        st.caption("Add exercises as you train, or start from a preset.")
        return

    for index, exercise_name in enumerate(active_exercises, start=1):
        exercise_sets = sets_for_exercise(workout_sets, exercise_name)
        set_count = len(exercise_sets)
        last_label = last_set_label(exercise_sets)
        sets_label = set_summary_label(exercise_sets)
        key_base = widget_key(f"{index}_{exercise_name}")

        info_col, button_col = st.columns([5.2, 1.15])

        with info_col:
            st.markdown(
                f"""
                <div style="
                    background: rgba(255, 255, 255, 0.045);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 18px;
                    padding: 0.5rem 0.78rem;
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
                    margin-bottom: 8px;
                ">
                    <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
                        <div>
                            <p style="color: var(--shape-text); font-size: 1.05rem; font-weight: 900; line-height: 1.12; margin: 0;">
                                {escape(exercise_name)}
                            </p>
                        </div>
                        <div style="color: var(--shape-green); font-size: 0.88rem; font-weight: 900; white-space: nowrap;">
                            {set_count} sets
                        </div>
                    </div>
                    <p class="subtle-text" style="margin-top: 0.32rem; font-size: 0.86rem;">Last set: {escape(last_label)}</p>
                    <p class="subtle-text" style="margin-top: 0.08rem; font-size: 0.86rem;">{escape(sets_label)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with button_col:
            with st.container(key=f"log_set_action_{key_base}"):
                if st.button("Log Set", key=f"log_set_{key_base}", use_container_width=True, type="primary"):
                    show_log_set_dialog(user_id, active_workout, exercise_name)

            if exercise_sets:
                latest_set = sorted(
                    exercise_sets,
                    key=lambda row: (row.get("set_number") or 0, row.get("created_at") or ""),
                )[-1]
                remove_key = f"remove_last_{active_workout['id']}_{widget_key(exercise_name)}"

                with st.container(key=f"remove_last_action_{key_base}"):
                    if st.button(
                        "x Remove Last",
                        key=remove_key,
                        use_container_width=True,
                        type="secondary",
                    ):
                        response = delete_workout_set(user_id, latest_set["id"])
                        deleted_rows = response.data or []

                        if deleted_rows:
                            st.rerun()

                        st.error(
                            "Could not remove the latest set. Supabase returned no deleted row. "
                            "Check the workout_sets delete RLS policy."
                        )

        if st.session_state.get("inline_log_set_exercise") == exercise_name:
            show_log_set_fields(user_id, active_workout, exercise_name)


def show_add_exercise(user_id, active_workout):
    workout_id = active_workout["id"]
    st.markdown(
        '<div class="card-label" style="margin: 0 0 8px 0;">Add exercise</div>',
        unsafe_allow_html=True,
    )
    active_exercises = remembered_workout_plan(workout_id)
    exercise_options = [
        exercise_name for exercise_name in EXERCISES
        if exercise_name not in active_exercises
    ]

    choice = st.selectbox(
        "Exercise",
        exercise_options + ["Custom exercise"],
        help="Open the menu and type to search.",
        key=f"add_exercise_choice_{workout_id}",
    )

    custom_name = ""
    if choice == "Custom exercise":
        custom_name = st.text_input("Exercise name", key=f"custom_exercise_{workout_id}")

    if st.button("Add exercise", use_container_width=True, key=f"add_exercise_button_{workout_id}", type="primary"):
        exercise_name = custom_name.strip() if choice == "Custom exercise" else choice

        if not exercise_name:
            st.error("Choose or enter an exercise first.")
        elif exercise_name in active_exercises:
            st.info("That exercise is already in this workout.")
        else:
            active_exercises.append(exercise_name)
            active_exercises = clean_exercise_list(active_exercises)
            remember_workout_plan(workout_id, active_exercises)
            active_workout["planned_exercises"] = active_exercises
            update_workout_plan(user_id, workout_id, active_exercises)
            st.session_state["workout_message"] = f"{exercise_name} added"
            st.rerun()

    render_spacer("md")

    with st.expander("Edit exercise order"):
        exercise_text = st.text_area(
            "Exercises, one per line",
            value=exercise_list_to_text(active_exercises),
            height=160,
            key=f"active_exercise_editor_{workout_id}_{len(active_exercises)}",
        )

        if st.button("Update exercise list", use_container_width=True, type="primary"):
            active_exercises = exercise_text_to_list(exercise_text)
            remember_workout_plan(workout_id, active_exercises)
            active_workout["planned_exercises"] = active_exercises
            update_workout_plan(user_id, workout_id, active_exercises)
            st.session_state["workout_message"] = "Exercise list updated"
            st.rerun()


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


def show_workout_complete_contents(summary):
    calories = summary.get("estimated_calories")
    time_range = workout_time_range(summary)
    calories_line = ""
    if calories is not None:
        calories_line = f'<p class="subtle-text">Estimated calories: <strong>{calories} kcal</strong></p>'

    st.markdown(
        f"""
        <div class="dashboard-card weight-card">
            <div class="card-label">Workout complete</div>
            <p class="hero-greeting">Workout complete 🎉</p>
            <p class="hero-subtitle">{escape(summary["display_name"])}</p>
            <p class="subtle-text" style="margin-top: 0.2rem;">{escape(time_range)}</p>
            <p class="subtle-text" style="margin-top: 0.15rem; opacity: 0.82;">{escape(workout_detail(summary))}</p>
            <div class="targets-grid">
                <div class="target-cell">
                    <div class="target-label">Duration</div>
                    <p class="target-value">{summary["duration_minutes"]} min</p>
                </div>
                <div class="target-cell">
                    <div class="target-label">Sets</div>
                    <p class="target-value">{summary["total_sets"]}</p>
                </div>
                <div class="target-cell">
                    <div class="target-label">Exercises</div>
                    <p class="target-value">{summary["exercise_count"]}</p>
                </div>
            </div>
            <p class="hero-change">{summary["pr_count"]} PRs<span>this workout</span></p>
            {calories_line}
        </div>
        """,
        unsafe_allow_html=True,
    )

    for exercise in summary.get("exercise_summaries", []):
        set_labels = [
            compact_set_label(row)
            for row in exercise.get("sets", [])
        ]
        set_summary = " • ".join(set_labels) if set_labels else "No sets"
        pr_line = ""
        if exercise.get("is_pr"):
            pr_line = '<p class="subtle-text" style="margin-top: 0.1rem; color: var(--shape-green); font-weight: 900;">New PR</p>'

        st.markdown(
            f"""
            <div style="
                background: rgba(255, 255, 255, 0.045);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 18px;
                padding: 0.75rem 0.9rem;
                margin-top: 0.65rem;
            ">
                <div style="display: flex; justify-content: space-between; gap: 1rem; align-items: center;">
                    <strong>{escape(exercise["exercise_name"])}</strong>
                    <span style="color: var(--shape-green); font-weight: 900;">{exercise["set_count"]} sets</span>
                </div>
                <p class="subtle-text" style="margin-top: 0.35rem;">{escape(set_summary)}</p>
                {pr_line}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("Done", use_container_width=True, key="close_workout_complete", type="primary"):
        st.session_state.pop("finished_workout_summary", None)
        st.rerun()


if hasattr(st, "dialog"):
    @st.dialog("Workout complete")
    def show_workout_complete_dialog():
        show_workout_complete_contents(st.session_state["finished_workout_summary"])
else:
    def show_workout_complete_dialog():
        show_workout_complete_contents(st.session_state["finished_workout_summary"])


def show_finish_workout(user_id, active_workout):
    if st.button("Finish Workout", use_container_width=True, type="primary"):
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
            summary = summarize_workout(user_id, workout)
            summary["display_name"] = workout_title(active_workout)
            clear_active_workout()
            st.session_state["finished_workout_summary"] = summary
            st.rerun()
        except Exception as e:
            st.error(f"Could not finish workout: {e}")


user_id, email = require_login()
show_logout_button(email)

profile = load_profile(user_id)
render_app_header(get_public_display_name(profile, email), profile.get("avatar_url") if profile else None)
render_page_heading("Log Workout", "Log strength sessions and simple cardio.")

active_workout = restore_active_workout(user_id)

if st.session_state.get("workout_message"):
    st.success(st.session_state.pop("workout_message"))

if st.session_state.get("finished_workout_summary"):
    show_workout_complete_dialog()

if active_workout is None:
    show_start_workout(user_id)
else:
    started_at = datetime.fromisoformat(active_workout["started_at"])
    active_title = workout_title(active_workout)
    active_detail = active_workout["workout_type"]
    if active_workout.get("subtype"):
        active_detail = f"{active_detail} · {active_workout['subtype']}"

    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="card-label">Active workout</div>
            <p class="stat-value">{active_title}</p>
            <p class="subtle-text">{active_detail} · Started {started_at.strftime('%H:%M')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_spacer("lg")

    if active_workout["workout_type"] == "Weight training":
        show_weight_training(user_id, active_workout)
    else:
        show_cardio(active_workout, profile)

    render_spacer("lg")
    show_finish_workout(user_id, active_workout)
