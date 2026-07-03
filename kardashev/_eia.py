"""
EIA Grid Monitor API client. Works for any US balancing authority.

Requires EIA_API_KEY env var (free at https://www.eia.gov/opendata/register.php).

Common BA codes: CISO, ERCO, PJM, MISO, NYIS, ISNE, SWPP, BPAT, TVA, SOCO, FPL, DUK, SRP, PSCO, PACE
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from kardashev import _http

_BASE = "https://api.eia.gov/v2/electricity/rto"


def api_key() -> str:
    key = os.environ.get("EIA_API_KEY", "")
    if not key:
        raise RuntimeError(
            "EIA_API_KEY not set. Register free at https://www.eia.gov/opendata/register.php"
        )
    return key


def paginate(endpoint: str, params: dict[str, Any]) -> list[dict]:
    """Fetch all pages from an EIA v2 electricity/rto endpoint."""
    params = dict(params)
    params["api_key"] = api_key()
    url = f"{_BASE}/{endpoint}"
    rows: list[dict] = []
    offset = 0
    length = int(params.get("length", 5000))
    while True:
        params["offset"] = offset
        r = _http.get(url, params=params)
        body = r.json()
        data = body.get("response", {}).get("data", [])
        rows.extend(data)
        total = int(body.get("response", {}).get("total", len(rows)))
        if len(rows) >= total or not data:
            break
        offset += length
    return rows


def get_demand(respondent: str, hours: int = 48) -> list[dict]:
    """
    Hourly actual demand (type=D) for any EIA respondent, newest first.
    Returns list of {period, respondent, type, value} dicts.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours + 2)
    return paginate("region-data/data", {
        "facets[respondent][]": respondent,
        "facets[type][]": "D",
        "start": start.strftime("%Y-%m-%dT%H"),
        "end":   now.strftime("%Y-%m-%dT%H"),
        "frequency": "hourly",
        "data[]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": hours + 5,
    })


def get_demand_df(respondent: str, hours: int = 48) -> pd.DataFrame:
    """Demand data as a DataFrame with columns: period, value."""
    rows = get_demand(respondent, hours)
    return pd.DataFrame(rows)


def get_fuel_mix(respondent: str, target: date) -> list[dict]:
    """Hourly fuel-type generation for a respondent on target date."""
    return paginate("fuel-type-data/data", {
        "facets[respondent][]": respondent,
        "start": f"{target.strftime('%Y-%m-%d')}T00",
        "end":   f"{target.strftime('%Y-%m-%d')}T23",
        "frequency": "hourly",
        "data[]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    })


# ---------------------------------------------------------------------------
# EIA-923: Monthly plant-level generation (aggregated by state + fuel type)
# Endpoint: electricity/electric-power-operational-data
# ---------------------------------------------------------------------------

def get_monthly_generation(months: int = 12) -> list[dict]:
    """
    Monthly net generation (MWh) by state and fuel type.
    Aggregated from EIA-923. Returns newest `months` of data.
    """
    now = datetime.now(timezone.utc)
    # EIA period format: "YYYY-MM"
    start_y = now.year - (months // 12 + 1)
    params = {
        "api_key": api_key(),
        "frequency": "monthly",
        "data[]": "generation",
        "facets[location][]": ["US"],  # national total; can also filter by state
        "start": f"{start_y}-01",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 5000,
    }
    url = "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/"
    r = _http.get(url, params=params)
    return r.json().get("response", {}).get("data", [])


# ---------------------------------------------------------------------------
# EIA-860: Annual generator capacity
# Endpoint: electricity/operating-generator-capacity
# ---------------------------------------------------------------------------

def get_generator_capacity(year: int | None = None) -> list[dict]:
    """
    Annual installed generator capacity (MW) by state, technology, and fuel type.
    Defaults to most recent available year.
    """
    params: dict = {
        "api_key": api_key(),
        "frequency": "annual",
        "data[]": "nameplate-capacity-mw",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 5000,
    }
    if year:
        params["start"] = str(year)
        params["end"]   = str(year)
    url = "https://api.eia.gov/v2/electricity/operating-generator-capacity/data/"
    r = _http.get(url, params=params)
    return r.json().get("response", {}).get("data", [])


# ---------------------------------------------------------------------------
# EIA-861: Monthly retail electricity prices and sales
# Endpoint: electricity/retail-sales
# ---------------------------------------------------------------------------

def get_interchange(respondent: str, hours: int = 24) -> list[dict]:
    """
    Hourly net interchange between a BA and its neighbors.
    Type TI = total interchange; type WHL = wheeling.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours + 2)
    return paginate("interchange-data/data", {
        "facets[respondent][]": respondent,
        "facets[type][]": "TI",
        "start": start.strftime("%Y-%m-%dT%H"),
        "end":   now.strftime("%Y-%m-%dT%H"),
        "frequency": "hourly",
        "data[]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": hours + 5,
    })


def get_retail_prices(months: int = 24) -> list[dict]:
    """
    Monthly retail electricity prices (cents/kWh) and sales (MWh) by state and sector.
    Sectors: residential (RES), commercial (COM), industrial (IND), all (ALL).
    """
    now = datetime.now(timezone.utc)
    start_y = now.year - (months // 12 + 2)
    params = {
        "api_key": api_key(),
        "frequency": "monthly",
        "data[]": ["price", "sales", "customers"],
        "start": f"{start_y}-01",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 5000,
    }
    url = "https://api.eia.gov/v2/electricity/retail-sales/data/"
    r = _http.get(url, params=params)
    return r.json().get("response", {}).get("data", [])
