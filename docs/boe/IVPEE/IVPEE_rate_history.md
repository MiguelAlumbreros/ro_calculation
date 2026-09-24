# IVPEE effective rate — history since 2022

IVPEE = Impuesto sobre el Valor de la Producción de la Energía Eléctrica, created by Ley
15/2012, de 27 de diciembre (BOE-A-2012-15649), whose art. 8 set a rate of **7%**. Two
different mechanisms have moved the effective rate since:

- **Base reductions** (2021–2026): the RDL leaves art. 8 at 7% and instead removes all or
  part of a quarter's *retribuciones* from the base imponible. Effective rate for that
  quarter = 7% x (1 - reduction).
- **Statutory rate changes** (2027 onward): RDL 18/2026 art. 15 rewrites art. 8 of
  Ley 15/2012 itself.

The suspensions began with **RDL 12/2021, de 24 de junio** (Q3 2021), were extended to
31 Dec 2021 by **RDL 17/2021, de 14 de septiembre**, and were rolled forward from there.

## Rate by period

| Period | Statutory rate | Base reduction | Effective rate | Legal basis |
|---|---|---|---|---|
| 2022 (all year) | 7% | 100% | 0% | **RDL 11/2022, de 25 de junio**, art. 17.Dos (BOE-A-2022-10557) — final wording of RDL 29/2021 DA 2.ª. Built up in steps: RDL 29/2021, de 21 de diciembre, DA 2.ª (BOE-A-2021-21096) zeroed Q1; RDL 6/2022, de 29 de marzo, DF 36.ª.Dos (BOE-A-2022-4972) extended it to Q1–Q2; RDL 11/2022 extended it to the whole year |
| 2023 (all year) | 7% | 100% | 0% | **RDL 20/2022, de 27 de diciembre**, art. 5 (BOE-A-2022-22685) |
| 2024 Q1 | 7% | 50% ("la mitad") | 3.5% | **RDL 8/2023, de 27 de diciembre**, art. 23 (BOE-A-2023-26452) — progressive reactivation |
| 2024 Q2 | 7% | 25% ("una cuarta parte") | 5.25% | RDL 8/2023, art. 23 |
| 2024 Q3–Q4 | 7% | none | 7% | RDL 8/2023, art. 23 provides no reduction for Q3/Q4; RDL 4/2024, de 26 de junio (BOE-A-2024-12944), which prorogued the other energy tax measures, does not touch the IVPEE |
| 2025 (all year) | 7% | none | 7% | no measure — Ley 15/2012 art. 8 applies unmodified |
| 2026 Q1 | 7% | 10% | 6.3% | **RDL 18/2026**, art. 14.1 (BOE-A-2026-14112); first enacted by **RDL 7/2026, de 20 de marzo**, art. 41 (BOE-A-2026-6544) |
| 2026 Q2 | 7% | 100% ("la totalidad") | 0% | RDL 18/2026, art. 14.1; first enacted by RDL 7/2026, art. 41 |
| 2026 Q3 | 7% | 30% | 4.9% | **RDL 18/2026, de 29 de junio**, art. 14.1 — published 30 June 2026, in force 1 July 2026 (DF 5.ª) |
| 2026 Q4 | 7% | 40% | 4.2% | RDL 18/2026, art. 14.1 |
| 2027 (all year) | **3.5%** | n/a | 3.5% | RDL 18/2026, **art. 15**, which rewrites art. 8 of Ley 15/2012 with effect 1 Jan 2027 and vigencia to 31 Dec 2027 |
| 2028 onward | **0%** | n/a | 0% | RDL 18/2026, art. 15 — "con efectos de 1 de enero de 2028, y vigencia indefinida, el Impuesto se exigirá al tipo del 0 por ciento". The tax is **not repealed**; its rate is set to zero indefinitely |

RDL 18/2026 art. 14.1 restates the Q1 and Q2 2026 reductions already in RDL 7/2026 art. 41
and adds Q3 and Q4, so art. 14 is the single governing text for the whole of 2026.

## How this maps to the code

The rates above are transcribed into [`IVPEE.xlsx`](../../../src/ro_calculation/data/IVPEE.xlsx), which is
what the pipeline reads — nothing here is hardcoded in `config.py`. `ivpee_for_quarter` in
[`src/ro_calculation/constants.py`](../../../src/ro_calculation/constants.py) matches the
target quarter's first day against the sheet's `start_period`/`end_period` range.

The sheet carries two rate columns. `tipo_efectivo_pct` is the rate actually levied — the
"Effective rate" column above. `tipo_usado_en_RO_pct` is the rate the **RO calculation** is
run at, and that is the one the code reads.

### What the published resolutions actually used (verified 2026-08-31)

Every quarter below was checked by recomputing its published RO from the resolution's own
inputs and matching against `ro_realised.xlsx`. All 21
values (7 quarters x 3 instalaciones tipo) reproduce to within 0.0008 EUR/MWhE.

