"""Look up an already-published (realised) RO instead of estimating one.

Once the BOE has published a quarter's RO there is nothing left to estimate, so the
pipeline short-circuits to the published figure rather than averaging futures closes.

The sheet (`config.realised_path()`) has one row per (quarter, instalación tipo):

    quarter  IT        ro
    26Q3     IT-01144  55.377

Only `config.INSTALLATION_TYPE` is read back, since that is the installation the
pipeline models by default.
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
    """The published RO for `target_quarter` in €/MWhE, or None if it isn't realised yet.

    A quarter counts as realised from its own first day onwards: the BOE publishes the
    resolution in the opening days of the quarter, and every averaging window has closed
    before it starts. Standing on an earlier `asof` the figure was not yet known, so
    `None` is returned and the caller estimates it as usual — which is what keeps
    backtests over historical as-of dates meaningful.

    `None` is also returned for a quarter the sheet has no row for (not yet published,
    or not yet transcribed). A missing sheet raises rather than silently estimating.
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
