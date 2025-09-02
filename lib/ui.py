import streamlit as st
from streamlit_option_menu import option_menu

def inject_base_css():
    st.markdown("""
    <style>
      /* remove default sidebar, tighten page */
      [data-testid="stSidebar"]{display:none;}
      .block-container{padding-top:1.6rem; padding-bottom:2rem; max-width:1200px;}
      header [data-testid="stHeader"] {background: transparent;}
      /* top nav container sticky */
      .topbar { position: sticky; top: 0; z-index: 999; padding: 0.6rem 0 0.2rem; 
                background: linear-gradient(180deg, rgba(11,16,33,0.9), rgba(11,16,33,0.75)); 
                backdrop-filter: blur(6px); border-bottom: 1px solid rgba(255,255,255,0.06); }
      /* card style */
      .card { border-radius: 16px; padding: 1rem 1.25rem; 
              background: #0f162c; border: 1px solid rgba(255,255,255,0.06); }
      .metric {font-size: 28px; font-weight: 700; line-height:1;}
      .metric-label{color:#9CA3AF; font-size: 12px; letter-spacing:.04em;}
      /* login centering */
      .center-wrap { min-height: 70vh; display:flex; align-items:center; justify-content:center; }
      .login-card { width: 420px; border-radius: 16px; padding: 24px;
                    background: #0f162c; border: 1px solid rgba(255,255,255,0.06); }
      .brand {font-weight:700; font-size:18px;}
    </style>
    """, unsafe_allow_html=True)

def top_nav(active="Dashboard"):
    with st.container():
        st.markdown('<div class="topbar">', unsafe_allow_html=True)
        cols = st.columns([1,6,2])
        with cols[0]:
            st.markdown('<div class="brand">🧩 HRMS</div>', unsafe_allow_html=True)
        with cols[1]:
            selected = option_menu(
                None,
                ["Dashboard", "Attendance", "Payroll", "Employees", "Reports"],
                icons=["grid", "clock", "cash-coin", "people", "bar-chart"],
                orientation="horizontal",
                default_index=["Dashboard","Attendance","Payroll","Employees","Reports"].index(active),
                styles={
                    "container": {"background": "transparent", "padding": "0"},
                    "nav-link": {"font-size": "14px", "padding":"8px 14px", "color":"#cbd5e1"},
                    "nav-link-selected": {"background-color": "#1f2937", "color":"white", "border-radius":"10px"},
                },
            )
        with cols[2]:
            # reserved for user / logout button space in header
            pass
        st.markdown('</div>', unsafe_allow_html=True)
    return selected

def stat_card(label:str, value:str):
    st.markdown(f"""
    <div class="card">
      <div class="metric">{value}</div>
      <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)
