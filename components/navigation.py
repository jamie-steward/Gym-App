import streamlit as st


PAGE_SLUGS = {
    "home",
    "progress",
    "log_workout",
    "workout_history",
    "profile",
    "communities",
}


def restore_page_from_query(default_page="home"):
    query_page = str(st.query_params.get("page") or "").strip().lower()

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = default_page

    if query_page in PAGE_SLUGS:
        st.session_state["current_page"] = query_page
    elif query_page:
        st.session_state["current_page"] = default_page
        st.query_params["page"] = default_page

    return st.session_state["current_page"]


def remember_current_page(page_slug):
    page_slug = str(page_slug or "home").strip().lower()
    if page_slug not in PAGE_SLUGS:
        page_slug = "home"

    st.session_state["current_page"] = page_slug
    if st.query_params.get("page") != page_slug:
        st.query_params["page"] = page_slug


def go_to_page(page_slug):
    remember_current_page(page_slug)
    st.rerun()
