# RO calculation

Computes the regulated **Retribución a la Operación (RO)** for Spanish cogeneration (CHP)
installation types, from forward market prices of **power**, **gas**, and **CO₂ emission
allowances (EUA)** plus the per-installation constants published in the BOE.

---

## Quick start

The main pipeline is **`run_asof`**: *"standing on date `asof`, what will the RO for
`target_quarter` be?"*

```python
from datetime import date
from ro_calculation import load_price_frames, run_asof

df_power, df_gas, df_eua = load_price_frames()        # reads data/futures.csv
result = run_asof(date(2026, 7, 24), df_power, df_gas, df_eua, "q4_26")

result["ro_scenarios"]     # {'fixed': nan, 'float': nan, 'reference': 56.21}
result["df"]               # full price breakdown + the RO row
```

`asof` and `target_quarter` each also accept a **list**, which returns a nested dict keyed
by as-of date and/or quarter — useful for tracking how the estimate moves as a window fills up.

### Arguments

| argument | type | meaning |
|---|---|---|
| `asof` | `date` or `list[date]` | the date you're standing on; decides how much of each averaging window has already elapsed (see *Fixed vs floating*). A list returns a dict keyed by each date. |
| `df_power`, `df_gas`, `df_eua` | `DataFrame` | the three commodity slices from `load_price_frames()` (or your own frames with the same schema — see *Structure of `df_power`/`df_gas`/`df_eua`*). |
| `target_quarter` | `str` or `list[str]` | the delivery quarter being remunerated, e.g. `"q4_26"`. A list returns a dict keyed by each quarter. |
| `constants` | `Mapping[str, float]` or `None` | per-installation BOE constants. Defaults to `constants_for(target_quarter)`, assembled from `STATIC_CONSTANTS` plus the packaged `ro_parameters.xlsx` and `IVPEE.xlsx`; pass your own mapping to override (used as-is, `IVPEE` not corrected) — see *Installation constants*. |
| `use_pfc` | `bool` | when `True`, sources the floating portion of each leg from the PFC instead of holding the last futures close flat — see *PFC input*. Default `False`. |
| `pfc_csv_path` | `Path` or `None` | override for the PFC CSV location; only used when `use_pfc=True`. Defaults to `config.pfc_path()` (or `RO_PFC_PATH`). |

### What the output represents

`run_asof` returns a dict with six keys:

| key | what it is |
|---|---|
| `run_as_of` | the `asof` date you asked for, echoed back |
| `run_as_of_status` | `trading_day`, `weekend` or `holiday` — a weekend/holiday `asof` means no new closes landed that day |
| `realised` | `True` when the RO below is the **published** BOE figure rather than an estimate — see *Realised quarters* |
| `ro_scenarios` | the three headline RO figures, in **€/MWhE** |
| `legs` | per leg: which exchange the price came from, and how many trading days are left in its averaging window (empty when `realised`) |
| `df` | the full component breakdown the scenarios were built from (below); the `RO` row alone when `realised` |

The **three scenarios** exist because the regulated price is an average over a window that is
usually only partly elapsed. `fixed` is the RO implied by *only what is already locked in*;
`float` is the RO if today's forward prices held for the rest of every window; **`reference` is
the number you normally want** — the day-weighted blend of the two, i.e. the current best estimate
of what the BOE will eventually publish. `fixed` and `float` are `NaN` whenever their part of the
window is empty (nothing elapsed yet, or nothing left to come); that is by design, not missing
data — see *Missing futures data*.

`result["df"]` is one row per **leg** (`Y`, `Q`, `M1`, `M2`, `M3`) per commodity, plus a `total`
row per commodity, plus a final `RO` row:

```
quarter commodity strip     fixed   float  reference  pct_open                              price_source primary_direct
  q4_26     power     Y 61.090828     NaN  61.090828  0.000000                                    [OMIP]           True
  q4_26     power     Q 98.952222 114.300 109.941989  0.716049                                    [OMIP]           True
  q4_26     power    M1       NaN 115.020 115.020000  1.000000                                    [OMIP]           True
  ...
  q4_26     power total       NaN     NaN  99.685804  0.664815                                    [OMIP]           True
  q4_26       gas    M2       NaN  61.661  61.661000  1.000000                          [EEX (fallback)]          False
  q4_26       gas total       NaN     NaN  53.222158  0.664815                  [MIBGAS, EEX (fallback)]          False
  q4_26       EUA total 81.121667  83.400  82.753066  0.716049                                     [ICE]           True
  q4_26        RO total       NaN     NaN  56.210887  0.681893 mixed (gas: ['MIBGAS', 'EEX (fallback)'])            NaN
```

