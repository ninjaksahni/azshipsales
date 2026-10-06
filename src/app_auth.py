from __future__ import annotations

import hashlib
import os
import secrets as secrets_mod
from typing import Any

import streamlit as st

from src.constants import SESSION_AUTHENTICATED, SESSION_AUTH_TOKEN


def _auth_token(password: str) -> str:
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


def _read_secret_password() -> Any:
    """Read app password from Streamlit secrets (several supported layouts)."""
    try:
        secrets = st.secrets
    except Exception:
        return None

    try:
        if "password" in secrets:
            return secrets["password"]
    except Exception:
        pass

    try:
        auth = secrets["auth"]
        if auth is not None and "password" in auth:
            return auth["password"]
    except Exception:
        pass

    try:
        return getattr(secrets, "password", None)
    except Exception:
        pass

    return None


def _configured_password() -> str | None:
    candidates: list[str] = []

    try:
        raw = _read_secret_password()
        if raw is not None:
            candidates.append(str(raw))
    except Exception:
        pass

    for env_key in ("password", "PASSWORD", "APP_PASSWORD"):
        env_val = os.environ.get(env_key)
        if env_val:
            candidates.append(env_val)

    for text in candidates:
        cleaned = text.strip()
        if cleaned:
            return cleaned
    return None


def passwords_match(entered: str, expected: str) -> bool:
    return secrets_mod.compare_digest(entered.strip(), expected.strip())


def _clear_auth_session() -> None:
    st.session_state.pop(SESSION_AUTHENTICATED, None)
    st.session_state.pop(SESSION_AUTH_TOKEN, None)


def _session_is_authenticated(expected: str) -> bool:
    if not st.session_state.get(SESSION_AUTHENTICATED):
        return False
    token = st.session_state.get(SESSION_AUTH_TOKEN)
    return isinstance(token, str) and token == _auth_token(expected)


def require_login() -> None:
    """
    When `password` is set in Streamlit secrets, show a login gate until the user signs in.
    Calls st.stop() until authenticated. No-op when password is not configured.
    """
    expected = _configured_password()
    if not expected:
        _clear_auth_session()
        return

    if _session_is_authenticated(expected):
        return

    _clear_auth_session()

    st.title("Sign in")
    st.caption("This app is private. Enter the password from your Streamlit secrets.")

    with st.form("app_login", clear_on_submit=False):
        entered = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Log in", type="primary")

    if submitted:
        if not entered.strip():
            st.error("Enter a password.")
        elif passwords_match(entered, expected):
            st.session_state[SESSION_AUTHENTICATED] = True
            st.session_state[SESSION_AUTH_TOKEN] = _auth_token(expected)
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()
