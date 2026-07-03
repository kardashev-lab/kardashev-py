"""Smoke tests using pytest-httpx to mock the API."""
from datetime import date

from pytest_httpx import HTTPXMock

from kardashev import Client

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

BASE = "https://data.kardashevlabs.org"

FUEL_MIX_RESPONSE = [
    {"ts": "2024-01-01T00:00:00Z", "iso": "CAISO", "fuel_type": "solar", "mw": 5000.0}
]


def _first(result, col: str):
    if _PANDAS:
        return result.iloc[0][col]
    return result[0][col]


def _len(result) -> int:
    return len(result)


def test_fuel_mix(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE}/fuel-mix?iso=CAISO&hours=24&limit=2000",
        json=FUEL_MIX_RESPONSE,
    )
    with Client() as kl:
        result = kl.fuel_mix("CAISO")
    assert _len(result) == 1
    assert _first(result, "iso") == "CAISO"


def test_fuel_mix_with_dates(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE}/fuel-mix?iso=CAISO&start=2024-01-01&end=2024-01-07&hours=24&limit=2000",
        json=FUEL_MIX_RESPONSE,
    )
    with Client() as kl:
        result = kl.fuel_mix(
            "CAISO",
            start=date(2024, 1, 1),
            end=date(2024, 1, 7),
        )
    assert _len(result) == 1


def test_carbon_latest(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE}/carbon/latest",
        json=[{"iso": "CAISO", "ts": "2024-01-01T00:00:00Z", "lbs_co2_per_mwh": 450.0, "total_mw": 30000.0, "pct_clean": 60.0}],
    )
    with Client() as kl:
        result = kl.carbon_latest()
    assert _first(result, "iso") == "CAISO"


def test_iso_uppercased(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE}/fuel-mix?iso=ERCOT&hours=24&limit=2000",
        json=[],
    )
    with Client() as kl:
        kl.fuel_mix("ercot")