| column | meaning |
|---|---|
| `strip` | the leg (`Y`/`Q`/`M1`/`M2`/`M3`), or `total` for the weighted commodity price |
| `fixed` / `float` / `reference` | that leg's price under each scenario, in €/MWh (€/tCO₂ for EUA) — except on the `RO` row, where they are the RO itself in €/MWhE |
| `pct_open` | share of the averaging window still in the future: `0.0` = fully settled and can no longer move, `1.0` = hasn't started |
| `price_source` | a **list** of the distinct sources that contributed, e.g. `["OMIP"]`, `["EEX (fallback)"]`, `["MIBGAS", "EEX (fallback)"]` (legs use different exchanges), or `["OMIP", "PFC"]` (blended with the PFC — see *PFC input*). A leg propagated from its parent is noted inline, e.g. `["OMIP, propagated from Q"]`. On the `RO` row this is instead a diagnostic string: `"consistent"`, or `"mixed (<commodity>: <price_source>; ...)"` listing which commodities weren't `primary_direct`. |
| `primary_direct` | `True` when the leg came straight from its primary exchange with no fallback, propagation, or PFC blending — i.e. nothing to double-check |

Reading the example above: the `Y` leg is fully settled (`pct_open` 0), the monthly legs haven't
started (`pct_open` 1, so `fixed` is `NaN`), and gas `M2`/`M3` had no MIBGAS quotes yet so they
fell back to EEX — which is why the RO row is flagged `mixed`. The `q4_26` RO currently references
**56.21 €/MWhE**, with ~68% of the averaging still open.

To write the result to the formatted Excel template instead, use `run()` or the CLI — see
*Entry points*.

---

## Install

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -e .                                     # add [notebooks] for the notebooks
```

Then either import it or run it:

```bash
python -m ro_calculation q3_26 --asof 2026-07-24
```

The regulatory sheets (`ro_parameters.xlsx`, `IVPEE.xlsx`, `ro_realised.xlsx`) and the output
template ship **inside the package**, so an ordinary `pip install` of this repo is enough to
calculate an RO. The market data is **yours to supply**: `futures.csv`, the hourly PFC and
`holidays.csv` are read from `./data` relative to the directory you run from, and workbooks are
written to `./output`. Set `RO_DATA_DIR` to read the market data from another folder (the
notebooks point it at `../data`), or pass explicit paths to `run()` / `run_asof()`.

## Layout

```
src/ro_calculation/
├── formula.py           # the pure BOE RO formula (calculate_ro) — no dependencies upward
├── config.py            # leg weights, exchange sourcing, static BOE constants, paths
├── constants.py         # assembles the constant set for a quarter from the packaged sheets
├── decomposition.py     # averaging/delivery windows + the fixed/floating split
├── realised.py          # already-published ROs, short-circuiting the calculation
├── trading_calendar.py  # trading-day counts from the shared holidays feed
├── pipeline.py          # run / run_asof / workbook output
├── __main__.py          # CLI
└── data/                # shipped with the package — no need to supply these
    ├── ro_realised.xlsx        # already-published ROs
    ├── ro_parameters.xlsx      # valores propios per (instalación tipo, year)
    ├── IVPEE.xlsx              # IVPEE rate per period
    └── ro_output_template.xlsx # the workbook run() fills in
