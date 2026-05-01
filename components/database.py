import pandas as pd
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    return create_client(supabase_url, supabase_key)


supabase = get_supabase_client()


AVATAR_BUCKET = "avatars"


def calculate_targets(goal, height_cm, weight_kg, age, activity_level):
    activity_multipliers = {
        "Sedentary": 1.2,
        "Light": 1.375,
        "Moderate": 1.55,
        "Very active": 1.725,
    }

    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    maintenance = bmr * activity_multipliers[activity_level]

    if goal == "Cut":
        calorie_low = maintenance - 600
        calorie_high = maintenance - 400
        protein_target = weight_kg * 2.0
    elif goal == "Lean bulk":
        calorie_low = maintenance + 150
        calorie_high = maintenance + 300
        protein_target = weight_kg * 1.8
    else:
        calorie_low = maintenance - 150
        calorie_high = maintenance + 150
        protein_target = weight_kg * 2.0

    return round(calorie_low), round(calorie_high), round(protein_target)


def load_profile(user_id):
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]

def load_workout_presets(user_id):
    response = (
        supabase.table("workout_presets")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
    )

    return response.data if response.data else []


def create_profile(user_id, email, name, goal, age, height_cm, weight_kg, activity_level):
    calorie_low, calorie_high, protein_target = calculate_targets(
        goal, height_cm, weight_kg, age, activity_level
    )

    profile = {
        "user_id": str(user_id),
        "email": email,
        "name": name,
        "display_name": name,
        "username": None,
        "avatar_url": None,
        "goal": goal,
        "age": int(age),
        "height_cm": int(height_cm),
        "weight_kg": float(weight_kg),
        "activity_level": activity_level,
        "calorie_low": int(calorie_low),
        "calorie_high": int(calorie_high),
        "protein_target": int(protein_target),
    }

    supabase.table("profiles").insert(profile).execute()


def normalize_username(username):
    return str(username or "").strip().lower()


def is_username_available(user_id, username):
    username = normalize_username(username)
    response = (
        supabase.table("profiles")
        .select("user_id")
        .eq("username", username)
        .neq("user_id", str(user_id))
        .limit(1)
        .execute()
    )

    return not response.data


def update_public_profile(user_id, username, display_name, avatar_url=None):
    record = {
        "username": normalize_username(username),
        "display_name": str(display_name or "").strip() or None,
    }

    if avatar_url:
        record["avatar_url"] = avatar_url

    response = (
        supabase.table("profiles")
        .update(record)
        .eq("user_id", str(user_id))
        .execute()
    )

    return response.data[0] if response.data else None


def upload_avatar(user_id, uploaded_file):
    file_name = uploaded_file.name or "avatar.png"
    extension = file_name.split(".")[-1].lower() if "." in file_name else "png"
    path = f"{user_id}/avatar.{extension}"
    content_type = uploaded_file.type or "image/png"

    supabase.storage.from_(AVATAR_BUCKET).upload(
        path,
        uploaded_file.getvalue(),
        file_options={
            "content-type": content_type,
            "upsert": "true",
        },
    )

    return supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)


def load_public_profiles(current_user_id):
    response = (
        supabase.table("profiles")
        .select("user_id,name,goal,username,display_name,avatar_url")
        .neq("user_id", str(current_user_id))
        .order("display_name")
        .execute()
    )

    return response.data or []


def load_following_ids(user_id):
    response = (
        supabase.table("follows")
        .select("following_id")
        .eq("follower_id", str(user_id))
        .execute()
    )

    return [row["following_id"] for row in (response.data or [])]


def load_following_profiles(user_id):
    following_ids = load_following_ids(user_id)

    if not following_ids:
        return []

    response = (
        supabase.table("profiles")
        .select("user_id,name,goal,username,display_name,avatar_url")
        .in_("user_id", following_ids)
        .execute()
    )

    return response.data or []


def follow_user(user_id, following_id):
    record = {
        "follower_id": str(user_id),
        "following_id": str(following_id),
    }

    response = (
        supabase.table("follows")
        .upsert(record, on_conflict="follower_id,following_id")
        .execute()
    )

    return response.data[0] if response.data else None


def unfollow_user(user_id, following_id):
    response = (
        supabase.table("follows")
        .delete()
        .eq("follower_id", str(user_id))
        .eq("following_id", str(following_id))
        .execute()
    )

    return response.data or []


def update_profile_targets(user_id, calorie_low, calorie_high):
    supabase.table("profiles").update({
        "calorie_low": int(round(calorie_low)),
        "calorie_high": int(round(calorie_high)),
    }).eq("user_id", str(user_id)).execute()


def update_full_profile(
    user_id,
    goal,
    age,
    height_cm,
    weight_kg,
    activity_level,
    calorie_low,
    calorie_high,
    protein_target,
):
    supabase.table("profiles").update({
        "goal": goal,
        "age": int(age),
        "height_cm": int(height_cm),
        "weight_kg": float(weight_kg),
        "activity_level": activity_level,
        "calorie_low": int(calorie_low),
        "calorie_high": int(calorie_high),
        "protein_target": int(protein_target),
    }).eq("user_id", str(user_id)).execute()


