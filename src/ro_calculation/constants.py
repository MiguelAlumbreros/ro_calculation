"""Assemble the BOE constant set for a target quarter from the sheets shipped in
the package (`src/ro_calculation/data/`).

Three sources are merged, in this order:

1. `config.STATIC_CONSTANTS`     — taxes, levies, storage canons and gas tolls, still
                                   hardcoded because no sheet carries them yet.
2. `ro_parameters.xlsx`          — the valores propios of the instalación tipo, one row
                                   per (Codigo, Ano). Transcribed from the Anexo of the
                                   orden de parámetros retributivos in force.
3. `IVPEE.xlsx`                  — the IVPEE rate, one row per period. Transcribed from
                                   the Real Decreto-ley measures in IVPEE_rate_history.md.

The IVPEE lookup raises rather than falling back to a default, so a quarter the sheet
does not cover fails loudly instead of being priced off a stale rate. The valores
propios lookup does carry the last year on file forward, with a warning — the orden de
parámetros retributivos only ever covers the current regulatory subperiod, so far-dated
quarters would otherwise be unpriceable.
"""

from __future__ import annotations

import warnings
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import cache
from .config import (
    INSTALLATION_TYPE,
    STATIC_CONSTANTS,
    ivpee_path,
    parameters_path,
)
from .decomposition import parse_target_quarter


__all__ = [
    "ivpee_for_quarter",
    "installation_parameters",
    "constants_for",
]


# Column in IVPEE.xlsx holding the rate the RO calculation is to be run with. This
# is not always the rate actually levied: where a Real Decreto-ley cut the base imponible
# but the RO was still set on the statutory 7%, the two differ (q2_26 is the known case),
# and the CNMC claws the difference back through the liquidación of the régimen
# retributivo específico instead. `tipo_efectivo_pct` in the same sheet holds the levied
# rate, for reference.
_IVPEE_RATE_COLUMN = "tipo_usado_en_RO_pct"

# ro_parameters.xlsx column (text before the unit parenthesis) → constant name.
_PARAMETER_COLUMNS: dict[str, str] = {
    "VC":         "Vc",           # consumo de combustible, MWhPCI/MWhE
    "CO&MyOtros": "C_OYM_OTROS",  # coste de operación y mantenimiento y otros, €/MWhE
    "VCO2":       "V_CO2",        # emisiones, tCO2/MWhE
    "VIVPEE-RI":  "V_IVPEE_RI",   # horas equivalentes usadas para repartir RINV, horas
    "VAC":        "V_AC",         # ajuste de mercado. NOTE — the sheet heads this column
                                  # "(%)" while formula.py uses it as a tanto por uno. It
                                  # is 0 for every row present, so the two agree today;
                                  # revisit the scaling before using a non-zero VAC.
    "VHV":        "V_HV",         # término variable del calor útil, MWhPCI/MWhE
    "VHF":        "V_HF",         # término fijo del calor útil, €/MWhE
    "INE":        "I_HE",         # estimación de los ingresos no eléctricos, €/MWhE
    "Potros":     "P_OTROS",      # otros conceptos del precio de compra, €/MWhE
    "Rinv":       "RINV",         # retribución a la inversión para el año «n», €/MW
}


def _normalise(header: object) -> str:
    """'CO&MyOtros  (EUR/MWhE)' -> 'CO&MyOtros'; drop the unit parenthesis."""
    return str(header).split("(")[0].strip()


def _quarter_start(target_quarter: str) -> date:
    year, quarter = parse_target_quarter(target_quarter)
    return date(year, 3 * quarter - 2, 1)


@lru_cache(maxsize=None)
def _ivpee_periods(path: Path, mtime_ns: int) -> tuple[tuple[pd.Timestamp, pd.Timestamp, float], ...]:
    """The sheet's periods as (start, end, rate), in sheet order; a blank end is open.

    Keyed on the file's modification time, as everything in `cache` is, so editing the
    sheet still takes effect while a run over many quarters parses it once.
    """
    df = cache.read_excel(path, "tipos")
    ends = df["end_period"].fillna(pd.Timestamp.max)
    return tuple(zip(df["start_period"], ends, df[_IVPEE_RATE_COLUMN]))


