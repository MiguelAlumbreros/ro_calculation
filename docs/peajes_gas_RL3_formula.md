# Cálculo del peaje de gas — Punto de suministro RL.3 (con telemedida)

**Referencia normativa:** BOE-A-2025-11064 — Resolución de 27 de mayo de 2025, CNMC, peajes de acceso a las redes de transporte, redes locales y regasificación para el año de gas 2026.

---

## Fórmula general

$$
Coste_{anual} = \left[\sum_{m=1}^{12} TF_{RL3,neto} \times M_m \times Q_{c,m}\right] + TV_{RL3} \times V_{anual}
$$

---

## Desglose de componentes

### a) Término fijo base de red local (RL.3, con telemedida)

$$
TF_{RL3} = 2{,}313687 \ \text{€/(kWh/día)/año}
$$

> **Fuente:** Anexo I, apartado 2.2 — *"Peajes aplicables a los puntos de suministro con obligación de disponer de telemedida..."*, tabla RL.1–RL.11, fila RL.3.

### b) Término fijo de otros costes de regasificación (RL.3, con telemedida)

$$
TF_{regas,RL3} = -0{,}043046 \ \text{€/(kWh/día)/año}
$$

> **Fuente:** Anexo I, apartado 3.2, segunda tabla — *"Peajes aplicables a los puntos de suministro con obligación de disponer de telemedida..."*, fila RL.3.
> Se suma al anterior porque el **Resuelvo Primero** de la parte dispositiva aprueba conjuntamente los peajes de transporte, redes locales e instalaciones de regasificación como un único bloque aplicable al suministro.

### Término fijo neto

$$
TF_{RL3,neto} = TF_{RL3} + TF_{regas,RL3} = 2{,}313687 - 0{,}043046 = 2{,}270641 \ \text{€/(kWh/día)/año}
$$

---

### c) Multiplicador mensual por duración del contrato ($M_m$)

> **Fuente:** Anexo I, apartado 1.2.c — *"Multiplicadores aplicables a los contratos de duración inferior a un año en las salidas de la red de transporte hacia salidas a redes locales"* (tabla mensual × Trimestral/Mensual/Diario/Intradiario).
>
> **Aplicabilidad a redes locales:** Anexo I, apartado 2.3 — *"Multiplicadores aplicables a los contratos de duración inferior a un año. Conforme al artículo 23 de la Circular 6/2020... a los contratos de duración inferior a un año les serán de aplicación los multiplicadores aplicables a las salidas de la red de transporte a redes locales."*
>
> **Base legal última:** artículos 23 y 35 de la Circular 6/2020 (metodología, no incluida en este BOE).
>
> Si la capacidad se contrata **en modalidad anual**, $M_m = 1$ para todos los meses (la tabla de multiplicadores solo aplica a productos de duración *inferior* a un año).

| Mes | Trimestral | Mensual | Diario | Intradiario |
|---|---|---|---|---|
| Enero | 1,43 | 1,87 | 2,44 | 5,75 |
| Febrero | 1,43 | 1,46 | 1,91 | 4,49 |
| Marzo | 1,43 | 1,40 | 1,83 | 4,30 |
| Abril | 1,03 | 1,08 | 1,41 | 3,32 |
| Mayo | 1,03 | 1,00 | 1,31 | 3,08 |
| Junio | 1,03 | 1,07 | 1,40 | 3,30 |
| Julio | 1,10 | 1,17 | 1,52 | 3,59 |
| Agosto | 1,10 | 1,07 | 1,40 | 3,29 |
| Septiembre | 1,10 | 1,14 | 1,49 | 3,52 |
| Octubre | 1,24 | 1,21 | 1,59 | 3,73 |
| Noviembre | 1,24 | 1,50 | 1,96 | 4,62 |
| Diciembre | 1,24 | 1,63 | 2,13 | 5,01 |

---

### d) Capacidad contratada ($Q_{c,m}$)

No está en el BOE — es el dato de contrato de acceso a la red (kWh/día contratados en cada periodo/producto).

---

### e) Término variable (RL.3, con telemedida)

$$
TV_{RL3} = 0{,}002018 \ \text{€/kWh}
$$

> **Fuente:** Anexo I, apartado 2.2, misma tabla que (a), columna "Término variable por volumen", fila RL.3.
>
> **Nota:** el concepto "otros costes de regasificación" (apartado 3.2) **no tiene** componente variable para consumidores con telemedida — la tabla correspondiente solo incluye término fijo. Por tanto no hay término variable adicional de ese concepto.

### f) Volumen anual consumido ($V_{anual}$)

Dato propio de consumo real, no proviene del BOE.

---

## Fórmula de coste unitario (€/MWh), caso capacidad anual ($M_m=1$)

Definiendo el factor de carga:

$$
Fc = \frac{V_{anual}}{365 \times Q_c}
$$

el coste por MWh consumido resulta:

$$
\frac{€}{MWh} = \frac{TF_{RL3,neto} \times 1000}{365 \times Fc} + TV_{RL3} \times 1000 = \frac{2270{,}641}{365 \times Fc} + 2{,}018
$$

---

## Nota — Tasa CNMC y cuota GTS

El **Resuelvo Primero** añade: *"A los peajes anteriores les será de aplicación la Tasa aplicable a la prestación de servicios y realización de actividades en relación con el sector de hidrocarburos gaseosos y la cuota del GTS correspondiente."*

Esta tasa/cuota **no está cuantificada en este BOE** — se regula en otra norma. No incluida en los cálculos anteriores.
