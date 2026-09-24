"""Regulated Retribución a la Operación (RO) for Spanish cogeneration installation types.

Two layers:

- `formula.calculate_ro` is the RO formula on its own. Give it three prices and the
  constants and it returns a number.
- `decomposition` and `pipeline` turn daily futures closes into those prices, split each
  into an already-fixed and a still-floating part, and produce the RO scenarios.

Typical use::

    from datetime import date
    from ro_calculation import load_price_frames, run_asof

    df_power, df_gas, df_eua = load_price_frames()
    result = run_asof(date(2026, 7, 24), df_power, df_gas, df_eua, "q3_26")
    print(result["ro_scenarios"]["reference"])

Pass a list of quarters, or of as-of dates, or both, to run several at once. Load the
price frames once and reuse them.

Set RO_HOLIDAYS_PATH, RO_PFC_PATH, RO_REALISED_PATH, RO_IVPEE_PATH or
RO_PARAMETERS_PATH to read any input from outside the project's data/ folder.
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
