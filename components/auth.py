import streamlit as st
import streamlit.components.v1 as components
import json
import re

from components.database import is_username_available, normalize_username, supabase


AUTH_STORAGE_KEY = "shapeup_auth_session"
AUTH_QUERY_PARAM = "shapeup_session"
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,20}$")


def validate_signup_public_profile(display_name, username):
    display_name = str(display_name or "").strip()
    username = normalize_username(username)

    if not display_name:
        return None, None, "Enter a display name."

    if not username:
        return None, None, "Choose a username."

    if not USERNAME_PATTERN.match(username):
        return None, None, "Use 3-20 lowercase letters, numbers, or underscores for your username."

    if not is_username_available(None, username):
        return None, None, "That username is already taken."

    return display_name, username, ""


def _session_payload():
    if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
        return None

    return {
        "logged_in": True,
        "user_id": st.session_state.get("user_id"),
        "email": st.session_state.get("email"),
        "access_token": st.session_state.get("access_token"),
        "refresh_token": st.session_state.get("refresh_token"),
    }


def persist_session_to_browser(reload_page=False):
    payload = _session_payload()
    if not payload:
        return

    reload_js = "window.parent.location.reload();" if reload_page else ""
    payload_json = json.dumps(payload)
    components.html(
        f"""
        <script>
        const payload = JSON.stringify({payload_json});
        try {{
            window.parent.localStorage.setItem("{AUTH_STORAGE_KEY}", payload);
        }} catch (error) {{
            localStorage.setItem("{AUTH_STORAGE_KEY}", payload);
        }}
        {reload_js}
        </script>
        """,
        height=0,
    )


def request_browser_session_restore():
    # Streamlit does not expose browser localStorage directly to Python.
    # This tiny bridge restores the Supabase session after mobile refresh/sleep
    # by passing the saved browser session back once, then clearing the URL.
    components.html(
        f"""
        <script>
        const key = "{AUTH_STORAGE_KEY}";
        const param = "{AUTH_QUERY_PARAM}";
        let saved = null;
        try {{
            saved = window.parent.localStorage.getItem(key);
        }} catch (error) {{
            saved = localStorage.getItem(key);
        }}
        const url = new URL(window.parent.location.href);
        if (saved && !url.searchParams.has(param)) {{
            url.searchParams.set(param, btoa(saved));
            window.parent.location.replace(url.toString());
        }}
        </script>
        """,
        height=0,
    )


def clear_browser_session():
    components.html(
        f"""
        <script>
        try {{
            window.parent.localStorage.removeItem("{AUTH_STORAGE_KEY}");
        }} catch (error) {{
            localStorage.removeItem("{AUTH_STORAGE_KEY}");
        }}
        </script>
        """,
        height=0,
    )


def apply_session(session_data):
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = session_data["user_id"]
    st.session_state["email"] = session_data["email"]
    st.session_state["access_token"] = session_data["access_token"]
    st.session_state["refresh_token"] = session_data["refresh_token"]
    st.session_state["last_email"] = session_data["email"]
    supabase.auth.set_session(session_data["access_token"], session_data["refresh_token"])


def store_auth_session(user, session):
    if user is None or session is None:
        raise ValueError("Supabase did not return a complete login session.")

    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user.id
    st.session_state["email"] = user.email
    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token
    st.session_state["last_email"] = user.email
    st.session_state.pop("manual_logout", None)


def restore_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state.get("logged_in") and st.session_state.get("access_token"):
        try:
            supabase.auth.set_session(
                st.session_state["access_token"],
                st.session_state["refresh_token"],
            )
            return
        except Exception:
            st.session_state["logged_in"] = False

    restored_payload = st.query_params.get(AUTH_QUERY_PARAM)
    if restored_payload and not st.session_state.get("manual_logout"):
        try:
            import base64

            session_data = json.loads(base64.b64decode(restored_payload).decode("utf-8"))
            apply_session(session_data)
            st.query_params.clear()
            st.rerun()
        except Exception:
            clear_browser_session()
            st.query_params.clear()

    if not st.session_state.get("logged_in") and not st.session_state.get("manual_logout"):
        request_browser_session_restore()


def login_user(email, password):
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

    store_auth_session(response.user, response.session)


def signup_user(email, password, display_name, username):
    display_name, username, validation_error = validate_signup_public_profile(display_name, username)
    if validation_error:
        raise ValueError(validation_error)

    response = supabase.auth.sign_up({
        "email": email,
        "password": password,
    })

    st.session_state["pending_public_profile"] = {
        "display_name": display_name,
        "username": username,
    }

    if response.user is not None and response.session is None:
        # With email verification enabled there is no authenticated Supabase
        # session yet, so RLS may block profile writes. Keep the signup friendly
        # and let the normal profile setup apply this after confirmed login.
        st.session_state["last_email"] = response.user.email or email
        return "email_confirmation_required"

    store_auth_session(response.user, response.session)
    return "logged_in"


def logout_user():
    st.session_state["manual_logout"] = True
    st.session_state["logged_in"] = False
    st.session_state.pop("user_id", None)
    st.session_state.pop("email", None)
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    supabase.auth.sign_out()


def show_login_form():
    if st.session_state.get("manual_logout"):
        clear_browser_session()

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
        login_email = st.text_input("Email", value=st.session_state.get("last_email", ""), key="login_email")
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
        signup_display_name = st.text_input("Display name", key="signup_display_name")
        signup_username = st.text_input(
            "Username",
            key="signup_username",
            help="Use 3-20 lowercase letters, numbers, or underscores.",
        ).strip().lower()

        st.info("After creating your login, you'll complete your fitness profile.")

        if st.button("Create login", use_container_width=True):
            try:
                signup_result = signup_user(
                    signup_email,
                    signup_password,
                    signup_display_name,
                    signup_username,
                )
                if signup_result == "email_confirmation_required":
                    st.success("Account created. Check your email to confirm your login, then come back and sign in.")
                    st.info("Your username will be applied when you complete your profile after your first confirmed login.")
                else:
                    st.success("Login created")
                    st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {e}")


def require_login():
    restore_session()

    if not st.session_state["logged_in"]:
        show_login_form()
        st.stop()

    persist_session_to_browser()
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
