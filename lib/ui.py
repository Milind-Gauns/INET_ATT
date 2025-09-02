# lib/ui.py
from __future__ import annotations
import base64
import streamlit as st
from typing import Dict
import altair as alt
import os

# ---- Palettes (light first) ----
PALETTE_LIGHT: Dict[str, str] = {
    "mode": "light",
    "primary": "#2E5AAC",           # HRMS blue
    "accent": "#10B981",            # emerald
    "bg": "#F7FAFC",
    "panel": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#64748B"              # slate-500
}

PALETTE_DARK: Dict[str, str] = {
    "mode": "dark",
    "primary": "#6EA8FE",
    "accent": "#34D399",
    "bg": "#0B1220",                # deep navy
    "panel": "#111827",             # slate-900
    "text": "#E5E7EB",              # slate-200
    "muted": "#9CA3AF"              # slate-400
}

def get_theme() -> Dict[str, str]:
    """Return the active theme dict. Defaults to LIGHT."""
    mode = st.session_state.get("theme", "light")
    return PALETTE_LIGHT if mode == "light" else PALETTE_DARK


def _img_to_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


def inject_theme_css(theme: Dict[str, str]) -> None:
    """Inject CSS variables & component styling."""
    css = f"""
    <style>
      :root {{
        --hrms-primary: {theme['primary']};
        --hrms-accent: {theme['accent']};
        --hrms-bg: {theme['bg']};
        --hrms-panel: {theme['panel']};
        --hrms-text: {theme['text']};
        --hrms-muted: {theme['muted']};
        --hrms-card-radius: 16px;
      }}

      /* App background */
      [data-testid="stAppViewContainer"] {{
        background: var(--hrms-bg);
        color: var(--hrms-text);
      }}

      /* Nav bar */
      .hrms-nav {{
        background: var(--hrms-panel);
        border-radius: 14px;
        padding: 10px 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 8px;
      }}
      .hrms-brand {{
        display: flex; align-items: center; gap: 10px;
        font-weight: 700; font-size: 20px; color: var(--hrms-text);
      }}
      .hrms-brand img {{
        height: 34px; width: 34px; border-radius: 8px;
        border: 1px solid rgba(0,0,0,0.06);
        background: #fff;
      }}
      .hrms-nav-links a {{
        text-decoration: none;
        color: var(--hrms-text);
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 10px;
      }}
      .hrms-nav-links a.active {{
        background: rgba(46,90,172,0.12);
        color: var(--hrms-primary);
      }}
      .hrms-right .toggle-label {{
        font-size: 12px; color: var(--hrms-muted); margin-right: 6px;
      }}

      /* KPI cards */
      .hrms-card {{
        background: var(--hrms-panel);
        border-radius: var(--hrms-card-radius);
        padding: 18px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.05);
      }}
      .hrms-kpi-title {{ color: var(--hrms-muted); font-size: 14px; margin-bottom: 4px; }}
      .hrms-kpi-value {{ font-size: 34px; font-weight: 800; color: var(--hrms-text); }}

      /* Section title spacing */
      .hrms-section-title h1, .hrms-section-title h2 {{
        margin-top: 6px !important;
        margin-bottom: 6px !important;
      }}

      /* Buttons */
      .stButton>button {{
        border-radius: 10px;
        border: none;
        background: var(--hrms-primary);
        color: white;
        padding: 8px 14px;
        font-weight: 600;
      }}
      .stButton>button:hover {{ filter: brightness(1.05); }}

      /* Tabs */
      .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # Altair global theme (clean)
    alt.themes.enable("none")


def _nav_link(label: str, key: str, active_key: str) -> str:
    cls = "active" if key == active_key else ""
    return f'<a class="{cls}" href="?page={key}">{label}</a>'


def top_nav(active_key: str, username: str, app_name: str = "INET HRMS",
            logo_path: str = "assets/logo.png") -> str:
    """
    Render a top nav with logo, brand, page links, and theme toggle.
    Returns the chosen page key (string).
    """
    theme = get_theme()
    light_on = theme["mode"] == "light"

    # Keep selected page via query param or session
    qp = st.query_params
    if "page" in qp:
        active_key = qp["page"]

    pages = [
        ("Dashboard", "dashboard"),
        ("Attendance", "attendance"),
        ("Payroll", "payroll"),
        ("Docs", "docs"),
        ("Employees", "employees"),
        ("Reports", "reports"),
    ]

    # Build HTML nav links
    links_html = "".join(_nav_link(lbl, key, active_key) for lbl, key in pages)

    # Logo b64
    b64 = _img_to_base64(logo_path)
    img_tag = f'<img src="data:image/png;base64,{b64}" alt="logo">' if b64 else ""

    with st.container():
        st.markdown(
            f"""
            <div class="hrms-nav">
              <div style="display:flex; align-items:center; justify-content:space-between;">
                <div class="hrms-brand">{img_tag}<span>{app_name}</span></div>
                <div class="hrms-nav-links" style="display:flex; gap:6px;">{links_html}</div>
                <div class="hrms-right" style="display:flex; align-items:center; gap:10px;">
                  <span class="toggle-label">Theme</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Render a real toggle (affects next rerun)
        col1, col2, col3 = st.columns([0.78, 0.12, 0.10])
        with col2:
            toggle = st.toggle("Light", value=light_on, label_visibility="collapsed")
        with col3:
            st.write(f"Signed in as **{username}**")

        # Handle toggle state
        st.session_state["theme"] = "light" if toggle else "dark"

    # Return active page key and also mirror to st.session_state
    st.session_state["active_page"] = active_key
    return active_key


def stat_card(title: str, value: str) -> None:
    st.markdown('<div class="hrms-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="hrms-kpi-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hrms-kpi-value">{value}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def chart_card(title: str, chart) -> None:
    st.markdown('<div class="hrms-card">', unsafe_allow_html=True)
    st.markdown(f"**{title}**")
    st.altair_chart(chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
