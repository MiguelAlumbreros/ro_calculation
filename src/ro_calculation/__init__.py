"""Regulated Retribución a la Operación (RO) for Spanish cogeneration installation types.

Two layers:

- `formula`      — the pure BOE RO formula (`calculate_ro`), no dependency on anything above it.
- `decomposition`/`pipeline` — turn daily futures closes into the regulated averaged
  prices, split each into already-fixed and still-floating parts, and produce RO scenarios.

Typical use::

    from ro_calculation import load_price_frames, run_asof

    df_power, df_gas, df_eua = load_price_frames()
    result = run_asof(date(2026, 7, 24), df_power, df_gas, df_eua, "q3_26")
"""

from .config import (
    INSTALLATION_TYPE,
    STATIC_CONSTANTS,
    ivpee_path,
    pfc_path,
    realised_path,
    parameters_path,
)
from .constants import constants_for, installation_parameters
from .decomposition import (
    averaging_window,
    delivery_window,
    gather_price_components,
    parse_target_quarter,
)
from .formula import REQUIRED_CONSTANTS, calculate_ro
from .pfc import load_pfc
from .realised import realised_ro
from .pipeline import (
    compute_ro_scenarios,
    ivpee_for_quarter,
    load_price_frames,
    run,
    run_asof,
    write_ro_workbook,
)

__all__ = [
    "calculate_ro",
    "REQUIRED_CONSTANTS",
    "STATIC_CONSTANTS",
    "INSTALLATION_TYPE",
    "constants_for",
    "installation_parameters",
    "ivpee_path",
    "parameters_path",
    "parse_target_quarter",
    "averaging_window",
    "delivery_window",
    "gather_price_components",
    "compute_ro_scenarios",
    "ivpee_for_quarter",
    "load_price_frames",
    "load_pfc",
    "pfc_path",
    "realised_ro",
    "realised_path",
    "write_ro_workbook",
    "run",
    "run_asof",
]

__version__ = "0.1.0"
