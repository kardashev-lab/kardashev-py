"""
SPP (Southwest Power Pool) raw data client.

Sources (no auth required):
  VER curtailments : https://portal.spp.org/file-browser-api/download/ver-curtailments
                     ?path=/{YYYY}/{MM}/VER-Curtailments-{YYYYMMDD}.csv
  Annual archive   : same base, path=/{YYYY}/{YYYY}.zip
  Gen mix rolling  : https://marketplace.spp.org/chart-api/gen-mix-365/asFile
  Fuel mix live    : https://portal.spp.org/file-browser-api/download/{endpoint}
                     ?path=/{prefix}-latestInterval.csv
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

from kardashev import _http

_FILE_BROWSER = "https://portal.spp.org/file-browser-api/download"

_VER_WIND_COLS = [
    "WindRedispatchCurtailments",
    "WindManualCurtailments",
    "WindCurtailedForEnergy",
]
_VER_SOLAR_COLS = [
    "SolarRedispatchCurtailments",
    "SolarManualCurtailments",
    "SolarCurtailedForEnergy",
]
_INTERVAL_H = 5 / 60  # 5-minute rows in MW → MWh


# ---------------------------------------------------------------------------
# VER curtailments
# ---------------------------------------------------------------------------

def get_ver_curtailments_raw(target: date) -> pd.DataFrame:
    """
    5-minute VER curtailment rows for target date.
    Columns include Wind/Solar Redispatch/Manual/CurtailedForEnergy (MW).
    """
    path = f"/{target.strftime('%Y')}/{target.strftime('%m')}/VER-Curtailments-{target.strftime('%Y%m%d')}.csv"
    url = f"{_FILE_BROWSER}/ver-curtailments"
    r = _http.get(url, params={"path": path})
    return pd.read_csv(io.StringIO(r.text))


def get_ver_curtailments_annual_raw(year: int) -> pd.DataFrame:
    """Full-year VER curtailments from the annual ZIP archive."""
    path = f"/{year}/{year}.zip"
    url = f"{_FILE_BROWSER}/ver-curtailments"
    members = _http.get_zip_csv(url, params={"path": path})
    if not members:
        raise ValueError(f"SPP: no CSV in annual zip for {year}")
    dfs = [pd.read_csv(buf) for _, buf in members]
    return pd.concat(dfs, ignore_index=True)


def get_curtailment_daily_totals(target: date) -> dict[str, float]:
    """
    Returns {solar_mwh, wind_mwh, total_mwh} for target date.
    Sums 5-min MW values × (5/60) across all curtailment categories.
    """
    df = get_ver_curtailments_raw(target)
    for col in _VER_WIND_COLS + _VER_SOLAR_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    wind_mwh  = float(df[_VER_WIND_COLS].sum().sum()  * _INTERVAL_H)
    solar_mwh = float(df[_VER_SOLAR_COLS].sum().sum() * _INTERVAL_H)
    return {
        "solar_mwh": round(solar_mwh, 2),
        "wind_mwh":  round(wind_mwh,  2),
        "total_mwh": round(solar_mwh + wind_mwh, 2),
    }


# ---------------------------------------------------------------------------
# Generation mix
# ---------------------------------------------------------------------------

def get_gen_mix_rolling365() -> pd.DataFrame:
    """365-day rolling hourly generation mix by fuel type."""
    url = "https://marketplace.spp.org/chart-api/gen-mix-365/asFile"
    r = _http.get(url)
    return pd.read_csv(io.StringIO(r.text))


def get_gen_mix_latest() -> pd.DataFrame:
    """Latest 5-min generation mix from SPP marketplace (rolling ~2h window)."""
    url = "https://marketplace.spp.org/chart-api/gen-mix/asFile"
    r = _http.get(url)
    return pd.read_csv(io.StringIO(r.text))


def get_gen_mix_365() -> pd.DataFrame:
    """
    365-day rolling 5-min generation mix from SPP marketplace.

    Columns split into Market/Self pairs per fuel. Returns a normalized
    DataFrame matching the get_gen_mix_latest() schema (fuel totals combined).
    """
    url = "https://marketplace.spp.org/chart-api/gen-mix-365/asFile"
    r = _http.get(url)
    raw = pd.read_csv(io.StringIO(r.text))

    fuel_pairs = [
        ("Coal", "Coal"),
        ("Diesel Fuel Oil", "Diesel Fuel Oil"),
        ("Hydro", "Hydro"),
        ("Natural Gas", "Natural Gas"),
        ("Nuclear", "Nuclear"),
        ("Solar", "Solar"),
        ("Waste Disposal Services", "Waste Disposal Services"),
        ("Wind", "Wind"),
        ("Waste Heat", "Waste Heat"),
        ("Other", "Other"),
    ]

    out = pd.DataFrame()
    out["GMT MKT Interval"] = raw["GMT MKT Interval"]
    out["BAA"] = "SPP"
    for fuel, col_name in fuel_pairs:
        market_col = f"{fuel} Market"
        self_col = f"{fuel} Self"
        out[col_name] = (
            pd.to_numeric(raw.get(market_col, 0), errors="coerce").fillna(0)
            + pd.to_numeric(raw.get(self_col, 0), errors="coerce").fillna(0)
        )
    return out


def get_lmp_rtbm_latest() -> pd.DataFrame:
    """Latest 5-min RTBM LMP by settlement location.
    Columns: Interval, GMTIntervalEnd, Settlement Location, Pnode, LMP, MLC, MCC, MEC, BAA
    """
    url = f"{_FILE_BROWSER}/rtbm-lmp-by-location"
    r = _http.get(url, params={"path": "/RTBM-LMP-SL-latestInterval.csv"})
    return pd.read_csv(io.StringIO(r.text))


def get_interconnection_queue() -> pd.DataFrame:
    """SPP generator interconnection queue (public CSV, no auth)."""
    r = _http.get("https://opsportal.spp.org/Studies/GenerateSummaryCSV")
    df = pd.read_csv(io.StringIO(r.text), skiprows=1)
    return df.rename(columns={
        "Generation Interconnection Number": "queue_position",
        " Nearest Town or County": "county",
        "State": "state",
        "Fuel Type": "fuel_type",
        "Capacity": "mw",
        "Status": "status",
        "Request Received": "queue_date",
        "Commercial Operation Date": "online_date",
        "Date Withdrawn": "withdrawal_date",
    })


# ---------------------------------------------------------------------------
# Load / demand
# ---------------------------------------------------------------------------

def get_load_forecast(target: date) -> pd.DataFrame:
    """Short-term load forecast vs actual for target date."""
    path = f"/{target.strftime('%Y')}/{target.strftime('%m')}/STLF-Vs-Actual-{target.strftime('%Y%m%d')}.csv"
    url = f"{_FILE_BROWSER}/stlf-vs-actual"
    r = _http.get(url, params={"path": path})
    return pd.read_csv(io.StringIO(r.text))
