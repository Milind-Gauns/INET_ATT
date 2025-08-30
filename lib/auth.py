import streamlit as st

# Demo credentials ONLY. Replace with real auth later.
USERS = {
    "admin":      {"password": "admin123", "role": "Admin"},
    "supervisor": {"password": "super123", "role": "Supervisor"},
    "client":     {"password": "client123", "role": "Client"},
    "employee":   {"password": "emp123",   "role": "Employee"},
}

def login_ui():
    st.title("HRMS Login")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            rec = USERS.get(username)
            if rec and rec["password"] == password:
                st.session_state.user = {"username": username, "role": rec["role"]}
                st.success(f"Welcome, {username} ({rec['role']})")
                st.rerun()  # modern Streamlit; replaces st.experimental_rerun()
            else:
                st.error("Invalid credentials")

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
    if "user" in st.session_state and st.sidebar.button("Logout"):
        del st.session_state["user"]
        st.rerun()
