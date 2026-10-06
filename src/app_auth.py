from __future__ import annotations

import secrets as secrets_mod

import streamlit as st

from src.constants import SESSION_AUTHENTICATED


def _configured_password() -> str | None:
    try:
        raw = st.secrets.get("password")
    except Exception:
        return None
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def require_login() -> None:
    """
    When `password` is set in Streamlit secrets, show a login gate until the user signs in.
    Calls st.stop() until authenticated. No-op when password is not configured.
    """
    expected = _configured_password()
    if not expected:
        return

    if st.session_state.get(SESSION_AUTHENTICATED):
        return

    st.title("Sign in")
    st.caption("This app is private. Enter the password from your Streamlit secrets.")

    with st.form("app_login", clear_on_submit=False):
        entered = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Log in", type="primary")

    if submitted:
        if secrets_mod.compare_digest(entered, expected):
            st.session_state[SESSION_AUTHENTICATED] = True
            st.rerun()
        st.error("Incorrect password.")

    st.stop()
