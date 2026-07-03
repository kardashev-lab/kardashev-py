from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _nyiso


class NYISO:
    """Direct NYISO data client. No API key required."""

    def get_fuel_mix(self, date: date | None = None) -> pd.DataFrame:
        """Real-time generation by fuel type (5-min)."""
        return _nyiso.get_fuel_mix(date or _dt.date.today())

    def get_load(self, date: date | None = None) -> pd.DataFrame:
        """Actual system load (5-min intervals)."""
        return _nyiso.get_load(date or _dt.date.today())

    def get_load_forecast(self, date: date | None = None) -> pd.DataFrame:
        """Day-ahead load forecast."""
        return _nyiso.get_load_forecast(date or _dt.date.today())

    def get_lmp(self, market: str = "RT", date: date | None = None) -> pd.DataFrame:
        """Zonal LMP prices. market='RT' (5-min) or 'DA' (hourly)."""
        target = date or _dt.date.today()
        if market.upper() == "DA":
            return _nyiso.get_lmp_dam_zone(target)
        return _nyiso.get_lmp_realtime_zone(target)

    def get_interconnection_queue(self) -> pd.DataFrame:
        """NYISO generator interconnection queue (xlsx download)."""
        return _nyiso.get_interconnection_queue()