data/                    # market data you supply, read relative to the working directory
├── futures.csv          # daily exchange closes (versioned)
├── holidays.csv         # trading calendar, copied from the sibling 1.2 Daily shaping project
├── shaped_curve_wide_hourly_*.csv   # hourly PFC
└── ro_realised_inputs.xlsx  # the published inputs behind each realised RO (verification)
output/                  # generated workbooks and exports (gitignored)
notebooks/               # test_run.ipynb, pfc_with_ro.ipynb, ro_from_pfc.ipynb, scrape_boe_constants.ipynb
docs/
├── boe/                 # boe_guide.txt: which BOE holds what (the PDFs are local-only)
│   └── IVPEE/           # IVPEE_rate_history.md — the RDLs behind IVPEE.xlsx
├── OCV tool/            # third-party spreadsheet, not part of the pipeline
├── product_open_dates.txt   # the regulatory averaging windows, verbatim
└── peajes_gas_RL3_formula.md
```

The two layers are deliberately separable:

- [`formula.py`](src/ro_calculation/formula.py) — the **pure RO formula** (`calculate_ro`). No
  dependency on the layers above it, so it can be tested/validated against published BOE values
  in isolation.
- [`decomposition.py`](src/ro_calculation/decomposition.py) +
  [`pipeline.py`](src/ro_calculation/pipeline.py) — the **orchestration layer**: they turn a stream
  of daily futures closes into the regulated averaged prices, split each price into its
  already-fixed and still-floating parts, and call `calculate_ro` to produce RO scenarios.

---

## Inputs

### 1. Price data — `data/futures.csv`

A long table of daily futures closes, refreshed from the market-data pipeline. It is tens of MB
and regenerated regularly, so `data/` is **gitignored** — the file has to be present locally.
Relevant columns:

| column | meaning |
|---|---|
| `commodity` | `power`, `gas`, or `EUA` |
| `exchange` | source exchange (`OMIP`, `EEX`, `MIBGAS`, `ICE`) — see *Exchange sourcing* below |
| `area` | delivery area (used to isolate Spain on exchanges that carry other countries) |
| `product` | contract family (used to isolate the PVB gas hub on EEX, which also carries Dutch TTF) |
| `price_type` | for MIBGAS only: `last` (last traded) vs `reference` (settlement) — the settlement price is used |
| `strip` | contract granularity — `cal`, `quarter`, `month` are used (others ignored) |
| `market_date` | the trading day the close was observed |
| `delivery_date` / `end_delivery_date` | the contract's delivery window (identifies the product) |
| `close` | settlement/close price used in the averages |

The frame is split into three inputs before being passed in — just by `commodity`, since
exchange/area/product selection happens inside `gather_price_components`. `load_price_frames`
does this for you:

```python
from ro_calculation import load_price_frames

