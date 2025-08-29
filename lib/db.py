import streamlit as st
from sqlalchemy import create_engine, text
from contextlib import contextmanager

# Use Neon Postgres if provided; fallback to local SQLite for quick testing.
PG_URL = st.secrets.get("postgres", {}).get("url")
DB_URL = PG_URL or "sqlite+pysqlite:///hrms.db"

engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

@contextmanager
def db() :
    with engine.begin() as conn:
        yield conn

def _ddl_postgres():
    return """
    CREATE TABLE IF NOT EXISTS employees(
      id SERIAL PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      first_name TEXT, last_name TEXT,
      base_salary NUMERIC NOT NULL DEFAULT 20000,
      active BOOLEAN NOT NULL DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS attendance_logs(
      id SERIAL PRIMARY KEY,
      employee_id INT REFERENCES employees(id),
      day DATE NOT NULL,
      punch_in TIMESTAMP NULL,
      punch_out TIMESTAMP NULL,
      source TEXT
    );
    CREATE TABLE IF NOT EXISTS payroll_runs(
      id SERIAL PRIMARY KEY,
      month INT NOT NULL, year INT NOT NULL,
      status TEXT, processed_on TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS payslips(
      id SERIAL PRIMARY KEY,
      run_id INT REFERENCES payroll_runs(id),
      employee_id INT REFERENCES employees(id),
      gross NUMERIC, deductions NUMERIC, net NUMERIC,
      url TEXT
    );
    """

def _ddl_sqlite():
    return """
    CREATE TABLE IF NOT EXISTS employees(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT UNIQUE NOT NULL,
      first_name TEXT, last_name TEXT,
      base_salary REAL NOT NULL DEFAULT 20000,
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS attendance_logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      employee_id INTEGER,
      day TEXT NOT NULL,
      punch_in TEXT, punch_out TEXT, source TEXT
    );
    CREATE TABLE IF NOT EXISTS payroll_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      month INTEGER NOT NULL, year INTEGER NOT NULL,
      status TEXT, processed_on TEXT
    );
    CREATE TABLE IF NOT EXISTS payslips(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER, employee_id INTEGER,
      gross REAL, deductions REAL, net REAL, url TEXT
    );
    """

def ensure_schema():
    ddl = _ddl_sqlite() if engine.dialect.name == "sqlite" else _ddl_postgres()
    with db() as conn:
        for stmt in ddl.split(";"):
            s = stmt.strip()
            if s:
                conn.exec_driver_sql(s + ";")

def seed_if_empty():
    with db() as conn:
        try:
            n = conn.exec_driver_sql("SELECT COUNT(*) FROM employees").scalar()
        except Exception:
            ensure_schema()
            n = conn.exec_driver_sql("SELECT COUNT(*) FROM employees").scalar()
        if n == 0:
            conn.exec_driver_sql("""
            INSERT INTO employees (code, first_name, last_name, base_salary) VALUES
            ('E001','Amit','Kumar',24000),
            ('E002','Sara','Iyer',28000),
            ('E003','Rohit','Das',22000),
            ('E004','Neha','Rao',26000),
            ('E005','Vikram','Shah',30000);
            """)