| Quarter | Levied | Used in the RO | Evidence |
|---|---|---|---|
| 2025 Q1–Q4 | 7% | **7%** | no measure in force; all four resolutions reproduce at 7% |
| 2026 Q1 | 6.3% | **7%** | the resolution predates RDL 7/2026 (published 21 Mar 2026) and mentions no minoración; 7% reproduces all three IT, 6.3% is off by ~0.85 EUR/MWhE |
| 2026 Q2 | 0% | **7%** | the resolution says so outright: *"se incluye como coste estimado de explotación el importe del Impuesto sobre el valor de la producción de la energía eléctrica, que será posteriormente retraído por la Comisión Nacional de los Mercados y la Competencia"* |
| 2026 Q3 | 4.9% | **4.9%** | the resolution cites art. 14 of RDL 18/2026, *"aplicándose una minoración del mismo de un 30 %"* |

So the base reduction reached the RO **only from Q3 2026 onward**. For Q1 and Q2 2026 the RO
was set on the statutory 7% and the CNMC claws the reduction back separately, per RDL 7/2026
DA 13.ª. `tipo_usado_en_RO_pct` was corrected from 6.3 to 7.0 for `q1_26` on 2026-08-31 as a
result of this check.

`tipo_usado_en_RO_pct` is still blank for 2022, 2023 and 2024 Q1–Q2, where the levied and
statutory rates differ and no published RO has been checked against them. Asking for such a
quarter raises `KeyError` rather than guessing.

## Notes / caveats

- **The base reduction is clawed back outside the RO formula.** RDL 7/2026 DA 13.ª orders
  the CNMC to run "la liquidación necesaria para la adaptación de la retribución procedente
  del régimen retributivo específico, detrayendo las cantidades no abonadas por las
  instalaciones como consecuencia de la reducción de la base imponible". The same wording
  appears in RDL 29/2021 DA 3.ª. This is why Q1 and Q2 2026 were set on the statutory 7%,
  as the table above confirms. Q4 2026 (4.2%) has not been published yet — check it the same
  way when it is, since the Q3 precedent suggests the reduction now does reach the RO.
- **A parameter update is pending.** RDL 18/2026 DA 5.ª requires the retributive parameters
  of Orden TED/53/2026 for the 2026–2028 subperiod to be updated by orden ministerial within
  3 months of 1 July 2026, to adapt them to the arts. 14 and 15 IVPEE reduction — i.e. due by
  1 October 2026. Watch for it: it can move `RINV` and the other valores propios in
  `ro_parameters.xlsx`, not just the IVPEE rate.
- RDL 18/2026 DA 6.ª declares the arts. 14/15 IVPEE changes a "cambio regulatorio" for the
  purpose of revising forward electricity hedging contracts.
- RDL 7/2026 and RDL 18/2026 are both subject to congressional convalidation (standard
  procedure for RDLs). If either is not convalidated, its measures lapse.

## Source PDFs

Kept locally, not in the repo:
- `BOE-A-2026-6544 RDL 7-2026 20 marzo Plan Oriente Medio (IVPEE Q1-Q2 2026).pdf` — art. 41
- `BOE-A-2026-14112 RDL 18-2026 29 junio Plan Oriente Medio (IVPEE Q3-Q4 2026, 2027, 2028+).pdf` — arts. 14, 15

Read online at `https://www.boe.es/boe/dias/<yyyy>/<mm>/<dd>/pdfs/<BOE-id>.pdf`:
- BOE-A-2021-21096 (RDL 29/2021), BOE-A-2022-4972 (RDL 6/2022), BOE-A-2022-10557 (RDL 11/2022),
  BOE-A-2022-22685 (RDL 20/2022), BOE-A-2023-26452 (RDL 8/2023), BOE-A-2024-12944 (RDL 4/2024)
- Consolidated Ley 15/2012: `https://www.boe.es/buscar/act.php?id=BOE-A-2012-15649`

The same table is in [`IVPEE.xlsx`](../../../src/ro_calculation/data/IVPEE.xlsx), one row per rate period.

## Other references consulted

- [Agencia Tributaria — Medidas extraordinarias en el IVPEE (RDL 7/2026)](https://sede.agenciatributaria.gob.es/Sede/impuestos-especiales-medioambientales/novedades-impuestos-especiales-medioambientales/2026/marzo/25/medidas-extraordinarias-impuesto-sobre-valor-medio.html)
- [Agencia Tributaria — Medidas tributarias del Real Decreto-ley 18/2026](https://sede.agenciatributaria.gob.es/Sede/todas-noticias/2026/junio/30/medidas-tributarias-real-decreto-ley-182026.html)
- [Real Decreto-ley 18/2026: principales medidas regulatorias en materia energética — PwC Periscopio Fiscal y Legal](https://periscopiofiscalylegal.pwc.es/real-decreto-ley-18-2026-principales-medidas-regulatorias-en-materia-energetica/)
- [El RD-ley 18/2026 prorroga las medidas fiscales en materia energética — Iberley](https://www.iberley.es/noticias/el-rd-ley-18-2026-prorroga-las-medidas-fiscales-materia-energetica-preve-su-retirada-progresiva-36675)
