from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _ercot, _ercot_lmp


class ERCOT:
    """Direct ERCOT data client. No API key required."""

    def get_fuel_mix(self) -> pd.DataFrame:
        """Live generation by fuel type from ERCOT dashboard."""
        return _ercot.get_fuel_mix()

    def get_fuel_mix_historical(self, start: date, end: date | None = None) -> pd.DataFrame:
        """Historical generation by fuel type."""
        return _ercot.get_fuel_mix_historical(start, end)

    def get_wind_generation(self) -> pd.DataFrame:
        """Live wind generation (MW) from ERCOT dashboard."""
        return _ercot.get_wind_generation()

    def get_solar_generation(self) -> pd.DataFrame:
        """Live solar generation (MW) from ERCOT dashboard."""
        return _ercot.get_solar_generation()

    def get_load_forecast(self) -> list[dict]:
        """ERCOT system-wide load forecast."""
        return _ercot.get_load_forecast()

    def get_lmp(self, market: str = "RT", date: date | None = None) -> list[dict]:
        """Settlement point prices. market='RT' (5-min CDR) or 'DA' (DAM hourly)."""
        if market.upper() == "DA":
            return _ercot_lmp.get_da_lmp(date)
        return _ercot_lmp.get_rt_lmp()

    def get_ancillary_services(self) -> list[dict]:
        """Real-time ancillary service prices from ERCOT dashboard."""
        return _ercot.get_as_monitor()
