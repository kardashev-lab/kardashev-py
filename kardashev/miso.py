from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _miso, _miso_lmp


class MISO:
    """Direct MISO data client. No API key required."""

    def get_fuel_mix(self) -> pd.DataFrame:
        """Live generation by fuel type from MISO public API."""
        return _miso.get_fuel_mix()

    def get_fuel_mix_today(self) -> pd.DataFrame:
        """Today's generation by fuel type (hourly)."""
        return _miso.get_fuel_mix_today()

    def get_load_forecast(self, date: date | None = None) -> pd.DataFrame:
        """Load forecast vs actual for target date."""
        return _miso.get_load_forecast_actual(date or _dt.date.today())

    def get_lmp(self, market: str = "RT", date: date | None = None) -> list[dict]:
        """Hub LMP prices. market='RT' (5-min) or 'DA' (hourly ex-ante)."""
        if market.upper() == "DA":
            return _miso_lmp.get_da_lmp(date or _dt.date.today())
        return _miso_lmp.get_rt_lmp()

    def get_generator_outages(self, date: date | None = None) -> pd.DataFrame:
        """7-day generation outage report from MISO market reports."""
        return _miso.get_generation_outages(date or _dt.date.today())
