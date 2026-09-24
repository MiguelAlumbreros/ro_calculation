"""Turn a stream of daily futures closes into the regulated averaged prices.

Two things live here:

1. **Windows** — `averaging_window` gives the dates the regulator averages over, and
   `delivery_window` gives the contract those closes belong to.
2. **Fixed / floating split** — for a given `asof`, how much of each window has already
   happened (fixed, an observed mean) and how much is still to come (floating, the last
   close carried forward, or the PFC's tenor average when a curve is supplied), plus the
   day-weighted blend of the two.

`gather_price_components` is the entry point: give it the three price frames and it
returns one row per leg plus a total row per commodity.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, NamedTuple

import numpy as np
import pandas as pd

from .config import (
    COMMODITY_LEGS,
    EXCHANGE_PRIORITY,
    EXCHANGE_ROW_FILTER,
    LEG_PARENT,
    WEIGHTS,
)
from .pfc import pfc_average


__all__ = [
    "parse_target_quarter",
    "averaging_window",
    "delivery_window",
    "gather_price_components",
    "normalize_prices",
    "COMPONENT_COLUMNS",
]


COMPONENT_COLUMNS = [
    "quarter", "commodity", "strip", "fixed", "float",
    "reference", "pct_open", "price_source", "primary_direct",
]

_FIRST_MONTH_OF_QUARTER = {1: 1, 2: 4, 3: 7, 4: 10}
_REQUIRED_STRIPS = {"cal", "quarter", "month"}


class Decomp(NamedTuple):
    fixed: float
    float_value: float
    reference: float
    pct_open: float
    n_fixed: int
    n_float: int


# ── Windows ────────────────────────────────────────────────────────────────────

def parse_target_quarter(target_quarter: str) -> tuple[int, int]:
    """Parse a quarter code like `q2_26` into `(year, quarter)`."""
    parts = target_quarter.lower().split("_")
    if len(parts) != 2 or not parts[0].startswith("q"):
        raise ValueError("target_quarter must look like 'q2_26'.")
    quarter_part = parts[0][1:]
    year_part = parts[1]
    if quarter_part not in {"1", "2", "3", "4"}:
        raise ValueError("Quarter must be one of q1, q2, q3, q4.")
    if not year_part.isdigit() or len(year_part) != 2:
        raise ValueError("Year suffix must be two digits, for example '26'.")
    return int(f"20{year_part}"), int(quarter_part)


def _previous_quarter(year: int, quarter: int) -> tuple[int, int]:
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def averaging_window(target_quarter: str, commodity: str, leg: str) -> tuple[date, date]:
    """Regulatory averaging window for one (target_quarter, commodity, leg).

    Returns the (start_date, end_date) window over which the futures closes are
    averaged to set the regulated price for a given (target_quarter, commodity, leg).
    The window depends on the leg and, for monthly legs, on the commodity:

    - Y  (yearly / Cal):
        June 1 to December 20 of the year *preceding* the target year.
        Example: target q1_26 → 2025-06-01 to 2025-12-20.

    - Q  (quarterly):
        The full *previous* quarter, from day 1 of its first month to day 20
        of its last month.
        Example: target q1_26 → previous quarter is 2025-Q4 →
        2025-10-01 to 2025-12-20.

    - M1, M2, M3 (monthly legs):
        * EUA: same window as Q (the full previous quarter, day 1 of its
          first month to day 20 of its last month). All three monthly legs
          share this window.
        * power / gas: only the *last month* of the previous quarter, from
          day 1 to day 20. All three monthly legs share this window.
          Example: target q1_26 → 2025-12-01 to 2025-12-20.

    Every window ends on day 20. Closes from day 21 to month-end are not averaged.
    """
    year, quarter = parse_target_quarter(target_quarter)

    if leg == "Y":
        return date(year - 1, 6, 1), date(year - 1, 12, 20)

    yp, kp = _previous_quarter(year, quarter)
    first_month_kp = _FIRST_MONTH_OF_QUARTER[kp]
    last_month_kp = first_month_kp + 2

    if leg == "Q":
        return date(yp, first_month_kp, 1), date(yp, last_month_kp, 20)

    if leg in ("M1", "M2", "M3"):
        if commodity == "EUA":
            return date(yp, first_month_kp, 1), date(yp, last_month_kp, 20)
        return date(yp, last_month_kp, 1), date(yp, last_month_kp, 20)

    raise ValueError(f"Unknown leg: {leg}")


def delivery_window(target_quarter: str, leg: str) -> tuple[date, date]:
    """Contract delivery window used to identify the row in the input frame."""
    year, quarter = parse_target_quarter(target_quarter)
    first_month_k = _FIRST_MONTH_OF_QUARTER[quarter]
    last_month_k = first_month_k + 2

    if leg == "Y":
        return date(year, 1, 1), date(year, 12, 31)

    if leg == "Q":
        last_day = (pd.Timestamp(year=year, month=last_month_k, day=1) + pd.offsets.MonthEnd(0)).date()
        return date(year, first_month_k, 1), last_day

    if leg == "M1":
        m = first_month_k
    elif leg == "M2":
        m = first_month_k + 1
    elif leg == "M3":
        m = last_month_k
    else:
        raise ValueError(f"Unknown leg: {leg}")
    last_day = (pd.Timestamp(year=year, month=m, day=1) + pd.offsets.MonthEnd(0)).date()
    return date(year, m, 1), last_day


# ── Fixed / floating decomposition ─────────────────────────────────────────────

def _product_rows(df: pd.DataFrame, delivery_start: date, delivery_end: date) -> pd.DataFrame:
    """The rows of one contract: exactly this delivery window.

    `df` must have been through `normalize_prices`, so that the two delivery columns
    hold datetime64 values. Row order is preserved.
    """
    matches = (
        (df["delivery_date"].to_numpy() == pd.Timestamp(delivery_start).to_datetime64())
        & (df["end_delivery_date"].to_numpy() == pd.Timestamp(delivery_end).to_datetime64())
    )
    return df.take(np.flatnonzero(matches))


def _decompose_product(
    df_prod: pd.DataFrame,
    delivery_start: date,
    delivery_end: date,
    avg_window: tuple[date, date],
    asof: date,
    commodity: str,
    pfc_df: pd.DataFrame | None = None,
) -> Decomp:
    """Decompose one product's mean into fixed (already observed) + floating (still open).

    `df_prod` holds the rows of that one product, as picked out by `_product_rows`.

    Window-day counts are calendar-day differences, not business days.

    The floating portion is the last observed futures close held flat. When `pfc_df` is
    given, it is the mean of the PFC's hourly `commodity` column over the contract's
    delivery window instead. The fixed portion always comes from futures.
    """
    win_start_ts = pd.Timestamp(avg_window[0])
    win_end_ts = pd.Timestamp(avg_window[1])
    asof_ts = pd.Timestamp(asof)

    if df_prod["market_date"].duplicated().any():
        price_conflicts = df_prod.groupby("market_date")["close"].nunique()
        if (price_conflicts > 1).any():
            bad_date = price_conflicts[price_conflicts > 1].index[0].date()
            raise ValueError(
                f"Duplicate market_date rows with conflicting prices for product "
                f"({delivery_start} -> {delivery_end}) on {bad_date}."
            )
        df_prod = df_prod.drop_duplicates(subset=["market_date"], keep="last")

    fixed_cutoff = min(asof_ts, win_end_ts)
    n_fixed = max(0, (fixed_cutoff - win_start_ts).days)
    n_total = max(0, (win_end_ts - win_start_ts).days)
    n_float = max(0, n_total - n_fixed)

    in_fixed = df_prod[
        (df_prod["market_date"] >= win_start_ts)
        & (df_prod["market_date"] <= fixed_cutoff)
    ]
    if n_fixed > 0 and len(in_fixed) > 0:
        fixed_mean = float(in_fixed["close"].mean())
    else:
        fixed_mean = float("nan")

    if n_float > 0 and pfc_df is not None:
        float_value = pfc_average(pfc_df, commodity, delivery_start, delivery_end)
    else:
        pre_asof = df_prod[(df_prod["market_date"] <= asof_ts) & df_prod["close"].notna()]
        if n_float > 0 and len(pre_asof) > 0:
            float_value = float(pre_asof.sort_values("market_date").iloc[-1]["close"])
        else:
            float_value = float("nan")

    if n_float == 0:
        reference = fixed_mean
    elif n_fixed == 0:
        reference = float_value
    elif pd.isna(fixed_mean) or pd.isna(float_value):
        reference = float("nan")
    else:
        reference = (fixed_mean * n_fixed + float_value * n_float) / (n_fixed + n_float)

    denom = n_fixed + n_float
    pct_open = n_float / denom if denom > 0 else 0.0
    pct_open = max(0.0, min(1.0, pct_open))

    return Decomp(fixed_mean, float_value, reference, pct_open, n_fixed, n_float)


# The columns the decomposition reads once an exchange has been picked. Add to this list
# if a new step needs another column from the price frame.
_DECOMP_COLUMNS = ["delivery_date", "end_delivery_date", "market_date", "close"]


def _rows_for_exchange(df: pd.DataFrame, commodity: str, exchange: str) -> pd.DataFrame:
    """Rows for one (commodity, exchange), narrowed to the Spanish product where needed."""
    mask = df["exchange"] == exchange
    for col, val in EXCHANGE_ROW_FILTER.get((commodity, exchange), {}).items():
        mask &= df[col] == val
    return df.loc[mask, _DECOMP_COLUMNS]


def _decompose_with_fallback(
    exchange_frames: Mapping[str, pd.DataFrame],
    target_quarter: str,
    commodity: str,
    leg: str,
    asof: date,
    pfc_df: pd.DataFrame | None = None,
) -> tuple[Decomp, str, str]:
    """Resolve a leg's price, trying exchanges in priority order, then the PFC, then the
    parent leg.

    For each exchange in `EXCHANGE_PRIORITY[commodity]` (primary first), checks whether
    that exchange has any rows for this leg with market_date <= asof; the first exchange
    that does is used (for both its fixed and, absent a PFC, its float portion).

    If no exchange has anything for this exact leg but `pfc_df` covers this commodity,
    the leg is resolved on its own delivery window anyway: fixed stays empty and float
    comes from the PFC.

    Only when neither an exchange nor the PFC has anything does the leg inherit fully
    from its parent leg (`M -> Q -> Y`), which repeats the same search.

    `exchange_frames` maps each exchange in `EXCHANGE_PRIORITY[commodity]` to its rows.
    Build it with `_rows_for_exchange`, once per commodity.

    Returns (decomp, source_leg, source_exchange): source_leg is the leg whose data was
    actually used (== leg unless it propagated from a parent), source_exchange is the
    exchange that data came from (or the primary exchange, as a placeholder, when only
    the PFC had anything).
    """
    delivery_start, delivery_end = delivery_window(target_quarter, leg)
    asof_ts = pd.Timestamp(asof)
    primary_exchange = EXCHANGE_PRIORITY[commodity][0]
    for exchange in EXCHANGE_PRIORITY[commodity]:
        df_prod = _product_rows(exchange_frames[exchange], delivery_start, delivery_end)
        if (df_prod["market_date"] <= asof_ts).any():
            avg_w = averaging_window(target_quarter, commodity, leg)
            decomp = _decompose_product(
                df_prod, delivery_start, delivery_end, avg_w, asof, commodity, pfc_df
            )
            return decomp, leg, exchange
    if pfc_df is not None and commodity in pfc_df.columns:
        avg_w = averaging_window(target_quarter, commodity, leg)
        df_prod = _product_rows(exchange_frames[primary_exchange], delivery_start, delivery_end)
        decomp = _decompose_product(
            df_prod, delivery_start, delivery_end, avg_w, asof, commodity, pfc_df
        )
        return decomp, leg, primary_exchange
    parent = LEG_PARENT.get(leg)
    if parent is None:
        raise ValueError(
            f"No data for {commodity} {leg} as of {asof} on any of "
            f"{EXCHANGE_PRIORITY[commodity]}, and no parent leg to fall back to."
        )
    return _decompose_with_fallback(
        exchange_frames, target_quarter, commodity, parent, asof, pfc_df
    )


_DATE_COLUMNS = ("market_date", "delivery_date", "end_delivery_date")

# Columns compared against a scalar to pick out one exchange's rows (see
# `_rows_for_exchange` and `EXCHANGE_ROW_FILTER`). `normalize_prices` holds them as
# pandas categories.
_FILTER_COLUMNS = ("strip", "exchange", "area", "price_type", "product")


def _is_normalized(df: pd.DataFrame) -> bool:
    """True if `df` has already been through `normalize_prices`."""
    if not all(pd.api.types.is_datetime64_any_dtype(df[c]) for c in _DATE_COLUMNS):
        return False
    if not all(isinstance(df[c].dtype, pd.CategoricalDtype)
               for c in _FILTER_COLUMNS if c in df.columns):
        return False
    return set(df["strip"].dtype.categories) <= _REQUIRED_STRIPS


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the strips the decomposition reads, parse the dates, narrow the dtypes.

    Call it on a frame built by hand; `pipeline.load_price_frames` and
    `pipeline.run_asof` already do it for you. An already-normalised frame is handed
    straight back unchanged, so calling it twice costs nothing.
    """
    if _is_normalized(df):
        return df
    out = df[df["strip"].isin(_REQUIRED_STRIPS)].copy()
    for column in _DATE_COLUMNS:
        out[column] = pd.to_datetime(out[column])
    for column in _FILTER_COLUMNS:
        if column in out.columns:
            out[column] = out[column].astype("category")
    return out


