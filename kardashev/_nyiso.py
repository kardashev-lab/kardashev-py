"""
NYISO data client. All endpoints are public CSV at mis.nyiso.com/public/csv/.

Daily files are only kept for ~11 days. For older data, use the monthly ZIP
archives (same base URL but first-of-month filename).
"""
from __future__ import annotations

import io
import zipfile
from datetime import date

import pandas as pd
import requests

from kardashev import _http

_BASE = "https://mis.nyiso.com/public/csv"


def _csv(dataset: str, target: date, suffix: str = "") -> pd.DataFrame:
    filename = f"{target.strftime('%Y%m%d')}{suffix or dataset}.csv"
    url = f"{_BASE}/{dataset}/{filename}"
    r = _http.get(url)
    return pd.read_csv(io.StringIO(r.text))


def _csv_with_zip_fallback(dataset: str, target: date, suffix: str) -> pd.DataFrame:
    """Try daily CSV; on 404 fall back to monthly ZIP archive."""
    try:
        return _csv(dataset, target, suffix)
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise
    # Monthly ZIP: named {YYYYMM}01{suffix}_csv.zip, contains {YYYYMMDD}{suffix}.csv
    zip_url = f"{_BASE}/{dataset}/{target.strftime('%Y%m')}01{suffix}_csv.zip"
    r = _http.get(zip_url)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        fname = f"{target.strftime('%Y%m%d')}{suffix}.csv"
        if fname not in zf.namelist():
            raise FileNotFoundError(f"NYISO: {fname} not in monthly ZIP")
        return pd.read_csv(io.BytesIO(zf.read(fname)))


# ---------------------------------------------------------------------------
# Fuel mix
# ---------------------------------------------------------------------------

def get_fuel_mix(target: date) -> pd.DataFrame:
    """
    5-minute real-time fuel mix by category for target date.
    Columns: Time Stamp, Time Zone, Fuel Category, Gen MW
    Falls back to monthly ZIP for dates older than ~11 days.
    """
    return _csv_with_zip_fallback("rtfuelmix", target, "rtfuelmix")


def get_fuel_mix_day_ahead(target: date) -> pd.DataFrame:
    """Day-ahead fuel mix by category."""
    return _csv("damlbmp", target, "damlbmp_zone")


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def get_load(target: date) -> pd.DataFrame:
    """
    5-minute actual load by zone for target date.
    Columns: Time Stamp, Time Zone, Name, PTID, Load
    Falls back to monthly ZIP for dates older than ~11 days.
    """
    return _csv_with_zip_fallback("pal", target, "pal")


def get_load_forecast(target: date) -> pd.DataFrame:
    """Day-ahead load forecast by zone."""
    return _csv("isolf", target, "isolf")


# ---------------------------------------------------------------------------
# LMP prices
# ---------------------------------------------------------------------------

def get_lmp_realtime_zone(target: date) -> pd.DataFrame:
    """Real-time 5-min LMP by zone."""
    return _csv("realtime", target, "realtime_zone")


def get_lmp_dam_zone(target: date) -> pd.DataFrame:
    """Day-ahead hourly LMP by zone."""
    return _csv("damlbmp", target, "damlbmp_zone")


# ---------------------------------------------------------------------------
# Renewables
# ---------------------------------------------------------------------------

def get_btm_solar(target: date) -> pd.DataFrame:
    """Behind-the-meter solar actual vs forecast (hourly)."""
    return _csv("btmactualforecast", target, "btmactualforecast")


# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

def get_generators() -> pd.DataFrame:
    """Full generator reference list with fuel type, zone, capacity."""
    url = f"{_BASE}/generator/generator.csv"
    return _http.get_csv(url)


def get_interconnection_queue() -> pd.DataFrame:
    """NYISO interconnection queue."""
    url = f"{_BASE}/interconnections/interconnections.csv"
    return _http.get_csv(url)
