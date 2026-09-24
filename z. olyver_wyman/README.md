# RO calculation

Computes the **Retribución a la Operación (RO)** for a Spanish cogeneration (CHP)
installation type, in **€/MWhE**, from forward prices of **power**, **gas** and **CO₂
emission allowances (EUA)** plus a set of per-installation constants.

This document covers **how to call the package** — signatures, inputs, outputs.

---

## Install

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -e .                                    # add [notebooks] for the notebook
```

Requires Python ≥ 3.12. Dependencies: `pandas`, `numpy`, `openpyxl`.

The regulatory sheets (`ro_parameters.xlsx`, `IVPEE.xlsx`, `ro_realised.xlsx`) and the output
template are shipped inside the package; you supply none of them. The market data is yours:
`futures.csv`, the hourly PFC and `holidays.csv` are read from `./data` relative to the folder
you run from, and workbooks are written to `./output`. Run the commands below from the root of
this folder, or set `RO_DATA_DIR` to the folder holding your market data. The notebooks run in
`notebooks/`, so they set `RO_DATA_DIR` to `../data` in their first cell.

---

## Quick start

```python
from datetime import date
from ro_calculation import load_price_frames, run_asof

df_power, df_gas, df_eua = load_price_frames()        # reads data/futures.csv
result = run_asof(date(2026, 7, 24), df_power, df_gas, df_eua, "q2_27")

result["ro_scenarios"]     # {'fixed': nan, 'float': 80.838, 'reference': 80.437}
result["df"]               # full price breakdown + the RO row
```

Or from the command line, which writes a filled workbook to `output/`:

```bash
python -m ro_calculation q2_27 --asof 2026-07-24
```

---

## `run_asof` — one as-of snapshot, in memory

```python
run_asof(asof, df_power, df_gas, df_eua, target_quarter,
         constants=None, use_pfc=False, pfc_csv_path=None)
