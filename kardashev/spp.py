from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _spp


class SPP:
    """Direct SPP data client. No API key required."""

    def get_fuel_mix(self) -> pd.DataFrame:
        """Latest generation by fuel type from SPP marketplace."""
        return _spp.get_gen_mix_latest()

    def get_fuel_mix_365(self) -> pd.DataFrame:
        """Rolling 365-day generation mix."""
        return _spp.get_gen_mix_365()

    def get_lmp(self) -> pd.DataFrame:
        """Latest RT Balancing Market (RTBM) LMP prices."""
        return _spp.get_lmp_rtbm_latest()

    def get_load_forecast(self, date: date | None = None) -> pd.DataFrame:
        """SPP load forecast for target date."""
        return _spp.get_load_forecast(date or _dt.date.today())

    def get_curtailment(self, date: date | None = None) -> dict[str, float]:
        """VER curtailment daily totals (solar + wind MWh)."""
        return _spp.get_curtailment_daily_totals(date or _dt.date.today())
