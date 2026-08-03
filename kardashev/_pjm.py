"""
PJM Interconnection data client.

Primary path (2026-08+): api.pjm.com with the public DataMiner2 UI
subscription key (https://dataminer2.pjm.com/config/settings.json),
overridable via PJM_API_KEY. Used for 5-min instantaneous load and
unverified 5-min RT LMP.

Legacy path: DataMiner2 CSV feeds (rt_hrl_lmps / da_hrl_lmps) required
PJM_USERNAME/PJM_PASSWORD and are DEAD as of 2026-07 — they return SPA HTML.
Kept below only for reference / if PJM restores them.
"""
from __future__ import annotations

import io
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests

from kardashev import _http

_DM2_BASE = "https://dataminer2.pjm.com/feed"
_SETTINGS_URL = "https://dataminer2.pjm.com/config/settings.json"
_API_BASE = "https://api.pjm.com/api/v1"
_KEY_CACHE: str | None = None

# Hubs + zones for RT LMP (not full bus set).
PJM_RT_PNODES: tuple[str, ...] = (
    "51217", "51287", "51288", "4669664", "33092311", "33092313", "33092315",
    "34497125", "34497127", "34497151", "35010337", "116013751",
    "1", "51291", "8445784", "8394954", "51292", "33092371", "34508503",
    "51293", "51295", "51296", "51297", "51300", "51298", "51299", "51301",
    "7633629",
)


def _api_key() -> str:
    global _KEY_CACHE
    env = os.environ.get("PJM_API_KEY", "").strip()
    if env:
        return env
    if _KEY_CACHE:
        return _KEY_CACHE
    r = _http.get(_SETTINGS_URL)
    key = r.json().get("subscriptionKey") or ""
    if not key:
        raise RuntimeError("PJM subscriptionKey missing from settings.json")
    _KEY_CACHE = key
    return key