def gather_price_components(
    df_power: pd.DataFrame,
    df_gas: pd.DataFrame,
    df_eua: pd.DataFrame,
    target_quarter: str,
    asof: date | None = None,
    pfc_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build a long-format DataFrame: 5 legs + total per power/gas, total only for EUA.

    A commodity with a single leg (EUA/M3) has no separate leg row. Its total row is
    that leg, at weight 1.0.

    `df_power`/`df_gas`/`df_eua` need only be filtered to their `commodity`. They may
    hold rows from several exchanges, areas and products at once: the right exchange is
    picked per leg via `EXCHANGE_PRIORITY`.

    `pfc_df` is the loaded hourly Price Forward Curve (see `pfc.py`). When given, it
    supplies the floating (still-open) portion of every leg for every commodity present
    in its columns; the fixed portion still comes from futures. Pass `None` to use
    futures for both.
    """
    if asof is None:
        asof = date.today()

    sources = {
        "power": normalize_prices(df_power),
        "gas":   normalize_prices(df_gas),
        "EUA":   normalize_prices(df_eua),
    }

    rows: list[dict] = []
    for commodity in ("power", "gas", "EUA"):
        df = sources[commodity]
        legs = COMMODITY_LEGS[commodity]
        primary_exchange = EXCHANGE_PRIORITY[commodity][0]
        leg_decomp: dict[str, Decomp] = {}
        leg_sources: list[str] = []
        leg_is_primary_direct: list[bool] = []
        commodity_pfc_df = pfc_df if pfc_df is not None and commodity in pfc_df.columns else None
        exchange_frames = {
            exchange: _rows_for_exchange(df, commodity, exchange)
            for exchange in EXCHANGE_PRIORITY[commodity]
        }
        for leg in legs:
            d, source_leg, exchange = _decompose_with_fallback(
                exchange_frames, target_quarter, commodity, leg, asof, commodity_pfc_df
            )
            leg_decomp[leg] = d
            exch_label = exchange if exchange == primary_exchange else f"{exchange} (fallback)"
            futures_source = exch_label if source_leg == leg else f"{exch_label}, propagated from {source_leg}"
            used_pfc = commodity_pfc_df is not None and d.n_float > 0
            if not used_pfc:
                price_source = [futures_source]
            elif d.n_fixed == 0:
                price_source = ["PFC"]
            else:
                price_source = [futures_source, "PFC"]
            leg_sources.append(price_source)
            leg_is_primary_direct.append(source_leg == leg and exchange == primary_exchange and not used_pfc)
            if len(legs) > 1:
                rows.append({
                    "quarter": target_quarter,
                    "commodity": commodity,
                    "strip": leg,
                    "fixed": d.fixed,
                    "float": d.float_value,
                    "reference": d.reference,
                    "pct_open": d.pct_open,
                    "price_source": price_source,
                    "primary_direct": leg_is_primary_direct[-1],
                })

        weights = WEIGHTS[commodity]
        total_fixed = sum(weights[lg] * leg_decomp[lg].fixed for lg in legs)
        total_float = sum(weights[lg] * leg_decomp[lg].float_value for lg in legs)
        total_ref   = sum(weights[lg] * leg_decomp[lg].reference for lg in legs)
        total_pct = sum(weights[lg] * leg_decomp[lg].pct_open for lg in legs)
        if all(leg_is_primary_direct):
            total_source = [primary_exchange]
        else:
            # The distinct sources used across the legs, in leg order.
            total_source = list(dict.fromkeys(s for leg_src in leg_sources for s in leg_src))

        rows.append({
            "quarter": target_quarter,
            "commodity": commodity,
            "strip": "total",
            "fixed": total_fixed,
            "float": total_float,
            "reference": total_ref,
            "pct_open": float(max(0.0, min(1.0, total_pct))),
            "price_source": total_source,
            "primary_direct": all(leg_is_primary_direct),
        })

    return pd.DataFrame(rows, columns=COMPONENT_COLUMNS)
