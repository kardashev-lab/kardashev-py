"""
ERCOT Settlement Point Prices from the public CDR portal (no auth needed).

SCED (RT 15-min): https://data.ercot.com/api/public-reports/archive/np6-788-er
DAM  (DA hourly):  https://data.ercot.com/api/public-reports/archive/np4-190-er

Key load zone hubs: HB_NORTH, HB_SOUTH, HB_WEST, HB_HOUSTON
"""
from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from kardashev import _http

_SCED_URL = "https://data.ercot.com/api/public-reports/archive/np6-788-er"
_DAM_URL  = "https://data.ercot.com/api/public-reports/archive/np4-190-er"
_RT_SPP_URL = "https://www.ercot.com/content/cdr/html/real_time_spp.html"

HUB_NODES = {
    # Settlement hubs
    "HB_BUSAVG", "HB_HOUSTON", "HB_HUBAVG", "HB_NORTH", "HB_PAN", "HB_SOUTH", "HB_WEST",
    # Load zones
    "LZ_AEN", "LZ_CPS", "LZ_HOUSTON", "LZ_LCRA", "LZ_NORTH", "LZ_RAYBN", "LZ_SOUTH", "LZ_WEST",
}

# Column name variants observed in ERCOT CSVs
_SPP_COL_CANDIDATES  = ["Settlement Point Price", "SPP", "Spp"]
_NODE_COL_CANDIDATES = ["Settlement Point", "SettlementPoint", "settlementPoint"]
_TS_COL_CANDIDATES   = ["Delivery Date", "DeliveryDate", "SCED Time Stamp",
                         "SCEDTimestamp", "Delivery Hour", "Hour Ending",
                         "Interval Ending", "intervalEnding"]


def _fetch_archive(url: str, params: dict | None = None) -> list[tuple[str, io.BytesIO]]:
    """
    Fetch archive index JSON from ERCOT public API, download the most recent
    file, and return list of (filename, BytesIO) for CSV members.
    """
    p = dict(params or {})
    p.setdefault("size", 1)
    p.setdefault("page", 1)

    resp = _http.get(url, params=p)
    meta = resp.json()

    # Shape: {"data": {"list": [{"docId": ..., "docName": ...}, ...]}}
    items: list[dict] = []
    if isinstance(meta, dict):
        data_block = meta.get("data", meta)
        if isinstance(data_block, dict):
            items = data_block.get("list", [])
        elif isinstance(data_block, list):
            items = data_block
    elif isinstance(meta, list):
        items = meta

    if not items:
        raise RuntimeError(f"ERCOT archive returned no items from {url}")

    # Most recent document is first (size=1 already filters it)
    doc = items[0]
    doc_id = doc.get("docId") or doc.get("id")
    if not doc_id:
        raise RuntimeError(f"ERCOT archive item missing docId: {doc}")

    file_url = f"https://data.ercot.com/api/public-reports/archive/{doc_id}"
    file_resp = _http.get(file_url)
    content_type = file_resp.headers.get("Content-Type", "")

    # Response is usually a zip
    if "zip" in content_type or file_resp.content[:2] == b"PK":
        return _http.get_zip_csv.__wrapped__(file_resp.content)  # type: ignore[attr-defined]

    # Fallback: plain CSV
    return [("data.csv", io.BytesIO(file_resp.content))]


def _unzip_content(content: bytes) -> list[tuple[str, io.BytesIO]]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        members = [n for n in zf.namelist() if n.endswith(".csv")]
        return [(name, io.BytesIO(zf.read(name))) for name in members]


def _fetch_latest_csv(base_url: str) -> pd.DataFrame | None:
    """Download most recent archive file and return as DataFrame."""
    params = {"size": 1, "page": 1}
    resp = _http.get(base_url, params=params)
    meta = resp.json()

    items: list[dict] = []
    if isinstance(meta, dict):
        block = meta.get("data", meta)
        if isinstance(block, dict):
            items = block.get("list", block.get("items", []))
        elif isinstance(block, list):
            items = block
    elif isinstance(meta, list):
        items = meta

    if not items:
        return None

    doc = items[0]
    doc_id = doc.get("docId") or doc.get("id") or doc.get("documentId")
    if not doc_id:
        return None

    dl_url = f"https://data.ercot.com/api/public-reports/archive/{doc_id}"
    file_resp = _http.get(dl_url)

    # Detect zip or raw CSV
    if file_resp.content[:2] == b"PK":
        pairs = _unzip_content(file_resp.content)
        if not pairs:
            return None
        _, buf = pairs[0]
        return pd.read_csv(buf)
    else:
        return pd.read_csv(io.BytesIO(file_resp.content))


