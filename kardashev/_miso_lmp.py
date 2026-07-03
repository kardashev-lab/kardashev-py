"""
MISO LMP client for RT and day-ahead prices. No auth required.

RT endpoint: public-api.misoenergy.org (JSON)
DA endpoint: docs.misoenergy.org market reports (CSV)
"""
from __future__ import annotations

import io
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from kardashev import _http

_RT_URL = "https://public-api.misoenergy.org/api/MarketPricing/GetLmpConsolidatedTable"
_DA_URL_TEMPLATE = "https://docs.misoenergy.org/marketreports/{date}_da_exante_lmp.csv"

# Hub node IDs, exact strings as returned by the API
_HUB_KEYWORDS = {
    "MISO.HUB",
    "INDIANA.HUB",
    "ILLINOIS.HUB",
    "MICHIGAN.HUB",
    "MINNESOTA.HUB",
    "ARKANSAS.HUB",
}


def get_rt_lmp() -> list[dict]:
    """
    Fetch current real-time 5-min LMP from MISO public API.

    Response shape (public-api.misoenergy.org):
      {"LMPData": {"RefId": "25-Jun-2026 - Interval 02:25 EST",
                   "FiveMinLMP": {"HourAndMin": "02:25",
                                  "PricingNode": [{"name": ..., "LMP": ..., "MLC": ..., "MCC": ...}]}}}
    """
    resp = _http.get(_RT_URL, headers={"Accept": "application/json"})
    data = resp.json()

    lmp_data = data.get("LMPData", {})
    raw_ts = lmp_data.get("RefId", "")
    ts = _parse_ts(raw_ts) or datetime.now(timezone.utc).replace(second=0, microsecond=0)

    nodes = lmp_data.get("FiveMinLMP", {}).get("PricingNode", [])

    rows: list[dict] = []
    for item in nodes:
        name = str(item.get("name", ""))
        if "HUB" not in name.upper():
            continue
        node_id = name.upper().replace(" ", ".")
        rows.append({
            "ts":         ts,
            "iso":        "MISO",
            "node_id":    node_id,
            "node_name":  name,
            "market":     "RT",
            "lmp":        _float(item.get("LMP")),
            "energy":     None,
            "congestion": _float(item.get("MCC")),
            "loss":       _float(item.get("MLC")),
        })

    return rows


def get_da_lmp(target: date) -> list[dict]:
    """
    Fetch day-ahead ex-ante LMP CSV for a given date.

    CSV columns (typical): Node, Type, Value, HourEnding columns (HE1..HE24)
    Returns list of dicts compatible with upsert_lmp().
    """
    date_str = target.strftime("%Y%m%d")
    url = _DA_URL_TEMPLATE.format(date=date_str)

    try:
        r = _http.get(url)
        # MISO DA CSVs have a 4-line preamble before the actual header row
        df = pd.read_csv(io.StringIO(r.text), skiprows=4)
    except Exception:
        import logging
        logging.getLogger(__name__).warning("MISO DA LMP: no CSV for %s", date_str)
        return []

    # Normalise column names
    df.columns = [str(c).strip() for c in df.columns]

    # Find node column (usually "Node" or "PNODE")
    node_col = next((c for c in df.columns if c.upper() in ("NODE", "PNODE", "NAME")), None)
    if node_col is None:
        return []

    # Find type column to filter for LMP rows
    type_col = next((c for c in df.columns if c.upper() in ("TYPE", "LMPTYPE", "VALUE TYPE")), None)

    # Hour-ending columns: "HE 1".."HE 24" (space between HE and digit)
    he_cols = [c for c in df.columns if c.upper().startswith("HE") and c[2:].strip().isdigit()]
    if not he_cols:
        return []

    # Filter to MISO aggregate hub nodes (names ending in .HUB e.g. ILLINOIS.HUB)
    df = df[df[node_col].str.upper().str.contains(r"\.HUB$", na=False, regex=True)]

    rows: list[dict] = []
    for _, row in df.iterrows():
        node_id   = str(row[node_col]).strip().upper()
        node_name = str(row[node_col]).strip()

        for he_col in he_cols:
            hour = int(he_col.upper().replace("HE", "")) - 1  # HE1 = hour 0
            ts = datetime(target.year, target.month, target.day, hour,
                          tzinfo=timezone.utc)
            try:
                lmp = float(row[he_col])
            except (TypeError, ValueError):
                continue
            rows.append({
                "ts":         ts,
                "iso":        "MISO",
                "node_id":    node_id,
                "node_name":  node_name,
                "market":     "DA",
                "lmp":        lmp,
                "energy":     None,
                "congestion": None,
                "loss":       None,
            })

    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    s = str(raw)
    # "25-Jun-2026 - Interval 02:25 EST"
    import re as _re
    m = _re.search(r"(\d{1,2}-\w{3}-\d{4})\s*-\s*Interval\s+(\d{2}:\d{2})", s)
    if m:
        try:
            import pytz
            eastern = pytz.timezone("US/Eastern")
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d-%b-%Y %H:%M")
            return eastern.localize(dt).astimezone(timezone.utc)
        except Exception:
            pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M"):
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
