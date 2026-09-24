"""Memoised reads of the reference sheets.

`read_excel` and `read_csv` parse a file once and hand the same DataFrame back on every
later call. The cache key includes the file's modification time, so editing a sheet on
disk takes effect on the next call without restarting Python.

The DataFrames handed back are shared between callers. Do not modify one in place:
derive a new frame instead, with `.rename`, `.copy()` or a boolean mask.

`futures.csv` does not go through here. Read it with `pipeline.load_price_frames` and
keep the three frames it returns.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd


__all__ = ["read_excel", "read_csv", "clear"]


@lru_cache(maxsize=None)
def _read_excel(path: Path, sheet_name: str | int, mtime_ns: int) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)


@lru_cache(maxsize=None)
def _read_csv(path: Path, parse_dates: tuple[str, ...], mtime_ns: int) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=list(parse_dates))


def read_excel(path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    """`pd.read_excel`, parsed once per (path, sheet, mtime). Do not modify the result."""
    path = Path(path).resolve()
    return _read_excel(path, sheet_name, path.stat().st_mtime_ns)


def read_csv(path: Path, parse_dates: tuple[str, ...] = ()) -> pd.DataFrame:
    """`pd.read_csv`, parsed once per (path, mtime). Do not modify the result."""
    path = Path(path).resolve()
    return _read_csv(path, parse_dates, path.stat().st_mtime_ns)


def clear() -> None:
    """Drop every cached frame. Call it if a file changed without its mtime changing."""
    _read_excel.cache_clear()
    _read_csv.cache_clear()