```

### Arguments

| argument | type | meaning |
|---|---|---|
| `asof` | `date` or `list[date]` | the date you are standing on; decides how much of each averaging window has already elapsed. A list returns a dict keyed by each date. |
| `df_power`, `df_gas`, `df_eua` | `DataFrame` | the three commodity slices from `load_price_frames()`, or your own frames with the same schema — see *Price data*. |
| `target_quarter` | `str` or `list[str]` | the delivery quarter, e.g. `"q4_26"`. A list returns a dict keyed by each quarter. |
| `constants` | `Mapping[str, float]` or `None` | per-installation constants. Defaults to `constants_for(target_quarter)`; pass your own mapping to override, in which case it is used as-is (`IVPEE` not corrected) — see *Installation constants*. |
| `use_pfc` | `bool` | when `True`, sources the floating portion of each leg from the PFC instead of holding the last futures close flat — see *PFC input*. Default `False`. |
| `pfc_csv_path` | `Path` or `None` | override for the PFC CSV location; only used when `use_pfc=True`. Defaults to `config.pfc_path()` (or the `RO_PFC_PATH` environment variable). |

Passing a list for `asof` or `target_quarter` (or both) changes only the return shape:

- scalar / scalar → a single result dict.
- one list → a dict keyed by the listed argument.
- both lists → a dict keyed by `asof`, each value a dict keyed by `target_quarter`.

### Return value

A dict with six keys:

| key | what it is |
|---|---|
| `run_as_of` | the `asof` date you asked for, echoed back |
| `run_as_of_status` | `trading_day`, `weekend` or `holiday` |
| `realised` | `True` when the RO returned is a published figure read from `ro_realised.xlsx` rather than a calculated one — see *Realised quarters* |
| `ro_scenarios` | `{'fixed': float, 'float': float, 'reference': float}`, in €/MWhE |
| `legs` | per leg: which exchange supplied the price, and how many trading days remain in its averaging window. Empty when `realised`. |
| `df` | the component breakdown the scenarios were built from (below). The `RO` row alone when `realised`. |

The three scenarios differ in which prices feed the calculation:

- **`fixed`** — built from closes **already observed** up to `asof`.
- **`float`** — built from the latest close carried forward across the rest of each window
  (or from the PFC, when `use_pfc=True`).
- **`reference`** — the day-weighted blend of the two; **this is normally the figure you
  want**.

`fixed` and `float` are `NaN` when their part of a window is empty — nothing elapsed yet,
or nothing left to come. See *NaN in the output*.

### `result["df"]`

One row per **leg** (`Y`, `Q`, `M1`, `M2`, `M3`) per commodity, plus a `total` row per
commodity, plus a final `RO` row:

```
quarter commodity strip    fixed     float  reference  pct_open                                                                          price_source primary_direct
  q2_27     power     Y 63.03075 70.900000  68.835296  0.737624                                                                                [OMIP]           True
  q2_27     power     Q      NaN 50.770000  50.770000  1.000000                                                                                [OMIP]           True
  q2_27     power    M1      NaN 50.770000  50.770000  1.000000                                                             [OMIP, propagated from Q]          False
  q2_27     power    M2      NaN 50.770000  50.770000  1.000000                                                             [OMIP, propagated from Q]          False
  q2_27     power    M3      NaN 50.770000  50.770000  1.000000                                                             [OMIP, propagated from Q]          False
  q2_27     power total      NaN 55.802500  55.286324  0.934406                                                       [OMIP, OMIP, propagated from Q]          False
  q2_27       gas     Y 36.82225 44.530000  42.507670  0.737624                                                                              [MIBGAS]           True
  q2_27       gas     Q      NaN 41.560000  41.560000  1.000000                                                                              [MIBGAS]           True
  q2_27       gas    M1      NaN 44.639000  44.639000  1.000000                                                                      [EEX (fallback)]          False
  q2_27       gas    M2      NaN 41.678000  41.678000  1.000000                                                                      [EEX (fallback)]          False
  q2_27       gas    M3      NaN 39.198000  39.198000  1.000000                                                                      [EEX (fallback)]          False
  q2_27       gas total      NaN 42.427750  41.922167  0.934406                                                              [MIBGAS, EEX (fallback)]          False
  q2_27       EUA total      NaN 84.950000  84.950000  1.000000                                                                                 [ICE]           True
  q2_27        RO total      NaN 80.838357  80.436517  0.956271 mixed (power: ['OMIP', 'OMIP, propagated from Q']; gas: ['MIBGAS', 'EEX (fallback)'])            NaN
```

Reading it: the `Y` legs are partly elapsed (`pct_open` 0.74, so they have a `fixed` price),
every shorter leg is still fully open (`pct_open` 1, `fixed` is `NaN`), power's monthly legs
had no quotes of their own and took the `Q` price, and gas's monthly legs came from the
fallback exchange — which is why the `RO` row is flagged `mixed`.

| column | meaning |
|---|---|
| `strip` | the leg (`Y`/`Q`/`M1`/`M2`/`M3`), or `total` for the weighted commodity price |
| `fixed` / `float` / `reference` | that leg's price under each scenario, in €/MWh (€/tCO₂ for EUA) — except on the `RO` row, where the three are the RO itself in €/MWhE |
| `pct_open` | share of the averaging window still in the future: `0.0` = fully elapsed, `1.0` = not started |
| `price_source` | a **list** of the distinct sources that contributed, e.g. `["OMIP"]`, `["EEX (fallback)"]`, `["MIBGAS", "EEX (fallback)"]`, or `["OMIP", "PFC"]`. A leg taking its price from its parent leg is noted inline, e.g. `["OMIP, propagated from Q"]`. On the `RO` row this is instead a diagnostic string: `"consistent"`, or `"mixed (<commodity>: <price_source>; ...)"` naming the commodities that were not `primary_direct`. |
| `primary_direct` | `True` when the leg came straight from its primary exchange — no fallback, no propagation, no PFC |

---

## `run` — end-to-end, writes a workbook

```python
run(target_quarter, asof=None, csv_path=None, template_path=None, out_dir=None,
    constants=None, use_pfc=False, pfc_csv_path=None) -> pd.DataFrame
