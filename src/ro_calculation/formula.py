"""The RO formula itself, exactly as published in the BOE.

Pure and dependency-free by design: it takes the three averaged price inputs plus
the installation constants and returns a number, so it can be validated field-by-field
against published BOE values without any of the price-sourcing machinery above it.
"""

from __future__ import annotations

from typing import Mapping


__all__ = ["REQUIRED_CONSTANTS", "calculate_ro"]


REQUIRED_CONSTANTS: tuple[str, ...] = (
    "IVPEE",
    "D_RS",
    "TASA_CNMC",
    "TASA_GTS",
    "C_AS_BASE",
    "C_AS_EXTRA",
    "C_I_BASE",
    "C_E_BASE",
    "TC_SA",
    "TV_SA",
    "TC_OCR_J_BASE",
    "TC_RL_J_BASE_1",
    "TC_RL_J_BASE_2",
    "TV_RL_J_BASE",
    "Vc",
    "PCI",
    "C_OYM_OTROS",
    "V_CO2",
    "RINV",
    "V_IVPEE_RI",
    "V_AC",
    "P_OTROS",
    "V_HV",
    "V_HF",
    "I_HE",
)

_REQUIRED_PRICES: tuple[str, ...] = ("P_pvb", "P_m", "P_co2")


def calculate_ro(prices: Mapping[str, float], constants: Mapping[str, float]) -> float:
    """Calculate RO from price inputs and model constants.

    Args:
        prices: Mapping containing `P_pvb`, `P_m`, `P_co2`.
        constants: Mapping containing every key in `REQUIRED_CONSTANTS`.

    Returns:
        Calculated RO value in EUR/MWhE.

    Raises:
        KeyError: If required price keys or constant keys are missing.
    """
    missing_prices = [k for k in _REQUIRED_PRICES if k not in prices]
    if missing_prices:
        raise KeyError(f"Missing required price inputs: {missing_prices}")

    missing_constants = [k for k in REQUIRED_CONSTANTS if k not in constants]
    if missing_constants:
        raise KeyError(f"Missing required constants: {missing_constants}")

    # prices rounded to 3 decimals as calculated in the BOE
    p_pvb = round(prices["P_pvb"], 3)
    p_m = round(prices["P_m"], 3)
    p_co2 = round(prices["P_co2"], 3)

    # CNMC levy + GTS (system technical manager) fee, applied on top of the published
    # toll rates. Both constants are percentages.
    surcharge = 1 + constants["TASA_CNMC"] / 100 + constants["TASA_GTS"] / 100

    # Underground-storage canons: storage (AS), injection (I), extraction (E).
    c_as = constants["C_AS_BASE"] * surcharge + constants["C_AS_EXTRA"]
    c_i = constants["C_I_BASE"] * surcharge
    c_e = constants["C_E_BASE"] * surcharge

    # Storage cost of the mandatory security stock: D_RS days' worth, with injection and
    # extraction weighted at 0.3 (the annual canons are prorated to a daily basis).
    cm_as = constants["D_RS"] / 365 * (c_as + 0.3 * (c_i / 365 + c_e / 365))

    # Gas tolls: national exit (SA), other regasification costs (OCR), local network (RL).
    # Every one of these carries the CNMC/GTS surcharge: the exit-toll rows in the BOE
    # resolution are marked with footnote (1), "valor que ha de ser incrementado con la
    # tasa de la CNMC y con la cuota del GTS". Verified against the resolutions' own
    # published gas price per RL level.
    t_c_sa = constants["TC_SA"] * surcharge
    t_c_ocr_j = constants["TC_OCR_J_BASE"] * surcharge
    # Note: the operator applies the CNMC/GTS surcharge to the unit charges
    # ("cargos unitarios", TC_RL_J_BASE_1) too, although the BOE text does not.
    t_c_rl_j_1 = constants["TC_RL_J_BASE_1"] * surcharge
    t_c_rl_j_2 = constants["TC_RL_J_BASE_2"] * surcharge
    t_v_rl_j = constants["TV_RL_J_BASE"] * surcharge

    # Access/toll component of the delivered gas price, EUR/MWh. Capacity terms are
    # EUR/(kWh/day)/year, so they are divided by 248 (the regulatory equivalent-hours
    # figure) to reach an energy basis; *1000 converts EUR/kWh to EUR/MWh.
    p_e = 1000 * (
        (t_c_sa + t_c_ocr_j + t_c_rl_j_1 + t_c_rl_j_2) / 248
        + constants["TV_SA"] * surcharge
        + t_v_rl_j
        + cm_as
    )

    p_comb = p_pvb + p_e                                        # delivered gas cost
    c_c = p_comb / constants["PCI"] * constants["Vc"]            # fuel cost, EUR/MWhE
    c_co2 = p_co2 * constants["V_CO2"]                           # CO2 allowance cost
    # IVPEE payable on market revenue plus the investment remuneration per equivalent hour.
    c_ivpee_pmri = constants["IVPEE"] / 100 * (
        p_m + constants["RINV"] / constants["V_IVPEE_RI"]
    )
    i_eac = constants["V_AC"] * (p_m + constants["P_OTROS"])     # market-adjustment income
    i_h = p_comb / constants["PCI"] * constants["V_HV"] + constants["V_HF"]  # useful-heat income

    # RO = regulated generation cost minus market/heat income, grossed up for IVPEE
    # (the plant receives RO net of the tax, so the payment is divided by 1 - rate).
    return (
        1 / (1 - constants["IVPEE"] / 100)
        * (
            c_c
            + constants["C_OYM_OTROS"]
            + c_co2
            + c_ivpee_pmri
            - p_m
            - i_eac
            - i_h
            - constants["I_HE"]
        )
    )
