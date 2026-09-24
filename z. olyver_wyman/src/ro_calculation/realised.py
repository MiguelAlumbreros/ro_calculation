"""Look up an already-published (realised) RO.

The sheet at `config.realised_path()` has one row per (quarter, instalación tipo):

    quarter  IT        ro
    26Q3     IT-01144  55.377

Only rows for `config.INSTALLATION_TYPE` are read.
"""

from __future__ import annotations

from datetime import date

from . import cache
from .config import INSTALLATION_TYPE, realised_path
from .decomposition import parse_target_quarter


__all__ = ["realised_ro"]


def _quarter_key(year: int, quarter: int) -> str:
    """(2026, 3) -> '26Q3', the quarter label used in the realised sheet."""
    return f"{year % 100:02d}Q{quarter}"


def realised_ro(target_quarter: str, asof: date) -> float | None:
    """The published RO for `target_quarter` in EUR/MWhE, or None.

    A quarter counts as realised from its own first day onwards. Standing on an earlier
    `asof`, or on a quarter the sheet has no row for, the return value is None and the
    caller estimates the RO instead.

    The sheet ships inside the package. Raises FileNotFoundError if it is missing; set
    RO_REALISED_PATH to point at another copy.
    """
    year, quarter = parse_target_quarter(target_quarter)
    if asof < date(year, 3 * quarter - 2, 1):
        return None

    path = realised_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Realised RO sheet not found at {path}. "
            f"Set RO_REALISED_PATH to point at it."
        )

    df = cache.read_excel(path)
    match = df[
        (df["quarter"].astype(str).str.strip().str.upper() == _quarter_key(year, quarter))
        & (df["IT"].astype(str).str.strip() == INSTALLATION_TYPE)
    ]
    if match.empty:
        return None
    return float(match["ro"].iloc[0])
