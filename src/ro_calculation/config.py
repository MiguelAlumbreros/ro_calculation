"""Static configuration: leg weights, exchange sourcing, tax schedule, BOE constants.

Everything here is a manual snapshot of published regulation or of the shape of the
price feed. It changes when the BOE publishes, not when the code does.
"""

from __future__ import annotations

import os
from pathlib import Path


__all__ = [
    "WEIGHTS",
    "COMMODITY_LEGS",
    "LEG_PARENT",
    "EXCHANGE_PRIORITY",
    "COMMODITY_CALENDAR",
    "STATIC_CONSTANTS",
    "INSTALLATION_TYPE",
    "holidays_path",
    "pfc_path",
    "realised_path",
    "ivpee_path",
    "parameters_path",
    "data_dir",
    "templates_dir",
    "output_dir",
]


# ── File layout ────────────────────────────────────────────────────────────────
# Two kinds of file, resolved differently so the package works once pip-installed:
#
# - Regulatory reference sheets and the output template ship inside the package
#   (src/ro_calculation/data/). They are the same for every user and version with the code.
# - Market data (futures.csv, the PFC, holidays.csv) and outputs belong to the caller and
#   are resolved against the current working directory: ./data and ./output. Set
#   RO_DATA_DIR to read market data from elsewhere (the notebooks point it at ../data).
PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"


def data_dir() -> Path:
    override = os.environ.get("RO_DATA_DIR")
    return Path(override) if override else Path.cwd() / "data"


def templates_dir() -> Path:
    return PACKAGE_DATA_DIR


def output_dir() -> Path:
    return Path.cwd() / "output"


# Trading calendar, produced by the sibling "1.2 Daily shaping" project. Only
# `run_asof`'s trading-day counts need it. Override with RO_HOLIDAYS_PATH.
def holidays_path() -> Path:
    override = os.environ.get("RO_HOLIDAYS_PATH")
    return Path(override) if override else data_dir() / "holidays.csv"


# Hourly Price Forward Curve, produced by the sibling "1.1 Hourly shaping v2" project and
# copied into data/ alongside futures.csv. Override with the RO_PFC_PATH environment
# variable, or pass an explicit path to run()/run_asof() when use_pfc=True.
def pfc_path() -> Path:
    override = os.environ.get("RO_PFC_PATH")
    return Path(override) if override else data_dir() / "shaped_curve_wide_hourly_2026-08-26.csv"


# Already-published (realised) RO values, transcribed from the BOE resolutions listed in
# docs/boe/boe_guide.txt. One row per (quarter, installation type). Override with the
# RO_REALISED_PATH environment variable.
def realised_path() -> Path:
    override = os.environ.get("RO_REALISED_PATH")
    return Path(override) if override else PACKAGE_DATA_DIR / "ro_realised.xlsx"


# IVPEE rate per period, transcribed from the Real Decreto-ley measures listed in
# docs/boe/IVPEE/IVPEE_rate_history.md (the legal basis of each row).
# Override with the RO_IVPEE_PATH environment variable.
def ivpee_path() -> Path:
    override = os.environ.get("RO_IVPEE_PATH")
    return Path(override) if override else PACKAGE_DATA_DIR / "IVPEE.xlsx"


# Valores propios de cada instalación tipo, per year, transcribed from the Anexo of the
# orden de parámetros retributivos in force (currently Orden TED/53/2026, Anexos IV and
# X.A). Override with the RO_PARAMETERS_PATH environment variable.
def parameters_path() -> Path:
    override = os.environ.get("RO_PARAMETERS_PATH")
    return Path(override) if override else PACKAGE_DATA_DIR / "ro_parameters.xlsx"


# ── Leg structure ──────────────────────────────────────────────────────────────
WEIGHTS: dict[str, dict[str, float]] = {
    "power": {"Y": 0.25, "Q": 0.30, "M1": 0.15, "M2": 0.15, "M3": 0.15},
    "gas":   {"Y": 0.25, "Q": 0.30, "M1": 0.15, "M2": 0.15, "M3": 0.15},
    "EUA":   {"M3": 1.0},
}

COMMODITY_LEGS: dict[str, list[str]] = {
    "power": ["Y", "Q", "M1", "M2", "M3"],
    "gas":   ["Y", "Q", "M1", "M2", "M3"],
    "EUA":   ["M3"],
}

# Leg a missing leg inherits its price from, when no exchange has data for it.
LEG_PARENT: dict[str, str] = {"M1": "Q", "M2": "Q", "M3": "Q", "Q": "Y"}


