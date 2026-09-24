"""Trading-calendar lookups backed by the shared holidays feed.

Only `run_asof`'s "how many trading days are left in this window" reporting needs
this; the holidays file is loaded lazily and cached so importing the package never
requires it to be present.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import pandas as pd

from .config import COMMODITY_CALENDAR, holidays_path


__all__ = ["trading_days_remaining", "asof_status"]


@lru_cache(maxsize=1)
def _load_holidays() -> tuple[pd.DataFrame, dict[tuple[str, str], frozenset]]:
    """Load holidays.csv and build non-trading-day sets per (exchange, commodity)."""
    path = holidays_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Holidays file not found at {path}. "
            f"Set RO_HOLIDAYS_PATH to point at it."
        )
    df_hol = pd.read_csv(path, parse_dates=["date"])
    non_trading = {
        (exchange, comm): frozenset(grp["date"].dt.date)
        for (exchange, comm), grp in df_hol.groupby(["exchange", "commodity"])
    }
    return df_hol, non_trading


def trading_days_remaining(asof: date, win_end: date, commodity: str) -> int:
    """Trading days strictly after `asof` up to and including `win_end`."""
    if asof >= win_end:
        return 0
    exchange, comm = COMMODITY_CALENDAR[commodity]
    _, non_trading = _load_holidays()
    non_trading_set = non_trading.get((exchange, comm), frozenset())
    days = pd.date_range(
        start=pd.Timestamp(asof) + pd.Timedelta(days=1),
        end=pd.Timestamp(win_end),
        freq="D",
    )
    return sum(1 for d in days.date if d not in non_trading_set)


def asof_status(asof: date) -> str:
    """Returns 'trading_day', 'weekend', or 'holiday'.

    Checks all exchanges in COMMODITY_CALENDAR. If asof is non-trading on
    any of them, returns the type found (weekends and major holidays overlap).
    """
    df_hol, non_trading = _load_holidays()
    for exchange, comm in set(COMMODITY_CALENDAR.values()):
        non_trading_set = non_trading.get((exchange, comm), frozenset())
        if asof in non_trading_set:
            row = df_hol[
                (df_hol["date"].dt.date == asof)
                & (df_hol["exchange"] == exchange)
                & (df_hol["commodity"] == comm)
            ]
            return str(row.iloc[0]["type"]) if not row.empty else "non_trading"
    return "trading_day"
