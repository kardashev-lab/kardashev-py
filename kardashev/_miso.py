"""
MISO (Midcontinent ISO) raw data client.

Sources (no auth required):
  Fuel mix live    : https://public-api.misoenergy.org/api/FuelMix
  Fuel mix today   : https://public-api.misoenergy.org/api/FuelMix/Today
  Fuel mix yest.   : https://public-api.misoenergy.org/api/FuelMix/Yesterday
  Binding constr.  : https://public-api.misoenergy.org/api/BindingConstraints/RealTime
  Interchange      : https://public-api.misoenergy.org/api/Interchange/GetNai/Imports
  Market reports   : https://docs.misoenergy.org/marketreports/{YYYYMMDD}_{report}.{ext}
    Load forecast  : YYYYMMDD_df_al.xls
    DA binding     : YYYYMMDD_da_bc.xls
    RT binding     : YYYYMMDD_rt_bc.xls (also YYYYMMDD_rt_rpe.xls)
    Historical BC  : {YYYY}_da_bc_HIST.csv  /  {YYYY}_rt_bc_HIST.csv
    Historical load: {YYYY}12_dfal_HIST_xls.zip

NOTE: MISO does not expose renewable curtailment via any unauthenticated
public endpoint. Curtailment data requires a registered MISO Data Miner
account (dms.miso.energy).
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

from kardashev import _http

_PUBLIC_API = "https://public-api.misoenergy.org/api"
_MARKET_REPORTS = "https://docs.misoenergy.org/marketreports"


# ---------------------------------------------------------------------------
# Fuel mix  (real-time & recent)
# ---------------------------------------------------------------------------

def _parse_fuel_mix_response(data: dict) -> pd.DataFrame:
    import pytz
    _EST = pytz.timezone("US/Eastern")
    fuel_types = data.get("Fuel", {}).get("Type", [])
    rows = []
    for ft in fuel_types:
        rows.append({
            "timestamp": ft.get("INTERVALEST"),
            "category": ft.get("CATEGORY"),
            "mw": float(ft.get("ACT", 0) or 0),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # INTERVALEST timestamps are Eastern time, convert to UTC-aware
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"])
        .dt.tz_localize(_EST, ambiguous="infer", nonexistent="shift_forward")
        .dt.tz_convert("UTC")
    )
    return df.pivot(index="timestamp", columns="category", values="mw").reset_index()


def get_fuel_mix() -> pd.DataFrame:
    """Current 5-minute fuel mix snapshot."""
    data = _http.get(f"{_PUBLIC_API}/FuelMix").json()
    return _parse_fuel_mix_response(data)


def get_realtime_total_mw() -> dict | None:
    """
    Current system total load from the public FuelMix endpoint.
    Returns {ts: datetime (UTC), mw: float} or None on failure.
    Source: /api/FuelMix, updated every ~5 minutes.
    """
    import datetime as _dt

    import pytz as _pytz
    data = _http.get(f"{_PUBLIC_API}/FuelMix").json()
    total_mw = data.get("TotalMW")
    if total_mw is None:
        return None
    fuel_types = data.get("Fuel", {}).get("Type", [])
    interval_str = fuel_types[0].get("INTERVALEST") if fuel_types else None
    if interval_str:
        est = _pytz.timezone("US/Eastern")
        ts = _dt.datetime.strptime(interval_str, "%Y-%m-%d %I:%M:%S %p")
        ts = est.localize(ts).astimezone(_dt.timezone.utc)
    else:
        ts = _dt.datetime.now(_dt.timezone.utc)
    return {"ts": ts, "mw": float(total_mw)}


def get_fuel_mix_today() -> pd.DataFrame:
    """Today's fuel mix (all intervals so far)."""
    data = _http.get(f"{_PUBLIC_API}/FuelMix/Today").json()
    return _parse_fuel_mix_response(data)


def get_fuel_mix_yesterday() -> pd.DataFrame:
    """Yesterday's complete fuel mix."""
    data = _http.get(f"{_PUBLIC_API}/FuelMix/Yesterday").json()
    return _parse_fuel_mix_response(data)


# ---------------------------------------------------------------------------
# Binding constraints
# ---------------------------------------------------------------------------

def get_binding_constraints_realtime() -> pd.DataFrame:
    """Current real-time binding constraints."""
    data = _http.get(f"{_PUBLIC_API}/BindingConstraints/RealTime").json()
    constraints = data.get("Constraint", [])
    return pd.DataFrame(constraints)


