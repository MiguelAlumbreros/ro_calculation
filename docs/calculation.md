# Calculating the RO

This walks through how the pipeline gets from three averaged commodity prices to a single RO
figure, component by component, matching [`formula.py`](../src/ro_calculation/formula.py) exactly.
See the [README](../README.md) for how those three prices are themselves built up from futures
legs (*Quick start*) and split into fixed/floating parts (*Fixed vs floating*).

### Step 1 — Regulated averaged prices

Each commodity price is a weighted blend of several **legs** (yearly `Y`, quarterly `Q`, and the
three months `M1/M2/M3`), each averaged over its own **regulatory window** (see
[`product_open_dates.txt`](product_open_dates.txt) and `averaging_window`):

| leg | window (target year *n*, quarter *k*) |
|---|---|
| `Y` (Cal) | 1 Jun → 20 Dec of year *n-1* |
| `Q` | full *previous* quarter: day 1 of its first month → day 20 of its last month |
| `M1/M2/M3` (power, gas) | last month of the previous quarter, day 1 → day 20 |
| `M3` (EUA) | same window as `Q` |

Leg weights (`WEIGHTS`):

- **power / gas:** `Y` 0.25, `Q` 0.30, `M1` 0.15, `M2` 0.15, `M3` 0.15
- **EUA:** `M3` 1.0

The weighted totals become the three price inputs to the formula, each rounded to 3 decimals
first (matching the BOE):

- `P_m`  = power total (market power price), €/MWh
- `P_pvb`= gas total (PVB gas price), €/MWh
- `P_co2`= EUA total, €/tCO₂

### Step 2 — The RO formula (`calculate_ro`)

Conceptually, RO is the regulated **generation cost minus market/heat income**, grossed up for
the IVPEE tax:

```
RO = 1/(1 - IVPEE) * ( C_c + C_OYM_OTROS + C_co2 + C_ivpee_pmri
                       - P_m - I_eac - I_h - I_HE )
```

where `IVPEE` here is the tax **rate as a fraction** (the constant is stored as a percentage, so
the code divides it by 100: `4.9` → `0.049`). Everything inside the parentheses is a cost (added)
or an income (subtracted), all in €/MWhE; dividing by `1 - IVPEE` grosses the net amount up so
that, after the plant pays the tax on it, it is left with the intended net RO.

Each term is built up below, in the order `calculate_ro` computes them.

#### Gas access/toll price `P_e`

The delivered gas price isn't just the market PVB price — the plant also pays network tolls and
storage canons to actually take delivery. `P_e` bundles all of that into a single €/MWh add-on to
`P_pvb`.

**CNMC/GTS surcharge.** Most toll and canon components have a percentage surcharge applied on
top: the CNMC fee (`TASA_CNMC`) and the GTS (Gestor Técnico del Sistema) fee (`TASA_GTS`):

```
surcharge = 1 + TASA_CNMC/100 + TASA_GTS/100
```

**Underground storage canons** (*canon de almacenamiento subterráneo*) — storage (`AS`),
injection (`I`), extraction (`E`), each a fixed €/(kWh/día)/año rate, with the surcharge applied
to `AS` and `I`/`E` but not to the extra auction premium `C_AS_EXTRA`:

```
c_as = C_AS_BASE * surcharge + C_AS_EXTRA
c_i  = C_I_BASE * surcharge
c_e  = C_E_BASE * surcharge
```

`D_RS` is the number of days of mandatory security stock (*existencias mínimas de seguridad*) the
plant must hold; the annual `AS`/`I`/`E` canons are prorated to that many days, with `I` and `E`
weighted at 0.3 (only 30% of the stock is assumed to be cycled through injection/extraction each
year):

```
cm_as = D_RS/365 * (c_as + 0.3 * (c_i/365 + c_e/365))
```

**Gas tolls** (*peajes*) — national transport exit (`SA`), other regasification costs (`OCR`), and
local network (`RL`), split into fixed capacity terms (`TC_*`, €/(kWh/día)/año) and variable
volume terms (`TV_*`, €/kWh). The `RL` (red local) level depends on the specific installation's
connection point — `STATIC_CONSTANTS` currently uses **RL11** (see
[`peajes_gas_RL3_formula.md`](peajes_gas_RL3_formula.md) for the RL3 variant):

