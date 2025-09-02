import streamlit as st
from pathlib import Path

# -------------------- THEME --------------------

def get_theme() -> str:
    """
    Returns 'light' or 'dark'. Default is LIGHT.
    """
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"   # default to light
    return st.session_state["theme"]

def _rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()  # older Streamlit
        except Exception:
            pass

def inject_theme_css(current: str):
    """
    Injects CSS variables for both themes and applies the chosen one.
    """
    light_vars = """
    --bg: #F7F9FC;
    --card: #FFFFFF;
    --text: #0F172A;
    --muted: #475569;
    --primary: #2563EB;          /* indigo-600 */
    --primary-contrast: #FFFFFF;
    --success: #16A34A;          /* green-600 */
    --warning: #F59E0B;          /* amber-500 */
    --danger: #DC2626;           /* red-600 */
    --kpi: #0EA5E9;              /* sky-500 */
    --border: #E5E7EB;
    """

    dark_vars = """
    --bg: #0F172A;               /* slate-900 */
    --card: #111827;             /* gray-900 */
    --text: #E5E7EB;             /* gray-200 */
    --muted: #9CA3AF;            /* gray-400 */
    --primary: #60A5FA;          /* blue-400 */
    --primary-contrast: #0B1220;
    --success: #34D399;          /* green-400 */
    --warning: #FBBF24;          /* amber-400 */
    --danger: #F87171;           /* red-400 */
    --kpi: #38BDF8;              /* sky-400 */
    --border: #1F2937;
    """

    chosen = light_vars if current == "light" else dark_vars

    st.markdown(
        f"""
        <style>
        :root {{ {light_vars} }}
        [data-theme="dark"] {{ {dark_vars} }}
        [data-theme="light"] {{ {light_vars} }}

        /* Apply theme to body */
        body, .stApp {{ background: var(--bg); color: var(--text); }}

        /* Top brand bar */
        .hrms-navbar {{
            position: sticky; top: 0; z-index: 100;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            background: var(--bg);
        }}
        .hrms-brand {{
            display:flex; align-items:center; gap:10px;
        }}
        .hrms-brand img {{
            height: 40px; width:auto;
            filter: drop-shadow(0 2px 6px rgba(0,0,0,.12));
            border-radius: 10px;
        }}
        .hrms-brand .name {{
            font-weight: 800; letter-spacing:.3px;
            font-size: 18px;
        }}
        .hrms-menu a, .hrms-menu button {{
            padding: 8px 10px; border-radius: 10px;
            text-decoration:none; border:1px solid transparent;
            color: var(--text); background: transparent;
        }}
        .hrms-menu .active {{
            background: color-mix(in srgb, var(--primary) 12%, transparent);
            border: 1px solid color-mix(in srgb, var(--primary) 30%, transparent);
            color: var(--text);
        }}

        /* Stat card */
        .hrms-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px 18px 14px;
        }}
        .hrms-card .label {{ color: var(--muted); font-size: 13px; }}
        .hrms-card .value {{ font-size: 28px; font-weight: 800; }}

        /* Buttons */
        .hrms-primary button {{
            background: var(--primary) !important;
            color: var(--primary-contrast) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    # mark the chosen theme in DOM so CSS above can target
    st.html(f"""<script>
      document.documentElement.setAttribute('data-theme', '{current}');
    </script>""")

# -------------------- NAV --------------------

def _nav_button(label: str, key: str, active: bool) -> bool:
    css = "active" if active else ""
    return st.button(label, key=f"nav_{key}", use_container_width=False, type="secondary")

def top_nav(active_page: str = "Dashboard", username: str = "") -> str:
    """
    Renders the top navigation bar and returns the current page.
    Stores the selected page in st.session_state['page'].
    """
    if "page" not in st.session_state:
        st.session_state["page"] = active_page

    with st.container():
        st.markdown('<div class="hrms-navbar">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([0.34, 0.46, 0.20])

        # Brand + Logo
        with c1:
            logo_path = Path("assets/logo.png")
            logo_html = ""
            if logo_path.exists():
                logo_html = f'<img src="app://assets/logo.png" alt="logo" />'
            st.markdown(
                f"""
                <div class="hrms-brand">
                    {logo_html}
                    <div class="name">INET HRMS</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Menu
        with c2:
            cols = st.columns(6)
            items = ["Dashboard", "Attendance", "Payroll", "Docs", "Employees", "Reports"]
            for idx, it in enumerate(items):
                with cols[idx]:
                    pressed = st.button(it, key=f"menu_{it}",
                                        help=it,
                                        type="secondary",
                                        use_container_width=True)
                    # 'active' look handled by CSS when needed; we keep logic simple here
                    if pressed:
                        st.session_state["page"] = it

        # Theme + User
        with c3:
            st.write(f"Signed in as **{username or 'user'}**")
            switch = st.toggle("Light", value=(get_theme() == "light"))
            new_theme = "light" if switch else "dark"
            if new_theme != get_theme():
                st.session_state["theme"] = new_theme
                _rerun()

            st.button("Logout", key="logout_btn", type="secondary")

        st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state["page"]

# -------------------- CARDS/CHART WRAPPERS --------------------

def stat_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="hrms-card">
          <div class="value">{value}</div>
          <div class="label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def chart_card(title: str, chart):
    st.markdown(
        f'<div class="hrms-card" style="padding:16px 16px 6px;"><div class="label" style="font-weight:700;margin-bottom:6px;">{title}</div>',
        unsafe_allow_html=True,
    )
    st.altair_chart(chart, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
