from sqlalchemy import text
from .pdf import build_payslip_pdf
from .storage import put_bytes, presigned_url

def _param(engine):
    return "?" if engine.dialect.name == "sqlite" else "%s"

def run_payroll(engine, month: int, year: int):
    p = _param(engine)
    with engine.begin() as conn:
        # create run
        conn.exec_driver_sql(f"INSERT INTO payroll_runs(month,year,status) VALUES ({p},{p},{p})",
                             (month, year, "Processing"))
        run_id = conn.exec_driver_sql("SELECT max(id) FROM payroll_runs").scalar()

        # process each employee
        rows = conn.exec_driver_sql("SELECT id, code, first_name, last_name, base_salary FROM employees WHERE active=TRUE" if engine.dialect.name!="sqlite"
                                    else "SELECT id, code, first_name, last_name, base_salary FROM employees WHERE active=1").fetchall()
        results = []
        for r in rows:
            basic = float(r.base_salary)
            pf = round(basic * 0.12, 2)  # demo PF
            tds = 0.0                    # demo TDS
            gross = basic
            deductions = pf + tds
            net = gross - deductions

            pdf = build_payslip_pdf(f"{r.first_name} {r.last_name}", r.code, month, year, gross, deductions, net)
            key = f"{year}/{month:02d}/payslip_{r.code}.pdf"
            stored = put_bytes(key, pdf)
            url = presigned_url(key) or stored

            conn.exec_driver_sql(
                f"INSERT INTO payslips(run_id, employee_id, gross, deductions, net, url) VALUES ({p},{p},{p},{p},{p},{p})",
                (run_id, r.id, gross, deductions, net, url)
            )
            results.append({"code": r.code, "name": f"{r.first_name} {r.last_name}", "gross": gross, "deductions": deductions, "net": net, "url": url})

        conn.exec_driver_sql("UPDATE payroll_runs SET status='Completed' WHERE id=" + str(run_id))
        return results
