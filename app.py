import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

from lib.auth import require_login, user_role
from lib.db import ensure_schema, seed_if_empty, db, engine
from lib.payroll import run_payroll
from lib.ui import inject_theme_css, top_nav, stat_card, chart_card, get_theme

# ---------- Page & Theme ----------
st.set_page_config(page_title="HRMS Dashboard", page_icon="🧩", layout="wide")
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"
inject_theme_css(get_theme())

# ---------- Data init (safe to call every run) ----------
ensure_schema()
seed_if_empty()

# ---------- Auth ----------
require_login()
username = st.session_state["user"]["username"]
role = user_role()

# ---------- Top Navigation ----------
page = top_nav("Dashboard", username=username)

# ======================================================
#                         PAGES
# ======================================================

# ---------- DASHBOARD ----------
if page == "Dashboard":
    st.title("Overview")

    with db() as conn:
        # Headcount
        headcount_sql = (
            "SELECT COUNT(*) FROM employees WHERE active=TRUE"
            if engine.dialect.name != "sqlite"
            else "SELECT COUNT(*) FROM employees WHERE active=1"
        )
        headcount = conn.exec_driver_sql(headcount_sql).scalar()

        # Total net paid (all-time)
        total_net = float(conn.exec_driver_sql("SELECT COALESCE(SUM(net),0) FROM payslips").scalar() or 0)

        # Attendance trend (last 30 days)
        att_df = pd.read_sql(
            "SELECT day AS d, COUNT(*) AS punches "
            "FROM attendance_logs GROUP BY day ORDER BY day DESC LIMIT 30",
            conn.connection,
        ).sort_values("d")

        # Wages vs Deductions by payroll run
        wvd = pd.read_sql(
            """
            SELECT pr.year, pr.month, SUM(p.gross) AS gross, SUM(p.deductions) AS deductions, SUM(p.net) AS net
            FROM payslips p
            JOIN payroll_runs pr ON pr.id = p.run_id
            GROUP BY pr.year, pr.month
            ORDER BY pr.year, pr.month
            """,
            conn.connection,
        )
        if not wvd.empty:
            wvd["period"] = wvd["year"].astype(str) + "-" + wvd["month"].astype(int).astype(str).str.zfill(2)

    c1, c2, c3 = st.columns(3)
    with c1:
        stat_card("Headcount", f"{headcount}")
    with c2:
        stat_card("Salary Disbursed (All-time)", f"₹ {total_net:,.0f}")
    with c3:
        stat_card("Compliance", "✅ PF/ESI Filed")  # placeholder

    # Charts
    if not att_df.empty:
        chart1 = alt.Chart(att_df).mark_line(point=True).encode(
            x=alt.X("d:T", title="Day"),
            y=alt.Y("punches:Q", title="Punches"),
            tooltip=["d", "punches"],
        ).properties(height=260)
        chart_card("Attendance Trend (last 30 days)", chart1)
    else:
        st.info("No attendance yet. Import a CSV on the Attendance page.")

    if not wvd.empty:
        melted = wvd.melt(
            id_vars=["period"],
            value_vars=["gross", "deductions"],
            var_name="type",
            value_name="amount",
        )
        chart2 = alt.Chart(melted).mark_bar().encode(
            x=alt.X("period:N", title="Period"),
            y=alt.Y("amount:Q", title="Amount"),
            color=alt.Color("type:N", scale=alt.Scale(scheme="tableau10")),
            tooltip=["period", "type", "amount"],
        ).properties(height=300)
        chart_card("Wages vs Deductions", chart2)
    else:
        st.info("Run payroll to see Wages vs Deductions.")

# ---------- ATTENDANCE ----------
elif page == "Attendance":
    st.title("Attendance Import (CSV)")
    st.write("CSV header: **code, day, punch_in, punch_out, source**")

    f = st.file_uploader("Upload CSV", type=["csv"])
    if f:
        df = pd.read_csv(f)
        st.dataframe(df.head(), use_container_width=True)

        inserted = 0
        with db() as conn:
            codes = tuple(df["code"].unique().tolist())
            if codes:
                if engine.dialect.name != "sqlite":
                    q = "SELECT id, code FROM employees WHERE code IN %(codes)s"
                    res = conn.exec_driver_sql(q, {"codes": codes}).fetchall()
                else:
                    placeholders = ",".join(["?"] * len(codes))
                    q = f"SELECT id, code FROM employees WHERE code IN ({placeholders})"
                    res = conn.exec_driver_sql(q, tuple(codes)).fetchall()

                id_by_code = {r.code: r.id for r in res}
                pmark = "?" if engine.dialect.name == "sqlite" else "%s"

                for _, row in df.iterrows():
                    emp_id = id_by_code.get(row["code"])
                    if not emp_id:
                        continue
                    conn.exec_driver_sql(
                        f"INSERT INTO attendance_logs(employee_id, day, punch_in, punch_out, source) "
                        f"VALUES ({pmark}, {pmark}, {pmark}, {pmark}, {pmark})",
                        (
                            emp_id,
                            row.get("day"),
                            row.get("punch_in"),
                            row.get("punch_out"),
                            row.get("source", "csv"),
                        ),
                    )
                    inserted += 1

        st.success(f"Imported {inserted} rows")

# ---------- PAYROLL ----------
elif page == "Payroll":
    st.title("Payroll")
    col1, col2 = st.columns(2)
    month = col1.selectbox("Month", list(range(1, 13)), index=date.today().month - 1)
    year = col2.number_input("Year", min_value=2000, max_value=2100, value=date.today().year, step=1)

    if st.button("Process Payroll Run", use_container_width=True, type="primary"):
        results = run_payroll(engine, int(month), int(year))
        st.success(f"Processed {len(results)} employees")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

# ---------- EMPLOYEES ----------
elif page == "Employees":
    st.title("Employees")
    # Pandas can read directly from the SQLAlchemy engine
    df = pd.read_sql(
        "SELECT id, code, first_name, last_name, base_salary, active FROM employees",
        con=engine,
    )
    st.dataframe(df, use_container_width=True)

# ---------- REPORTS ----------
elif page == "Reports":
    st.title("Reports")
    st.info("Add attendance trends, compliance, embeds, etc.")
