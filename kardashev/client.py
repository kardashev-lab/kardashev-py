from __future__ import annotations

from datetime import date
from typing import Any, Optional, Union

import httpx

_BASE = "https://data.kardashevlabs.org"

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False


def _to_df(data: list[dict]) -> Any:
    if _PANDAS and data:
        df = pd.DataFrame(data)
        for col in df.columns:
            if "ts" in col or col in ("start_time", "end_time", "report_date"):
                try:
                    df[col] = pd.to_datetime(df[col], utc=True)
                except Exception:
                    pass
        return df
    return data


def _fmt(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


class Client:
    """Python client for the Kardashev Labs energy data API.

    Parameters
    ----------
    base_url:
        Override the API base URL (useful for local dev).
    timeout:
        HTTP timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = _BASE,
        timeout: float = 30.0,
    ) -> None:
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    def _get(self, path: str, **params: Any) -> list[dict]:
        clean = {k: v for k, v in params.items() if v is not None}
        r = self._http.get(path, params=clean)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Fuel mix
    # ------------------------------------------------------------------

    def fuel_mix(
        self,
        iso: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Real-time fuel mix (MW by fuel type) for an ISO."""
        return _to_df(self._get(
            "/fuel-mix",
            iso=iso.upper(),
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Carbon intensity
    # ------------------------------------------------------------------

    def carbon(
        self,
        iso: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Hourly carbon intensity (lbs CO₂/MWh) for an ISO."""
        return _to_df(self._get(
            "/carbon",
            iso=iso.upper(),
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    def carbon_latest(self, iso: Optional[str] = None) -> Any:
        """Latest carbon snapshot — one row per ISO."""
        return _to_df(self._get("/carbon/latest", iso=iso.upper() if iso else None))

    # ------------------------------------------------------------------
    # LMP
    # ------------------------------------------------------------------

    def lmp(
        self,
        iso: str,
        node_id: Optional[str] = None,
        market: str = "RT",
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Locational marginal prices (LMP, energy, congestion, loss)."""
        return _to_df(self._get(
            "/lmp",
            iso=iso.upper(),
            node_id=node_id,
            market=market.upper(),
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    def lmp_map(self, iso: str, market: str = "RT") -> Any:
        """Latest LMP for all nodes with lat/lng — for map rendering."""
        return _to_df(self._get("/lmp/map", iso=iso.upper(), market=market.upper()))

    def lmp_hubs(self, iso: Optional[str] = None) -> Any:
        """List all tracked LMP pricing nodes."""
        return _to_df(self._get("/lmp/hubs", iso=iso.upper() if iso else None))

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(
        self,
        iso: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Actual grid load (MW) by ISO."""
        return _to_df(self._get(
            "/load",
            iso=iso.upper() if iso else None,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    def load_forecast(
        self,
        iso: Optional[str] = None,
        hours: int = 24,
    ) -> Any:
        """Load forecast (MW) for the next N hours."""
        return _to_df(self._get(
            "/load/forecast",
            iso=iso.upper() if iso else None,
            hours=hours,
        ))

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generation(
        self,
        iso: Optional[str] = None,
        fuel_type: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Generation by fuel type for an ISO."""
        return _to_df(self._get(
            "/generation",
            iso=iso.upper() if iso else None,
            fuel_type=fuel_type,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Curtailment
    # ------------------------------------------------------------------

    def curtailment(
        self,
        iso: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Renewable curtailment (MWh) by ISO."""
        return _to_df(self._get(
            "/curtailment",
            iso=iso.upper() if iso else None,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Interchange
    # ------------------------------------------------------------------

    def interchange(
        self,
        ba: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 5000,
    ) -> Any:
        """Net interchange (MW) from a balancing authority to neighbors."""
        return _to_df(self._get(
            "/interchange",
            ba=ba.upper(),
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Natural gas
    # ------------------------------------------------------------------

    def nat_gas(
        self,
        hub: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 90,
        limit: int = 5000,
    ) -> Any:
        """Daily natural gas spot prices ($/MMBtu) at major US hubs."""
        return _to_df(self._get(
            "/natural-gas",
            hub=hub,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    def nat_gas_storage(
        self,
        region: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        weeks: int = 52,
        limit: int = 2000,
    ) -> Any:
        """Weekly EIA natural gas in storage (Bcf) by region."""
        return _to_df(self._get(
            "/natural-gas/storage",
            region=region,
            start=_fmt(start),
            end=_fmt(end),
            weeks=weeks,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------

    def weather(
        self,
        iso: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Hourly temperature at representative ISO hub cities."""
        return _to_df(self._get(
            "/weather",
            iso=iso.upper() if iso else None,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # BPA
    # ------------------------------------------------------------------

    def bpa(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """BPA 5-min balancing area: wind, hydro, thermal, load."""
        return _to_df(self._get(
            "/bpa",
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Generator outages
    # ------------------------------------------------------------------

    def outages(
        self,
        iso: Optional[str] = None,
        outage_type: Optional[str] = None,
        active_only: bool = False,
        days: int = 7,
        limit: int = 2000,
    ) -> Any:
        """Generator outages (unit-level and aggregate) by ISO."""
        return _to_df(self._get(
            "/outages",
            iso=iso.upper() if iso else None,
            outage_type=outage_type,
            active_only=active_only if active_only else None,
            days=days,
            limit=limit,
        ))

    def outages_summary(self, iso: Optional[str] = None) -> Any:
        """Total MW in outage grouped by ISO × outage type."""
        return _to_df(self._get(
            "/outages/summary",
            iso=iso.upper() if iso else None,
        ))

    # ------------------------------------------------------------------
    # Ancillary services
    # ------------------------------------------------------------------

    def ancillary(
        self,
        iso: Optional[str] = None,
        market: Optional[str] = None,
        service_type: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Ancillary service clearing prices and operational capacity."""
        return _to_df(self._get(
            "/ancillary",
            iso=iso.upper() if iso else None,
            market=market.upper() if market else None,
            service_type=service_type,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    def ancillary_latest(self, iso: Optional[str] = None) -> Any:
        """Latest ancillary snapshot — one row per (ISO, market, service_type)."""
        return _to_df(self._get(
            "/ancillary/latest",
            iso=iso.upper() if iso else None,
        ))

    # ------------------------------------------------------------------
    # Nuclear
    # ------------------------------------------------------------------

    def nuclear_status(self, iso: Optional[str] = None) -> Any:
        """Current nuclear unit capacity and output."""
        return _to_df(self._get(
            "/nuclear/status",
            iso=iso.upper() if iso else None,
        ))

    # ------------------------------------------------------------------
    # Emissions
    # ------------------------------------------------------------------

    def emissions(
        self,
        iso: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """SO₂, NOₓ, CO₂ emissions by ISO."""
        return _to_df(self._get(
            "/emissions",
            iso=iso.upper() if iso else None,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Hydro
    # ------------------------------------------------------------------

    def hydro(
        self,
        iso: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Hydro generation and reservoir conditions."""
        return _to_df(self._get(
            "/hydro",
            iso=iso.upper() if iso else None,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Solar
    # ------------------------------------------------------------------

    def solar(
        self,
        iso: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Solar generation and curtailment by ISO."""
        return _to_df(self._get(
            "/solar",
            iso=iso.upper() if iso else None,
            start=_fmt(start),
            end=_fmt(end),
            hours=hours,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Interconnection queue
    # ------------------------------------------------------------------

    def queue(
        self,
        iso: Optional[str] = None,
        status: Optional[str] = None,
        fuel_type: Optional[str] = None,
        limit: int = 5000,
    ) -> Any:
        """Generator interconnection queue entries."""
        return _to_df(self._get(
            "/queue",
            iso=iso.upper() if iso else None,
            status=status,
            fuel_type=fuel_type,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Commodities
    # ------------------------------------------------------------------

    def commodities(
        self,
        commodity: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 90,
        limit: int = 2000,
    ) -> Any:
        """Commodity prices (coal, uranium, carbon credits)."""
        return _to_df(self._get(
            "/commodities",
            commodity=commodity,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Carbon markets
    # ------------------------------------------------------------------

    def carbon_markets(
        self,
        market: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 90,
        limit: int = 2000,
    ) -> Any:
        """Carbon credit prices (RGGI, WCI, VCM)."""
        return _to_df(self._get(
            "/carbon-markets",
            market=market,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
