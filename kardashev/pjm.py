from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _pjm


class PJM:
    """
    Direct PJM data client.

    `get_lmp()` still calls legacy DataMiner2 hourly CSV feeds
    (`PJM_USERNAME` / `PJM_PASSWORD`), which PJM decommissioned in 2026-07.
    Prefer `Client.lmp(iso="PJM", ...)` until this class is rewired to
    api.pjm.com. Package helpers for instantaneous load and unverified
    5-min RT LMP already use api.pjm.com (public subscription key /
    optional `PJM_API_KEY`).
    """

    def get_lmp(
        self,
        market: str = "RT",
        node_id: str = "51291",
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """
        LMP prices for a PJM pricing node.
        market='RT' (hourly real-time) or 'DA' (day-ahead hourly).
        Default node 51291 = AEP-GEN hub.
        """
        today = _dt.date.today()
        s = start or today
        e = end or today
        if market.upper() == "DA":
            return _pjm.get_lmp_da_hourly(node_id=node_id, start=s, end=e)
        return _pjm.get_lmp_rt_hourly(node_id=node_id, start=s, end=e)
