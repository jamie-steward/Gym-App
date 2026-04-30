import altair as alt
import pandas as pd
import streamlit as st


GOAL_COLORS = {
    "Cut": "#4dabf7",
    "Lean bulk": "#51cf66",
    "Recomp": "#ffd43b",
}


def _get_goal_status_label(goal, weekly_change):
    if weekly_change is None:
        return "Building baseline"

    if goal == "Cut":
        if -0.75 <= weekly_change <= -0.25:
            return "On track"
        if weekly_change < -0.75:
            return "Dropping fast"
        return "Needs momentum"

    if goal == "Lean bulk":
        if 0.10 <= weekly_change <= 0.35:
            return "On track"
        if weekly_change > 0.35:
            return "Rising fast"
        return "Needs fuel"

    if goal == "Recomp":
        if -0.15 <= weekly_change <= 0.15:
            return "On track"
        return "Watch trend"

    return "Building baseline"


def calculate_weight_summary(user_logs):
    weight_logs = user_logs.copy()

    if weight_logs.empty:
        return {
            "current_weight": None,
            "latest_7_day_avg": None,
            "previous_7_day_avg": None,
            "weekly_change": None,
            "streak": 0,
            "goal_status_label": "Building baseline",
        }

    weight_logs["date"] = pd.to_datetime(weight_logs["date"], errors="coerce")
    weight_logs["weight"] = pd.to_numeric(weight_logs["weight"], errors="coerce")
    weight_logs = weight_logs.dropna(subset=["date", "weight"]).sort_values("date")

    if weight_logs.empty:
        return {
            "current_weight": None,
            "latest_7_day_avg": None,
            "previous_7_day_avg": None,
            "weekly_change": None,
            "streak": 0,
            "goal_status_label": "Building baseline",
        }

    current_weight = float(weight_logs.iloc[-1]["weight"])
    latest_goal = weight_logs.iloc[-1].get("goal")

    if len(weight_logs) >= 14:
        latest_7_day_avg = float(weight_logs.tail(7)["weight"].mean())
        previous_7_day_avg = float(weight_logs.iloc[-14:-7]["weight"].mean())
        weekly_change = latest_7_day_avg - previous_7_day_avg
    else:
        latest_7_day_avg = None
        previous_7_day_avg = None
        weekly_change = None

    logged_dates = set(weight_logs["date"].dt.date)
    check_date = pd.Timestamp.today().date()
    streak = 0

    while check_date in logged_dates:
        streak += 1
        check_date = check_date.fromordinal(check_date.toordinal() - 1)

    return {
        "current_weight": current_weight,
        "latest_7_day_avg": latest_7_day_avg,
        "previous_7_day_avg": previous_7_day_avg,
        "weekly_change": weekly_change,
        "streak": streak,
        "goal_status_label": _get_goal_status_label(latest_goal, weekly_change),
    }


def show_weight_chart(user_logs):
    st.subheader("Weight progress")

    if user_logs.empty:
        st.write("No data yet")
        return

    user_logs = user_logs.copy()
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
            scale=alt.Scale(domain=[min_weight - padding, max_weight + padding]),
        ),
        tooltip=["date:T", "weight:Q"],
    )

    trend_line = alt.Chart(daily_weights).mark_line(strokeWidth=5).encode(
        x="date:T",
        y="weight_14_day_avg:Q",
        color=alt.Color(
            "goal:N",
            scale=alt.Scale(
                domain=["Cut", "Lean bulk", "Recomp"],
                range=[GOAL_COLORS["Cut"], GOAL_COLORS["Lean bulk"], GOAL_COLORS["Recomp"]],
            ),
        ),
        tooltip=["date:T", "weight_14_day_avg:Q", "goal"],
    )

    chart = raw_points + trend_line
    st.altair_chart(chart, use_container_width=True)


