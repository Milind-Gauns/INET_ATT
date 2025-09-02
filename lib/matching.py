import re
from difflib import SequenceMatcher
from typing import List, Tuple
import pandas as pd

def _norm(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.upper()
    s = re.sub(r"[^A-Z\s]", " ", s)       # drop punctuation
    s = re.sub(r"\s+", " ", s).strip()    # collapse spaces
    return s

def _full(first: str, last: str) -> str:
    return _norm(f"{first} {last}")

def best_match(needle: str, haystack: List[str], threshold: float = 0.86) -> Tuple[str, float]:
    """
    Return (best_value, score) for the closest string in haystack to needle.
    Score in [0..1]. If best score < threshold, returns ("", 0.0).
    """
    best, score = "", 0.0
    for h in haystack:
        r = SequenceMatcher(None, needle, h).ratio()
        if r > score:
            best, score = h, r
    if score >= threshold:
        return best, score
    return "", 0.0

def match_consolidated_names(
    df_consol: pd.DataFrame, df_employees: pd.DataFrame, threshold: float = 0.86
) -> pd.DataFrame:
    """
    Inputs:
      df_consol: columns ["name", "designation", "wage_rate", "net"]
      df_employees: columns ["id","code","first_name","last_name"]

    Output DataFrame with:
      name, designation, wage_rate, net, emp_id, emp_name, match_type, score
    """
    df = df_consol.copy()
    df_employees = df_employees.fillna("")
    df_employees["full_norm"] = df_employees.apply(
        lambda r: _full(r["first_name"], r["last_name"]), axis=1
    )
    pool = df_employees["full_norm"].tolist()

    out_rows = []
    for _, row in df.iterrows():
        raw_name = str(row.get("name", ""))
        needle = _norm(raw_name)

        # exact on full
        exact = df_employees[df_employees["full_norm"] == needle]
        if not exact.empty:
            r = exact.iloc[0]
            out_rows.append({
                "name": raw_name,
                "designation": row.get("designation"),
                "wage_rate": row.get("wage_rate"),
                "net": row.get("net"),
                "emp_id": int(r["id"]),
                "emp_name": f"{r['first_name']} {r['last_name']}".strip(),
                "match_type": "exact",
                "score": 1.0
            })
            continue

        # fuzzy on full
        best, score = best_match(needle, pool, threshold)
        if best:
            r = df_employees[df_employees["full_norm"] == best].iloc[0]
            out_rows.append({
                "name": raw_name,
                "designation": row.get("designation"),
                "wage_rate": row.get("wage_rate"),
                "net": row.get("net"),
                "emp_id": int(r["id"]),
                "emp_name": f"{r['first_name']} {r['last_name']}".strip(),
                "match_type": "fuzzy",
                "score": round(float(score), 4)
            })
        else:
            out_rows.append({
                "name": raw_name,
                "designation": row.get("designation"),
                "wage_rate": row.get("wage_rate"),
                "net": row.get("net"),
                "emp_id": None,
                "emp_name": "",
                "match_type": "unmatched",
                "score": 0.0
            })
    return pd.DataFrame(out_rows)
