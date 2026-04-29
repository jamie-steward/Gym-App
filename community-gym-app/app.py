import streamlit as st
import pandas as pd
from datetime import date
import os
import altair as alt

st.set_page_config(page_title="Community Gym App", layout="wide")

# -----------------------------
# FILE PATHS
# -----------------------------
users_path = "data/users.csv"
logs_path = "data/logs.csv"
profiles_path = "data/profiles.csv"

# -----------------------------
# SIMPLE TARGET CALCULATOR
# -----------------------------
def calculate_targets(goal, height_cm, weight_kg, age, activity_level):
    activity_multipliers = {
        "Sedentary": 1.2,
        "Light": 1.375,
        "Moderate": 1.55,
        "Very active": 1.725,
    }

    # Simple male BMR formula for now
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

    else:  # Recomp
        calorie_low = maintenance - 150
        calorie_high = maintenance + 150
        protein_target = weight_kg * 2.0

    return round(calorie_low), round(calorie_high), round(protein_target)


# -----------------------------
# LOAD / CREATE DATA FILES
# -----------------------------
if os.path.exists(users_path):
    users = pd.read_csv(users_path)
else:
    users = pd.DataFrame(columns=["user_id", "name"])
    users.to_csv(users_path, index=False)

if os.path.exists(logs_path):
    logs = pd.read_csv(logs_path)
else:
    logs = pd.DataFrame(columns=["user_id", "date", "goal", "weight", "calories", "protein"])
    logs.to_csv(logs_path, index=False)

if os.path.exists(profiles_path):
    profiles = pd.read_csv(profiles_path)
else:
    profiles = pd.DataFrame(columns=[
        "user_id", "name", "goal", "age", "height_cm", "weight_kg",
        "activity_level", "calorie_low", "calorie_high", "protein_target"
    ])
    profiles.to_csv(profiles_path, index=False)

if not logs.empty:
    logs["date"] = pd.to_datetime(logs["date"]).dt.date

# -----------------------------
# HEADER
# -----------------------------
st.title("Community Gym App")
st.caption("Create a profile, track your weight/calories/protein, and get simple coaching feedback.")
st.divider()

# -----------------------------
# CREATE ACCOUNT
# -----------------------------
with st.expander("Create new account"):
    new_name = st.text_input("Name")
    new_goal = st.selectbox("Goal", ["Cut", "Lean bulk", "Recomp"], key="new_goal")
    new_age = st.number_input("Age", min_value=10, max_value=100, value=32, key="new_age")
    new_height = st.number_input("Height (cm)", min_value=100, max_value=230, value=183, key="new_height")
    new_weight = st.number_input("Current weight (kg)", min_value=30.0, max_value=200.0, value=72.0, step=0.1, key="new_weight")
    new_activity = st.selectbox("Activity level", ["Sedentary", "Light", "Moderate", "Very active"], index=2, key="new_activity")

    if st.button("Create account"):
        if new_name.strip() == "":
            st.error("Enter a name first.")
        else:
            if users.empty:
                new_user_id = 1
            else:
                new_user_id = int(users["user_id"].max()) + 1

            calorie_low, calorie_high, protein_target = calculate_targets(
                new_goal, new_height, new_weight, new_age, new_activity
            )

            new_user = pd.DataFrame([{
                "user_id": new_user_id,
                "name": new_name
            }])

            new_profile = pd.DataFrame([{
                "user_id": new_user_id,
                "name": new_name,
                "goal": new_goal,
                "age": new_age,
                "height_cm": new_height,
                "weight_kg": new_weight,
                "activity_level": new_activity,
                "calorie_low": calorie_low,
                "calorie_high": calorie_high,
                "protein_target": protein_target
            }])

            users = pd.concat([users, new_user], ignore_index=True)
            profiles = pd.concat([profiles, new_profile], ignore_index=True)

            users.to_csv(users_path, index=False)
            profiles.to_csv(profiles_path, index=False)

            st.success("Account created ✅")
            st.rerun()

# -----------------------------
# PICK USER
# -----------------------------
if users.empty:
    st.warning("Create an account first.")
    st.stop()

user = st.selectbox("Sign in as", users["name"])

selected_user = users[users["name"] == user].iloc[0]
user_id = int(selected_user["user_id"])

st.write(f"Logged in as: **{user}**")

# -----------------------------
# PROFILE CHECK
# -----------------------------
user_profile = profiles[profiles["user_id"] == user_id]

