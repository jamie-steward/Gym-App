import streamlit as st
import streamlit.components.v1 as components
import json
import re

from components.database import apply_default_follows, is_username_available, normalize_username, supabase

try:
    from streamlit_cookies_controller import CookieController
except Exception:
    CookieController = None


AUTH_STORAGE_KEY = "shapeup_auth_session"
AUTH_QUERY_PARAM = "shapeup_session"
AUTH_ACCESS_COOKIE = "sb_access_token"
AUTH_REFRESH_COOKIE = "sb_refresh_token"
AUTH_COOKIE_CONTROLLER_KEY = "auth_cookie_controller"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,20}$")
_runtime_cookie_controller = None
COOKIE_WRITE_METHOD = "streamlit-cookies-controller"
COOKIE_WRITE_NOTE = "st.context.cookies only updates on next browser request/rerun"


def auth_debug(message):
    if bool(st.secrets.get("DEV_MODE", False)):
        print(f"[ShapeUp auth] {message}")


def _token_info(token):
    token_text = str(token or "")
    return {
        "exists": bool(token_text),
        "length": len(token_text),
    }


def _safe_context_cookie_keys():
    try:
        return sorted(list(st.context.cookies.keys()))
    except Exception as e:
        return [f"could_not_read_cookie_keys: {e}"]


def auth_debug_state(**updates):
    current = st.session_state.get("auth_debug_state", {})
    current.update(updates)
    st.session_state["auth_debug_state"] = current


def auth_log_event(event, **details):
    safe_details = {
        key: value
        for key, value in details.items()
        if "token" not in key.lower() or key.lower().endswith("_info")
    }
    events = st.session_state.get("auth_debug_events", [])
    events.append({"event": event, **safe_details})
    st.session_state["auth_debug_events"] = events[-25:]
    auth_debug(f"{event}: {safe_details}")


def get_auth_debug_snapshot():
    auth_user = st.session_state.get("auth_user")
    access_cookie = get_access_token_from_cookie()
    refresh_cookie = get_refresh_token_from_cookie()
    state = st.session_state.get("auth_debug_state", {})

    return {
        "st_context_cookie_keys": _safe_context_cookie_keys(),
        "sb_access_token": _token_info(access_cookie),
        "sb_refresh_token": _token_info(refresh_cookie),
        "auth_restore_attempted": st.session_state.get("auth_restore_attempted", False),
        "auth_restore_result": state.get("restore_result", "not_attempted"),
        "auth_user_exists": auth_user is not None,
        "auth_user_email": getattr(auth_user, "email", None),
        "auth_user_id": getattr(auth_user, "id", None),
        "session_auth_access_token": _token_info(st.session_state.get("auth_access_token")),
        "session_auth_refresh_token": _token_info(st.session_state.get("auth_refresh_token")),
        "cookie_write_method": state.get("cookie_write_method"),
        "cookie_write_attempted": state.get("cookie_write_attempted", False),
        "cookie_write_error": state.get("cookie_write_error"),
        "note": state.get("note", COOKIE_WRITE_NOTE),
        "debug_events": st.session_state.get("auth_debug_events", []),
    }


def render_auth_debug_panel():
    st.subheader("Temporary auth debug")
    st.caption("Token values are hidden. Only existence and string length are shown.")
    st.json(get_auth_debug_snapshot())


def show_auth_debug_panel():
    if not bool(st.secrets.get("DEV_MODE", False)):
        return

    st.sidebar.caption("Auth debug")
    st.sidebar.json(get_auth_debug_snapshot())


def initialize_cookie_controller():
    global _runtime_cookie_controller

    if CookieController is None:
        return None

    _runtime_cookie_controller = CookieController(key=AUTH_COOKIE_CONTROLLER_KEY)
    return _runtime_cookie_controller


def get_cookie_controller():
    if _runtime_cookie_controller is not None:
        return _runtime_cookie_controller

    return initialize_cookie_controller()


