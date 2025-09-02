import os
import streamlit as st
from .ui import inject_theme_css, apply_login_layout  # <-- add apply_login_layout

USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "supervisor": {"password": "super123", "role": "Supervisor"},
    "client": {"password": "client123", "role": "Client"},
    "employee": {"password": "emp123", "role": "Employee"},
}

def login_ui():
    inject_theme_css()
    apply_login_layout()  # <-- removes top padding on login page

    st.markdown('<div class="center-wrap">', unsafe_allow_html=True)

    # ---- brand block (big logo + title) ----
    st.markdown('<div class="login-hero">', unsafe_allow_html=True)
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        # No use_column_width; just set width (bigger logo)
        st.image(logo_path, width=120)
    st.markdown("#### INET Computer Services HRMS")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- card with form ----
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("### Sign in")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            rec = USERS.get(username)
            if rec and rec["password"] == password:
                st.session_state.user = {"username": username, "role": rec["role"]}
                st.success(f"Welcome, {username} ({rec['role']})")
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.markdown('</div>', unsafe_allow_html=True)  # /login-card
    st.markdown('</div>', unsafe_allow_html=True)  # /center-wrap

def require_login(roles=None):
    if "user" not in st.session_state:
        login_ui(); st.stop()
    if roles and st.session_state.user["role"] not in roles:
        st.error("You don’t have access to this page."); st.stop()

def user_role():
    return st.session_state.get("user", {}).get("role")