# ---------------------------------------------------------------------------
# Market reports  (historical, daily XLS/CSV)
# ---------------------------------------------------------------------------

def _market_report_url(target: date, suffix: str) -> str:
    return f"{_MARKET_REPORTS}/{target.strftime('%Y%m%d')}_{suffix}"


def get_load_forecast_actual(target: date) -> pd.DataFrame:
    """
    Forecasted and actual load by Local Resource Zone (LRZ).
    Source: YYYYMMDD_df_al.xls
    """
    url = _market_report_url(target, "df_al.xls")
    r = _http.get(url)
    return pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=4)


def get_da_binding_constraints(target: date) -> pd.DataFrame:
    """Day-ahead binding constraints for target date. Source: YYYYMMDD_da_bc.xls"""
    url = _market_report_url(target, "da_bc.xls")
    r = _http.get(url)
    return pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=3)


def get_rt_binding_constraints(target: date) -> pd.DataFrame:
    """Real-time binding constraints for target date. Source: YYYYMMDD_rt_rpe.xls"""
    url = _market_report_url(target, "rt_rpe.xls")
    r = _http.get(url)
    return pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=3)


def get_da_binding_constraints_annual(year: int) -> pd.DataFrame:
    """Full-year day-ahead binding constraints CSV. Source: {YYYY}_da_bc_HIST.csv"""
    url = f"{_MARKET_REPORTS}/{year}_da_bc_HIST.csv"
    return _http.get_csv(url)


def get_rt_binding_constraints_annual(year: int) -> pd.DataFrame:
    """Full-year real-time binding constraints CSV. Source: {YYYY}_rt_bc_HIST.csv"""
    url = f"{_MARKET_REPORTS}/{year}_rt_bc_HIST.csv"
    return _http.get_csv(url)


def get_interconnection_queue() -> pd.DataFrame:
    """MISO generator interconnection queue (public JSON API, no auth)."""
    r = _http.get("https://www.misoenergy.org/api/giqueue/getprojects")
    df = pd.DataFrame(r.json())
    return df.rename(columns={
        "projectNumber": "queue_position",
        "county": "county",
        "state": "state",
        "fuelType": "fuel_type",
        "summerNetMW": "mw",
        "applicationStatus": "status",
        "queueDate": "queue_date",
        "inService": "online_date",
        "withdrawnDate": "withdrawal_date",
    })


def get_generation_outages(target: date) -> pd.DataFrame:
    """
    7-day generation outage forecast by region and type from MISO mom.xlsx OUTAGE sheet.
    Columns: [report_date, region, outage_type, date, mw, is_forecast]
    """
    import io, warnings
    url = f"https://docs.misoenergy.org/marketreports/{target.strftime('%Y%m%d')}_mom.xlsx"
    r = _http.get(url)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        df_raw = pd.read_excel(io.BytesIO(r.content), sheet_name="OUTAGE", header=None, engine="openpyxl")

    # Row 6 is date headers, rows 7-22 are data (North/Central/South/MISO x Derated/Forced/Planned/Unplanned)
    # Find date header row
    date_row = None
    for i, row in df_raw.iterrows():
        vals = [str(v) for v in row if str(v) != "nan"]
        if vals and any("/" in v and "26" in v or "25" in v for v in vals):
            date_row = i
            break
    if date_row is None:
        return pd.DataFrame()

    dates = [v for v in df_raw.iloc[date_row] if str(v) != "nan" and "/" in str(v)]
    rows = []
    for i in range(date_row + 1, len(df_raw)):
        r_data = df_raw.iloc[i]
        non_nan = [str(v) for v in r_data if str(v) != "nan"]
        if len(non_nan) < 3:
            continue
        region = non_nan[0]
        outage_type = non_nan[1]
        if region not in ("North", "Central", "South", "MISO"):
            continue
        values = [v for v in r_data if str(v) != "nan"][2:]
        for j, d_str in enumerate(dates):
            if j >= len(values):
                break
            try:
                d = pd.to_datetime(d_str.replace(" **", "").replace(" *", ""))
                mw = float(str(values[j]).replace(",", ""))
                rows.append({"region": region, "outage_type": outage_type, "date": d, "mw": mw})
            except Exception:
                continue
    return pd.DataFrame(rows)
