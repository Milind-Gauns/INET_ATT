import re
import pdfplumber
import pandas as pd
from io import BytesIO
from typing import Dict, Any, List

MONTH_MAP = {
    "JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
    "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12
}

def _extract_text(file_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        parts = []
        for p in pdf.pages:
            txt = p.extract_text() or ""
            parts.append(txt)
        return "\n".join(parts)

def parse_payslip(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse single pay slip PDF.
    Returns dict: name, month, year, gross, basic, hra, pf_ee, pf_er, esi_ee, esi_er, lwf_ee, lwf_er, admin_pf, net
    """
    text = _extract_text(file_bytes)

    def num(pat):
        m = re.search(pat, text, re.I)
        if not m: return None
        s = m.group(1).replace(",", "")
        try: return float(s)
        except: return None

    # month/year
    m = re.search(r"PAY SLIP FOR THE MONTH OF\s+([A-Z]{3})\s+(\d{4})", text, re.I)
    month = MONTH_MAP.get(m.group(1).upper(), None) if m else None
    year = int(m.group(2)) if m else None

    # name
    mname = re.search(r"NAME OF THE STAFF:\s*([A-Z][A-Z\s\.\-']+)", text, re.I)
    name = mname.group(1).strip() if mname else None

    # parts
    basic  = num(r"BASIC\s*PAY.*?:\s*([0-9\.,]+)")
    hra    = num(r"H\.?R\.?A.*?:\s*([0-9\.,]+)")
    gross  = num(r"(?:SUB TOTAL|GROSS SALARY|SUB\s*TOTAL.*\[B\])\D+([0-9\.,]+)")
    pf_ee  = num(r"PROVIDENT FUND\s*\(EMPLOYEE\).*?:\s*([0-9\.,]+)")
    pf_er  = num(r"PROVIDENT FUND\s*\(EMPLOYER\).*?:\s*([0-9\.,]+)")
    esi_ee = num(r"E\.?S\.?I\.?C\.?\s*\(EMPLOYEE\).*?:\s*([0-9\.,]+)")
    esi_er = num(r"E\.?S\.?I\.?C\.?\s*\(EMPLOYER\).*?:\s*([0-9\.,]+)")
    lwf_ee = num(r"L\.?W\.?F\.?\s*\(EMPLOYEE\).*?:\s*([0-9\.,]+)")
    lwf_er = num(r"L\.?W\.?F\.?\s*\(EMPLOYER\).*?:\s*([0-9\.,]+)")
    admin  = num(r"ADMIN.*?CHARGES.*?:\s*([0-9\.,]+)")
    net    = num(r"NET\s*(?:PAYABLE|PAY).+?:\s*Rs?\.?\s*([0-9\.,]+)")

    return {
        "name": name, "month": month, "year": year,
        "gross": gross, "basic": basic, "hra": hra,
        "pf_ee": pf_ee, "pf_er": pf_er, "esi_ee": esi_ee, "esi_er": esi_er,
        "lwf_ee": lwf_ee, "lwf_er": lwf_er, "admin_pf": admin, "net": net,
        "raw_text": text,
    }

def parse_consolidated(file_bytes: bytes) -> pd.DataFrame:
    """
    Parses a pipe-separated consolidated salary table.
    Returns DataFrame with columns: name, designation, wage_rate, net
    """
    text = _extract_text(file_bytes)
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("|") and "|" in ln]
    rows: List[dict] = []
    for ln in lines:
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) < 10:
            continue
        if not parts[1].isdigit():  # SR NO guard
            continue
        try:
            name = parts[2]
            desg = parts[5]
            wage_rate = float(parts[6].replace(",", "")) if parts[6] else None
            tail = [p for p in parts[-4:]]  # pick last few numeric cells
            nums = [float(x.replace(",", "")) for x in tail if re.fullmatch(r"[0-9,\.]+", x)]
            net = nums[-1] if nums else None
            rows.append({"name": name, "designation": desg, "wage_rate": wage_rate, "net": net})
        except Exception:
            continue
    return pd.DataFrame(rows)
