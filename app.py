import streamlit as st
import pandas as pd
from datetime import date
from lib.auth import require_login, logout_button, user_role
from lib.db import ensure_schema, seed_if_empty, db, engine
from lib.payroll import run_payroll

st.set_page_config(page_title="HRMS Dashboard", page_icon="🧩", layout="wide")

# one-time init
ensure_schema(); seed_if_empty()

# auth
require_login()
logout_button()
st.sidebar.write(f"**Role:** {user_role()}")

# navigation
page = st.sidebar.radio("Go to", ["Dashboard", "Attendance", "Payroll", "Employees", "Reports"])

# --- Dashboard ---
if page == "Dashboard":
    st.title("🧩 HRMS Dashboard")
    with db() as conn:
        headcount = conn.exec_driver_sql("SELECT COUNT(*) FROM employees WHERE active=TRUE" if engine.dialect.name!="sqlite" else "SELECT COUNT(*) FROM employees WHERE active=1").scalar()
        pays = conn.exec_driver_sql("SELECT COALESCE(SUM(net),0) FROM payslips").scalar()
    c1, c2 = st.columns(2)
    c1.metric("Headcount", headcount)
    c2.metric("Salary Disbursed (All-time)", f"{float(pays):,.2f}")
    st.info("Add more KPIs / charts as needed (attendance trend, wage vs deductions, etc.).")

# --- Attendance ---
elif page == "Attendance":
    st.title("🕒 Attendance Import (CSV)")
    st.write("CSV columns expected: **code, day, punch_in, punch_out, source** (ISO dates).")
    f = st.file_uploader("Upload CSV", type=["csv"])
    if f is not None:
        df = pd.read_csv(f)
        st.dataframe(df.head())
        inserted = 0
        from sqlalchemy import text
        with db() as conn:
            # map employee code -> id
            codes = tuple(df["code"].unique().tolist())
            if not codes:
                st.warning("No rows."); st.stop()
            q = "SELECT id, code FROM employees WHERE code IN %(codes)s" if engine.dialect.name!="sqlite" else \
                f"SELECT id, code FROM employees WHERE code IN ({','.join(['?']*len(codes))})"
            res = conn.exec_driver_sql(q, {"codes": codes} if engine.dialect.name!="sqlite" else tuple(codes)).fetchall()
            id_by_code = {r.code: r.id for r in res}
            p = "?" if engine.dialect.name=="sqlite" else "%s"
            for _, row in df.iterrows():
                emp_id = id_by_code.get(row["code"])
                if not emp_id: 
                    continue
                conn.exec_driver_sql(
                    f"INSERT INTO attendance_logs(employee_id,day,punch_in,punch_out,source) VALUES ({p},{p},{p},{p},{p})",
                    (emp_id, row.get("day"), row.get("punch_in"), row.get("punch_out"), row.get("source","csv"))
                )
                inserted += 1
        st.success(f"Imported {inserted} rows")

# --- Payroll ---
elif page == "Payroll":
    st.title("💸 Payroll")
    col1, col2 = st.columns(2)
    month = col1.selectbox("Month", list(range(1,13)), index=date.today().month-1)
    year  = col2.number_input("Year", min_value=2000, max_value=2100, value=date.today().year, step=1)
    if st.button("Process Payroll Run"):
        results = run_payroll(engine, int(month), int(year))
        st.success(f"Processed {len(results)} employees")
        df = pd.DataFrame(results)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode(), "payroll_results.csv", "text/csv")

# --- Employees ---
elif page == "Employees":
    st.title("🧑‍💼 Employees")
    with db() as conn:
        df = pd.read_sql("SELECT id, code, first_name, last_name, base_salary, active FROM employees", conn.connection)
    st.dataframe(df, use_container_width=True)

# --- Reports (placeholder) ---
elif page == "Reports":
    st.title("📊 Reports")
    st.info("Add attendance trend, wages vs deductions, compliance, etc. here.")
