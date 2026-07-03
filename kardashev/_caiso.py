"""
CAISO (California ISO) raw data client.

Sources (no auth required):
  Curtailment   : https://www.caiso.com/documents/daily-renewable-report-{mon-dd-yyyy}.html
  Fuel mix live : https://www.caiso.com/outlook/current/fuelsource.csv
  Fuel mix hist : https://www.caiso.com/outlook/history/{YYYYMMDD}/fuelsource.csv
  Load / demand : https://www.caiso.com/outlook/current/demand.csv
  OASIS API     : https://oasis.caiso.com/oasisapi/  (LMP, load forecast, interchange)
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from kardashev import _http

_CAISO_TZ = "US/Pacific"

# ---------------------------------------------------------------------------
# Curtailment
# ---------------------------------------------------------------------------

_CURTAIL_VARS = {
    # (solar_cols, wind_cols): JS variable names embedded in the daily HTML report
    "solar": [
        "curt_hr_tot_solar_econ_local_mwh",
        "curt_hr_tot_solar_econ_system_mwh",
        "curt_hr_tot_solar_ss_local_mwh",
        "curt_hr_tot_solar_ss_system_mwh",
        "curt_hr_tot_solar_oi_local_mwh",
        "curt_hr_tot_solar_oi_system_mwh",
    ],
    "wind": [
        "curt_hr_tot_wind_econ_local_mwh",
        "curt_hr_tot_wind_econ_system_mwh",
        "curt_hr_tot_wind_ss_local_mwh",
        "curt_hr_tot_wind_ss_system_mwh",
        "curt_hr_tot_wind_oi_local_mwh",
        "curt_hr_tot_wind_oi_system_mwh",
    ],
}


def _extract_js_array(html: str, var_name: str) -> list[float]:
    pattern = rf'{var_name}\s*=\s*(?:JSON\.parse\(\["?)?\[([^\]]*)\]'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return []
    values = []
    for item in m.group(1).split(","):
        item = item.strip().strip('"')
        if item in ("NA", ""):
            values.append(np.nan)
        else:
            try:
                values.append(float(item))
            except ValueError:
                values.append(np.nan)
    return values


def _fetch_curtailment_html(target: date) -> str:
    slug = target.strftime("%b-%d-%Y").lower()
    for suffix in ("", "-corrected"):
        url = f"https://www.caiso.com/documents/daily-renewable-report-{slug}{suffix}.html"
        try:
            r = _http.get(url)
            return r.text
        except Exception:
            continue
    raise ValueError(f"CAISO: no curtailment report found for {target}")


def get_curtailment(target: date) -> pd.DataFrame:
    """
    Hourly solar + wind curtailment (MWh) for target date.

    Returns DataFrame with columns:
      hour (0-23), solar_mwh, wind_mwh, total_mwh
    """
    html = _fetch_curtailment_html(target)

    def _sum_vars(keys: list[str]) -> list[float]:
        arrays = [_extract_js_array(html, k) for k in keys]
        arrays = [a for a in arrays if a]
        if not arrays:
            return [0.0] * 24
        length = max(len(a) for a in arrays)
        result = [0.0] * length
        for arr in arrays:
            for i, v in enumerate(arr):
                if not np.isnan(v):
                    result[i] += v
        return result

    solar_hourly = _sum_vars(_CURTAIL_VARS["solar"])
    wind_hourly  = _sum_vars(_CURTAIL_VARS["wind"])

    rows = []
    for h, (s, w) in enumerate(zip(solar_hourly, wind_hourly)):
        rows.append({"hour": h, "solar_mwh": s, "wind_mwh": w, "total_mwh": s + w})

    return pd.DataFrame(rows)


def get_curtailment_daily_totals(target: date) -> dict[str, float]:
    """Returns {solar_mwh, wind_mwh, total_mwh} summed for the day."""
    df = get_curtailment(target)
    solar = float(df["solar_mwh"].sum())
    wind  = float(df["wind_mwh"].sum())
    return {"solar_mwh": round(solar, 2), "wind_mwh": round(wind, 2), "total_mwh": round(solar + wind, 2)}


# ---------------------------------------------------------------------------
# Fuel mix  (actual generation by source)
# ---------------------------------------------------------------------------

def get_fuel_mix(target: date | None = None) -> pd.DataFrame:
    """
    5-minute fuel mix for target date (default: today/current).

    Returns DataFrame: timestamp, Solar, Wind, Geothermal, Biomass, Biogas,
      Small_hydro, Coal, Nuclear, Natural_Gas, Large_Hydro, Batteries, Imports, Other
    """
    if target is None:
        url = "https://www.caiso.com/outlook/current/fuelsource.csv"
    else:
        url = f"https://www.caiso.com/outlook/history/{target.strftime('%Y%m%d')}/fuelsource.csv"

    import pytz
    _PT = pytz.timezone("US/Pacific")
    df = _http.get_csv(url)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={"Time": "timestamp"})
    raw_ts = (
        target.isoformat() + " " + df["timestamp"].astype(str)
        if target else df["timestamp"].astype(str)
    )
    # Localize Pacific → UTC so all downstream consumers get tz-aware timestamps
    df["timestamp"] = (
        pd.to_datetime(raw_ts, errors="coerce")
        .dt.tz_localize(_PT, ambiguous="infer", nonexistent="shift_forward")
        .dt.tz_convert("UTC")
    )
    return df


# ---------------------------------------------------------------------------
# Load / demand
# ---------------------------------------------------------------------------

def get_load(target: date | None = None) -> pd.DataFrame:
    """
    5-minute actual + forecast demand.

    Returns DataFrame: timestamp, actual_mw, forecast_mw
    """
    if target is None:
        url = "https://www.caiso.com/outlook/current/demand.csv"
    else:
        url = f"https://www.caiso.com/outlook/history/{target.strftime('%Y%m%d')}/demand.csv"

    df = _http.get_csv(url)
    df.columns = [c.strip() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# OASIS API  (LMP, interchange, ancillary services)
# ---------------------------------------------------------------------------

_OASIS_BASE = "https://oasis.caiso.com/oasisapi/SingleZip"


def _oasis_query(queryname: str, start: date, end: date, extra: dict | None = None) -> pd.DataFrame:
    params = {
        "resultformat": "6",
        "queryname": queryname,
        "startdatetime": start.strftime("%Y%m%dT00:00-0000"),
        "enddatetime": (end + timedelta(days=1)).strftime("%Y%m%dT00:00-0000"),
        "version": "1",
        **(extra or {}),
    }
    r = _http.get(_OASIS_BASE, params=params)
    import io as _io
    import zipfile
    with zipfile.ZipFile(_io.BytesIO(r.content)) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise ValueError(f"CAISO OASIS: no CSV in zip for {queryname}")
        return pd.read_csv(_io.BytesIO(zf.read(csv_names[0])))


def get_lmp_dam(node: str, start: date, end: date) -> pd.DataFrame:
    """Day-ahead LMP for a pricing node."""
    return _oasis_query("PRC_LMP", start, end, {"market_run_id": "DAM", "node": node})


def get_lmp_rtm(node: str, start: date, end: date) -> pd.DataFrame:
    """Real-time 5-min LMP for a pricing node."""
    return _oasis_query("PRC_INTVL_LMP", start, end, {"market_run_id": "RTM", "node": node})


def get_load_forecast(start: date, end: date) -> pd.DataFrame:
    """CAISO system load forecast (day-ahead)."""
    return _oasis_query("SLD_FCST", start, end)


def get_generator_outages(target: date) -> pd.DataFrame:
    """
    Curtailed and non-operational generator report for target date.
    Published daily by CAISO. Returns unit-level outage records for the prior trade date.
    Source: https://www.caiso.com/documents/curtailed-non-operational-generator-prior-trade-date-report-{date}.xlsx
    """
    import io, warnings
    date_str = target.strftime("%Y%m%d")
    url = f"https://www.caiso.com/documents/curtailed-non-operational-generator-prior-trade-date-report-{date_str}.xlsx"
    r = _http.get(url)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        content_io = io.BytesIO(r.content)
        test = pd.read_excel(content_io, usecols="B:M", sheet_name="PREV_DAY_OUTAGES", engine="openpyxl")
        first_col = test[test.columns[0]]
        idx = first_col[first_col == "OUTAGE MRID"].index[0] + 1
        content_io.seek(0)
        df = pd.read_excel(content_io, usecols="B:M", skiprows=idx, sheet_name="PREV_DAY_OUTAGES", engine="openpyxl")
    return df.dropna(axis=1, how="all")


def get_as_prices_dam(target: date) -> pd.DataFrame:
    """
    CAISO Day-Ahead Market ancillary service clearing prices.
    Types: NR (Non-Spin), RD (Reg Down), RU (Reg Up), SR (Spinning),
           RMD (Mileage Down), RMU (Mileage Up).
    Source: OASIS PRC_AS queryname.
    """
    import io
    start = f"{target.strftime('%Y%m%d')}T00:00-0000"
    end   = f"{target.strftime('%Y%m%d')}T23:00-0000"
    url = (
        "https://oasis.caiso.com/oasisapi/SingleZip"
        f"?queryname=PRC_AS&startdatetime={start}&enddatetime={end}"
        "&market_run_id=DAM&anc_type=ALL&anc_region=AS_CAISO&version=12&resultformat=6"
    )
    import zipfile
    r = _http.get(url)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".csv"))
        df = pd.read_csv(io.BytesIO(zf.read(name)))
    return df
