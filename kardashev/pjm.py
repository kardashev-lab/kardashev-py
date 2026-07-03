from __future__ import annotations

import datetime as _dt
from datetime import date

import pandas as pd

from kardashev import _pjm


class PJM:
    """
    Direct PJM data client via DataMiner2.

    Requires environment variables:
      PJM_USERNAME and PJM_PASSWORD
    Free account at dataminer2.pjm.com
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
