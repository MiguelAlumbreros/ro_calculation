"""Load the hourly Price Forward Curve (PFC) and average it over a delivery window.

`load_pfc` reads the curve file. `pfc_average` averages one commodity's hourly values
over a date range. Pass the loaded curve to `run_asof(..., use_pfc=True)` to source the
still-open portion of each leg from it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from . import cache
from .config import COMMODITY_LEGS


__all__ = ["load_pfc", "pfc_average"]


def load_pfc(csv_path: Path) -> pd.DataFrame:
    """Load the hourly PFC CSV: a `datetime` column plus one column per commodity
    (`power`, `gas`, `EUA`).

    Curve columns named `<commodity>_<exchange>` (for example `power_EEX`) are renamed
    to the bare commodity, so look a column up as `power`, `gas` or `EUA`.
    """
    df = cache.read_csv(csv_path, parse_dates=("datetime",))
    return df.rename(columns={
        col: commodity
        for col in df.columns
        for commodity in COMMODITY_LEGS
        if col.startswith(f"{commodity}_")
    })


def pfc_average(pfc_df: pd.DataFrame, commodity: str, start: date, end: date) -> float:
    """Mean of `commodity`'s hourly PFC values over `start`..`end`.

    Both bounds are inclusive, and `end` covers the whole of that day. Returns NaN if
    the curve has no hours in the range.
    """
    mask = (
        (pfc_df["datetime"] >= pd.Timestamp(start))
        & (pfc_df["datetime"] < pd.Timestamp(end) + pd.Timedelta(days=1))
    )
    values = pfc_df.loc[mask, commodity]
    return float(values.mean()) if len(values) > 0 else float("nan")
