import streamlit as st
import pandas as pd
from datetime import date
from lib.auth import require_login, logout_button, user_role
from lib.db import ensure_schema, seed_if_empty, db, engine
from lib.payroll import run_payroll
from lib.ui import inject_base_css, top_nav, stat_card

st.set_page_config(page_title="HRMS Dashboard", page_icon="🧩", layout="wide")

# base CSS + data init
inject_base_css()
ensure_schema(); seed_if_empty()

# auth
require_login()
role = user_role()

# --- Top navigation ---
page = top_nav("Dashboard")

# --- Pages ---
if page == "Dashboard":
    st.title("Overview")
    with db() as conn:
        headcount = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM employees WHERE active=TRUE" if engine.dialect.name!="sqlite"
            else "SELECT COUNT(*) FROM employees WHERE active=1").scalar()
        total_net = float(conn.exec_driver_sql("SELECT COALESCE(SUM(net),0) FROM payslips").scalar() or 0)
    c1, c2, c3 = st.columns(3)
    with c1: stat_card("Headcount", f"{headcount}")
    with c2: stat_card("Salary Disbursed (All-time)", f"₹ {total_net:,.0f}")
    with c3: stat_card("Compliance", "✅ PF/ESI Filed")  # placeholder

elif page == "Attendance":
    st.title("Attendance Import (CSV)")
    st.write("CSV header: **code, day, punch_in, punch_out, source**")
    f = st.file_uploader("Upload CSV", type=["csv"])
    if f:
        df = pd.read_csv(f); st.dataframe(df.head(), use_container_width=True)
        inserted = 0
        with db() as conn:
            codes = tuple(df["code"].unique().tolist())
            if codes:
                q = "SELECT id, code FROM employees WHERE code IN %(codes)s" if engine.dialect.name!="sqlite" \
                    else f"SELECT id, code FROM employees WHERE code IN ({','.join(['?']*len(codes))})"
                res = conn.exec_driver_sql(q, {"codes": codes} if engine.dialect.name!="sqlite" else tuple(codes)).fetchall()
                id_by_code = {r.code: r.id for r in res}
                p = "?" if engine.dialect.name=="sqlite" else "%s"
                for _, row in df.iterrows():
                    emp_id = id_by_code.get(row["code"])
                    if not emp_id: continue
                    conn.exec_driver_sql(
                        f"INSERT INTO attendance_logs(employee_id,day,punch_in,punch_out,source) "
                        f"VALUES ({p},{p},{p},{p},{p})",
                        (emp_id, row.get("day"), row.get("punch_in"), row.get("punch_out"), row.get("source","csv"))
                    )
                    inserted += 1
        st.success(f"Imported {inserted} rows")

elif page == "Payroll":
    st.title("Payroll")
    col1, col2 = st.columns(2)
    month = col1.selectbox("Month", list(range(1,13)), index=date.today().month-1)
    year  = col2.number_input("Year", min_value=2000, max_value=2100, value=date.today().year, step=1)
    if st.button("Process Payroll Run", use_container_width=True, type="primary"):
        results = run_payroll(engine, int(month), int(year))
        st.success(f"Processed {len(results)} employees")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

elif page == "Employees":
    st.title("Employees")
    with db() as conn:
        df = pd.read_sql("SELECT id, code, first_name, last_name, base_salary, active FROM employees", conn.connection)
    st.dataframe(df, use_container_width=True)

elif page == "Reports":
    st.title("Reports")
    st.info("Add attendance trends, wages vs deductions, compliance, etc.")