def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find first matching column name (case-insensitive)."""
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def get_rt_lmp() -> list[dict]:
    """
    Fetch most recent ERCOT RT settlement point prices for hub nodes.

    Parses the public CDR HTML report (no auth required). The archive API
    at data.ercot.com now requires a subscriber account.

    CDR columns: Oper Day, Interval Ending, HB_BUSAVG, HB_HOUSTON,
                 HB_HUBAVG, HB_NORTH, HB_PAN, HB_SOUTH, HB_WEST, LZ_*
    """
    import re

    resp = _http.get(_RT_SPP_URL)
    html = resp.text

    headers = re.findall(r"<th[^>]*>([^<]+)</th>", html)
    rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)

    if not headers or len(rows_html) < 2:
        return []

    hub_cols = {i: h for i, h in enumerate(headers) if h.upper() in HUB_NODES}

    results: list[dict] = []
    for row_html in rows_html[1:]:
        cells = re.findall(r"<td[^>]*>([^<]+)</td>", row_html)
        if len(cells) < len(headers):
            continue

        # Oper Day: "06/25/2026", Interval Ending: "0015" = 00:15
        try:
            oper_day = cells[0].strip()
            interval = cells[1].strip().zfill(4)
            hour, minute = int(interval[:2]), int(interval[2:])
            ts = datetime.strptime(oper_day, "%m/%d/%Y").replace(
                hour=hour, minute=minute, tzinfo=timezone.utc
            )
        except (ValueError, IndexError):
            continue

        for col_idx, node_id in hub_cols.items():
            try:
                lmp = float(cells[col_idx])
            except (ValueError, IndexError):
                continue
            results.append({
                "ts":         ts,
                "iso":        "ERCOT",
                "node_id":    node_id,
                "node_name":  node_id,
                "market":     "RT",
                "lmp":        lmp,
                "energy":     None,
                "congestion": None,
                "loss":       None,
            })

    return results


def get_da_lmp(target: date | None = None) -> list[dict]:
    """
    Fetch ERCOT day-ahead market settlement point prices.

    target: date to fetch. If None, fetches the most recent available.
    Returns list of dicts compatible with upsert_lmp() filtered to hub nodes.
    """
    df = _fetch_latest_csv(_DAM_URL)
    if df is None or df.empty:
        return []

    df.columns = [c.strip() for c in df.columns]
    node_col = _col(df, _NODE_COL_CANDIDATES)
    spp_col  = _col(df, _SPP_COL_CANDIDATES)

    if not node_col or not spp_col:
        return []

    # Filter to hub nodes
    mask = df[node_col].astype(str).str.upper().isin(HUB_NODES)
    df = df[mask]

    # Filter to target date if specified
    ts_col = _col(df, _TS_COL_CANDIDATES)

    rows: list[dict] = []
    for _, row in df.iterrows():
        ts = _parse_row_ts(row, ts_col)
        if ts is None:
            continue
        if target and ts.date() != target:
            continue

        node_id = str(row[node_col]).strip().upper()
        try:
            lmp = float(row[spp_col])
        except (TypeError, ValueError):
            continue

        rows.append({
            "ts":         ts,
            "iso":        "ERCOT",
            "node_id":    node_id,
            "node_name":  node_id,
            "market":     "DA",
            "lmp":        lmp,
            "energy":     None,
            "congestion": None,
            "loss":       None,
        })

    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_row_ts(row: Any, ts_col: str | None) -> datetime | None:
    if ts_col is None:
        return None

    raw = str(row.get(ts_col, "") if hasattr(row, "get") else row[ts_col] if ts_col in row.index else "")
    if not raw or raw == "nan":
        return None

    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(raw[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