if user_profile.empty:
    st.warning("This user does not have a profile yet. Create one below.")

    profile_goal = st.selectbox("Goal", ["Cut", "Lean bulk", "Recomp"])
    profile_age = st.number_input("Age", min_value=10, max_value=100, value=32)
    profile_height = st.number_input("Height (cm)", min_value=100, max_value=230, value=183)
    profile_weight = st.number_input("Current weight (kg)", min_value=30.0, max_value=200.0, value=72.0, step=0.1)
    profile_activity = st.selectbox("Activity level", ["Sedentary", "Light", "Moderate", "Very active"], index=2)

    if st.button("Save profile"):
        calorie_low, calorie_high, protein_target = calculate_targets(
            profile_goal, profile_height, profile_weight, profile_age, profile_activity
        )

        new_profile = pd.DataFrame([{
            "user_id": user_id,
            "name": user,
            "goal": profile_goal,
            "age": profile_age,
            "height_cm": profile_height,
            "weight_kg": profile_weight,
            "activity_level": profile_activity,
            "calorie_low": calorie_low,
            "calorie_high": calorie_high,
            "protein_target": protein_target
        }])

        profiles = pd.concat([profiles, new_profile], ignore_index=True)
        profiles.to_csv(profiles_path, index=False)

        st.success("Profile saved ✅")
        st.rerun()

    st.stop()

profile = user_profile.iloc[0]

CALORIE_LOW = int(profile["calorie_low"])
CALORIE_HIGH = int(profile["calorie_high"])
PROTEIN_TARGET = int(profile["protein_target"])

# -----------------------------
# EDIT PROFILE
# -----------------------------
with st.expander("Edit profile / recalculate targets"):
    edit_goal = st.selectbox(
        "Goal",
        ["Cut", "Lean bulk", "Recomp"],
        index=["Cut", "Lean bulk", "Recomp"].index(profile["goal"])
    )

    edit_age = st.number_input("Age", min_value=10, max_value=100, value=int(profile["age"]))
    edit_height = st.number_input("Height (cm)", min_value=100, max_value=230, value=int(profile["height_cm"]))
    edit_weight = st.number_input("Current weight (kg)", min_value=30.0, max_value=200.0, value=float(profile["weight_kg"]), step=0.1)
    edit_activity = st.selectbox(
        "Activity level",
        ["Sedentary", "Light", "Moderate", "Very active"],
        index=["Sedentary", "Light", "Moderate", "Very active"].index(profile["activity_level"])
    )

    new_low, new_high, new_protein = calculate_targets(
        edit_goal, edit_height, edit_weight, edit_age, edit_activity
    )

    st.write(f"Calculated calorie range: **{new_low}–{new_high} kcal**")
    st.write(f"Calculated protein target: **{new_protein}g**")

    if st.button("Update profile"):
        profiles.loc[profiles["user_id"] == user_id, "goal"] = edit_goal
        profiles.loc[profiles["user_id"] == user_id, "age"] = edit_age
        profiles.loc[profiles["user_id"] == user_id, "height_cm"] = edit_height
        profiles.loc[profiles["user_id"] == user_id, "weight_kg"] = edit_weight
        profiles.loc[profiles["user_id"] == user_id, "activity_level"] = edit_activity
        profiles.loc[profiles["user_id"] == user_id, "calorie_low"] = new_low
        profiles.loc[profiles["user_id"] == user_id, "calorie_high"] = new_high
        profiles.loc[profiles["user_id"] == user_id, "protein_target"] = new_protein

        profiles.to_csv(profiles_path, index=False)
        st.success("Profile updated ✅")
        st.rerun()

# -----------------------------
# TODAY STATUS
# -----------------------------
st.subheader("Today's status")

today = date.today()

today_entry = logs[
    (logs["user_id"] == user_id) &
    (logs["date"] == today)
]

