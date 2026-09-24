"""Memoised reads of the reference sheets, keyed on path and modification time.

A multi-quarter run fans out over (asof, quarter) pairs, and every pair re-parsed
`ro_parameters.xlsx`, `IVPEE.xlsx` and `ro_realised.xlsx` from scratch — about half a
second a pair, almost all of it inside openpyxl. The loaders here parse a file once and
hand back the same frame afterwards.

The cache key carries the file's `st_mtime_ns`, so editing a sheet in place — the usual
way a newly published BOE value arrives — is picked up without restarting the kernel.
The frames handed back are shared between callers, so treat them as read-only: derive a
new frame (`.rename`, `.copy()`, a boolean mask) rather than assigning into one.

`futures.csv` deliberately does not go through here. It is read once per `run` and the
frame is over 300 MB, which is not worth holding for the lifetime of the process.
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
    """Drop every cached frame. Only needed if a file changed without its mtime moving."""
    _read_excel.cache_clear()
    _read_csv.cache_clear()
