"""
ISO New England REST API client.

Replaces legacy HTML scrape with the official ISO-NE web services API.
Basic-auth credentials: ISONE_USERNAME / ISONE_PASSWORD env vars.

API docs: https://webservices.iso-ne.com/api/v1.1/swagger-ui.html

Hubs (location IDs):
  .Z.MAINE          4001
  .Z.NEWHAMPSHIRE   4002
  .Z.VERMONT        4003
  .Z.CONNECTICUT    4004
  .Z.RHODEISLAND    4005
  .Z.SEMASS         4006
  .Z.WCMASS         4007
  .Z.NEMASSBOST     4008
  .H.INTERNALHUB    4000  (system hub aggregate)
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any

from kardashev import _http

_BASE = "https://webservices.iso-ne.com/api/v1.1"

# Hub location ID → readable name
HUBS: dict[int, str] = {
    4000: ".H.INTERNALHUB",
    4001: ".Z.MAINE",
    4002: ".Z.NEWHAMPSHIRE",
    4003: ".Z.VERMONT",
    4004: ".Z.CONNECTICUT",
    4005: ".Z.RHODEISLAND",
    4006: ".Z.SEMASS",
    4007: ".Z.WCMASS",
    4008: ".Z.NEMASSBOST",
}


def _auth() -> tuple[str, str]:
    user = os.environ.get("ISONE_USERNAME", "")
    pwd  = os.environ.get("ISONE_PASSWORD", "")
    if not user or not pwd:
        raise RuntimeError(
            "ISONE_USERNAME and ISONE_PASSWORD must be set. "
            "Register free at https://webservices.iso-ne.com/api/v1.1"
        )
    return (user, pwd)


def _get(path: str) -> Any:
    """GET from ISO-NE API with basic auth and JSON Accept header."""
    url = f"{_BASE}/{path.lstrip('/')}"
    resp = _http.get(url, auth=_auth(), headers={"Accept": "application/json"})
    return resp.json()


def get_rt_lmp() -> list[dict]:
    """
    Fetch current 5-min real-time LMP for all hub locations.

    Returns list of dicts compatible with upsert_lmp():
        ts, iso, node_id, node_name, market, lmp, energy, congestion, loss
    """
    data = _get("/fiveminutelmp/current")
    # Response: {"FiveMinLmps": {"FiveMinLmp": [...]}} or flat list depending on version
    items = _extract_list(data, "FiveMinLmp", "FiveMinLmps")
    return _parse_lmp_items(items, market="RT")


def get_da_lmp(target: date) -> list[dict]:
    """
    Fetch day-ahead hourly LMP for all hub locations on target date.

    Returns list of dicts compatible with upsert_lmp().
    """
    date_str = target.strftime("%Y%m%d")
    all_rows: list[dict] = []

    for loc_id, loc_name in HUBS.items():
        try:
            data = _get(f"/hourlylmp/day/{date_str}/location/{loc_id}")
            items = _extract_list(data, "HourlyLmp", "HourlyLmps")
            rows = _parse_lmp_items(items, market="DA", override_node_id=str(loc_id),
                                    override_node_name=loc_name)
            all_rows.extend(rows)
        except Exception:
            # A single missing hub shouldn't abort the whole run
            import logging
            logging.getLogger(__name__).warning(
                "ISONE DA LMP: no data for loc %s (%s)", loc_id, loc_name
            )

    return all_rows


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_list(data: Any, inner_key: str, outer_key: str) -> list[dict]:
    """
    ISO-NE API wraps responses in various shapes. Normalise to a plain list.

    Shapes seen in the wild:
      {"FiveMinLmps": {"FiveMinLmp": [...]}}
      {"FiveMinLmps": {"FiveMinLmp": {...}}}   <- single-item is not a list
      [...]                                     <- bare list
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        outer = data.get(outer_key, data)
        if isinstance(outer, dict):
            inner = outer.get(inner_key, [])
            if isinstance(inner, list):
                return inner
            if isinstance(inner, dict):
                return [inner]
        if isinstance(outer, list):
            return outer
    return []


def _parse_lmp_items(
    items: list[dict],
    market: str,
    override_node_id: str | None = None,
    override_node_name: str | None = None,
) -> list[dict]:
    """Convert raw ISO-NE LMP dicts to canonical upsert_lmp row format."""
    rows: list[dict] = []
    for item in items:
        # Period: "2024-06-15T14:00:00.000-04:00" or similar
        raw_ts = item.get("BeginDate") or item.get("StartDate") or item.get("BeginDateUtc", "")
        try:
            ts = datetime.fromisoformat(raw_ts.replace(".000", "")).astimezone(timezone.utc)
        except (ValueError, AttributeError):
            continue

        loc_id   = override_node_id   or str(item.get("Location", {}).get("@LocId", ""))
        loc_name = override_node_name or item.get("Location", {}).get("$", loc_id)

        try:
            lmp        = _float(item.get("LmpTotal"))
            energy     = _float(item.get("EnergyComponent"))
            congestion = _float(item.get("CongestionComponent"))
            loss       = _float(item.get("LossComponent"))
        except (TypeError, ValueError):
            continue

        rows.append({
            "ts":         ts,
            "iso":        "ISONE",
            "node_id":    loc_id,
            "node_name":  loc_name,
            "market":     market,
            "lmp":        lmp,
            "energy":     energy,
            "congestion": congestion,
            "loss":       loss,
        })
    return rows


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