def show_recent_weight_chart(user_logs):
    if user_logs.empty:
        st.caption("Log more weights to see your chart.")
        return

    chart_data = user_logs.copy()
    chart_data["date"] = pd.to_datetime(chart_data["date"], errors="coerce")
    chart_data["weight"] = pd.to_numeric(chart_data["weight"], errors="coerce")
    chart_data = (
        chart_data
        .dropna(subset=["date", "weight"])
        .sort_values("date")
        .tail(14)
    )

    if len(chart_data) < 2:
        st.caption("Log more weights to see your chart.")
        return

    min_weight = chart_data["weight"].min()
    max_weight = chart_data["weight"].max()
    padding = 0.5

    x_axis = alt.X(
        "date:T",
        axis=alt.Axis(
            title=None,
            tickCount=4,
            ticks=False,
            domain=False,
            labelColor="#8f98aa",
            labelFontSize=11,
            labelAngle=0,
            format="%d %b",
        ),
    )
    y_axis = alt.Y(
        "weight:Q",
        scale=alt.Scale(domain=[min_weight - padding, max_weight + padding]),
        axis=alt.Axis(
            title=None,
            tickCount=3,
            ticks=False,
            domain=False,
            labelColor="#8f98aa",
            labelFontSize=11,
            format=".1f",
        ),
    )

    line = alt.Chart(chart_data).mark_line(
        color="#66f05f",
        strokeWidth=4,
        interpolate="monotone",
    ).encode(
        x=x_axis,
        y=y_axis,
        tooltip=["date:T", "weight:Q"],
    )

    points = alt.Chart(chart_data).mark_circle(
        size=42,
        color="#66f05f",
        opacity=0.95,
    ).encode(
        x=x_axis,
        y=y_axis,
        tooltip=["date:T", "weight:Q"],
    )

    chart = (line + points).properties(
        height=185,
    ).configure_view(
        strokeWidth=0,
    ).configure_axis(
        grid=True,
        gridColor="rgba(255,255,255,0.07)",
        domain=False,
    )

    st.altair_chart(chart, use_container_width=True)


def show_goal_feedback(user_logs, profile, summary=None):
    st.markdown(
        """
        <div class="section-title-row">
            <h3>Goal Feedback</h3>
            <span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if summary is None:
        summary = calculate_weight_summary(user_logs)

    if summary["weekly_change"] is None:
        st.info("Log at least 14 days of weight data to get trend feedback.")
        return

    latest_avg_weight = summary["latest_7_day_avg"]
    previous_avg_weight = summary["previous_7_day_avg"]
    weight_change = summary["weekly_change"]
    status_label = summary["goal_status_label"]
    latest_goal = profile["goal"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="dashboard-card stat-card">
                <div class="stat-icon">7</div>
                <div class="card-label">Latest 7-day avg</div>
                <p class="stat-value">{latest_avg_weight:.2f} kg</p>
                <p class="subtle-text">Latest 7 logged entries</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="dashboard-card stat-card">
                <div class="stat-icon">P</div>
                <div class="card-label">Previous 7-day avg</div>
                <p class="stat-value">{previous_avg_weight:.2f} kg</p>
                <p class="subtle-text">Previous 7 logged entries</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="dashboard-card stat-card">
                <div class="stat-icon">↕</div>
                <div class="card-label">Weekly change</div>
                <p class="stat-value">{weight_change:+.2f} kg</p>
                <p class="subtle-text">Latest avg minus previous avg</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if latest_goal == "Cut":
        if status_label == "On track":
            st.success("Cut is on track")
        elif status_label == "Dropping fast":
            st.warning("Weight is dropping quickly. Make sure performance and recovery are okay.")
        else:
            st.warning("Weight is not dropping much yet. Watch the trend over the next week.")

    elif latest_goal == "Lean bulk":
        if status_label == "On track":
            st.success("Lean bulk is on track")
        elif status_label == "Rising fast":
            st.warning("Weight is rising quickly. You may be gaining faster than needed.")
        else:
            st.warning("Weight is not rising much yet. You may need more food if this continues.")

    elif latest_goal == "Recomp":
        if status_label == "On track":
            st.success("Weight is stable - ideal for recomp")
        else:
            st.info("Weight is moving. That may be fine, but recomp usually works best with a stable trend.")