df_power, df_gas, df_eua = load_price_frames()   # defaults to data/futures.csv
```

#### Exchange sourcing

Per leg, each commodity has a **primary exchange** and, if the primary has no data by `asof`,
a **fallback exchange** (`EXCHANGE_PRIORITY`):

| commodity | primary | fallback |
|---|---|---|
| power | OMIP | EEX |
| gas | MIBGAS | EEX (PVB product only) |
| EUA | ICE | *(none)* |

`_rows_for_exchange` narrows a given exchange's rows to the Spanish product where the exchange
also carries other countries/hubs (`EXCHANGE_ROW_FILTER`): OMIP/EEX power to `area == "ES"`, EEX
gas to `product == "PVB"` (excluding Dutch TTF and the PVB/TTF spread product). MIBGAS additionally
carries two price series per contract (`price_type` `last` vs `reference`); only `reference`
(settlement) is used, matching the BOE's "precio de cierre (settlement price)" wording.

`_decompose_with_fallback` tries the primary exchange first, then the fallback, for **each leg
independently** — so, for example, power `M1` can come from EEX (fallback) while `M2`/`M3` still
come from OMIP. Only if *no* exchange has data for a leg does it fall through to the PFC (if one
was supplied) or inherit from the parent leg (`M → Q → Y`) — see *Missing futures data* below. The
`price_source` column in the output is a list recording which source(s) (exchange, and/or `PFC`)
were actually used.

#### Structure of `df_power` / `df_gas` / `df_eua`

All three are slices of the same table, so they share one schema. Each **row is one contract's
close on one trading day**. Only these columns are consumed downstream (via `_normalize_input`,
`_rows_for_exchange`, and `_decompose_product`); any others are ignored:

| column | dtype | role |
|---|---|---|
| `exchange` | str | source exchange — selected per leg via `EXCHANGE_PRIORITY` |
| `area` / `product` / `price_type` | str | sub-filters applied per `(commodity, exchange)`, see *Exchange sourcing* |
| `strip` | str | contract granularity — only rows in `{cal, quarter, month}` are kept; identifies the leg family |
| `delivery_date` | date | first day of the contract's delivery window |
| `end_delivery_date` | date | last day of the contract's delivery window — together with `delivery_date` this **identifies the product** (e.g. a specific quarter or month contract) |
| `market_date` | date | the trading day on which `close` was observed |
| `close` | float | the settlement/close price that enters the averages |

Notes:

- A single product (fixed `delivery_date` + `end_delivery_date`) appears on **many rows**, one per
  `market_date` — that time series is what gets averaged over the regulatory window.
- `_normalize_input` coerces `market_date`, `delivery_date`, `end_delivery_date` to datetimes and
  drops any row whose `strip` is not `cal`/`quarter`/`month`.
- Duplicate `market_date` rows for the same product **on the same exchange** are tolerated only if
  their `close` agrees; conflicting prices on the same day raise a `ValueError`. This is why the
  MIBGAS `last`/`reference` duplication above must be filtered out before this check runs.
- The three frames differ only in which products they contain: `df_power` carries Spanish power
  Cal/Q/month contracts from OMIP and EEX, `df_gas` the PVB gas contracts from MIBGAS and EEX,
  `df_eua` the EUA contracts from ICE (only the relevant month is used for EUA).

### 1a. PFC data — `data/shaped_curve_5year_hourly_<date>.csv` (optional, for `use_pfc`)

Only needed when calling `run()`/`run_asof()` with `use_pfc=True`. Produced by the sibling
*1.1 Hourly shaping v2* project and copied into `data/` alongside `futures.csv`: one row per
hour, a `datetime` column, and one column per commodity it covers (`power`, `gas`, `EUA` — column
names matched by string equality against `commodity`). `load_pfc` parses `datetime` and returns
the frame as-is; `pfc_average` takes the mean of a commodity's column over a given date range. See
*PFC input* below for how this feeds into the fixed/floating split.

### 2. Installation constants

The CHP installation-type parameters from the BOE resolution for the target quarter (heat
rate `Vc`, O&M `C_OYM_OTROS`, CO₂ factor `V_CO2`, gas tolls, RL-level toll constants,
investment remuneration `RINV`, etc.). `constants_for(target_quarter)` in
[`constants.py`](src/ro_calculation/constants.py) assembles the set from three sources:

| Source | What it supplies | Keyed by |
|---|---|---|
| `STATIC_CONSTANTS` in [`config.py`](src/ro_calculation/config.py) | taxes, levies, storage canons, gas tolls, `PCI` | nothing — a manual snapshot |
| [`ro_parameters.xlsx`](src/ro_calculation/data/ro_parameters.xlsx) | the *valores propios*: `Vc`, `C_OYM_OTROS`, `V_CO2`, `V_IVPEE_RI`, `V_AC`, `V_HV`, `V_HF`, `I_HE`, `P_OTROS`, `RINV` | (instalación tipo, year) |
| [`IVPEE.xlsx`](src/ro_calculation/data/IVPEE.xlsx) | `IVPEE` | period (see below) |

`run()` and `run_asof()` call this automatically whenever `constants` is left as the
default (`None`); an explicit `constants` argument is used as-is, uncorrected.

`STATIC_CONSTANTS` is still a manual snapshot — currently the **RL11** gas-toll level,
verified field-by-field against
the Resolución de 2 de julio de 2026
([BOE-A-2026-14552](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-14552)). Update it per BOE when changing
target quarter or connection point.
[`notebooks/scrape_boe_constants.ipynb`](notebooks/scrape_boe_constants.ipynb) scrapes a
BOE text and diffs it against the assembled set.

Which installation type is read from `ro_parameters.xlsx` defaults to
`config.INSTALLATION_TYPE` (`IT-01144`); pass `installation_type` to `constants_for` or
`installation_parameters` for another. A missing (type, year) row raises `KeyError` rather
than falling back to a neighbouring year.

#### IVPEE — quarterly-varying tax rate

`IVPEE` (impuesto sobre el valor de la producción de energía eléctrica) has been
temporarily cut below its 7% statutory rate by a series of Real Decreto-ley crisis-response
measures, with a different rate almost every quarter. `ivpee_for_quarter` reads it from the
`tipos` sheet of [`IVPEE.xlsx`](src/ro_calculation/data/IVPEE.xlsx), matching the quarter's first day
against the sheet's `start_period`/`end_period` range (a blank `end_period` is open-ended).

The column read is **`tipo_usado_en_RO_pct`**, not `tipo_efectivo_pct`. The two differ
where a Real Decreto-ley cut the base imponible but the RO was still set on the statutory
7% — `q2_26` is the known case (0% levied, 7% used) — with the CNMC clawing the difference
back through the liquidación of the régimen retributivo específico instead. A period with
`tipo_usado_en_RO_pct` blank, or no period covering the quarter at all, raises `KeyError`
rather than silently using a stale or wrong rate.

Current sheet: 2025 7.0%; 2026 Q1 7.0% (6.3% levied), Q2 7.0% (0% levied), Q3 4.9%, Q4 4.2%;
2027 3.5%; 2028+ 0.0%. Q1 and Q2 2026 keep the statutory rate because their resolutions were
set on it — confirmed by recomputing the published ROs (see *Verifying against published ROs*).
The legal basis of every row is in
[`docs/boe/IVPEE/IVPEE_rate_history.md`](docs/boe/IVPEE/IVPEE_rate_history.md), alongside
the source RDL PDFs.

## Verifying against published ROs

`calculate_ro` has been checked by recomputing every RO the BOE has already published and
diffing it against [`ro_realised.xlsx`](src/ro_calculation/data/ro_realised.xlsx), with three
independent checks per quarter, all against figures the resolution itself publishes:

1. **Storage cost** — our `cm_as` vs the resolution's *coste medio de almacenamiento subterráneo*.
2. **Gas tolls** — our `P_pvb + p_e` vs the resolution's own gas price at RL11.
3. **RO** — the full `calculate_ro` vs every published value.

Inputs come from `data/ro_realised_inputs.xlsx`, one row per quarter transcribed from the
resolution PDFs listed in [`docs/boe/boe_guide.txt`](docs/boe/boe_guide.txt), so the check isolates
the formula and the valores propios from the price averaging upstream.

As of 2026-08-31 all **21 values** (7 quarters × 3 instalaciones tipo) reproduce to within
**0.0008 €/MWhE** — the BOE rounds both its inputs and its ROs to 3 decimals, so that is the
floor. All three installation types are at the **RL11** gas-toll level.

Two quirks are encoded in the inputs sheet rather than inferred:

- **26Q1 uses the 2025 valores propios.** Its resolution predates Orden TED/53/2026 (27 Jan
  2026) and cites Orden TED/526/2024 throughout, so the 2026 parameters did not yet apply.
  Its `valores_propios_year` is therefore 2025.
- **26Q1 and 26Q2 use the statutory 7% IVPEE**, not the reduced rate — see
  [`docs/boe/IVPEE/IVPEE_rate_history.md`](docs/boe/IVPEE/IVPEE_rate_history.md).

### 2a. Realised RO — `ro_realised.xlsx`

The ROs the BOE has already published, transcribed by hand from the quarterly
resolutions listed in [`docs/boe/boe_guide.txt`](docs/boe/boe_guide.txt). One row per (quarter, instalación tipo), with the quarter
labelled `<yy>Q<n>` rather than the `q<n>_<yy>` code used elsewhere:

| quarter | IT | ro |
|---|---|---|
| `26Q3` | `IT-01144` | `55.377` |

Only the row for `config.INSTALLATION_TYPE` (`IT-01144` — the installation the pipeline
models) is read back; the other installation types are carried for reference. Add a row per
quarter as each resolution is published. See *Realised quarters* for when it short-circuits the
calculation. Overridable with the `RO_REALISED_PATH` environment variable.

### 3. Target quarter and as-of date

- `target_quarter` — the delivery quarter being remunerated, e.g. `"q3_26"`.
- `asof` — the date you are standing on. It decides how much of each averaging window has
  already happened (see *Fixed vs floating* below).

### 4. Trading calendar — `holidays.csv`

`run_asof` reports how many **trading days remain** in each averaging window. Non-trading days
come from a holidays file produced by the sibling *1.2 Daily shaping* project, mapped per commodity
via `COMMODITY_CALENDAR`. A copy of it lives at `data/holidays.csv`; the default path is
`<working directory>/data/holidays.csv`, overridable with the `RO_HOLIDAYS_PATH` environment
variable. It is loaded lazily, so the rest of the pipeline runs without it — refresh the copy from
the sibling project when that project's calendar changes.

`COMMODITY_CALENDAR` is independent from `EXCHANGE_PRIORITY` above: the holidays feed only
covers EEX and ICE, so it is used for the trading-day calendar regardless of which exchange
actually supplied the price (e.g. gas trading days are approximated off the ICE calendar even
though prices normally come from MIBGAS).

---

For how the three averaged prices feed into the RO formula itself — the toll/canon build-up,
fuel/CO₂/heat components, and the final gross-up — see
[`docs/calculation.md`](docs/calculation.md).

## Realised quarters

Before anything is decomposed, `run_asof`/`run` ask a prior question: **has the BOE already
published this quarter's RO?** If so there is nothing to estimate, and the published figure is
returned verbatim ([`realised.py`](src/ro_calculation/realised.py)).

A quarter counts as realised when **both** hold:

1. `asof` has reached the target quarter's first day (`q3_26` → `2026-07-01`). The resolution is
   published in the opening days of the quarter, and every averaging window has closed before the
   quarter starts. Standing on an earlier `asof` the figure was not yet known, so it is estimated
   as usual — which is what keeps backtests across historical as-of dates meaningful.
2. `ro_realised.xlsx` has a row for that quarter and for `config.INSTALLATION_TYPE`.

```python
run_asof(date(2026, 8, 27), ..., "q3_26")["ro_scenarios"]   # {'fixed': 55.377, 'float': 55.377, 'reference': 55.377}
run_asof(date(2026, 6, 30), ..., "q3_26")["ro_scenarios"]   # {'fixed': 55.525, 'float': nan, 'reference': 55.525}
```

A realised result keeps the same shape as a calculated one, so frames from both paths still
concatenate — but `realised` is `True`, `legs` is empty, `df` holds only the `RO` row
(`price_source = "realised"`, `pct_open = 0.0`), and all three scenarios are equal, since a
published RO can no longer move. Neither the futures CSV, the PFC, nor the BOE constants are
touched on this path, so a realised quarter also needs no row in `IVPEE.xlsx`.

A quarter the sheet has no row for (not yet published, or not yet transcribed) falls through to
the normal calculation. A **missing sheet raises** rather than silently estimating.

## Fixed vs floating

For any `asof`, an averaging window is split at that date (`_decompose_product`):

- **Fixed** — the part of the window **already elapsed** (`win_start … min(asof, win_end)`).
  Its price is the **mean of the closes actually observed** in that sub-window. This part can no
  longer change.
- **Floating** — the part of the window **still in the future** (`asof … win_end`). It has no
  observed closes yet, so it is estimated by **carrying forward the last observed close** on or
  before `asof` — or, when `use_pfc=True`, by the **PFC's tenor average** instead (see *PFC input*
  below). Either way, the fixed portion is never touched.
- **Reference** — the day-weighted blend of the two, i.e. what the final regulated price is
  currently expected to be:

  ```
  reference = (fixed * n_fixed + float * n_float) / (n_fixed + n_float)
  pct_open  = n_float / (n_fixed + n_float)      # share of the window still open
  ```

  Day counts are calendar days (an approximation vs. exchange settlement days, sufficient for the
  weighting). When the window is fully in the past, `reference == fixed` and `pct_open == 0`;
  when it hasn't started, `reference == float` and `pct_open == 1`.

If a leg has no futures data at all by `asof`, `_decompose_with_fallback` falls through to the PFC
(when one covers this commodity) or, failing that, **inherits from its parent leg** (`M → Q → Y`);
either way the output marks how, in `price_source` — see *Missing futures data* below.

### RO scenarios

`compute_ro_scenarios` runs `calculate_ro` three times — once on the **fixed** totals, once on
the **float** totals, once on the **reference** totals — giving three RO figures:

- **fixed RO** — RO implied by only what is already locked in (NaN until at least one full leg is fixed).
- **float RO** — RO if today's forward prices held for the rest of every window.
- **reference RO** — the current best estimate, blending the two.

### PFC input

`run()` / `run_asof()` accept `use_pfc=True` (plus an optional `pfc_csv_path` override) to source
the **floating** portion of every leg from an hourly Price Forward Curve instead of a futures close
held flat. For a given leg, the PFC value is the mean of its hourly column over the leg's
**delivery window** (`delivery_window`) — e.g. `Y` averages every hour of the target year, `M2`
averages every hour of the quarter's second month. Only commodities present as columns in the PFC
are affected (matched by name: `power`, `gas`, `EUA`); the rest keep using futures for both fixed
and float. The fixed portion is always futures-sourced regardless of `use_pfc`.

When no exchange has any futures data at all for a leg, `use_pfc=True` also changes *which* window
gets used for its price: instead of inheriting the parent leg's price (`M → Q → Y`), the leg is
resolved on its own delivery window with the PFC supplying its (fully open) float — see *Missing
futures data* below. This is why `use_pfc=True` alone is enough to cover far-future quarters that
otherwise raise for lack of any futures quote (e.g. EUA, whose exchange only lists near-term
contracts).

When PFC contributes to a leg, `price_source` includes `"PFC"` as one of its list entries — e.g.
`["PFC"]` for a fully open leg, or `["OMIP", "PFC"]` for a partially elapsed one — and
`primary_direct` becomes `False` for that leg. The default PFC location is `config.pfc_path()`
(overridable with the `RO_PFC_PATH` environment variable or `pfc_csv_path`).

---

## Missing futures data

Missing futures prices are **not faked or (usually) turned into an error** — they become `NaN`
that propagates up to the affected RO scenario. There are three mechanisms, applied in this order:

1. **A leg with no data at all up to `asof` → try the fallback exchange, then the PFC, then
   inherit the parent leg.** `_decompose_with_fallback` first tries each exchange in
   `EXCHANGE_PRIORITY[commodity]` in order (primary, then fallback). If none of them have data for
   that leg and `use_pfc=True` covers this commodity, the leg is resolved on its own delivery
   window anyway, with the PFC supplying its (fully open) float — `price_source` becomes
   `["PFC"]`. Only if neither an exchange nor the PFC has anything does it fall back `M → Q → Y`
   and mark the row `price_source = ["<exchange>, propagated from <leg>"]` (rather than producing
   NaN). The one hard failure: if even the yearly `Y` leg has no data on any exchange and no PFC
   is supplied, there is no parent and it raises `ValueError`.

2. **A leg that has data but with gaps → the gaps are skipped.**
   In `_decompose_product` the fixed price is `close.mean()`, which ignores missing days. A leg
   only becomes NaN when a whole *needed* sub-window has nothing usable:
   - `fixed` is NaN when the **elapsed** part of the window has no valid close;
   - `float` is NaN when there is no valid close **at or before `asof`** (it filters `close.notna()`).

3. **Any NaN leg poisons the commodity total → the RO scenario is `NaN`.**
   The `power`/`gas`/`EUA` `total` is a plain weighted **sum** of its legs, so a single NaN leg
   makes the whole total NaN for that column. `compute_ro_scenarios` then checks
   `P_m`/`P_pvb`/`P_co2` and sets that scenario to `NaN` — `calculate_ro` is **never called with
   NaN inputs**. Each scenario (fixed / float / reference) is evaluated independently, so a valid
   `reference` RO can coexist with a `NaN` `fixed` RO.

**Not every NaN means missing data.** By design, `fixed` is NaN *before* a window opens (nothing
elapsed yet) and `float` is NaN *after* a window fully closes (nothing left to carry forward). A
NaN RO scenario only indicates missing futures when it appears where a real number is expected —
e.g. `reference` RO is NaN, or `fixed` RO is NaN after the window has already closed.

`use_pfc=True` (see *PFC input* above) sources the floating portion from the PFC instead of a
futures close, and prefers a leg's own PFC window over inheriting a parent leg's price — between
the two, this removes both the `float` gaps and the hard `ValueError` for whatever horizon the PFC
covers. The fixed portion, and any commodity absent from the PFC, still follow the rules above.

## Entry points

- **`run_asof(asof, df_power, df_gas, df_eua, target_quarter, constants=None, use_pfc=False, pfc_csv_path=None)`**
  — one as-of snapshot. Returns the as-of date and its trading-calendar status, whether the
  quarter was already `realised`, the three RO scenarios, per-leg `price_source` and
  `trading_days_remaining`, and the full components DataFrame with an appended `RO` row.
  In-memory only. Either of `asof`/`target_quarter` also accepts a list, returning a nested dict.
- **`run(target_quarter, asof=None, ..., use_pfc=False, pfc_csv_path=None)`** — end-to-end batch:
  load CSV → decompose → compute RO scenarios → write the filled output workbook from a template.
  Also available as `python -m ro_calculation <quarter> --asof <date> [--use-pfc | --pfc-csv <path>]`.

See [`notebooks/test_run.ipynb`](notebooks/test_run.ipynb) for `run_asof` exercised across as-of
dates that probe each window transition, including the exchange-fallback paths, and
[`notebooks/pfc_with_ro.ipynb`](notebooks/pfc_with_ro.ipynb) for extending the hourly PFC with an
`RO` column (one RO per delivery quarter, realised where published).