```

Loads the CSV, computes the scenarios, writes a filled copy of the workbook template
shipped in the package into `output/`, and returns the components frame
(the same `df` as `run_asof`). Same calculation as `run_asof`; `template_path` and `out_dir`
override the defaults, `asof` defaults to today.

CLI equivalent:

```bash
python -m ro_calculation <quarter> --asof <YYYY-MM-DD> [--use-pfc | --pfc-csv <path>]
```

---

## Other entry points

| call | returns |
|---|---|
| `load_price_frames(csv_path=None)` | `(df_power, df_gas, df_eua)` split by `commodity`; defaults to `data/futures.csv` |
| `load_pfc(csv_path)` | the hourly PFC as a `DataFrame`, `datetime` column parsed |
| `constants_for(target_quarter, installation_type="IT-01144")` | the full constant mapping for a quarter |
| `installation_parameters(year, installation_type="IT-01144")` | the per-installation parameters for one year |
| `ivpee_for_quarter(target_quarter)` | the IVPEE rate (%) used for that quarter |
| `calculate_ro(prices, constants)` | the RO in €/MWhE. `prices` is a mapping with `P_m`, `P_pvb`, `P_co2`; `constants` must carry every key in `REQUIRED_CONSTANTS`. Missing keys raise `KeyError`. |
| `parse_target_quarter("q4_26")` | `(2026, 4)` |
| `averaging_window(target_quarter, commodity, leg)` | `(start, end)` of the window a leg is averaged over |
| `delivery_window(target_quarter, leg)` | `(start, end)` of a leg's delivery period |
| `gather_price_components(df_power, df_gas, df_eua, target_quarter, asof=None, pfc_df=None)` | the per-leg decomposition `run_asof` builds its `df` from |
| `compute_ro_scenarios(components, constants)` | the three RO figures from a components frame |
| `realised_ro(target_quarter, asof)` | the published RO for a quarter, or `None` |
| `write_ro_workbook(components, ro_scenarios, target_quarter, template_path, output_path)` | writes the output workbook from a components frame |

---

## Inputs

Market data is read from `./data`, relative to the working directory; the regulatory sheets come
from inside the package. Each location has an environment-variable override:

| file | default location | override |
|---|---|---|
| futures closes | `data/futures.csv` | `csv_path` argument |
| hourly PFC | `data/shaped_curve_wide_hourly_2026-08-26.csv` | `RO_PFC_PATH`, or `pfc_csv_path` |
| trading calendar | `data/holidays.csv` | `RO_HOLIDAYS_PATH` |
| *(the whole `data/` folder)* | `<working directory>/data` | `RO_DATA_DIR` |
| published ROs | shipped in the package | `RO_REALISED_PATH` |
| per-installation parameters | shipped in the package | `RO_PARAMETERS_PATH` |
| IVPEE rates | shipped in the package | `RO_IVPEE_PATH` |

> **Running from another folder.** The three market-data files are looked up under the working
> directory. From anywhere else, set `RO_DATA_DIR` first:
> ```python
> import os; os.environ["RO_DATA_DIR"] = r"C:\path\to\z. olyver_wyman\data"
> ```
> `holidays.csv` is loaded lazily and only feeds the `trading_days_remaining` figures in `legs`,
> so everything else runs without it.

### Price data — `data/futures.csv`

A long table of daily futures closes; one **row per contract per trading day**. Columns
consumed downstream (any others are ignored):

| column | dtype | role |
|---|---|---|
| `commodity` | str | `power`, `gas` or `EUA` — how `load_price_frames` splits the file |
| `exchange` | str | source exchange (`OMIP`, `EEX`, `MIBGAS`, `ICE`) |
| `area` / `product` / `price_type` | str | sub-filters applied per `(commodity, exchange)` — see *Exchange selection* |
| `strip` | str | contract granularity; only `cal`, `quarter`, `month` are kept |
| `delivery_date` | date | first day of the contract's delivery window |
| `end_delivery_date` | date | last day of the delivery window; together with `delivery_date` this identifies the product |
| `market_date` | date | the trading day on which `close` was observed |
| `close` | float | the price that enters the averages |

Notes on the schema:

- A single product (fixed `delivery_date` + `end_delivery_date`) appears on **many rows**,
  one per `market_date`; that series is what gets averaged.
- Dates are coerced to datetimes on input, and rows whose `strip` is not
  `cal`/`quarter`/`month` are dropped.
- Duplicate `market_date` rows for the same product on the same exchange are tolerated only
  when their `close` agrees; conflicting prices on the same day raise `ValueError`.

#### Exchange selection

Per leg, each commodity is taken from its primary exchange, falling back to the next when
the primary has no data by `asof` (`config.EXCHANGE_PRIORITY`):

| commodity | primary | fallback |
|---|---|---|
| power | OMIP | EEX |
| gas | MIBGAS | EEX (PVB product only) |
| EUA | ICE | *(none)* |

Rows are narrowed per `(commodity, exchange)` by `config.EXCHANGE_ROW_FILTER`: OMIP/EEX
power to `area == "ES"`, EEX gas to `product == "PVB"`, MIBGAS to
`price_type == "reference"`. Fallback is decided **per leg**, so power `M1` can come from
EEX while `M2`/`M3` still come from OMIP.

### PFC input — `use_pfc=True`

`run()` / `run_asof()` accept `use_pfc=True` (plus an optional `pfc_csv_path`) to source the
**floating** portion of every leg from an hourly Price Forward Curve rather than from a
futures close held flat. The PFC file has one row per hour, a `datetime` column, and one
column per commodity it covers (`power`, `gas`, `EUA` — matched by name). Only commodities
present as columns are affected; the rest use futures throughout. The `fixed` portion is
always futures-sourced.

`use_pfc=True` also lets a leg with no futures quote at all resolve on its own delivery
window, which is what makes far-dated quarters (typically EUA) computable. Legs the PFC
contributed to carry `"PFC"` in `price_source` and `primary_direct = False`.

### Installation constants

`constants_for(target_quarter)` assembles the mapping passed to `calculate_ro` from three
sources:

| source | supplies | keyed by |
|---|---|---|
| `config.STATIC_CONSTANTS` | taxes, levies, storage canons, gas tolls, `PCI` | nothing — a manual snapshot |
| `ro_parameters.xlsx` (packaged) | `Vc`, `C_OYM_OTROS`, `V_CO2`, `V_IVPEE_RI`, `V_AC`, `V_HV`, `V_HF`, `I_HE`, `P_OTROS`, `RINV` | (installation type, year) |
| `IVPEE.xlsx` (packaged) | `IVPEE` | period |

`run()` and `run_asof()` call it automatically when `constants` is left as `None`; an
explicit `constants` argument is used as-is.

The installation type defaults to `config.INSTALLATION_TYPE` (`IT-01144`); pass
`installation_type` to `constants_for` / `installation_parameters` for another. An
installation type absent from the sheet raises `KeyError`. A year absent for a type that is
present carries the last year on file forward and emits a `UserWarning`.

`ivpee_for_quarter` matches the quarter's first day against the `start_period`/`end_period`
range of the `tipos` sheet (a blank `end_period` is open-ended) and reads the
`tipo_usado_en_RO_pct` column. No covering period, or a blank value in one, raises
`KeyError`.

`STATIC_CONSTANTS` is a manual snapshot at the **RL11** gas-toll level; the `TC_*`/`TV_*`
entries are level-dependent and have to be updated when changing target quarter or
connection point.

---

## Realised quarters

`run_asof` / `run` first check whether the quarter's RO has already been published; if so
that figure is returned verbatim and nothing is calculated. A quarter counts as realised
when **both** hold:

1. `asof` has reached the target quarter's first day (`q3_26` → `2026-07-01`); and
2. `ro_realised.xlsx` has a row for that quarter and for `config.INSTALLATION_TYPE`.

```python
run_asof(date(2026, 8, 27), ..., "q3_26")["ro_scenarios"]   # {'fixed': 55.377, 'float': 55.377, 'reference': 55.377}
run_asof(date(2026, 6, 30), ..., "q3_26")["ro_scenarios"]   # {'fixed': 55.536, 'float': nan, 'reference': 55.536}
```

The result keeps the same shape, so frames from both paths still concatenate — but
`realised` is `True`, `legs` is empty, `df` holds only the `RO` row (`price_source =
"realised"`, `pct_open = 0.0`), and all three scenarios are equal. No futures, PFC or
constants are read on this path. A quarter with no row falls through to the normal
calculation; a **missing sheet raises**.

`ro_realised.xlsx` has one row per (quarter, installation type), with the quarter
labelled `<yy>Q<n>` rather than the `q<n>_<yy>` code used everywhere else:

| quarter | IT | ro |
|---|---|---|
| `26Q3` | `IT-01144` | `55.377` |

---

## NaN in the output

Missing prices are not substituted; they propagate as `NaN` into the affected scenario.

1. **A leg with no data at all up to `asof`** → the fallback exchange is tried, then the PFC
   (when `use_pfc=True` covers that commodity), then the parent leg (`M → Q → Y`), which is
   recorded as `["<exchange>, propagated from <leg>"]`. If even the `Y` leg has no data on
   any exchange and no PFC is supplied, it raises `ValueError`.
2. **A leg with gaps** → the gaps are skipped; the average ignores missing days. A leg
   becomes `NaN` only when a whole needed sub-window has nothing usable: `fixed` when the
   elapsed part has no valid close, `float` when there is no valid close at or before
   `asof`.
3. **Any `NaN` leg makes its commodity total `NaN`**, and that scenario's RO is set to
   `NaN` — `calculate_ro` is never called with `NaN` inputs. The three scenarios are
   evaluated independently, so a valid `reference` RO can coexist with a `NaN` `fixed` RO.

**Not every `NaN` means missing data.** `fixed` is `NaN` before a window opens and `float`
is `NaN` after one fully closes, by construction. A `NaN` scenario indicates missing prices
only where a number is expected — e.g. a `NaN` `reference`, or a `NaN` `fixed` after the
window has closed.

---

## Layout

```
src/ro_calculation/
├── formula.py           # calculate_ro — the RO from three averaged prices + constants
├── config.py            # leg weights, exchange selection, static constants, paths
├── constants.py         # assembles the constant set for a quarter from the packaged sheets
├── decomposition.py     # averaging/delivery windows + the fixed/floating split
├── realised.py          # published ROs, short-circuiting the calculation
├── trading_calendar.py  # trading-day counts from the holidays feed
├── pipeline.py          # run / run_asof / workbook output
├── __main__.py          # CLI
└── data/                # shipped with the package — you supply none of these
    ├── ro_realised.xlsx        # published ROs
    ├── ro_parameters.xlsx      # per-installation parameters
    ├── IVPEE.xlsx              # IVPEE rate per period
    └── ro_output_template.xlsx # the workbook run() fills in
data/                    # the market data you supply — see Inputs
notebooks/               # test_run.ipynb, ro_from_pfc.ipynb — worked examples of the calls above
output/                  # generated workbooks and exports
```

`formula.py` imports nothing from the rest of the package, so `calculate_ro` can be called
on its own with a constant mapping and three prices.