# ── Price-data sourcing ────────────────────────────────────────────────────────
# In priority order: first entry is the primary source, the rest are fallbacks tried
# (in order) when the primary has no data for a leg.
EXCHANGE_PRIORITY: dict[str, list[str]] = {
    "power": ["OMIP", "EEX"],
    "gas":   ["MIBGAS", "EEX"],
    "EUA":   ["ICE"],
}

# Extra column filters to isolate the Spanish product on exchanges that also carry
# other areas/products under the same `commodity`/`exchange` (e.g. EEX power spans
# ES/DE/FR/IT; EEX gas spans the Spanish PVB hub and the Dutch TTF hub).
EXCHANGE_ROW_FILTER: dict[tuple[str, str], dict[str, str]] = {
    ("power", "OMIP"):  {"area": "ES"},
    ("power", "EEX"):   {"area": "ES"},
    # MIBGAS carries two price series per contract ("last" traded vs "reference"
    # settlement, see `price_type`); the regulatory averaging uses settlement prices.
    ("gas", "MIBGAS"):  {"price_type": "reference"},
    ("gas", "EEX"):     {"product": "PVB"},
    ("EUA", "ICE"):     {},
}

# RO commodity → (exchange, commodity) in the holidays file. Independent from
# EXCHANGE_PRIORITY: the holidays feed only covers EEX and ICE, so gas trading days
# are approximated off the ICE calendar even though prices come from MIBGAS.
COMMODITY_CALENDAR: dict[str, tuple[str, str]] = {
    "power": ("EEX", "power"),
    "gas":   ("ICE", "gas"),
    "EUA":   ("ICE", "eua"),
}


# ── Installation constants ─────────────────────────────────────────────────────
# The instalación tipo the pipeline models by default: which row of ro_parameters.xlsx
# supplies the valores propios, and which row of the realised-RO sheet is read back.
INSTALLATION_TYPE = "IT-01144"

# The part of the constant set that is still hardcoded. Two blocks are NOT here because
# they come from data/ instead — see `constants.py`:
#   - IVPEE               → data/IVPEE.xlsx, keyed by period
#   - the valores propios → data/ro_parameters.xlsx, keyed by (instalación tipo, year)
#
# What remains are the taxes, levies, storage canons and gas tolls, taken from the
# Resolución de 2 de julio de 2026 (BOE-A-2026-14552) at the RL11 gas-toll level.
# These are quarter- and RL-dependent: update them per BOE when changing target quarter
# or connection point.
STATIC_CONSTANTS: dict[str, float] = {
    # ── Taxes and levies (percentages) ──
    "TASA_CNMC": 0.14,       # tasa de la Comisión Nacional de los Mercados y la Competencia
    "TASA_GTS": 1.354,       # cuota del Gestor Técnico del Sistema

    # ── Underground storage (almacenamiento subterráneo) ──
    "D_RS": 20.6,            # días de existencias mínimas de seguridad exigidos por la normativa
                             # vigente; no cuentan los días exentos del pago de canon
    "C_AS_BASE": 0.002525,   # término fijo del canon de almacenamiento subterráneo
    "C_AS_EXTRA": 0,         # prima de las subastas de adjudicación de la capacidad
    "C_I_BASE": 0.141516,    # canon de inyección, €/(kWh/día)/año
    "C_E_BASE": 0.101405,    # canon de extracción, €/(kWh/día)/año

    # ── Gas tolls (peajes). The TC_*/TV_* below depend on the RL (red local) level;
    #    this set is RL11. See docs/peajes_gas_RL3_formula.md. ──
    "TC_SA": 0.091488,       # término fijo de capacidad del peaje de salida de transporte
                             # (salida nacional), €/(kWh/día)/año
    "TV_SA": 0.0,            # término variable de volumen del peaje de salida, €/kWh
    "TC_OCR_J_BASE": -0.010160,  # término fijo de capacidad del peaje de otros costes de
                                 # regasificación, escalón «j», €/(kWh/día)/año
    "TC_RL_J_BASE_1": 0.006140,  # cargos unitarios del escalón «j», €/(kWh/día)/año. The BOE
                                 # does not apply the CNMC/GTS surcharge to these; the operator
                                 # does, and formula.py follows the operator.
    "TC_RL_J_BASE_2": 0.139655,  # término fijo de capacidad de red local, escalón «j»,
                                 # €/(kWh/día)/año — CNMC/GTS surcharge applies
    "TV_RL_J_BASE": 0.000046,    # término variable de red local, escalón «j», €/kWh

    # ── Assumption, not a BOE table value ──
    "PCI": 0.9,              # conversión de gas a electricidad; se asume 0.9 para el gas
}
