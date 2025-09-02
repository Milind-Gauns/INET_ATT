import os
import streamlit as st
from streamlit_option_menu import option_menu

# ---------- Theme tokens we control ----------
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

          /* Make the whole app follow our theme (fixes light/dark inconsistencies) */
          html, body, .stApp {{ background-color: var(--bg) !important; color: var(--text) !important; }}
          .block-container {{ padding-top: 1.2rem; padding-bottom: 1.6rem; max-width: 1200px; margin: 0 auto; }}
          header [data-testid="stHeader"] {{ background: transparent; }}
          [data-testid="stSidebar"] {{ display: none; }}

          /* Top bar */
          .topbar {{
            position: sticky; top: 0; z-index: 1000;
            background: linear-gradient(180deg, var(--bg) 65%, rgba(0,0,0,0));
            border-bottom: 1px solid var(--border);
            padding: .6rem 0 .25rem;
          }}
          .brand {{ display:flex; gap:.6rem; align-items:center; font-weight:700; }}
          .brand span {{ font-size:18px; }}

          /* Cards / metrics */
          .card {{ border-radius:16px; padding:1rem 1.25rem; background:var(--card); border:1px solid var(--border); }}
          .metric {{ font-size:28px; font-weight:700; line-height:1; }}
          .metric-label {{ color:var(--muted); font-size:12px; letter-spacing:.04em; }}

          /* Centered login */
          .center-wrap {{
