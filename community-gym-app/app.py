import streamlit as st
import pandas as pd
from datetime import date
import altair as alt
from supabase import create_client

st.set_page_config(page_title="Community Gym App", layout="wide")

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]

supabase = create_client(supabase_url, supabase_key)

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


# -----------------------------
# AUTH HELPERS
# -----------------------------
def login_user(email, password):
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

    st.session_state["logged_in"] = True
    st.session_state["user_id"] = response.user.id
    st.session_state["email"] = response.user.email
    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token


def signup_user(email, password):
    response = supabase.auth.sign_up({
        "email": email,
        "password": password
    })

    st.session_state["logged_in"] = True
    st.session_state["user_id"] = response.user.id
    st.session_state["email"] = response.user.email
    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token


def logout_user():
    st.session_state["logged_in"] = False
    st.session_state.pop("user_id", None)
    st.session_state.pop("email", None)
    supabase.auth.sign_out()


# -----------------------------
# SUPABASE DATA HELPERS
# -----------------------------
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
        "protein_target": int(protein_target)
    }

    supabase.table("profiles").insert(profile).execute()


def update_profile_targets(user_id, calorie_low, calorie_high):
    supabase.table("profiles").update({
        "calorie_low": int(round(calorie_low)),
        "calorie_high": int(round(calorie_high))
    }).eq("user_id", str(user_id)).execute()


def update_full_profile(user_id, goal, age, height_cm, weight_kg, activity_level, calorie_low, calorie_high, protein_target):
    supabase.table("profiles").update({
        "goal": goal,
        "age": int(age),
        "height_cm": int(height_cm),
        "weight_kg": float(weight_kg),
        "activity_level": activity_level,
        "calorie_low": int(calorie_low),
        "calorie_high": int(calorie_high),
        "protein_target": int(protein_target)
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


def save_log_entry(user_id, entry_date, goal, weight, calories, protein):
    record = {
        "user_id": str(user_id),
        "date": entry_date.isoformat(),
        "goal": goal,
        "weight": float(weight),
        "calories": int(calories),
        "protein": int(protein)
    }

    supabase.table("logs").upsert(
        record,
        on_conflict="user_id,date"
    ).execute()


# -----------------------------
# HEADER
# -----------------------------
st.title("Community Gym App")
st.caption("Create a profile, track your weight/calories/protein, and get simple coaching feedback.")
st.divider()

# -----------------------------
# LOGIN / SIGNUP
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state.get("logged_in") and st.session_state.get("access_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"]
    )


if not st.session_state["logged_in"]:
    st.subheader("Log in or create account")

    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    with tab_login:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log in", use_container_width=True):
            try:
                login_user(login_email, login_password)
                st.success("Logged in ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")

        st.info("After creating your login, you'll complete your fitness profile.")

        if st.button("Create login", use_container_width=True):
            try:
                signup_user(signup_email, signup_password)
                st.success("Login created ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {e}")

    st.stop()

user_id = st.session_state["user_id"]
email = st.session_state["email"]

top_left, top_right = st.columns([3, 1])

with top_left:
    st.write(f"Logged in as: **{email}**")

with top_right:
    if st.button("Log out", use_container_width=True):
        logout_user()
        st.rerun()

# -----------------------------
# PROFILE SETUP
# -----------------------------
profile = load_profile(user_id)

if profile is None:
    st.subheader("Complete your profile")

    profile_name = st.text_input("Name")
    profile_goal = st.selectbox("Goal", ["Cut", "Lean bulk", "Recomp"])
    profile_age = st.number_input("Age", min_value=10, max_value=100, value=32)
    profile_height = st.number_input("Height (cm)", min_value=100, max_value=230, value=183)
    profile_weight = st.number_input("Current weight (kg)", min_value=30.0, max_value=200.0, value=72.0, step=0.1)
    profile_activity = st.selectbox("Activity level", ["Sedentary", "Light", "Moderate", "Very active"], index=2)

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
                activity_level=profile_activity
            )

            st.success("Profile saved ✅")
            st.rerun()

    st.stop()

user_name = profile["name"]

st.write(f"Profile: **{user_name}**")

CALORIE_LOW = int(profile["calorie_low"])
CALORIE_HIGH = int(profile["calorie_high"])
PROTEIN_TARGET = int(profile["protein_target"])

logs = load_logs(user_id)

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
        update_full_profile(
            user_id=user_id,
            goal=edit_goal,
            age=edit_age,
            height_cm=edit_height,
            weight_kg=edit_weight,
            activity_level=edit_activity,
            calorie_low=new_low,
            calorie_high=new_high,
            protein_target=new_protein
        )

        st.success("Profile updated ✅")
        st.rerun()

# -----------------------------
# TODAY STATUS
# -----------------------------
st.subheader("Today's status")

today = date.today()

today_entry = logs[
    (logs["user_id"] == str(user_id)) &
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
    col4.metric("Goal", profile["goal"])

else:
    st.info("No entry logged for today yet")

st.divider()

st.info(f"Your current targets: **{CALORIE_LOW}–{CALORIE_HIGH} kcal** and **{PROTEIN_TARGET}g protein**")

# -----------------------------
# DATE INPUT
# -----------------------------
entry_date = st.date_input("Date", date.today())

user_previous_logs = logs[
    (logs["user_id"] == str(user_id)) &
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
    default_weight = float(default_row["weight"])
    default_calories = int(default_row["calories"])
    default_protein = int(default_row["protein"])
else:
    default_weight = float(profile["weight_kg"])
    default_calories = CALORIE_LOW
    default_protein = PROTEIN_TARGET

user_logs = logs[logs["user_id"] == str(user_id)].copy()

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
        save_log_entry(
            user_id=user_id,
            entry_date=entry_date,
            goal=profile["goal"],
            weight=weight,
            calories=calories,
            protein=protein
        )

        st.success("Entry saved ✅")
        st.rerun()

with right:
    st.subheader("Weight progress")

    if not user_logs.empty:
        user_logs["date"] = pd.to_datetime(user_logs["date"])
        user_logs = user_logs.sort_values("date")

        daily_weights = (
            user_logs[["date", "weight"]]
            .dropna()
            .groupby("date", as_index=False)["weight"].mean()
            .set_index("date")
            .asfreq("D")
        )

        daily_weights["weight_interpolated"] = daily_weights["weight"].interpolate(method="time")

        goal_map = (
            user_logs[["date", "goal"]]
            .dropna()
            .drop_duplicates(subset=["date"], keep="last")
            .set_index("date")["goal"]
        )

        daily_weights["goal"] = goal_map
        daily_weights["goal"] = daily_weights["goal"].ffill()

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
                update_profile_targets(user_id, suggested_low, suggested_high)
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
                update_profile_targets(user_id, suggested_low, suggested_high)
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
                update_profile_targets(user_id, suggested_low, suggested_high)
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
