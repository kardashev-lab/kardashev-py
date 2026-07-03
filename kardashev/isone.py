from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _isone


class ISONE:
    """
    Direct ISO-NE data client.

    LMP endpoints require credentials set via environment variables:
      ISONE_USERNAME and ISONE_PASSWORD
    All other endpoints are public.
    """

    def get_fuel_mix(self, date: date | None = None) -> pd.DataFrame:
        """Generation by fuel type for target date."""
        return _isone.get_fuel_mix(date or _dt.date.today())

    def get_load(self, start: date | None = None, end: date | None = None) -> pd.DataFrame:
        """Actual system load."""
        today = _dt.date.today()
        return _isone.get_load(start or today, end)

    def get_load_forecast(self, start: date | None = None, end: date | None = None) -> pd.DataFrame:
        """Day-ahead load forecast."""
        today = _dt.date.today()
        return _isone.get_load_forecast(start or today, end)

    def get_lmp(
        self,
        market: str = "RT",
        location: str | int = ".Z.NEPOOL",
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """
        LMP prices for a location.
        market='RT' returns 5-min prices; 'DA' returns hourly prices.
        Requires ISONE_USERNAME / ISONE_PASSWORD env vars.
        """
        today = _dt.date.today()
        if market.upper() == "DA":
            return _isone.get_lmp_hourly(location, start or today, end)
        return _isone.get_lmp_fiveminute(location, start or today, end)

    def get_interconnection_queue(self) -> pd.DataFrame:
        """ISO-NE generator interconnection queue from irtt.iso-ne.com."""
        return _isone.get_interconnection_queue()
