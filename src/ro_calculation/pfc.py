"""Load the hourly Price Forward Curve (PFC) and average it over a delivery window.

The PFC is a single deterministic hourly curve, not an asof-based settlement history,
so it stands in only for the *floating* half of decomposition.py's fixed/float split:
the portion of a regulatory averaging window that hasn't been observed yet is drawn
from the PFC's shape instead of a futures close held flat. Already-observed history
(the fixed portion) is left untouched.
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

    The shaping project names its curve columns `<commodity>_<exchange>` (`power_EEX`),
    recording which exchange's marks the curve was built from. The suffix is dropped here
    so callers can look a column up by the bare commodity name used everywhere else.
    """
    df = cache.read_csv(csv_path, parse_dates=("datetime",))
    return df.rename(columns={
        col: commodity
        for col in df.columns
        for commodity in COMMODITY_LEGS
        if col.startswith(f"{commodity}_")
    })


def pfc_average(pfc_df: pd.DataFrame, commodity: str, start: date, end: date) -> float:
    """Mean of `commodity`'s hourly PFC values over `start`..`end` inclusive.

    The bounds are compared as timestamps rather than via `.dt.date`, which would build a
    Python `date` object per hour of the curve on every call. `end` is inclusive of the
    whole day, so the upper bound is the midnight that starts the following day.
    """
    mask = (
        (pfc_df["datetime"] >= pd.Timestamp(start))
        & (pfc_df["datetime"] < pd.Timestamp(end) + pd.Timedelta(days=1))
    )
    values = pfc_df.loc[mask, commodity]
    return float(values.mean()) if len(values) > 0 else float("nan")
