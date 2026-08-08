"""Regression: CAISO current fuelsource must stamp Pacific calendar date, not UTC date."""
from datetime import date, datetime
from unittest.mock import patch

import pandas as pd
import pytz

from kardashev import _caiso as caiso


def test_current_fuel_mix_uses_pacific_day_not_utc(monkeypatch):
    """After 17:00 PT, UTC is already the next calendar day.

    Bare pd.to_datetime('20:00') on a UTC host would stamp evening rows onto
    the wrong Pacific day. get_fuel_mix() must force Pacific today.
    """
    _PT = pytz.timezone("US/Pacific")
    # Freeze "now" at Aug 4 20:00 PT = Aug 5 03:00 UTC
    frozen_pt = _PT.localize(datetime(2026, 8, 4, 20, 0, 0))

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_pt.replace(tzinfo=None)
            return frozen_pt.astimezone(tz)

    csv = pd.DataFrame({
        "Time": ["00:00", "20:00"],
        "Batteries": [1000.0, 10400.0],
        "Solar": [0.0, 0.0],
    })
    monkeypatch.setattr(caiso._http, "get_csv", lambda url: csv.copy())

    with patch("datetime.datetime", FrozenDateTime):
        df = caiso.get_fuel_mix()

    assert not df.empty
    days = sorted({ts.tz_convert("US/Pacific").date() for ts in df["timestamp"]})
    assert days == [date(2026, 8, 4)], f"expected Pacific Aug 4 only, got {days}"

    evening = df.iloc[1]["timestamp"].tz_convert("US/Pacific")
    assert evening.hour == 20
    assert evening.date() == date(2026, 8, 4)


def test_historical_fuel_mix_keeps_target_date(monkeypatch):
    csv = pd.DataFrame({
        "Time": ["09:00", "20:00"],
        "Batteries": [-8900.0, 10400.0],
        "Solar": [100.0, 0.0],
    })
    monkeypatch.setattr(caiso._http, "get_csv", lambda url: csv.copy())
    df = caiso.get_fuel_mix(date(2026, 8, 4))
    days = {ts.tz_convert("US/Pacific").date() for ts in df["timestamp"]}
    assert days == {date(2026, 8, 4)}


def test_buggy_bare_hhmm_would_use_utc_date():
    """Document the failure mode we fixed: bare HH:MM follows machine date."""
    _PT = pytz.timezone("US/Pacific")
    # Simulate UTC host on Aug 5 while Pacific day is still Aug 4 evening
    with patch("datetime.datetime") as mock_dt:
        # not needed — demonstrate pandas behavior with an explicit wrong date
        pass
    wrong = pd.to_datetime(["2026-08-05 20:00"]).tz_localize(_PT)
    right = pd.to_datetime(["2026-08-04 20:00"]).tz_localize(_PT)
    assert wrong[0].date() != right[0].date()
