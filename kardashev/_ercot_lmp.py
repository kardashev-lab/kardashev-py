"""
ERCOT Settlement Point Prices from the public CDR/MIS portals (no auth needed).

RT (15-min): https://www.ercot.com/content/cdr/html/real_time_spp.html
DAM (hourly): MIS report NP4-190-CD via IceDocListJsonWS (reportTypeId 12331)

Key load zone hubs: HB_NORTH, HB_SOUTH, HB_WEST, HB_HOUSTON

Conventions: timestamps are interval-START in UTC. ERCOT publishes
hour/interval-ending in US Central prevailing time; both are converted here.
"""
from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from kardashev import _http

_SCED_URL = "https://data.ercot.com/api/public-reports/archive/np6-788-er"
_DAM_URL  = "https://data.ercot.com/api/public-reports/archive/np4-190-er"
_RT_SPP_URL = "https://www.ercot.com/content/cdr/html/real_time_spp.html"
_MIS_LIST_URL = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS"
_MIS_DOWNLOAD_URL = "https://www.ercot.com/misdownload/servlets/mirDownload"
_DAM_DAILY_REPORT_ID = 12331  # NP4-190-CD DAM Settlement Point Prices (daily)

_CENTRAL = ZoneInfo("America/Chicago")


def _central_to_utc(naive: datetime, repeated: bool = False) -> datetime:
    """Localize a naive US Central prevailing time to UTC.

    repeated=True marks the second occurrence of the DST fall-back hour
    (ERCOT 'Repeated Hour Flag' / 'DSTFlag' = Y).
    """
    return naive.replace(tzinfo=_CENTRAL, fold=1 if repeated else 0).astimezone(timezone.utc)

HUB_NODES = {
    # Settlement hubs
    "HB_BUSAVG", "HB_HOUSTON", "HB_HUBAVG", "HB_NORTH", "HB_PAN", "HB_SOUTH", "HB_WEST",
    # Load zones
    "LZ_AEN", "LZ_CPS", "LZ_HOUSTON", "LZ_LCRA", "LZ_NORTH", "LZ_RAYBN", "LZ_SOUTH", "LZ_WEST",
}

# Column name variants observed in ERCOT CSVs
_SPP_COL_CANDIDATES  = ["Settlement Point Price", "SettlementPointPrice", "SPP", "Spp"]
_NODE_COL_CANDIDATES = ["Settlement Point", "SettlementPoint", "settlementPoint",
                        "Settlement Point Name", "SettlementPointName"]
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

        # Oper Day: "06/25/2026", Interval Ending: "0015" = 00:15 Central.
        # Interval ending 2400 belongs to the same oper day (23:45-24:00).
        try:
            oper_day = cells[0].strip()
            interval = cells[1].strip().zfill(4)
            hour, minute = int(interval[:2]), int(interval[2:])
            base = datetime.strptime(oper_day, "%m/%d/%Y")
            ending = base + timedelta(hours=hour, minutes=minute)
            ts = _central_to_utc(ending) - timedelta(minutes=15)  # interval start
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


def list_mis_docs(report_type_id: int) -> list[dict]:
    """List documents for an ERCOT MIS report type, newest first."""
    resp = _http.get(_MIS_LIST_URL, params={"reportTypeId": report_type_id})
    docs = resp.json().get("ListDocsByRptTypeRes", {}).get("DocumentList", [])
    return [d.get("Document", {}) for d in docs]


def download_mis_doc(doc_id: str | int) -> bytes:
    """Download an ERCOT MIS document by DocID."""
    resp = _http.get(_MIS_DOWNLOAD_URL, params={"doclookupId": doc_id})
    return resp.content


def get_da_lmp(target: date | None = None) -> list[dict]:
    """
    Fetch ERCOT day-ahead market settlement point prices for hub/load-zone
    nodes from the daily MIS NP4-190-CD report.

    target: delivery date to fetch. If None, returns the most recent file
    (the DAM for tomorrow once published, ~12:30 Central).
    Timestamps are hour-START in UTC.
    """
    csv_docs = [d for d in list_mis_docs(_DAM_DAILY_REPORT_ID)
                if "csv" in str(d.get("FriendlyName", "")).lower()]

    for doc in csv_docs[:10]:  # newest first; scan back for target
        content = download_mis_doc(doc["DocID"])
        if content[:2] == b"PK":
            pairs = _unzip_content(content)
            if not pairs:
                continue
            df = pd.read_csv(pairs[0][1])
        else:
            df = pd.read_csv(io.BytesIO(content))

        df.columns = [c.strip() for c in df.columns]
        date_col = _col(df, ["Delivery Date", "DeliveryDate"])
        he_col   = _col(df, ["Hour Ending", "HourEnding"])
        node_col = _col(df, _NODE_COL_CANDIDATES)
        spp_col  = _col(df, _SPP_COL_CANDIDATES)
        dst_col  = _col(df, ["DSTFlag", "Repeated Hour Flag", "RepeatedHourFlag"])
        if not all([date_col, he_col, node_col, spp_col]):
            continue

        df = df[df[node_col].astype(str).str.upper().isin(HUB_NODES)]
        if df.empty:
            continue

        rows: list[dict] = []
        matched = False
        for _, row in df.iterrows():
            try:
                day = datetime.strptime(str(row[date_col]).strip(), "%m/%d/%Y")
                he = int(str(row[he_col]).split(":")[0])
                repeated = str(row[dst_col]).strip().upper() == "Y" if dst_col else False
                ts = _central_to_utc(day + timedelta(hours=he - 1), repeated)
                lmp = float(row[spp_col])
            except (TypeError, ValueError):
                continue
            if target and day.date() != target:
                continue
            matched = True
            rows.append({
                "ts":         ts,
                "iso":        "ERCOT",
                "node_id":    str(row[node_col]).strip().upper(),
                "node_name":  str(row[node_col]).strip().upper(),
                "market":     "DA",
                "lmp":        lmp,
                "energy":     None,
                "congestion": None,
                "loss":       None,
            })

        if target is None or matched:
            return rows

    return []


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
