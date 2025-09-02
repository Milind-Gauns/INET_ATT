# lib/ui.py
from __future__ import annotations
import base64
from typing import Dict

import altair as alt
import streamlit as st

# ---- Palettes (light first) ----
PALETTE_LIGHT: Dict[str, str] = {
    "mode": "light",
    "primary": "#2E5AAC",  # HRMS blue
    "accent":  "#10B981",  # emerald
    "bg":      "#F7FAFC",
    "panel":   "#FFFFFF",
    "text":    "#0F172A",
    "muted":   "#64748B",  # slate-500
}

PALETTE_DARK: Dict[str, str] = {
    "mode": "dark",
    "primary": "#6EA8FE",
    "accent":  "#34D399",
    "bg":      "#0B1220",
    "panel":   "#111827",
    "text":    "#E5E7EB",
    "muted":   "#9CA3AF",
}

def get_theme() -> Dict[str, str]:
    mode = st.session_state.get("theme", "light")
    return PALETTE_LIGHT if mode == "light" else PALETTE_DARK


def _img_to_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


def inject_theme_css(theme: Dict[str, str]) -> None:
    css = f"""
    <style>
      :root {{
        --hrms-primary: {theme['primary']};
        --hrms-accent:  {theme['accent']};
        --hrms-bg:      {theme['bg']};
        --hrms-panel:   {theme['panel']};
        --hrms-text:    {theme['text']};
        --hrms-muted:   {theme['muted']};
        --hrms-card-radius: 16px;
      }}

      [data-testid="stAppViewContainer"] {{
        background: var(--hrms-bg);
        color: var(--hrms-text);
      }}

      .hrms-nav {{
        background: var(--hrms-panel);
        border-radius: 14px;
        padding: 10px 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 8px;
      }}
      .hrms-brand {{
        display:flex; align-items:center; gap:10px;
        font-weight:700; font-size:20px; color:var(--hrms-text);
      }}
      .hrms-brand img {{
        height:34px; width:34px; border-radius:8px;
        border:1px solid rgba(0,0,0,0.06); background:#fff;
      }}
      .hrms-right .toggle-label {{
        font-size:12px; color:var(--hrms-muted); margin-right:6px;
      }}

      .hrms-card {{
        background: var(--hrms-panel);
        border-radius: var(--hrms-card-radius);
        padding: 18px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.05);
      }}
      .hrms-kpi-title {{ color: var(--hrms-muted); font-size:14px; margin-bottom:4px; }}
      .hrms-kpi-value {{ font-size:34px; font-weight:800; color: var(--hrms-text); }}

      .stButton>button {{
        border-radius: 10px;
        border: none;
        background: var(--hrms-primary);
        color: white;
        padding: 8px 12px;
        font-weight: 600;
      }}
      .stButton>button:hover {{ filter: brightness(1.05); }}
      .stTabs [data-baseweb="tab"] {{ font-weight:600; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    alt.themes.enable("none")


def top_nav(active_key: str, username: str, app_name: str = "INET HRMS",
            logo_path: str = "assets/logo.png") -> str:
    """
    Render a top nav with logo/brand, page buttons (no new tabs), theme toggle.
    Returns the chosen page key.
    """
    theme = get_theme()
    light_on = theme["mode"] == "light"

    # If query param has a page, prefer it
    qp = st.query_params
    if "page" in qp:
        active_key = qp["page"]

    pages = [
        ("Dashboard",  "dashboard"),
        ("Attendance", "attendance"),
        ("Payroll",    "payroll"),
        ("Docs",       "docs"),
        ("Employees",  "employees"),
        ("Reports",    "reports"),
    ]

    # Brand bar
    b64 = _img_to_base64(logo_path)
    img_tag = f'<img src="data:image/png;base64,{b64}" alt="logo">' if b64 else ""
    st.markdown(
        f"""
        <div class="hrms-nav">
          <div style="display:flex; align-items:center; justify-content:space-between;">
            <div class="hrms-brand">{img_tag}<span>{app_name}</span></div>
            <div class="hrms-right" style="display:flex; align-items:center; gap:10px;">
              <span class="toggle-label">Theme</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Theme toggle + "Signed in" row
    c1, c2, c3 = st.columns([0.78, 0.12, 0.10])
    with c2:
        toggle = st.toggle("Light", value=light_on, label_visibility="collapsed")
    with c3:
        st.write(f"Signed in as **{username}**")
    st.session_state["theme"] = "light" if toggle else "dark"

    # Page buttons row
    cols = st.columns(len(pages))
    clicked = None
    for i, (label, key) in enumerate(pages):
        style = {}
        if key == active_key:
            # subtle visual hint: we just show it as pressed via label
            label_txt = f"• {label}"
        else:
            label_txt = label
        if cols[i].button(label_txt, key=f"nav_{key}", use_container_width=True):
            clicked = key

    if clicked:
        st.session_state["active_page"] = clicked
        st.query_params["page"] = clicked
        st.rerun()

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
