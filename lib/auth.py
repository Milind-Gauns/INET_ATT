import streamlit as st

# Demo credentials ONLY (replace with hashed passwords later)
USERS = {
    "admin":      {"password": "admin123", "role": "Admin"},
    "supervisor": {"password": "super123", "role": "Supervisor"},
    "client":     {"password": "client123", "role": "Client"},
    "employee":   {"password": "emp123",   "role": "Employee"},
}

def login_ui():
    st.title("HRMS Login")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
        if ok:
            rec = USERS.get(u)
            if rec and rec["password"] == p:
                st.session_state.user = {"username": u, "role": rec["role"]}
                st.success(f"Welcome, {u} ({rec['role']})")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

def require_login(roles=None):
    if "user" not in st.session_state:
        login_ui(); st.stop()
    if roles and st.session_state.user["role"] not in roles:
        st.error("You don’t have access to this page."); st.stop()

def user_role():
    if "user" in st.session_state:
        return st.session_state.user["role"]
    return None

def logout_button():
    if "user" in st.session_state and st.sidebar.button("Logout"):
        del st.session_state["user"]
        st.experimental_rerun()