if not today_entry.empty:
    row = today_entry.iloc[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Weight", f"{row['weight']} kg")

    cal_value = int(row["calories"])

    if CALORIE_LOW <= cal_value <= CALORIE_HIGH:
        cal_label = f"{cal_value} ✅"
    elif cal_value < CALORIE_LOW:
        cal_label = f"{cal_value} ({CALORIE_LOW - cal_value} under)"
    else:
        cal_label = f"{cal_value} ({cal_value - CALORIE_HIGH} over)"

    col2.metric("Calories", cal_label)

    protein_value = int(row["protein"])

    if protein_value >= PROTEIN_TARGET:
        protein_label = f"{protein_value} g ✅"
    else:
        protein_label = f"{protein_value} g ({PROTEIN_TARGET - protein_value}g under)"

    col3.metric("Protein", protein_label)
    col4.metric("Goal", row[profile["goal"]])

else:
    st.info("No entry logged for today yet")

st.divider()

st.info(f"Your current targets: **{CALORIE_LOW}–{CALORIE_HIGH} kcal** and **{PROTEIN_TARGET}g protein**")

# -----------------------------
# DATE INPUT
# -----------------------------
entry_date = st.date_input("Date", date.today())

user_previous_logs = logs[
    (logs["user_id"] == user_id) &
    (logs["date"] <= entry_date)
].sort_values("date")

user_previous_weight_logs = user_previous_logs.dropna(subset=["weight"])

existing_today = user_previous_logs[user_previous_logs["date"] == entry_date]

if not existing_today.empty:
    default_row = existing_today.iloc[-1]
    prefill_message = "Existing entry found for this date — fields pre-filled ✅"

elif not user_previous_weight_logs.empty:
    default_row = user_previous_weight_logs.iloc[-1]
    prefill_message = "No entry for this date yet — using your most recent previous entry as a starting point ✅"

else:
    default_row = None
    prefill_message = ""

if default_row is not None:
    default_goal = default_row["goal"] if default_row["goal"] in ["Cut", "Lean bulk", "Recomp"] else profile["goal"]
    default_weight = float(default_row["weight"])
    default_calories = int(default_row["calories"])
    default_protein = int(default_row["protein"])
else:
    default_goal = profile["goal"]
    default_weight = float(profile["weight_kg"])
    default_calories = CALORIE_LOW
    default_protein = PROTEIN_TARGET

user_logs = logs[logs["user_id"] == user_id].copy()

# -----------------------------
# SPLIT SCREEN
# -----------------------------
left, right = st.columns([1, 1.4])

with left:
    st.subheader("Log data")

    if prefill_message:
        st.info(prefill_message)



    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1, value=default_weight)
    calories = st.number_input("Calories", min_value=0, step=50, value=default_calories)
    protein = st.number_input("Protein (g)", min_value=0, step=5, value=default_protein)

    if st.button("Save entry", use_container_width=True):
        existing_entry = (logs["user_id"] == user_id) & (logs["date"] == entry_date)

        if existing_entry.any():
            logs.loc[existing_entry, "goal"] = profile["goal"]
            logs.loc[existing_entry, "weight"] = weight
            logs.loc[existing_entry, "calories"] = calories
            logs.loc[existing_entry, "protein"] = protein
        else:
            new_log = pd.DataFrame([{
                "user_id": user_id,
                "date": entry_date,
                "goal": profile["goal"],
                "weight": weight,
                "calories": calories,
                "protein": protein
            }])

            logs = pd.concat([logs, new_log], ignore_index=True)

        logs.to_csv(logs_path, index=False)
        st.rerun()

with right:
    st.subheader("Weight progress")

    if not user_logs.empty:
        user_logs["date"] = pd.to_datetime(user_logs["date"])
        user_logs = user_logs.sort_values("date")

# Create daily date range and fill gaps
        daily_weights = (
            user_logs[["date", "weight"]]
            .dropna()
            .set_index("date")
            .asfreq("D")
        )

# Straight-line fill missing weights between real weigh-ins
        daily_weights["weight_interpolated"] = daily_weights["weight"].interpolate(method="time")

        # Add goal to daily data
        goal_map = user_logs.set_index("date")["goal"]

        daily_weights["goal"] = goal_map
        daily_weights["goal"] = daily_weights["goal"].ffill()

        # Smooth the interpolated trend
        daily_weights["weight_14_day_avg"] = (
            daily_weights["weight_interpolated"]
            .rolling(window=14, min_periods=3)
            .mean()
        )

        daily_weights = daily_weights.reset_index()

        min_weight = user_logs["weight"].min()
        max_weight = user_logs["weight"].max()

        padding = 0.5

        raw_points = alt.Chart(user_logs).mark_circle(size=20, opacity=0.2).encode(
            x="date:T",
            y=alt.Y(
                "weight:Q",
                scale=alt.Scale(domain=[min_weight - padding, max_weight + padding])
            ),
            tooltip=["date:T", "weight:Q"]
        )

        trend_line = alt.Chart(daily_weights).mark_line(strokeWidth=5).encode(
            x="date:T",
            y="weight_14_day_avg:Q",
            color=alt.Color(
                "goal:N",
                scale=alt.Scale(
                    domain=["Cut", "Lean bulk", "Recomp"],
                    range=["#4dabf7", "#51cf66", "#ffd43b"]
                )
            ),
            tooltip=["date:T", "weight_14_day_avg:Q", "goal"]
        )

        chart = raw_points + trend_line

        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("No data yet")

    st.divider()

    st.subheader("Coach feedback")

if len(user_logs) < 14:
    st.info("Log at least 14 days of data to get proper adaptive coaching.")