def set_auth_cookies(access_token, refresh_token, controller=None):
    auth_debug_state(
        cookie_write_method=COOKIE_WRITE_METHOD,
        cookie_write_attempted=True,
        cookie_write_error=None,
        note=COOKIE_WRITE_NOTE,
    )
    auth_log_event(
        "set_auth_cookies_start",
        cookie_write_method=COOKIE_WRITE_METHOD,
        access_token_info=_token_info(access_token),
        refresh_token_info=_token_info(refresh_token),
    )

    try:
        controller = controller or get_cookie_controller()
        if controller is None:
            auth_debug_state(cookie_write_error="cookie_controller_unavailable")
            auth_log_event("set_auth_cookies_failed", reason="cookie_controller_unavailable")
            return False

        controller.set(AUTH_ACCESS_COOKIE, access_token, max_age=COOKIE_MAX_AGE, same_site="lax")
        controller.set(AUTH_REFRESH_COOKIE, refresh_token, max_age=COOKIE_MAX_AGE, same_site="lax")
        auth_log_event(
            "set_auth_cookies_success",
            cookie_write_method=COOKIE_WRITE_METHOD,
            note=COOKIE_WRITE_NOTE,
            access_token_info=_token_info(access_token),
            refresh_token_info=_token_info(refresh_token),
        )
        return True
    except Exception as e:
        auth_debug_state(cookie_write_error=str(e))
        auth_log_event("set_auth_cookies_failed", error=str(e))
        raise


def clear_auth_cookies(controller=None):
    auth_debug_state(
        cookie_write_method=COOKIE_WRITE_METHOD,
        cookie_write_attempted=True,
        cookie_write_error=None,
        note=COOKIE_WRITE_NOTE,
    )
    auth_log_event("clear_auth_cookies_start")

    try:
        controller = controller or get_cookie_controller()
        if controller is None:
            auth_log_event("clear_auth_cookies_skipped", reason="cookie_controller_unavailable")
            return

        for cookie_name in (AUTH_ACCESS_COOKIE, AUTH_REFRESH_COOKIE):
            try:
                controller.remove(cookie_name)
            except KeyError:
                auth_log_event("clear_auth_cookie_missing", cookie_name=cookie_name)

        auth_log_event("clear_auth_cookies_success")
    except Exception as e:
        auth_log_event("clear_auth_cookies_failed", error=str(e))
        raise


def get_refresh_token_from_cookie(controller=None):
    return st.context.cookies.get(AUTH_REFRESH_COOKIE)


def get_access_token_from_cookie(controller=None):
    return st.context.cookies.get(AUTH_ACCESS_COOKIE)


def render_cookie_write_reload():
    auth_user = st.session_state.get("auth_user")
    access_token = st.session_state.get("auth_access_token")
    refresh_token = st.session_state.get("auth_refresh_token")

    if auth_user is None or not access_token or not refresh_token:
        return

    components.html(
        """
        <script>
        setTimeout(() => {
            window.parent.location.reload();
        }, 700);
        </script>
        """,
        height=0,
    )
    st.info("Finishing secure login...")
    st.stop()