def _api_get(path: str, params: dict[str, Any]) -> list[dict]:
    r = requests.get(
        f"{_API_BASE}/{path}",
        params=params,
        headers={
            "Ocp-Apim-Subscription-Key": _api_key(),
            "Accept": "application/json",
            "User-Agent": "kardashev/0.3.2",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("items") if isinstance(data, dict) else data
    return list(items or [])


def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def get_inst_load(
    area: str = "PJM RTO",
    *,
    datetime_beginning_ept: str = "LastHour",
    row_count: int = 100,
) -> list[dict]:
    """5-min instantaneous load. Returns [{ts UTC, area, mw}]."""
    items = _api_get(
        "inst_load",
        {
            "rowCount": row_count,
            "startRow": 1,
            "datetime_beginning_ept": datetime_beginning_ept,
            "area": area,
            "fields": "datetime_beginning_utc,area,instantaneous_load",
        },
    )
    out: list[dict] = []
    for row in items:
        try:
            mw = row.get("instantaneous_load")
            ts_raw = row.get("datetime_beginning_utc")
            if mw is None or not ts_raw:
                continue
            out.append({"ts": _parse_ts(str(ts_raw)), "area": row.get("area") or area, "mw": float(mw)})
        except Exception:
            continue
    out.sort(key=lambda r: r["ts"])
    return out


def get_lmp_rt_5min(
    pnode_ids: tuple[str, ...] | list[str] | None = None,
    *,
    datetime_beginning_ept: str = "LastHour",
    row_count: int = 2000,
) -> list[dict]:
    """Unverified 5-min RT LMP for selected hubs/zones."""
    ids = list(pnode_ids) if pnode_ids is not None else list(PJM_RT_PNODES)
    items = _api_get(
        "rt_unverified_fivemin_lmps",
        {
            "rowCount": row_count,
            "startRow": 1,
            "datetime_beginning_ept": datetime_beginning_ept,
            "pnode_id": ";".join(ids),
        },
    )
    out: list[dict] = []
    for row in items:
        try:
            lmp = row.get("total_lmp_rt")
            ts_raw = row.get("datetime_beginning_utc")
            if lmp is None or not ts_raw:
                continue
            out.append({
                "ts": _parse_ts(str(ts_raw)),
                "node_id": str(row.get("pnode_id", "")),
                "node_name": row.get("pnode_name"),
                "node_type": row.get("type"),
                "lmp": float(lmp),
                "congestion": float(row.get("congestion_price_rt") or 0),
                "loss": float(row.get("marginal_loss_price_rt") or 0),
                "energy": None,
            })
        except Exception:
            continue
    return out


def _creds() -> tuple[str, str]:
    u = os.environ.get("PJM_USERNAME", "")
    p = os.environ.get("PJM_PASSWORD", "")
    if not u or not p:
        raise EnvironmentError("PJM_USERNAME and PJM_PASSWORD env vars required")
    return u, p


def _dt_str(d: date) -> str:
    return f"{d.strftime('%Y-%m-%d')} 00:00"


def _dm2_fetch(feed: str, start: date, end: date, node_type: str | None = None) -> pd.DataFrame:
    """Fetch a DataMiner2 feed as CSV, auto-paginating up to 200k rows.

    DEPRECATED: feeds return SPA HTML as of 2026-07. Prefer get_lmp_rt_5min /
    get_inst_load against api.pjm.com.
    """
    u, p = _creds()
    rows_per_page = 50_000
    frames: list[pd.DataFrame] = []
    start_row = 1

    while True:
        params: dict = {
            "startrow": start_row,
            "numrows": rows_per_page,
            "username": u,
            "password": p,
            "starttime": _dt_str(start),
            "endtime": _dt_str(end + timedelta(days=1)),
        }
        if node_type:
            params["type"] = node_type

        r = _http.get(f"{_DM2_BASE}/{feed}/csv", params=params)
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty:
            break
        frames.append(df)
        if len(df) < rows_per_page:
            break
        start_row += rows_per_page
        if start_row > 200_000:
            break

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_lmp_rt_hourly(
    start: date,
    end: date | None = None,
    node_type: str = "HUB",
) -> pd.DataFrame:
    """Legacy DataMiner2 RT hourly LMP (broken as of 2026-07)."""
    return _dm2_fetch("rt_hrl_lmps", start, end or start, node_type=node_type)


def get_lmp_da_hourly(
    start: date,
    end: date | None = None,
    node_type: str = "HUB",
) -> pd.DataFrame:
    """Legacy DataMiner2 DA hourly LMP (broken as of 2026-07)."""
    return _dm2_fetch("da_hrl_lmps", start, end or start, node_type=node_type)


# ---------------------------------------------------------------------------
# Interconnection queue
# ---------------------------------------------------------------------------

_QUEUE_EXPORT_URL = "https://services.pjm.com/PJMPlanningApi/api/Queue/ExportToXls"
_QUEUE_SUBSCRIPTION_KEY = "E29477D0-70E0-4825-89B0-43F460BF9AB4"


def get_interconnection_queue() -> pd.DataFrame:
    """PJM planning queue (all projects: active, in service, withdrawn)."""
    r = _http.post(
        _QUEUE_EXPORT_URL,
        headers={
            "api-subscription-key": _QUEUE_SUBSCRIPTION_KEY,
            "Host": "services.pjm.com",
            "Origin": "https://www.pjm.com",
            "Referer": "https://www.pjm.com/",
        },
    )
    df = pd.read_excel(io.BytesIO(r.content))
    return df.rename(columns={
        "Project ID": "queue_position",
        "Name": "project_name",
        "County": "county",
        "State": "state",
        "Fuel": "fuel_type",
        "MW Capacity": "mw",
        "Status": "status",
        "Submitted Date": "queue_date",
        "Projected In Service Date": "online_date",
        "Withdrawal Date": "withdrawal_date",
    })
