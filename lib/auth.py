# lib/auth.py
from __future__ import annotations
import os
import streamlit as st

USERS = {
    "admin":      {"password": "admin",  "role": "Admin"},
    "client":     {"password": "client", "role": "Client"},
    "supervisor": {"password": "super",  "role": "Supervisor"},
    "employee":   {"password": "emp",    "role": "Employee"},
}

APP_TITLE = "INET Computer Services HRMS"
LOGO_PATH = "assets/logo.png"

def _logo():
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=96)

def login_ui() -> None:
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    _logo()
    st.markdown(
        f"<h3 style='text-align:center;margin:6px 0 18px 0'>{APP_TITLE}</h3>",
        unsafe_allow_html=True,
    )
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Username", autocomplete="username")
        p = st.text_input("Password", type="password", autocomplete="current-password")
        ok = st.form_submit_button("Sign in", type="primary")
    if ok:
        rec = USERS.get(u)
        if rec and p == rec["password"]:
            st.session_state["user"] = {"username": u, "role": rec["role"]}
            st.rerun()
        else:
            st.error("Invalid username or password")

def require_login() -> None:
    if st.session_state.get("user"):
        return
    login_ui()
    st.stop()

def logout_button(label: str = "Logout") -> None:
    if st.button(label, key="logout_btn"):
        st.session_state.pop("user", None)
        st.session_state.pop("active_page", None)
        st.rerun()

def user_role() -> str:
    return (st.session_state.get("user") or {}).get("role", "Guest")
