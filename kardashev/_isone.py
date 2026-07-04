"""
ISONE (ISO New England) raw data client.

Primary source: EIA Grid Monitor API (free key required):
  https://www.eia.gov/opendata/register.php
  Set EIA_API_KEY environment variable.
  Respondent code: ISNE

Fallback: ISONE transform/csv endpoints now require an authenticated
session (403 without login cookies) so they are no longer used for
fuel mix or load. LMP and queue endpoints are kept as-is since they
may work with future auth support.

EIA fuel-type data endpoint:
  GET https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/
      ?api_key=KEY
      &facets[respondent][]=ISNE
      &start=2026-06-01T00
      &end=2026-06-01T23
      &frequency=hourly
      &data[]=value
      &sort[0][column]=period
      &sort[0][direction]=asc
      &length=5000
"""
from __future__ import annotations

import io
from datetime import date
from typing import Any

import pandas as pd

from kardashev import _http
from kardashev import _eia

_ISONE_RESPONDENT = "ISNE"

_BASE_TRANSFORM = "https://www.iso-ne.com/transform/csv"

_ISONE_HEADERS = {
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.iso-ne.com/isoexpress/",
    "Origin": "https://www.iso-ne.com",
}


# ---------------------------------------------------------------------------
# Fuel mix (via EIA)
# ---------------------------------------------------------------------------

def get_fuel_mix(target: date) -> pd.DataFrame:
    """
    Hourly fuel mix for ISONE on target date via EIA Grid Monitor API.
    Columns: period (UTC hour), fueltype, value (MW), respondent
    Requires EIA_API_KEY env var.
    """
    rows = _eia.get_fuel_mix(_ISONE_RESPONDENT, target)
    return pd.DataFrame(rows)


def get_fuel_mix_range(start: date, end: date) -> pd.DataFrame:
    """Hourly fuel mix for ISONE over a date range via EIA."""
    rows = _eia.paginate("fuel-type-data/data", {
        "facets[respondent][]": _ISONE_RESPONDENT,
        "start": f"{start.strftime('%Y-%m-%d')}T00",
        "end":   f"{end.strftime('%Y-%m-%d')}T23",
        "frequency": "hourly",
        "data[]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Load (via EIA)
# ---------------------------------------------------------------------------

def get_load(start: date, end: date | None = None) -> pd.DataFrame:
    """
    Hourly actual demand for ISONE via EIA Grid Monitor.
    Columns: period (UTC hour), value (MWh), respondent
    Requires EIA_API_KEY env var.
    """
    end = end or start
    rows = _eia.paginate("region-data/data", {
        "facets[respondent][]": _ISONE_RESPONDENT,
        "facets[type][]": "D",
        "start": f"{start.strftime('%Y-%m-%d')}T00",
        "end":   f"{end.strftime('%Y-%m-%d')}T23",
        "frequency": "hourly",
        "data[]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    })
    return pd.DataFrame(rows)


def get_load_forecast(start: date, end: date | None = None) -> pd.DataFrame:
    """Hourly day-ahead load forecast for ISONE via EIA."""
    end = end or start
    rows = _eia.paginate("region-data/data", {
        "facets[respondent][]": _ISONE_RESPONDENT,
        "facets[type][]": "DF",
        "start": f"{start.strftime('%Y-%m-%d')}T00",
        "end":   f"{end.strftime('%Y-%m-%d')}T23",
        "frequency": "hourly",
        "data[]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# LMP prices (ISONE transform CSV, may require auth)
# ---------------------------------------------------------------------------

def _isone_session():
    return _http.session(extra_headers=_ISONE_HEADERS)


def _transform_csv(endpoint: str, params: dict[str, Any]) -> pd.DataFrame:
    url = f"{_BASE_TRANSFORM}/{endpoint}"
    s = _isone_session()
    r = s.get(url, params=params, timeout=60)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def _date_params(start: date, end: date | None = None) -> dict:
    p = {"start": start.strftime("%Y%m%d")}
    if end:
        p["end"] = end.strftime("%Y%m%d")
    return p


def get_lmp_fiveminute(location: str | int, start: date, end: date | None = None) -> pd.DataFrame:
    """5-minute real-time LMP for a location node (requires ISONE session)."""
    params = _date_params(start, end or start)
    params["location"] = str(location)
    return _transform_csv("fiveminutelmp", params)


def get_lmp_hourly(location: str | int, start: date, end: date | None = None) -> pd.DataFrame:
    """Hourly day-ahead LMP for a location node (requires ISONE session)."""
    params = _date_params(start, end or start)
    params["location"] = str(location)
    return _transform_csv("hourlylmp", params)


# ---------------------------------------------------------------------------
# Static / reference data
# ---------------------------------------------------------------------------

def get_interconnection_queue() -> pd.DataFrame:
    """ISONE interconnection queue.

    The old transform/csv endpoint (used by other functions in this file)
    returns 404 for this dataset now. ISO-NE publishes the live public
    queue as an HTML table on the IRTT tool instead.
    """
    r = _http.get("https://irtt.iso-ne.com/reports/external")
    df = pd.read_html(io.StringIO(r.text), attrs={"id": "publicqueue"})[0]
    return df.rename(columns={
        "QP": "Queue No",
        "Alternative Name": "Project Name",
        "County": "Town",
        "ST": "State",
        "Summer MW": "Summer Capacity (MW)",
        "Requested": "Queue Date",
        "Op Date": "Proposed In-Service",
    })


def get_capacity_market() -> pd.DataFrame:
    """Forward Capacity Market results (requires ISONE session)."""
    return _transform_csv("capacitymarket", {})


# ---------------------------------------------------------------------------
# WebSocket real-time  (generator)
# ---------------------------------------------------------------------------

def make_websocket_subscribe_message(topics: list[str] | None = None) -> dict:
    """
    Returns the JSON payload to subscribe to ISONE real-time WebSocket topics.

    Usage (requires websockets library):
        import asyncio, json, websockets
        async def stream():
            async with websockets.connect("wss://www.iso-ne.com/ws/wsclient") as ws:
                await ws.send(json.dumps(make_websocket_subscribe_message()))
                async for msg in ws:
                    data = json.loads(msg)
                    print(data)
        asyncio.run(stream())

    Default topics: gen_mix_rt, load_rt
    """
    if topics is None:
        topics = ["gen_mix_rt", "load_rt"]
    return {"type": "subscribe", "topics": topics}