else:
    user_logs["date"] = pd.to_datetime(user_logs["date"])
    user_logs = user_logs.sort_values("date")

    latest_7 = user_logs.tail(7).copy()
    previous_7 = user_logs.iloc[-14:-7].copy()

    latest_7["calories"] = pd.to_numeric(latest_7["calories"], errors="coerce")
    previous_7["calories"] = pd.to_numeric(previous_7["calories"], errors="coerce")

    latest_avg_weight = latest_7["weight"].mean()
    previous_avg_weight = previous_7["weight"].mean()

    weight_change = latest_avg_weight - previous_avg_weight

    avg_calories = latest_7["calories"].mean()

    # Estimate real maintenance from weight trend
    # 1kg bodyweight change roughly = 7700 calories
    daily_energy_balance = (weight_change * 7700) / 7
    estimated_maintenance = avg_calories - daily_energy_balance

    latest_goal = profile["goal"]

    col1, col2, col3 = st.columns(3)

    col1.metric("Latest 7-day avg", f"{latest_avg_weight:.2f} kg")
    col2.metric("Trend", f"{weight_change:+.2f} kg")
    col3.metric("Estimated maintenance", f"{estimated_maintenance:.0f} kcal")

    st.write(f"Average calories this week: **{avg_calories:.0f} kcal/day**")

    if latest_goal == "Cut":
        suggested_low = estimated_maintenance - 600
        suggested_high = estimated_maintenance - 400

        st.write(f"Adaptive cut range: **{suggested_low:.0f}–{suggested_high:.0f} kcal**")

        if st.button("Update my profile to this calorie range"):
            profiles.loc[profiles["user_id"] == user_id, "calorie_low"] = round(suggested_low)
            profiles.loc[profiles["user_id"] == user_id, "calorie_high"] = round(suggested_high)

            profiles.to_csv(profiles_path, index=False)

            st.success("Profile calorie range updated ✅")
            st.rerun()

        if weight_change < -0.25:
            st.success("Cut is moving nicely. Keep your current range.")
        elif -0.25 <= weight_change <= 0:
            st.warning("Weight is barely moving. Your app suggests lowering your range slightly.")
        else:
            st.error("Weight is rising while cutting. Your range is probably too high.")

    elif latest_goal == "Lean bulk":
        suggested_low = estimated_maintenance + 150
        suggested_high = estimated_maintenance + 300

        st.write(f"Adaptive lean bulk range: **{suggested_low:.0f}–{suggested_high:.0f} kcal**")

        if st.button("Update my profile to this calorie range"):
            profiles.loc[profiles["user_id"] == user_id, "calorie_low"] = round(suggested_low)
            profiles.loc[profiles["user_id"] == user_id, "calorie_high"] = round(suggested_high)

            profiles.to_csv(profiles_path, index=False)

            st.success("Profile calorie range updated ✅")
            st.rerun()

        if 0.15 <= weight_change <= 0.35:
            st.success("Lean bulk rate looks good. Keep your current range.")
        elif weight_change < 0.15:
            st.warning("You are gaining too slowly. Your app suggests increasing calories slightly.")
        else:
            st.error("You may be gaining too quickly. Your app suggests reducing calories slightly.")

    elif latest_goal == "Recomp":
        suggested_low = estimated_maintenance - 150
        suggested_high = estimated_maintenance + 150

        st.write(f"Adaptive recomp range: **{suggested_low:.0f}–{suggested_high:.0f} kcal**")

        if st.button("Update my profile to this calorie range"):
            profiles.loc[profiles["user_id"] == user_id, "calorie_low"] = round(suggested_low)
            profiles.loc[profiles["user_id"] == user_id, "calorie_high"] = round(suggested_high)

            profiles.to_csv(profiles_path, index=False)

            st.success("Profile calorie range updated ✅")
            st.rerun()

        if -0.15 <= weight_change <= 0.15:
            st.success("Weight is stable — ideal for recomp.")
        elif weight_change < -0.15:
            st.warning("You may be drifting into a cut.")
        else:
            st.warning("You may be drifting into a bulk.")

    st.divider()

    st.subheader("Weekly protein consistency")

    if len(user_logs) >= 7:
        last_7 = user_logs.tail(7).copy()
        last_7["protein"] = pd.to_numeric(last_7["protein"], errors="coerce")

        days_hit = (last_7["protein"] >= PROTEIN_TARGET).sum()
        consistency = (days_hit / 7) * 100

        col1, col2 = st.columns(2)

        col1.metric("Protein target hit", f"{days_hit}/7 days")
        col2.metric("Consistency", f"{consistency:.0f}%")

        if consistency >= 85:
            st.success("Excellent consistency — this is elite level adherence.")
        elif consistency >= 60:
            st.warning("Decent, but room for improvement. Aim for 6/7 days.")
        else:
            st.error("Protein consistency is low — this will limit progress.")
    else:
        st.info("Log at least 7 days to see protein consistency.")

st.divider()

with st.expander("See raw data"):
    st.write(user_logs)