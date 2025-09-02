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
            color: var(--primary-contra
