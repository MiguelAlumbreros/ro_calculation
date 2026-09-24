"""Static configuration: file locations, leg weights, exchange sourcing, BOE constants.

Edit this file when the BOE publishes new toll or levy values, or when the price feed
gains an exchange. Every path function below can be overridden with an environment
variable, which is the way to run against data held outside the working directory.
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
# Two kinds of file:
#
# - Shipped inside the package, in src/ro_calculation/data/: ro_parameters.xlsx,
#   IVPEE.xlsx, ro_realised.xlsx and the output template. You supply none of them.
# - Supplied by you: futures.csv, the PFC and holidays.csv are read from ./data, and
#   workbooks are written to ./output, both relative to the current working directory.
#   Set RO_DATA_DIR to read the market data from somewhere else. A notebook runs in
#   notebooks/, so the notebooks set RO_DATA_DIR to ../data.
PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"


def data_dir() -> Path:
    """Folder the market data is read from: RO_DATA_DIR, else ./data."""
    override = os.environ.get("RO_DATA_DIR")
    return Path(override) if override else Path.cwd() / "data"


def templates_dir() -> Path:
    """Folder holding the output workbook template."""
    return PACKAGE_DATA_DIR


def output_dir() -> Path:
    """Folder `run` writes workbooks to: ./output."""
    return Path.cwd() / "output"


# Trading calendar. Needed only for the trading-day counts `run_asof` reports.
# Override with RO_HOLIDAYS_PATH.
def holidays_path() -> Path:
    override = os.environ.get("RO_HOLIDAYS_PATH")
    return Path(override) if override else data_dir() / "holidays.csv"


# Hourly Price Forward Curve. Override with RO_PFC_PATH, or pass an explicit path to
# run()/run_asof() as `pfc_csv_path`.
def pfc_path() -> Path:
    override = os.environ.get("RO_PFC_PATH")
    return Path(override) if override else data_dir() / "shaped_curve_wide_hourly_2026-08-26.csv"


# Already-published (realised) RO values, one row per (quarter, instalación tipo).
# Override with RO_REALISED_PATH.
def realised_path() -> Path:
    override = os.environ.get("RO_REALISED_PATH")
    return Path(override) if override else PACKAGE_DATA_DIR / "ro_realised.xlsx"


# IVPEE rate per period, one row per period. Override with RO_IVPEE_PATH.
def ivpee_path() -> Path:
    override = os.environ.get("RO_IVPEE_PATH")
    return Path(override) if override else PACKAGE_DATA_DIR / "IVPEE.xlsx"


# Valores propios de cada instalación tipo, one row per (instalación tipo, year).
# Override with RO_PARAMETERS_PATH.
def parameters_path() -> Path:
    override = os.environ.get("RO_PARAMETERS_PATH")
    return Path(override) if override else PACKAGE_DATA_DIR / "ro_parameters.xlsx"


# ── Leg structure ──────────────────────────────────────────────────────────────
# Weight of each leg in a commodity's blended price. The weights sum to 1.
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
# In priority order: the first entry is the primary source, the rest are tried in turn
# when the primary has no data for a leg.
EXCHANGE_PRIORITY: dict[str, list[str]] = {
    "power": ["OMIP", "EEX"],
    "gas":   ["MIBGAS", "EEX"],
    "EUA":   ["ICE"],
}

# Extra column filters that isolate the Spanish product where an exchange carries other
# areas or products under the same commodity. EEX power spans ES/DE/FR/IT; EEX gas spans
# the Spanish PVB hub and the Dutch TTF hub; MIBGAS carries a traded and a settlement
# price series per contract, and the settlement one is used.
EXCHANGE_ROW_FILTER: dict[tuple[str, str], dict[str, str]] = {
    ("power", "OMIP"):  {"area": "ES"},
    ("power", "EEX"):   {"area": "ES"},
    ("gas", "MIBGAS"):  {"price_type": "reference"},
    ("gas", "EEX"):     {"product": "PVB"},
    ("EUA", "ICE"):     {},
}

# RO commodity → (exchange, commodity) in the holidays file. The holidays feed covers
# EEX and ICE only, so gas trading days are counted off the ICE calendar.
COMMODITY_CALENDAR: dict[str, tuple[str, str]] = {
    "power": ("EEX", "power"),
    "gas":   ("ICE", "gas"),
    "EUA":   ("ICE", "eua"),
}


# ── Installation constants ─────────────────────────────────────────────────────
# The instalación tipo the pipeline models: which row of ro_parameters.xlsx supplies the
# valores propios, and which row of the realised-RO sheet is read back.
INSTALLATION_TYPE = "IT-01144"

# The hardcoded part of the constant set: taxes, levies, storage canons and gas tolls,
# at the RL11 gas-toll level. Two blocks are not here and come from data/ instead:
#   - IVPEE               → data/IVPEE.xlsx, keyed by period
#   - the valores propios → data/ro_parameters.xlsx, keyed by (instalación tipo, year)
#
# Update the values below per BOE when changing target quarter or connection point.
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

    # ── Gas tolls (peajes), RL (red local) level 11 ──
    "TC_SA": 0.091488,       # término fijo de capacidad del peaje de salida de transporte
                             # (salida nacional), €/(kWh/día)/año
    "TV_SA": 0.0,            # término variable de volumen del peaje de salida, €/kWh
    "TC_OCR_J_BASE": -0.010160,  # término fijo de capacidad del peaje de otros costes de
                                 # regasificación, escalón «j», €/(kWh/día)/año
    "TC_RL_J_BASE_1": 0.006140,  # cargos unitarios del escalón «j», €/(kWh/día)/año.
                                 # The CNMC/GTS surcharge is applied to these.
    "TC_RL_J_BASE_2": 0.139655,  # término fijo de capacidad de red local, escalón «j»,
                                 # €/(kWh/día)/año
    "TV_RL_J_BASE": 0.000046,    # término variable de red local, escalón «j», €/kWh

    # ── Conversion assumption ──
    "PCI": 0.9,              # conversión de gas a electricidad
}
