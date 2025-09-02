import streamlit as st
from .ui import inject_base_css

# Demo credentials ONLY
USERS = {
    "admin":      {"password": "admin123", "role": "Admin"},
    "supervisor": {"password": "super123", "role": "Supervisor"},
    "client":     {"password": "client123", "role": "Client"},
    "employee":   {"password": "emp123",   "role": "Employee"},
}

def login_ui():
    inject_base_css()
    st.markdown('<div class="center-wrap"><div class="login-card">', unsafe_allow_html=True)
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
    st.markdown('</div></div>', unsafe_allow_html=True)

def require_login(roles=None):
    if "user" not in st.session_state:
        login_ui()
        st.stop()
    if roles and st.session_state.user["role"] not in roles:
        st.error("You don’t have access to this page.")
        st.stop()

def user_role():
    return st.session_state.get("user", {}).get("role")

def logout_button():
    # Optional: put a logout button somewhere in content; or keep top-right reserved (see ui.top_nav)
    if "user" in st.session_state and st.button("Logout"):
        del st.session_state["user"]
        st.rerun()
