"""Shared HTTP utilities: retry, rate-limiting, common headers."""
from __future__ import annotations

import io
import zipfile
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_RETRY = Retry(
    total=4,
    backoff_factor=1.5,
    status_forcelist={429, 500, 502, 503, 504},
    allowed_methods={"GET", "POST"},
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def session(extra_headers: dict[str, str] | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    if extra_headers:
        s.headers.update(extra_headers)
    adapter = HTTPAdapter(max_retries=_RETRY)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# Shared session so we reuse connections and avoid TLS handshake overhead on every request.
_shared_session: requests.Session | None = None


def _get_shared_session() -> requests.Session:
    global _shared_session
    if _shared_session is None:
        _shared_session = session()
    return _shared_session


def get(url: str, params: dict | None = None, **kwargs: Any) -> requests.Response:
    r = _get_shared_session().get(url, params=params, timeout=60, **kwargs)
    r.raise_for_status()
    return r


def get_csv(url: str, params: dict | None = None, **kwargs: Any):
    import pandas as pd
    r = get(url, params=params, **kwargs)
    return pd.read_csv(io.StringIO(r.text))


def get_excel(url: str, params: dict | None = None, sheet_name: str | int = 0, **kwargs: Any):
    import pandas as pd
    r = get(url, params=params, **kwargs)
    return pd.read_excel(io.BytesIO(r.content), sheet_name=sheet_name)


def post(url: str, headers: dict | None = None, **kwargs: Any) -> requests.Response:
    r = _get_shared_session().post(url, timeout=60, headers=headers, **kwargs)
    r.raise_for_status()
    return r


def get_zip_csv(url: str, params: dict | None = None, filename_hint: str = "") -> list:
    """Download a zip and return list of (filename, BytesIO) for CSV members."""
    r = get(url, params=params)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        members = [n for n in zf.namelist() if n.endswith(".csv")]
        if filename_hint:
            members = [m for m in members if filename_hint in m] or members
        return [(name, io.BytesIO(zf.read(name))) for name in members]


def post_json(url: str, data: dict, **kwargs: Any) -> Any:
    r = _get_shared_session().post(url, data=data, timeout=60, **kwargs)
    r.raise_for_status()
    return r.json()
