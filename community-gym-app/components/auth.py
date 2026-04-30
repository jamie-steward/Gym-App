import streamlit as st

from components.database import supabase


def restore_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state.get("logged_in") and st.session_state.get("access_token"):
        supabase.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"],
        )


def login_user(email, password):
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

    st.session_state["logged_in"] = True
    st.session_state["user_id"] = response.user.id
    st.session_state["email"] = response.user.email
    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token
    st.session_state["last_email"] = response.user.email


def signup_user(email, password):
    response = supabase.auth.sign_up({
        "email": email,
        "password": password,
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
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    supabase.auth.sign_out()


def show_login_form():
    st.markdown(
        """
        <div class="shape-brand" style="margin: 2rem 0 1.5rem 0;">
            <div class="shape-brand-title">Shape<span>Up</span></div>
            <p class="shape-brand-subtitle">Stronger together.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Log in or create account")

    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    with tab_login:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log in", use_container_width=True):
            try:
                login_user(login_email, login_password)
                st.success("Logged in")
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
                st.success("Login created")
                st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {e}")


def require_login():
    restore_session()

    if not st.session_state["logged_in"]:
        show_login_form()
        st.stop()

    return st.session_state["user_id"], st.session_state["email"]


def show_logout_button(email):
    st.markdown('<div class="account-bar">', unsafe_allow_html=True)
    top_left, top_right = st.columns([4, 1])

    with top_left:
        st.markdown(
            f'<div class="account-email">Logged in as <span>{email}</span></div>',
            unsafe_allow_html=True,
        )

    with top_right:
        if st.button("Log out", use_container_width=True):
            logout_user()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