@lru_cache(maxsize=None)
def _valores_propios(
    path: Path, mtime_ns: int, installation_type: str
) -> dict[int, tuple[tuple[str, float], ...]]:
    """Every year on file for `installation_type`, as year -> (name, value) pairs.

    Keyed on modification time for the same reason as `_ivpee_periods`.
    """
    df = cache.read_excel(path).rename(columns=_normalise)

    missing = set(_PARAMETER_COLUMNS) - set(df.columns)
    if missing:
        raise KeyError(f"{path.name} is missing column(s): {sorted(missing)}.")

    for_type = df[df["Codigo"].astype(str).str.strip() == installation_type]
    if for_type.empty:
        raise KeyError(
            f"{path.name} has no rows at all for {installation_type}. "
            f"Add it from the orden de parámetros retributivos in force."
        )

    by_year: dict[int, tuple[tuple[str, float], ...]] = {}
    for _, row in for_type.iterrows():
        by_year.setdefault(int(row["Ano"]), tuple(
            (name, float(row[column])) for column, name in _PARAMETER_COLUMNS.items()
        ))
    return by_year


def ivpee_for_quarter(target_quarter: str) -> float:
    """The IVPEE rate (%) to run `target_quarter` at, from `config.ivpee_path()`.

    Matches the quarter's first day against the sheet's [start_period, end_period]
    ranges; a blank `end_period` means open-ended. Raises `KeyError` if no row covers
    the quarter, or if the row covering it has no rate recorded in the RO column.
    """
    path = ivpee_path()
    if not path.exists():
        raise FileNotFoundError(
            f"IVPEE sheet not found at {path}. Set RO_IVPEE_PATH to point at it."
        )

    start = pd.Timestamp(_quarter_start(target_quarter))
    for period_start, period_end, period_rate in _ivpee_periods(path, path.stat().st_mtime_ns):
        if period_start <= start <= period_end:
            rate = period_rate
            break
    else:
        raise KeyError(
            f"No IVPEE period in {path.name} covers '{target_quarter}' "
            f"({start.date()}). Add a row for it."
        )

    if pd.isna(rate):
        raise KeyError(
            f"The IVPEE period covering '{target_quarter}' in {path.name} has no "
            f"'{_IVPEE_RATE_COLUMN}' recorded. Fill it in — the levied rate and the rate "
            f"the RO is set on are not always the same."
        )
    return float(rate)


def installation_parameters(
    year: int,
    installation_type: str = INSTALLATION_TYPE,
) -> dict[str, float]:
    """The valores propios of `installation_type` for `year`, from `parameters_path()`.

    The parameters are revised per regulatory subperiod, so the sheet routinely stops
    short of the far-dated quarters a long PFC spans. A year with no row of its own
    carries forward the last year on file for that installation type and warns; only an
    installation type absent from the sheet entirely raises `KeyError`.
    """
    path = parameters_path()
    if not path.exists():
        raise FileNotFoundError(
            f"RO parameters sheet not found at {path}. "
            f"Set RO_PARAMETERS_PATH to point at it."
        )

    by_year = _valores_propios(path, path.stat().st_mtime_ns, installation_type)

    if year not in by_year:
        years = sorted(by_year)
        earlier = [y for y in years if y < year]
        fallback_year = earlier[-1] if earlier else years[0]
        warnings.warn(
            f"{path.name} has no row for {installation_type} in {year}; using "
            f"{fallback_year} instead. The RO for that year is priced off stale valores "
            f"propios — add the real row from the orden de parámetros retributivos.",
            stacklevel=2,
        )
        year = fallback_year

    return dict(by_year[year])


def constants_for(
    target_quarter: str,
    installation_type: str = INSTALLATION_TYPE,
) -> dict[str, float]:
    """The full constant set for `target_quarter`: statics + valores propios + IVPEE."""
    year, _ = parse_target_quarter(target_quarter)
    return {
        **STATIC_CONSTANTS,
        **installation_parameters(year, installation_type),
        "IVPEE": ivpee_for_quarter(target_quarter),
    }
