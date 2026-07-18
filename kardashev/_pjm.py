"""
PJM Interconnection data client (DataMiner2 feed API).

Auth: PJM username + password from dataminer2.pjm.com account.
      Set PJM_USERNAME and PJM_PASSWORD env vars.

DataMiner2 feed base: https://dataminer2.pjm.com/feed/
Key feeds used:
  rt_hrl_lmps  - RT hourly LMP, all nodes (posted daily ~11am-12pm ET)
  da_hrl_lmps  - DA hourly LMP, all nodes (posted morning of delivery day)

Node types: HUB, ZONE, AGGREGATE, BUS, INTERFACE, LOAD_ZONE

KNOWN ISSUE (as of 2026-07-18): PJM appears to have decommissioned this
CSV feed API entirely. dataminer2.pjm.com/feed/rt_hrl_lmps/csv now returns
a static, cached copy of the DataMiner2 web app's index.html for any
request, valid credentials or not (confirmed via response headers: a
long-lived Cache-Control/Last-Modified pair, served by IIS, identical for
garbage vs. real username/password). get_lmp_rt_hourly/get_lmp_da_hourly
will raise a pandas ParserError when this happens ("Expected 1 fields ...
saw 3") since the HTML gets fed to pd.read_csv. PJM's interconnection
queue (get_interconnection_queue, above) already lives on their modern
platform (services.pjm.com, api-subscription-key header) -- LMP fetching
needs the same kind of migration, to api.pjm.com via apiportal.pjm.com,
which requires a paid subscription we don't currently have.
"""
from __future__ import annotations

import io
import os
from datetime import date, timedelta

import pandas as pd

from kardashev import _http

_DM2_BASE = "https://dataminer2.pjm.com/feed"


def _creds() -> tuple[str, str]:
    u = os.environ.get("PJM_USERNAME", "")
    p = os.environ.get("PJM_PASSWORD", "")
    if not u or not p:
        raise EnvironmentError("PJM_USERNAME and PJM_PASSWORD env vars required")
    return u, p


def _dt_str(d: date) -> str:
    return f"{d.strftime('%Y-%m-%d')} 00:00"


def _dm2_fetch(feed: str, start: date, end: date, node_type: str | None = None) -> pd.DataFrame:
    """Fetch a DataMiner2 feed as CSV, auto-paginating up to 200k rows."""
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


# ---------------------------------------------------------------------------
# LMP - RT hourly (settled, posted daily)
# ---------------------------------------------------------------------------

def get_lmp_rt_hourly(
    start: date,
    end: date | None = None,
    node_type: str = "HUB",
) -> pd.DataFrame:
    """
    RT hourly LMP from DataMiner2 (settled, posted ~11am-12pm ET daily).

    node_type: HUB | ZONE | AGGREGATE | BUS (BUS = all 20k+ nodes, slow)

    Columns returned:
      datetime_beginning_utc, pnode_id, pnode_name, type, zone,
      total_lmp_rt, system_energy_price_rt, congestion_price_rt, marginal_loss_price_rt
    """
    return _dm2_fetch("rt_hrl_lmps", start, end or start, node_type=node_type)


# ---------------------------------------------------------------------------
# LMP - DA hourly (posted morning of delivery day)
# ---------------------------------------------------------------------------

def get_lmp_da_hourly(
    start: date,
    end: date | None = None,
    node_type: str = "HUB",
) -> pd.DataFrame:
    """
    DA hourly LMP from DataMiner2.

    Columns returned:
      datetime_beginning_utc, pnode_id, pnode_name, type, zone,
      total_lmp_da, system_energy_price_da, congestion_price_da, marginal_loss_price_da
    """
    return _dm2_fetch("da_hrl_lmps", start, end or start, node_type=node_type)


# ---------------------------------------------------------------------------
# Interconnection queue
# ---------------------------------------------------------------------------

# PJM's public planning-queue export doesn't go through DataMiner2 — it's a
# separate services.pjm.com endpoint used by pjm.com's own queue viewer.
# The subscription key below is the one that page ships to browsers (not a
# PJM_USERNAME/PJM_PASSWORD-gated secret); PJM may rotate it without notice.
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