```
t_c_sa     = TC_SA                          # no surcharge — published net of it
t_c_ocr_j  = TC_OCR_J_BASE * surcharge
t_c_rl_j_1 = TC_RL_J_BASE_1 * surcharge     # "cargos unitarios" — BOE text omits the
                                             # surcharge here, but the operator applies it
                                             # anyway; formula.py follows the operator
t_c_rl_j_2 = TC_RL_J_BASE_2 * surcharge
t_v_rl_j   = TV_RL_J_BASE * surcharge
```

**Assembling `P_e`.** The fixed capacity terms are €/(kWh/día)/año; dividing by 248 (the
regulatory equivalent-hours figure for this installation type) converts that into an energy basis,
and multiplying by 1000 converts €/kWh to €/MWh:

```
P_e = 1000 * ( (t_c_sa + t_c_ocr_j + t_c_rl_j_1 + t_c_rl_j_2) / 248
               + TV_SA + t_v_rl_j + cm_as )
```

#### Delivered gas cost and fuel cost

```
P_comb = P_pvb + P_e                    # delivered gas price, €/MWh
C_c    = P_comb / PCI * Vc              # fuel cost, €/MWhE
```

`PCI` converts gas energy content to the basis used for electricity (fixed at 0.9 for gas); `Vc`
is the installation's fuel consumption per unit of electricity produced (MWh<sub>PCI</sub> per
MWhE) — together they turn a €/MWh gas price into a €/MWhE fuel cost.

#### CO₂ cost

```
C_co2 = P_co2 * V_CO2
```

`V_CO2` is the installation's emissions factor (tCO₂ per MWhE produced).

#### IVPEE on market revenue + investment remuneration

```
C_ivpee_pmri = IVPEE/100 * ( P_m + RINV / V_IVPEE_RI )
```

`RINV` is the annual investment remuneration for the installation (€/MW); dividing by `V_IVPEE_RI`
(the equivalent operating hours used to spread that annual figure) turns it into a €/MWhE rate.
This whole bracket — the market price plus that per-hour investment remuneration — is itself
subject to IVPEE, on top of the overall gross-up applied to the RO total.

#### Market-adjustment income `I_eac`

```
I_eac = V_AC * (P_m + P_OTROS)
```

`V_AC` is a market-adjustment coefficient (currently `0.0` in `data/ro_parameters.xlsx`, i.e. inactive);
`P_OTROS` covers other components of the electricity purchase price besides the market price
itself. When `V_AC` is 0 this whole term drops out.

#### Useful-heat income `I_h`

```
I_h = P_comb / PCI * V_HV + V_HF
```

Cogeneration plants sell the useful heat they produce alongside electricity, which is income that
must be netted against the RO. `V_HV` (MWh<sub>PCI</sub> of heat per MWhE) scales with the same
delivered-gas-price basis as the fuel cost above; `V_HF` is a flat €/MWhE component independent of
the gas price.

#### Other non-electrical income `I_HE`

A flat, installation-specific estimate of non-electrical income (€/MWhE) not otherwise captured
above — folded straight into the RO total as an income (subtracted), with no further computation.

#### O&M `C_OYM_OTROS`

A flat, installation-specific estimate of operation & maintenance and other costs (€/MWhE) —
folded straight into the RO total as a cost (added), with no further computation.

### Putting it together

```
RO = 1/(1 - IVPEE/100) * ( C_c + C_OYM_OTROS + C_co2 + C_ivpee_pmri
                            - P_m - I_eac - I_h - I_HE )
```

Reading it as cost minus income: `C_c` (fuel), `C_OYM_OTROS` (O&M), `C_co2` (CO₂), and
`C_ivpee_pmri` (the IVPEE due on market revenue + investment remuneration) are costs the plant
needs to recover; `P_m` (it already sells at the market price), `I_eac` (market adjustment),
`I_h` (heat sales), and `I_HE` (other income) are income the plant already receives and which
therefore reduce the regulated top-up it still needs. The `1/(1 - IVPEE)` factor grosses the net
figure up so the plant nets the intended amount after paying IVPEE on the RO payment itself.

See [`formula.py`](../src/ro_calculation/formula.py) for the implementation and the inline note on
where it intentionally diverges from the BOE text (the CNMC/GTS surcharge on `TC_RL_J_BASE_1`).
