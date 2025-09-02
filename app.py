import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
import datetime as dt
from sqlalchemy import text

from lib.auth import require_login, user_role
from lib.db import ensure_schema, seed_if_empty, db, engine
from lib.payroll import run_payroll
from lib.ui import inject_theme_css, top_nav, stat_card, chart_card, get_theme
from lib.pdf_ingest import parse_payslip, parse_consolidated
from lib.storage import put_bytes, presigned_url

# ---------- Page & Theme ----------
st.set_page_config(page_title="HRMS Dashboard", page_icon="🧩", layout="wide")
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"
inject_theme_css(get_theme())

# ---------- Data init ----------
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

# ---------- DOCS (PDF ingest) ----------
elif page == "Docs":
    st.title("Payroll Documents")
    tab1, tab2 = st.tabs(["Single Pay Slip", "Consolidated Statement"])

    # ---- Single Pay Slip ----
    with tab1:
        f = st.file_uploader("Upload Pay Slip (PDF)", type=["pdf"], key="pslip")
        if f:
            data = f.read()
            parsed = parse_payslip(data)

            colA, colB = st.columns(2)
            with colA:
                st.write("**Employee**:", parsed.get("name"))
                st.write("**Month/Year**:", f"{parsed.get('month')}-{parsed.get('year')}")
                st.write("**Gross**:", parsed.get("gross"))
                st.write("**Basic** / **HRA**:", parsed.get("basic"), "/", parsed.get("hra"))
            with colB:
                st.write("**PF (EE/ER)**:", parsed.get("pf_ee"), "/", parsed.get("pf_er"))
                st.write("**ESI (EE/ER)**:", parsed.get("esi_ee"), "/", parsed.get("esi_er"))
                st.write("**LWF (EE/ER)**:", parsed.get("lwf_ee"), "/", parsed.get("lwf_er"))
                st.write("**Admin PF**:", parsed.get("admin_pf"))
                st.write("**NET**:", parsed.get("net"))

            if st.button("Save to DB & Storage", type="primary"):
                year = int(parsed["year"]); month = int(parsed["month"])
                emp_name = (parsed["name"] or "").strip()

                fname, *rest = emp_name.split(" ")
                lname = " ".join(rest) if rest else ""

                with db() as conn:
                    # find employee by first/last name
                    row = conn.execute(
                        text("SELECT id FROM employees WHERE lower(first_name)=lower(:f) AND lower(last_name)=lower(:l)"),
                        {"f": fname, "l": lname},
                    ).fetchone()

                    if row:
                        emp_id = row[0]
                    else:
                        # create minimal employee
                        code = "E" + str(abs(hash(emp_name)) % 10_000)
                        conn.exec_driver_sql(
                            "INSERT INTO employees(code, first_name, last_name, base_salary, active) VALUES (?, ?, ?, ?, ?)"
                            if engine.dialect.name=="sqlite" else
                            "INSERT INTO employees(code, first_name, last_name, base_salary, active) VALUES (%s,%s,%s,%s,%s)",
                            (code, fname, lname, parsed.get("gross") or 0, 1)
                        )
                        emp_id = conn.exec_driver_sql(
                            "SELECT last_insert_rowid()" if engine.dialect.name=="sqlite" else "SELECT max(id) FROM employees"
                        ).scalar()

                    # ensure payroll run
                    run = conn.exec_driver_sql(
                        "SELECT id FROM payroll_runs WHERE month=? AND year=?"
                        if engine.dialect.name=="sqlite" else
                        "SELECT id FROM payroll_runs WHERE month=%s AND year=%s",
                        (month, year)
                    ).fetchone()
                    if run:
                        run_id = run[0]
                    else:
                        conn.exec_driver_sql(
                            "INSERT INTO payroll_runs(month,year,status,processed_on) VALUES (?,?,?,?)"
                            if engine.dialect.name=="sqlite" else
                            "INSERT INTO payroll_runs(month,year,status,processed_on) VALUES (%s,%s,%s,%s)",
                            (month, year, "Imported", dt.datetime.utcnow())
                        )
                        run_id = conn.exec_driver_sql(
                            "SELECT last_insert_rowid()" if engine.dialect.name=="sqlite" else "SELECT max(id) FROM payroll_runs"
                        ).scalar()

                    # store PDF & insert payslip
                    key = f"uploads/{year}/{month:02d}/payslip_{emp_id}.pdf"
                    put_bytes(key, data)
                    url = presigned_url(key) or key

                    conn.exec_driver_sql(
                        "INSERT INTO payslips(run_id, employee_id, gross, deductions, net, url) VALUES (?,?,?,?,?,?)"
                        if engine.dialect.name=="sqlite" else
                        "INSERT INTO payslips(run_id, employee_id, gross, deductions, net, url) VALUES (%s,%s,%s,%s,%s,%s)",
                        (
                            run_id,
                            emp_id,
                            parsed.get("gross") or 0,
                            (parsed.get("gross") or 0) - (parsed.get("net") or 0),
                            parsed.get("net") or 0,
                            url
                        )
                    )
                st.success("Saved payslip & uploaded PDF")

    # ---- Consolidated ----
    with tab2:
        f2 = st.file_uploader("Upload Consolidated Statement (PDF)", type=["pdf"], key="consol")
        if f2:
            df = parse_consolidated(f2.read())
            st.dataframe(df, use_container_width=True)
            st.download_button("Download as CSV", df.to_csv(index=False).encode(), "consolidated.csv", "text/csv")
            st.info("(Optional) We can add a bulk ‘Write to payslips’ that matches names to employees and inserts records.")

# ---------- EMPLOYEES ----------
elif page == "Employees":
    st.title("Employees")
    df = pd.read_sql(
        "SELECT id, code, first_name, last_name, base_salary, active FROM employees",
        con=engine,
    )
    st.dataframe(df, use_container_width=True)

# ---------- REPORTS ----------
elif page == "Reports":
    st.title("Reports")
    st.info("Add attendance trends, compliance, embeds, etc.")
