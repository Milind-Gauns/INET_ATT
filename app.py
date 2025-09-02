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
from lib.matching import match_consolidated_names  # used on Docs page

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

# ---------- ATTENDANCE (UPDATED) ----------
elif page == "Attendance":
    st.title("Attendance Import (CSV)")
    st.write("CSV header: **code, day, punch_in, punch_out, source**")

    att_file = st.file_uploader("Upload CSV", type=["csv"], key="att_csv")
    map_file = st.file_uploader(
        "Optional: Upload code→name map (CSV) to auto-create missing employees",
        type=["csv"],
        key="map_csv",
        help="Columns required: code,name (e.g., from the employee_code_map.csv I gave you)",
    )
    auto_create = st.checkbox("Create missing employees automatically", value=True)

    if att_file:
        df = pd.read_csv(att_file, dtype={"code": str})
        st.dataframe(df.head(), use_container_width=True)

        # Optional mapping CSV
        code_to_name = {}
        if map_file:
            map_df = pd.read_csv(map_file, dtype={"code": str})
            # normalize keys
            for _, r in map_df.iterrows():
                c = str(r.get("code", "")).strip()
                n = str(r.get("name", "")).strip()
                if c:
                    code_to_name[c] = n

        created, inserted = 0, 0
        with db() as conn:
            # Load all codes once (works on SQLite/Postgres)
            emp_df = pd.read_sql("SELECT id, code, first_name, last_name FROM employees", conn.connection)
            id_by_code = {str(r["code"]).strip(): int(r["id"]) for _, r in emp_df.iterrows()}

            # Figure out missing codes from the CSV
            csv_codes = {str(c).strip() for c in df["code"].tolist()}
            missing = sorted(csv_codes - set(id_by_code.keys()))

            # Create employees for missing codes (optional)
            if missing and auto_create:
                for code in missing:
                    fname = ""
                    lname = ""
                    if code in code_to_name and code_to_name[code]:
                        # split provided full name
                        parts = [p for p in code_to_name[code].replace(".", "").split() if p]
                        if parts:
                            fname = parts[0]
                            lname = " ".join(parts[1:])
                    conn.exec_driver_sql(
                        "INSERT INTO employees(code, first_name, last_name, base_salary, active) VALUES (?, ?, ?, ?, ?)"
                        if engine.dialect.name == "sqlite" else
                        "INSERT INTO employees(code, first_name, last_name, base_salary, active) VALUES (%s,%s,%s,%s,%s)",
                        (code, fname, lname, 0, 1),
                    )
                    created += 1

                # refresh map after inserts
                emp_df = pd.read_sql("SELECT id, code FROM employees", conn.connection)
                id_by_code = {str(r["code"]).strip(): int(r["id"]) for _, r in emp_df.iterrows()}

            # Insert attendance rows
            pmark = "?" if engine.dialect.name == "sqlite" else "%s"
            for _, row in df.iterrows():
                code = str(row["code"]).strip()
                emp_id = id_by_code.get(code)
                if not emp_id:
                    continue  # still missing & not created -> skip
                conn.exec_driver_sql(
                    f"INSERT INTO attendance_logs(employee_id, day, punch_in, punch_out, source) "
                    f"VALUES ({pmark}, {pmark}, {pmark}, {pmark}, {pmark})",
                    (emp_id, str(row["day"]), str(row["punch_in"]), str(row["punch_out"]), str(row.get("source", "csv"))),
                )
                inserted += 1

        if created:
            st.success(f"Created {created} missing employee(s).")
        if inserted:
            st.success(f"Imported {inserted} attendance row(s).")
        if not inserted:
            if not auto_create and missing:
                st.warning(f"No rows imported. {len(missing)} code(s) not found. Upload a mapping CSV or enable 'Create missing employees'.")
            else:
                st.warning("No rows imported. Check that the 'code' values in your CSV match the employees table.")

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

# ---------- DOCS (PDF ingest + bulk write) ----------
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

            # controls for run
            c1, c2 = st.columns(2)
            sel_month = c1.selectbox("Payroll month", list(range(1, 13)), index=date.today().month - 1, key="consol_m")
            sel_year  = c2.number_input("Payroll year", min_value=2000, max_value=2100, value=date.today().year, step=1, key="consol_y")

            # Preview & match
            if st.button("Preview & Match names", type="primary"):
                with db() as conn:
                    emp_df = pd.read_sql("SELECT id, code, first_name, last_name FROM employees", conn.connection)
                matched = match_consolidated_names(df, emp_df, threshold=0.86)
                st.session_state["consol_matched"] = matched
                st.session_state["consol_month"] = int(sel_month)
                st.session_state["consol_year"] = int(sel_year)

            if "consol_matched" in st.session_state:
                matched = st.session_state["consol_matched"]
                st.subheader("Match preview")
                st.dataframe(matched, use_container_width=True)

                um = matched[matched["match_type"] == "unmatched"]
                if not um.empty:
                    st.warning(f"{len(um)} names were not matched. You can download and correct them.")
                    st.download_button(
                        "Download unmatched (CSV)",
                        um.to_csv(index=False).encode(),
                        "unmatched_names.csv",
                        "text/csv",
                    )
                else:
                    st.success("All names matched.")

                if st.button("Write matched to payslips"):
                    month = st.session_state["consol_month"]
                    year  = st.session_state["consol_year"]
                    to_write = matched[matched["emp_id"].notna()].copy()

                    inserted = 0
                    with db() as conn:
                        # ensure run
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

                        pmark = "?" if engine.dialect.name == "sqlite" else "%s"
                        for _, r in to_write.iterrows():
                            emp_id = int(r["emp_id"])
                            net = float(r["net"] or 0.0)
                            gross = net
                            ded = 0.0
                            conn.exec_driver_sql(
                                f"INSERT INTO payslips(run_id, employee_id, gross, deductions, net, url) "
                                f"VALUES ({pmark},{pmark},{pmark},{pmark},{pmark},{pmark})",
                                (run_id, emp_id, gross, ded, net, None)
                            )
                            inserted += 1

                    st.success(f"Wrote {inserted} payslips to run {month:02d}/{year}.")

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
