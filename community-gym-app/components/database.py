import pandas as pd
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    return create_client(supabase_url, supabase_key)


supabase = get_supabase_client()


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
        .eq("user_id", user_id)
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


def get_previous_best_1rm(user_id, exercise_name, current_workout_id=None):
    query = (
        supabase.table("workout_sets")
        .select("estimated_1rm")
        .eq("user_id", str(user_id))
        .eq("exercise_name", exercise_name)
    )

    if current_workout_id is not None:
        query = query.neq("workout_id", current_workout_id)

    response = query.order("estimated_1rm", desc=True).limit(1).execute()

    if not response.data:
        return None

    return float(response.data[0]["estimated_1rm"])


def save_workout_set(user_id, workout_id, exercise_name, set_number, weight, reps):
    estimated_1rm = float(weight) * (1 + (int(reps) / 30))
    previous_best = get_previous_best_1rm(user_id, exercise_name, workout_id)

    record = {
        "user_id": str(user_id),
        "workout_id": workout_id,
        "exercise_name": exercise_name,
        "set_number": int(set_number),
        "weight": float(weight),
        "reps": int(reps),
        "estimated_1rm": round(estimated_1rm, 2),
    }

    response = supabase.table("workout_sets").insert(record).execute()
    is_pr = previous_best is None or estimated_1rm > previous_best

    return response.data[0], is_pr


def delete_workout_set(user_id, set_id):
    supabase.table("workout_sets").delete().eq("id", set_id).eq("user_id", str(user_id)).execute()


def save_workout_preset(user_id, name, preset_data):
    record = {
        "user_id": str(user_id),
        "name": name,
        "preset_data": preset_data,
    }

    response = supabase.table("workout_presets").insert(record).execute()
    return response.data[0]
