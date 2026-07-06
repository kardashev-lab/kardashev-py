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
        """Latest carbon snapshot. One row per ISO."""
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
        """Latest LMP for all nodes with lat/lng, for map rendering."""
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

    def generation_wind_solar(
        self,
        iso: str,
        fuel_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Wind/solar generation forecast for an ISO."""
        return _to_df(self._get(
            "/generation/wind-solar",
            iso=iso.upper(),
            fuel_type=fuel_type,
            hours=hours,
            limit=limit,
        ))

    def generation_battery(
        self,
        iso: str = "CAISO",
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Battery storage state of charge/output. Currently CAISO only."""
        return _to_df(self._get("/generation/battery", iso=iso.upper(), hours=hours, limit=limit))

    def generation_btm_solar(
        self,
        iso: str = "NYISO",
        hours: int = 24,
        limit: int = 2000,
    ) -> Any:
        """Behind-the-meter solar estimate. Currently NYISO only."""
        return _to_df(self._get("/generation/btm-solar", iso=iso.upper(), hours=hours, limit=limit))

    def generation_reserve_margins(self, iso: Optional[str] = None) -> Any:
        """Planning reserve margins by ISO."""
        return _to_df(self._get("/generation/reserve-margins", iso=iso.upper() if iso else None))

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
        """Latest ancillary snapshot. One row per (ISO, market, service_type)."""
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
            "/nuclear",
            iso=iso.upper() if iso else None,
        ))

    def nuclear_summary(self, iso: Optional[str] = None) -> Any:
        """Nuclear capacity/output summary. Returns a single object, not rows."""
        clean = {k: v for k, v in {"iso": iso.upper() if iso else None}.items() if v is not None}
        r = self._http.get("/nuclear/summary", params=clean)
        r.raise_for_status()
        return r.json()

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

    def hydro_reservoirs(
        self,
        reservoir: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 90,
        limit: int = 5000,
    ) -> Any:
        """Reservoir storage levels."""
        return _to_df(self._get(
            "/hydro/reservoirs",
            reservoir=reservoir,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    def hydro_reservoirs_latest(self) -> Any:
        """Latest reservoir storage snapshot."""
        return _to_df(self._get("/hydro/reservoirs/latest"))

    def hydro_streamflow(
        self,
        site_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 7,
        limit: int = 5000,
    ) -> Any:
        """USGS streamflow by site."""
        return _to_df(self._get(
            "/hydro/streamflow",
            site_id=site_id,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Solar
    # ------------------------------------------------------------------

    def solar_irradiance(
        self,
        location: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 7,
        limit: int = 10000,
    ) -> Any:
        """Solar irradiance by location."""
        return _to_df(self._get(
            "/solar/irradiance",
            location=location,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    def solar_irradiance_locations(self) -> Any:
        """Tracked irradiance station locations."""
        return _to_df(self._get("/solar/irradiance/locations"))

    def solar_irradiance_latest(self) -> Any:
        """Latest irradiance snapshot per location."""
        return _to_df(self._get("/solar/irradiance/latest"))

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
            "/interconnection-queue",
            iso=iso.upper() if iso else None,
            status=status,
            fuel_type=fuel_type,
            limit=limit,
        ))

    # ------------------------------------------------------------------
    # Commodities
    # ------------------------------------------------------------------

    def commodities_coal(
        self,
        rank: Optional[str] = None,
        months: int = 24,
    ) -> Any:
        """EIA monthly coal prices by rank ($/short ton)."""
        return _to_df(self._get("/commodities/coal", rank=rank, months=months))

    def commodities_petroleum(
        self,
        product: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        days: int = 90,
        limit: int = 5000,
    ) -> Any:
        """EIA daily petroleum spot prices (WTI, Brent, RBOB, heating oil)."""
        return _to_df(self._get(
            "/commodities/petroleum",
            product=product,
            start=_fmt(start),
            end=_fmt(end),
            days=days,
            limit=limit,
        ))

    def commodities_power_burn(
        self,
        state: Optional[str] = None,
        months: int = 12,
    ) -> Any:
        """EIA monthly natural gas used for power generation ("power burn")."""
        return _to_df(self._get("/commodities/power-burn", state=state, months=months))

    def steo_forecast(self) -> Any:
        """EIA Short-Term Energy Outlook: monthly 2-year energy forecasts."""
        return _to_df(self._get("/forecasts/steo"))

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
