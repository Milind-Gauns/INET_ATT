import os
import streamlit as st
from streamlit_option_menu import option_menu

# ---------- Theme tokens ----------
_THEMES = {
    "dark": {
        "bg": "#0B1021",
        "bg2": "#121A2B",
        "card": "#0F162C",
        "text": "#E5E7EB",
        "muted": "#9CA3AF",
        "border": "rgba(255,255,255,.06)",
        "brand": "#2563EB",
        "nav_sel": "#1F2937",
        "alert_bg": "#0E1A30",
        "alert_text": "#C7D2FE",
    },
    "light": {
        "bg": "#F8FAFC",
        "bg2": "#FFFFFF",
        "card": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#6B7280",
        "border": "rgba(2,6,23,.06)",
        "brand": "#2563EB",
        "nav_sel": "#E5E7EB",
        "alert_bg": "#EEF2FF",
        "alert_text": "#1E3A8A",
    },
}

def get_theme():
    return st.session_state.get("theme", "dark")

def set_theme(name: str):
    st.session_state["theme"] = "light" if name == "light" else "dark"

def inject_theme_css(theme: str | None = None):
    t = _THEMES.get(theme or get_theme(), _THEMES["dark"])
    st.markdown(
        f"""
        <style>
          :root {{
            --bg: {t["bg"]};
            --bg2: {t["bg2"]};
            --card: {t["card"]};
            --text: {t["text"]};
            --muted: {t["muted"]};
            --border: {t["border"]};
            --brand: {t["brand"]};
            --nav-sel: {t["nav_sel"]};
            --alert-bg: {t["alert_bg"]};
            --alert-text: {t["alert_text"]};
          }}

          html, body, .stApp {{ background-color: var(--bg) !important; color: var(--text) !important; }}
          .block-container{{ padding-top:1.2rem; padding-bottom:1.6rem; max-width:1200px; margin:0 auto; }}
          header [data-testid="stHeader"] {{ background: transparent; }}
          [data-testid="stSidebar"]{{ display:none; }}

          .topbar {{
            position: sticky; top: 0; z-index: 1000;
            background: linear-gradient(180deg, var(--bg) 65%, rgba(0,0,0,0));
            border-bottom: 1px solid var(--border);
            padding: .6rem 0 .25rem;
          }}
          .brand {{ display:flex; gap:.6rem; align-items:center; font-weight:700; }}
          .brand span {{ font-size:18px; }}

          .card {{ border-radius:16px; padding:1rem 1.25rem; background:var(--card); border:1px solid var(--border); }}
          .metric {{ font-size:28px; font-weight:700; line-height:1; }}
          .metric-label {{ color:var(--muted); font-size:12px; letter-spacing:.04em; }}

          /* Full-height center for login */
          .center-wrap {{
            min-height: 100vh;
            display:flex; align-items:center; justify-content:center;
          }}
          .login-card {{
            width: 480px; border-radius:16px; padding: 26px;
            background: var(--card); border: 1px solid var(--border);
          }}
          .login-hero {{ text-align:center; margin-bottom: 18px; }}
          .login-logo {{ width: 120px; height:auto; opacity:.98; margin-bottom:.4rem; }}

          .stAlert {{ background: var(--alert-bg) !important; color: var(--alert-text) !important; border-radius:12px; }}
          .stAlert p {{ color: var(--alert-text) !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def apply_login_layout():
    """Tighten top spacing only on the login page."""
    st.markdown("""
    <style>
      .block-container{ padding-top: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# ---------- Building blocks ----------
def top_nav(active="Dashboard", username: str | None = None):
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    left, middle, right = st.columns([2, 6, 2])

    with left:
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=40)
        st.markdown('<div class="brand"><span>HRMS</span></div>', unsafe_allow_html=True)

    with middle:
        selected = option_menu(
            None,
            ["Dashboard", "Attendance", "Payroll", "Docs", "Employees", "Reports"],
            icons=["grid", "clock", "cash-coin", "file-earmark-text", "people", "bar-chart"],
            orientation="horizontal",
            default_index=["Dashboard","Attendance","Payroll","Docs","Employees","Reports"].index(active),
            styles={
                "container": {"background": "transparent", "padding": "0"},
                "nav-link": {"font-size": "14px", "padding":"8px 14px", "color":"var(--muted)"},
                "nav-link-selected": {"background-color": "var(--nav-sel)", "color":"var(--text)", "border-radius":"10px"},
            },
        )

    with right:
        is_light = st.toggle("Light", value=(get_theme()=="light"))
        new_theme = "light" if is_light else "dark"
        if new_theme != get_theme():
            set_theme(new_theme)
            st.rerun()

        if username:
            st.caption(f"Signed in as **{username}**")
            if st.button("Logout"):
                if "user" in st.session_state: del st.session_state["user"]
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    return selected

def stat_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="card">
          <div class="metric">{value}</div>
          <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def chart_card(title: str, chart):
    st.markdown(f"<div class='card'><div style='font-weight:700;margin-bottom:.3rem'>{title}</div>", unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
