from __future__ import annotations

from datetime import date

import pandas as pd

from kardashev import _caiso


class CAISO:
    """Direct CAISO data client. No API key required."""

    def get_fuel_mix(self, date: date | None = None) -> pd.DataFrame:
        """Live or historical generation by fuel type (5-min intervals)."""
        return _caiso.get_fuel_mix(date)

    def get_load(self, date: date | None = None) -> pd.DataFrame:
        """Actual grid load (5-min intervals)."""
        return _caiso.get_load(date)

    def get_lmp(
        self,
        market: str = "RT",
        node: str = "TH_NP15_GEN-APND",
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """LMP prices. market='RT' or 'DA'."""
        today = date.today() if start is None else start
        end = end or today
        if market.upper() == "DA":
            return _caiso.get_lmp_dam(node, today, end)
        return _caiso.get_lmp_rtm(node, today, end)

    def get_curtailment(self, date: date | None = None) -> pd.DataFrame:
        """Renewable curtailment data (hourly solar + wind MWh)."""
        import datetime as _dt
        return _caiso.get_curtailment(date or _dt.date.today())

    def get_load_forecast(self, start: date | None = None, end: date | None = None) -> pd.DataFrame:
        """CAISO system load forecast (day-ahead)."""
        import datetime as _dt
        today = _dt.date.today()
        return _caiso.get_load_forecast(start or today, end or today)

    def get_generator_outages(self, date: date | None = None) -> pd.DataFrame:
        """Curtailed and non-operational generator report for target date."""
        import datetime as _dt
        return _caiso.get_generator_outages(date or _dt.date.today())