def load_logs(user_id):
    response = (
        supabase.table("logs")
        .select("*")
        .eq("user_id", str(user_id))
        .execute()
    )

    data = response.data

    if not data:
        return pd.DataFrame(columns=[
            "id", "user_id", "date", "goal", "weight", "calories", "protein", "created_at"
        ])

    logs_df = pd.DataFrame(data)
    logs_df["date"] = pd.to_datetime(logs_df["date"], errors="coerce").dt.date
    logs_df["user_id"] = logs_df["user_id"].astype(str)
    logs_df["weight"] = pd.to_numeric(logs_df["weight"], errors="coerce")
    logs_df["calories"] = pd.to_numeric(logs_df["calories"], errors="coerce")
    logs_df["protein"] = pd.to_numeric(logs_df["protein"], errors="coerce")

    return logs_df


def save_log_entry(user_id, entry_date, goal, weight):
    record = {
        "user_id": str(user_id),
        "date": entry_date.isoformat(),
        "goal": goal,
        "weight": float(weight),
        "calories": None,
        "protein": None,
    }

    supabase.table("logs").upsert(
        record,
        on_conflict="user_id,date",
    ).execute()


def create_workout(user_id, workout_type, started_at, subtype=None):
    record = {
        "user_id": str(user_id),
        "workout_type": workout_type,
        "subtype": subtype,
        "started_at": started_at.isoformat(),
    }

    response = supabase.table("workouts").insert(record).execute()
    return response.data[0]