def render_cookie_clear_reload():
    components.html(
        """
        <script>
        setTimeout(() => {
            window.parent.location.reload();
        }, 700);
        </script>
        """,
        height=0,
    )
    st.info("Logging out...")
    st.stop()


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
    auth_user = st.session_state.get("auth_user")
    if not auth_user or not st.session_state.get("auth_access_token") or not st.session_state.get("auth_refresh_token"):
        return None

    return {
        "logged_in": True,
        "user_id": auth_user.id,
        "email": auth_user.email,
        "access_token": st.session_state.get("auth_access_token"),
        "refresh_token": st.session_state.get("auth_refresh_token"),
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
    st.session_state["auth_access_token"] = session_data["access_token"]
    st.session_state["auth_refresh_token"] = session_data["refresh_token"]
    st.session_state["last_email"] = session_data["email"]
    supabase.auth.set_session(session_data["access_token"], session_data["refresh_token"])


def store_auth_session(user, session, controller=None):
    if user is None or session is None:
        raise ValueError("Supabase did not return a complete login session.")

    st.session_state["auth_user"] = user
    st.session_state["auth_user_id"] = user.id
    st.session_state["auth_access_token"] = session.access_token
    st.session_state["auth_refresh_token"] = session.refresh_token
    st.session_state["last_email"] = user.email
    st.session_state.pop("manual_logout", None)
    st.session_state["auth_restore_attempted"] = True
    cookie_write_ok = set_auth_cookies(session.access_token, session.refresh_token, controller)
    st.session_state["auth_cookie_write_pending_reload"] = bool(cookie_write_ok)
    auth_debug_state(
        refresh_token_cookie_exists=bool(session.refresh_token),
        auth_user_exists=True,
    )
    auth_debug(
        "Stored auth session; "
        f"auth_user_exists={st.session_state.get('auth_user') is not None}; "
        f"access_cookie_set={bool(session.access_token)}; "
        f"refresh_cookie_set={bool(session.refresh_token)}"
    )


def restore_session_from_cookie(rerun_after_restore=False):
    auth_log_event("restore_session_from_cookie_start")
    auth_debug("restore_session_from_cookie() called")

    if st.session_state.get("auth_user") and st.session_state.get("auth_access_token"):
        auth_log_event(
            "restore_session_from_cookie_skip",
            reason="session_state_user_exists",
            auth_user_exists=True,
        )
        auth_debug(
            "Session restored from session_state; "
            f"auth_user_exists={st.session_state.get('auth_user') is not None}"
        )
        return True

    if st.session_state.get("manual_logout"):
        auth_log_event("restore_session_from_cookie_skip", reason="manual_logout")
        auth_debug("Cookie restore skipped after manual logout")
        auth_debug_state(restore_result="manual_logout")
        return False

    if st.session_state.get("auth_restore_attempted"):
        auth_log_event("restore_session_from_cookie_skip", reason="already_attempted")
        auth_debug("Cookie restore skipped; already attempted this Streamlit session")
        return False

    access_cookie = get_access_token_from_cookie()
    refresh_token = get_refresh_token_from_cookie()
    auth_log_event(
        "restore_session_cookie_read",
        context_cookie_keys=_safe_context_cookie_keys(),
        access_token_info=_token_info(access_cookie),
        refresh_token_info=_token_info(refresh_token),
    )
    auth_debug_state(
        refresh_token_cookie_exists=bool(refresh_token),
        auth_restore_attempted=False,
        auth_user_exists=False,
    )
    auth_debug(
        "Cookie check; "
        f"access_token_cookie_exists={bool(access_cookie)}; "
        f"refresh_token_cookie_exists={bool(refresh_token)}"
    )

    st.session_state["auth_restore_attempted"] = True
    auth_debug_state(auth_restore_attempted=True)

    if not refresh_token:
        auth_log_event("restore_session_from_cookie_result", result="no_cookie")
        auth_debug_state(restore_result="no_cookie")
        return False

    try:
        auth_log_event(
            "refresh_session_start",
            refresh_token_info=_token_info(refresh_token),
        )
        response = supabase.auth.refresh_session(refresh_token)
        session = response.session
        user = response.user or getattr(session, "user", None)

        if user is None or session is None:
            raise ValueError("Supabase did not return a refreshed session.")

        auth_log_event(
            "refresh_session_success",
            user_exists=user is not None,
            session_exists=session is not None,
            access_token_info=_token_info(getattr(session, "access_token", None)),
            refresh_token_info=_token_info(getattr(session, "refresh_token", None)),
        )
        store_auth_session(user, session)
        st.session_state["auth_restored_from_cookie"] = True
        auth_debug_state(
            restore_result="success",
            auth_user_exists=True,
            refresh_token_cookie_exists=True,
        )
        auth_debug(
            "refresh_session succeeded; "
            f"auth_user_exists={st.session_state.get('auth_user') is not None}; "
            f"new_access_token_exists={bool(st.session_state.get('auth_access_token'))}; "
            f"new_refresh_token_exists={bool(st.session_state.get('auth_refresh_token'))}"
        )

        if rerun_after_restore:
            st.rerun()

        return True
    except Exception as e:
        auth_log_event("refresh_session_failed", error=str(e))
        clear_auth_cookies()
        auth_debug_state(
            restore_result=f"failed: {e}",
            auth_user_exists=False,
        )
        auth_debug(f"refresh_session failed -> cleared cookies: {e}")
        return False


def restore_session():
    if st.session_state.get("auth_user") and st.session_state.get("auth_access_token"):
        try:
            supabase.auth.set_session(
                st.session_state["auth_access_token"],
                st.session_state["auth_refresh_token"],
            )
            auth_debug("Session restored from session_state")
            return
        except Exception:
            st.session_state.pop("auth_user", None)
            st.session_state.pop("auth_access_token", None)
            st.session_state.pop("auth_refresh_token", None)

    if restore_session_from_cookie(rerun_after_restore=True):
        return

    if not st.session_state.get("manual_logout"):
        st.session_state["auth_restore_attempted"] = True


def login_user(email, password):
    auth_log_event("login_start", email_provided=bool(email))

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        auth_log_event(
            "login_supabase_success",
            user_exists=response.user is not None,
            session_exists=response.session is not None,
            access_token_info=_token_info(getattr(response.session, "access_token", None)),
            refresh_token_info=_token_info(getattr(response.session, "refresh_token", None)),
        )
    except Exception as e:
        auth_log_event("login_supabase_failed", error=str(e))
        raise

    store_auth_session(response.user, response.session)
    try:
        applied_follows = apply_default_follows(response.user.id)
        auth_log_event("default_follows_applied", count=len(applied_follows))
    except Exception as e:
        auth_log_event("default_follows_failed", error=str(e))
    auth_log_event(
        "login_complete",
        auth_user_exists=st.session_state.get("auth_user") is not None,
        session_access_token_info=_token_info(st.session_state.get("auth_access_token")),
        session_refresh_token_info=_token_info(st.session_state.get("auth_refresh_token")),
    )


def login(email, password):
    login_user(email, password)


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
    try:
        applied_follows = apply_default_follows(response.user.id)
        auth_log_event("default_follows_applied", count=len(applied_follows))
    except Exception as e:
        auth_log_event("default_follows_failed", error=str(e))
    return "logged_in"


def logout_user():
    st.session_state["manual_logout"] = True
    st.session_state.pop("auth_user", None)
    st.session_state.pop("auth_user_id", None)
    st.session_state.pop("auth_access_token", None)
    st.session_state.pop("auth_refresh_token", None)
    st.session_state.pop("auth_restore_attempted", None)
    st.session_state.pop("auth_restored_from_cookie", None)
    st.session_state["auth_debug_state"] = {
        "refresh_token_cookie_exists": False,
        "restore_result": "logged_out",
        "auth_user_exists": False,
    }
    clear_auth_cookies()
    st.session_state["auth_cookie_clear_pending_reload"] = True
    clear_browser_session()
    supabase.auth.sign_out()


def logout():
    logout_user()


def get_current_user():
    restore_session()

    auth_user = st.session_state.get("auth_user")
    if auth_user is None:
        return None

    return {
        "user_id": auth_user.id,
        "email": auth_user.email,
    }


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
                st.session_state.pop("auth_cookie_write_pending_reload", None)
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
                    st.session_state.pop("auth_cookie_write_pending_reload", None)
                    st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {e}")


def require_login():
    restore_session()

    st.write("auth_user exists:", "auth_user" in st.session_state)

    auth_user = st.session_state.get("auth_user")
    if auth_user is None:
        show_login_form()
        st.stop()

    return auth_user.id, auth_user.email


def require_auth():
    return require_login()


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
            if st.session_state.pop("auth_cookie_clear_pending_reload", False):
                render_cookie_clear_reload()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