def load_active_workout(user_id):
    response = (
        supabase.table("workouts")
        .select("*")
        .eq("user_id", str(user_id))
        .filter("ended_at", "is", "null")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def finish_workout(
    user_id,
    workout_id,
    ended_at,
    duration_minutes,
    distance_km=None,
    cardio_duration_minutes=None,
    estimated_calories=None,
):
    record = {
        "ended_at": ended_at.isoformat(),
        "duration_minutes": int(round(duration_minutes)),
    }

    if distance_km is not None:
        record["distance_km"] = float(distance_km)

    if cardio_duration_minutes is not None:
        record["cardio_duration_minutes"] = int(round(cardio_duration_minutes))

    if estimated_calories is not None:
        record["estimated_calories"] = int(round(estimated_calories))

    response = (
        supabase.table("workouts")
        .update(record)
        .eq("id", workout_id)
        .eq("user_id", str(user_id))
        .execute()
    )

    return response.data[0] if response.data else None


def load_workout_sets(user_id, workout_id):
    response = (
        supabase.table("workout_sets")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("workout_id", workout_id)
        .order("created_at")
        .execute()
    )

    return response.data or []


def summarize_workout(user_id, workout):
    workout_sets = load_workout_sets(user_id, workout["id"])
    grouped_sets = {}

    for row in workout_sets:
        if row.get("exercise_name"):
            grouped_sets.setdefault(row["exercise_name"], []).append(row)

    best_current_by_exercise = {}
    best_bodyweight_by_exercise = {}

    for row in workout_sets:
        exercise_name = row["exercise_name"]
        load_mode = row.get("load_mode") or "external_weight"

        if load_mode in ["external_weight", "weighted_bodyweight"]:
            estimated_1rm = row.get("estimated_1rm")
            if estimated_1rm is None:
                continue

            current_best = best_current_by_exercise.get(exercise_name)
            if current_best is None or float(estimated_1rm) > current_best:
                best_current_by_exercise[exercise_name] = float(estimated_1rm)

        if load_mode == "bodyweight":
            reps = row.get("reps")
            if reps is None:
                continue

            current_best = best_bodyweight_by_exercise.get(exercise_name)
            if current_best is None or int(reps) > current_best:
                best_bodyweight_by_exercise[exercise_name] = int(reps)

    pr_count = 0
    pr_exercises = set()
    for exercise_name, estimated_1rm in best_current_by_exercise.items():
        previous_best = get_previous_best_1rm(
            user_id=user_id,
            exercise_name=exercise_name,
            current_workout_id=workout["id"],
        )

        if previous_best is None or estimated_1rm > previous_best:
            pr_count += 1
            pr_exercises.add(exercise_name)

    for exercise_name, reps in best_bodyweight_by_exercise.items():
        query = (
            supabase.table("workout_sets")
            .select("reps")
            .eq("user_id", str(user_id))
            .eq("exercise_name", exercise_name)
            .eq("load_mode", "bodyweight")
            .neq("workout_id", workout["id"])
            .order("reps", desc=True)
            .limit(1)
            .execute()
        )
        previous_best = int(query.data[0]["reps"]) if query.data else None

        if previous_best is None or reps > previous_best:
            pr_count += 1
            pr_exercises.add(exercise_name)

    exercise_summaries = []
    for exercise_name, rows in grouped_sets.items():
        ordered_rows = sorted(rows, key=lambda row: row["set_number"])
        exercise_summaries.append({
            "exercise_name": exercise_name,
            "set_count": len(ordered_rows),
            "sets": [
                {
                    "weight": row.get("weight"),
                    "reps": row.get("reps"),
                    "set_number": row.get("set_number"),
                    "load_mode": row.get("load_mode") or "external_weight",
                }
                for row in ordered_rows
            ],
            "is_pr": exercise_name in pr_exercises,
        })

    return {
        "workout": workout,
        "workout_type": workout.get("workout_type"),
        "subtype": workout.get("subtype"),
        "started_at": workout.get("started_at"),
        "ended_at": workout.get("ended_at"),
        "duration_minutes": workout.get("duration_minutes"),
        "estimated_calories": workout.get("estimated_calories"),
        "total_sets": len(workout_sets),
        "exercise_count": len(grouped_sets),
        "pr_count": pr_count,
        "exercise_summaries": exercise_summaries,
    }


def load_last_finished_workout(user_id):
    response = (
        supabase.table("workouts")
        .select("*")
        .eq("user_id", str(user_id))
        .filter("ended_at", "not.is", "null")
        .order("ended_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return summarize_workout(user_id, response.data[0])


def load_workout_summary(user_id, workout_id):
    response = (
        supabase.table("workouts")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("id", workout_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return summarize_workout(user_id, response.data[0])


def load_finished_workouts(user_id):
    response = (
        supabase.table("workouts")
        .select("*")
        .eq("user_id", str(user_id))
        .filter("ended_at", "not.is", "null")
        .order("ended_at", desc=True)
        .execute()
    )

    return [
        summarize_workout(user_id, workout)
        for workout in (response.data or [])
    ]


def get_previous_best_1rm(user_id, exercise_name, current_workout_id=None):
    query = (
        supabase.table("workout_sets")
        .select("estimated_1rm")
        .eq("user_id", str(user_id))
        .eq("exercise_name", exercise_name)
        .in_("load_mode", ["external_weight", "weighted_bodyweight"])
    )

    if current_workout_id is not None:
        query = query.neq("workout_id", current_workout_id)

    response = query.order("estimated_1rm", desc=True).limit(1).execute()

    if not response.data:
        return None

    return float(response.data[0]["estimated_1rm"])


def get_previous_bodyweight_best_reps(user_id, exercise_name, current_workout_id=None):
    query = (
        supabase.table("workout_sets")
        .select("reps")
        .eq("user_id", str(user_id))
        .eq("exercise_name", exercise_name)
        .eq("load_mode", "bodyweight")
    )

    if current_workout_id is not None:
        query = query.neq("workout_id", current_workout_id)

    response = query.order("reps", desc=True).limit(1).execute()

    if not response.data:
        return None

    return int(response.data[0]["reps"])


def save_workout_set(user_id, workout_id, exercise_name, set_number, weight, reps, load_mode="external_weight"):
    load_mode = load_mode or "external_weight"
    estimated_1rm = None
    previous_best = None
    previous_bodyweight_best = None

    if load_mode in ["external_weight", "weighted_bodyweight"]:
        estimated_1rm = float(weight) * (1 + (int(reps) / 30))
        previous_best = get_previous_best_1rm(user_id, exercise_name, workout_id)

    if load_mode == "bodyweight":
        previous_bodyweight_best = get_previous_bodyweight_best_reps(user_id, exercise_name, workout_id)

    record = {
        "user_id": str(user_id),
        "workout_id": workout_id,
        "exercise_name": exercise_name,
        "set_number": int(set_number),
        "weight": float(weight),
        "reps": int(reps),
        "estimated_1rm": round(estimated_1rm, 2) if estimated_1rm is not None else None,
        "load_mode": load_mode,
    }

    response = supabase.table("workout_sets").insert(record).execute()
    is_pr = False

    if load_mode in ["external_weight", "weighted_bodyweight"]:
        is_pr = previous_best is None or estimated_1rm > previous_best

    if load_mode == "bodyweight":
        is_pr = previous_bodyweight_best is None or int(reps) > previous_bodyweight_best

    return response.data[0], is_pr


def delete_workout_set(user_id, set_id):
    return (
        supabase.table("workout_sets")
        .delete()
        .eq("id", set_id)
        .eq("user_id", str(user_id))
        .execute()
    )


def save_workout_preset(user_id, name, preset_data):
    record = {
        "user_id": str(user_id),
        "name": name,
        "preset_data": preset_data,
    }

    response = supabase.table("workout_presets").insert(record).execute()
    return response.data[0]


def update_workout_preset(user_id, preset_id, name, preset_data):
    record = {
        "name": name,
        "preset_data": preset_data,
    }

    response = (
        supabase.table("workout_presets")
        .update(record)
        .eq("id", preset_id)
        .eq("user_id", str(user_id))
        .execute()
    )

    return response.data[0] if response.data else None
