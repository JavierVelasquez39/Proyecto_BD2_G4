# Reporte de carga ETL - Proyecto Olimpiadas

## Conteos (estado actual, esta corrida)

- PAIS: 204
- POBLACION_PAIS: 13026
- NOC: 236
- SEDE: 47
- ATLETA: 153443
- EDICION_OLIMPICA: 61
- DEPORTE: 95
- DEPORTE_EQUIVALENCIA: 2
- EVENTO: 2103
- PARTICIPACION: 319950
- RESULTADO: 320465

## Detalle / decisiones (esta corrida)

- Fuente 1 cargada: bios_clean=145500, bios_raw=145500, noc_regions=230, populations=266, results=308408, editions(ref, fallback residual)=59
- Fuente 2 cargada (solo para derivar SEDE/EDICION_OLIMPICA y para cross-check, NO se cargan sus participaciones): athlete_events=271116, noc_regions=230.
- Fuente 3 cargada: olympics_dataset.csv=252565 filas totales (1896-2024, todas las temporadas); se filtra a solo lo necesario más abajo.
- PAIS construido: 204 países (unión NOC vigentes + sedes).
- POBLACION_PAIS: 13026 filas cargadas de 16930 disponibles en populations.csv; 3904 filas descartadas por pertenecer a países/agregados del Banco Mundial que ningún NOC ni sede representa (ej. regiones agregadas 'World', 'OECD members', etc.).
- NOC construido: 236 códigos (16 con pais_id NULL: equipos históricos/mixtos, refugiados, atletas individuales, códigos sin país actual reconocible).
- Fuente 3: se retienen solo 14892 filas de Year==2024 de 252565 totales (1896-2024). Regla aplicada: se toma de fuente 3 únicamente el/los año(s) que NO aparecen ya en el catálogo de ediciones cargado desde fuente 1 (1896-2022) -- en la práctica, solo 2024 (París). El resto (1896-2020 Verano) se descarta explícitamente para no duplicar PARTICIPACION contra lo ya cargado de fuente 1. Al ser fuente 3 de licencia CC BY-NC-SA (más restrictiva que la CC0 de fuente 2), se usa solo para esto -- no como fuente de validación cruzada general -- para minimizar cuánto del dataset final hereda esa licencia (ver DECISIONES.md y FUENTES.md).
- SEDE: 47 sedes; EDICION_OLIMPICA: 61 ediciones. Ciudad real derivada de columna City: 51 ediciones de fuente 2 (1896-2016) + 1 de fuente 3 (2024 Verano). Solo 9 ediciones ([(2010, 'Verano-YOG'), (2012, 'Invierno-YOG'), (2014, 'Verano-YOG'), (2016, 'Invierno-YOG'), (2018, 'Invierno'), (2018, 'Verano-YOG'), (2020, 'Invierno-YOG'), (2020, 'Verano'), (2022, 'Invierno')]) siguen viniendo de reference_editions.csv porque ninguna fuente real trae City para esos años (fuente 2 no llega, fuente 3 es solo Verano); ver DECISIONES.md.
- ATLETA: 145500 personas cargadas desde bios (incluye roles no competitivos: coach/referee/administrator, ya que la fuente no separa esa información en un archivo distinto). 0 sin sexo registrado.
- DEPORTE: 93 disciplinas; EVENTO: 1904 eventos distintos (nombre, deporte).
- Se procesan 5842 filas de Juegos Olímpicos de la Juventud (YOG) catalogándolas en 'Verano-YOG' / 'Invierno-YOG'.
- Se descartan 2601 filas sin year/type resolvible en la fuente (no se puede construir la FK a EDICION_OLIMPICA).
- Se descartan 1 filas sin discipline/event (fila(s) malformada(s) en la fuente, sin datos suficientes para resolver DEPORTE/EVENTO).
- Se descartan 233 filas cuyo (anio,tipo) no calza con ninguna edición del catálogo de sedes.
- altura_cm/peso_kg en PARTICIPACION se toman del valor único registrado en bios por atleta. Simplificación documentada.
- Deduplicación de clave natural (atleta_id, edicion_id, evento_id): 428 grupos con más de una fila en results.csv (943 filas en total) colapsados a 1 fila de PARTICIPACION cada uno; se preserva 1 fila de RESULTADO por cada resultado distinto traído.
- PARTICIPACION: 305058 filas; RESULTADO: 305573 filas, de 308408 filas originales en results.csv.
- ATLETA (extensión fuente 3, solo 2024): 11113 atletas distintos en París 2024; 3170 calzaron (nombre normalizado + vivo + nacionalidad consistente con el NOC de fuente 3, o nacionalidad desconocida con candidato único); 7943 se cargan como nuevos. De los rechazos: 30 candidatos descartados por estar fallecidos en fuente 1 (no pueden competir en 2024), 81 rechazados por nacionalidad inconsistente con el NOC de fuente 3 (único candidato vivo, pero de otro país -- probable homónimo), 48 rechazados por ambigüedad (más de un candidato vivo con ese nombre). Ver auditoría manual y criterio revisado en DECISIONES.md.
- DEPORTE_EQUIVALENCIA: 2 equivalencias cargadas (ej. 'Equestrian' -> Deporte General 'Equestrian', 'Trampoline Gymnastics' -> 'Trampolining (Gymnastics)').
- PARTICIPACION/RESULTADO (fuente 3, solo edición 2024): 14892 filas de origen -> 14892 filas de PARTICIPACION (0 colapsadas por deduplicación de clave natural) y 14892 filas de RESULTADO. `edad`, `altura_cm`, `peso_kg` y `lugar` quedan NULL para todas estas filas: fuente 3 no trae esas columnas (limitación conocida, documentada).
- Carga a PostgreSQL completada y confirmada (COMMIT).

## Reconciliación de conteos NOC

Comparación real, columna por columna, entre `data_raw/Olympics-Dataset/clean-data/noc_regions.csv` (fuente 1, 230 filas) y `data_raw/fuente2_kaggle120/noc_regions.csv` (fuente 2, 230 filas), verificada en esta corrida:

- Códigos NOC solo en fuente 1: ninguno.
- Códigos NOC solo en fuente 2: ninguno.
- Diferencias de `region` para el mismo código NOC: 0 (ninguna).

**Los dos archivos son idénticos** (mismos 230 códigos, mismos nombres de región). Esto resuelve de forma definitiva la pregunta abierta en una revisión anterior sobre si fuente 1 y fuente 2 comparten el mismo `noc_regions.csv`.

El conteo final de **236** en la tabla `NOC` de esta carga es `230 (noc_regions.csv, idéntico en fuente 1 y fuente 2) + 6 (códigos agregados manualmente en el ETL porque aparecen en `results.csv` u `olympics_dataset.csv` pero no en `noc_regions.csv`: LBN, SGP, ROC, EOR, COR, AIN) = 236`.

De los 5 códigos agregados para fuente 1 (LBN, SGP, ROC, EOR, COR), se verificó contra `PARTICIPACION` que los 5 tienen atletas asociados (362, 389, 1128, 47 y 26 participaciones respectivamente en la corrida de fuente 1). En cambio, sus códigos "base" equivalentes que sí están en `noc_regions.csv` (LIB para Lebanon y SIN para Singapore) **tienen 0 participaciones**: `results.csv` usa exclusivamente los códigos modernos LBN/SGP, nunca LIB/SIN. AIN (agregado en esta corrida para fuente 3, atletas neutrales de París 2024) también tiene atletas asociados por construcción, al venir directo de `olympics_dataset.csv`.

## Reconciliación exacta de results.csv

Reconciliación exacta de results.csv -> PARTICIPACION/RESULTADO (con YOG cargados):

| Motivo | Filas |
|---|---:|
| Filas totales en `results.csv` | 308408 |
| (+) Incluidas de Youth Olympic Games (`event` contiene `(YOG)`) | 5842 |
| (-) Sin `year`/`type` resolvible en la fuente | 2601 |
| (-) Sin `discipline`/`event` (fila malformada) | 1 |
| (-) `(anio,tipo)` sin edición correspondiente en el catálogo de sedes | 233 |
| (-) Sin `evento_id` resoluble | 0 |
| (-) Sin `atleta_id` resoluble | 0 |
| **= Filas que sobreviven a RESULTADO** | **305573** |
| (-) Colapsadas por deduplicación de clave natural (428 grupos, 943 filas de origen -> 428 filas) | 515 |
| **= Filas finales en PARTICIPACION** | **305058** |

Verificación de cierre: 308408 - 2601 - 1 - 233 - 0 - 0 = 305573 (coincide con las 305573 filas de RESULTADO).

## Cross-check con fuente 2 (validación, NO se carga a la BD)

Fuente 2 (`athlete_events.csv`, 271,116 filas, 1896-2016) se usa únicamente para validar fuente 1, nunca para cargar participaciones adicionales (ya cubiertas).

- **Patrón multi-NOC:** agrupando por `ID` (columna propia de fuente 2, distinta del `athlete_id` de fuente 1) y contando `NOC` distintos, **1570 atletas** de fuente 2 compitieron bajo más de un NOC. Esto confirma cualitativamente el mismo patrón que fuente 1 (1,834 atletas, ver `DECISIONES.md`); los conteos no son directamente comparables 1:1 porque fuente 2 solo llega a 2016 (menos ediciones = menos oportunidades de cambio de NOC) y usa una numeración de atleta propia.

- **Consistencia de Height/Weight:** de 135571 atletas distintos en fuente 2, 98740 calzaron por nombre normalizado exacto con un atleta ya cargado de fuente 1. De los que tienen altura registrada en ambas fuentes (75935 personas), 623 difieren. De los que tienen peso registrado en ambas (73715 personas), 610 difieren. Las diferencias no se investigaron caso por caso en esta corrida (quedan registradas, no resueltas, según lo pedido).

## Historial de corridas

## Corrida 2026-09-12 (mañana): carga inicial (solo fuente 1)

Primera carga real contra Postgres 16 (Docker). Fuente 1 (GitHub
KeithGalli/Olympics-Dataset) como columna vertebral 1896-2022;
`SEDE`/`EDICION_OLIMPICA` poblada con `reference_editions.csv` (armado a
mano, ver `DECISIONES.md`); `PARTICIPACION` con deduplicación de clave
natural (caso Polo 1900). 0 violaciones de integridad.

| Tabla | Conteo |
|---|---:|
| pais | 204 |
| poblacion_pais | 13026 |
| noc | 235 |
| sede | 43 |
| atleta | 145500 |
| edicion_olimpica | 53 |
| deporte | 93 |
| evento | 1904 |
| participacion | 299216 |
| resultado | 299731 |


## Corrida 2026-09-12 (tarde): integración de fuente 2 y fuente 3 (carga inicial, antes de la auditoría del 2026-09-13)

Se reemplaza `reference_editions.csv` como fuente primaria de SEDE/EDICION_OLIMPICA por columnas `City` reales de fuente 2 (1896-2016) y fuente 3 (2024); solo 3 ediciones (2018 Invierno, 2020 Verano, 2022 Invierno) siguen viniendo del archivo manual porque ninguna fuente real trae `City` para esos años. Se agrega la edición 2024 Verano (París) cargando fuente 3 filtrada a `Year==2024`. Ver detalle completo en las secciones de arriba (SEDE/EDICION_OLIMPICA, ATLETA extensión fuente 3, DEPORTE/EVENTO extensión fuente 3, PARTICIPACION/RESULTADO fuente 3, reconciliación NOC 235 vs 230, cross-check fuente 2).

**Nota (2026-09-13):** los valores de `atleta` y `evento` de esta tabla son los de la carga INICIAL (emparejamiento por nombre exacto simple, sin canonicalización de EVENTO). Quedaron desactualizados por una corrección de esquema de este mismo reporte (una versión anterior de `dump()` los sobrescribió sin darse cuenta con los números ya auditados); se restauran aquí a sus valores originales para no perder el historial real. Ver la sección fechada 2026-09-13 más abajo para los números finales tras la auditoría.

| Tabla | Corrida anterior (solo fuente 1) | Esta corrida (+fuente 2 sedes +fuente 3 2024) | Diferencia |
|---|---:|---:|---:|
| pais | 204 | 204 | +0 |
| poblacion_pais | 13026 | 13026 | +0 |
| noc | 235 | 236 | +1 |
| sede | 43 | 43 | +0 |
| atleta | 145500 | 153869 | +8369 |
| edicion_olimpica | 53 | 55 | +2 |
| deporte | 93 | 96 | +3 |
| evento | 1904 | 2236 | +332 |
| participacion | 299216 | 314108 | +14892 |
| resultado | 299731 | 314623 | +14892 |


## Corrida 2026-09-13: estado final (fuente 1 + fuente 2 sedes + fuente 3 2024, con auditoría de emparejamiento)

Se reemplaza `reference_editions.csv` como fuente primaria de SEDE/EDICION_OLIMPICA por columnas `City` reales de fuente 2 (1896-2016) y fuente 3 (2024); solo 3 ediciones (2018 Invierno, 2020 Verano, 2022 Invierno) siguen viniendo del archivo manual porque ninguna fuente real trae `City` para esos años. Se agrega la edición 2024 Verano (París) cargando fuente 3 filtrada a `Year==2024`. Esta corrida incluye además la corrección del criterio de emparejamiento de atletas (nombre plegando tildes + vivo + nacionalidad consistente, en vez de nombre exacto simple) y la canonicalización de EVENTO/DEPORTE entre fuente 1 y fuente 3, ambas resultado de la auditoría del 2026-09-13 documentada en DECISIONES.md. Frente a la integración inicial de fuente 2/3 (sin auditar, `atleta`=153,869 y `evento`=2,236), esta corrida queda en `atleta`=153473 y `evento`=2103 tras corregir falsos positivos/negativos verificados a mano. Ver detalle completo en las secciones de arriba (SEDE/EDICION_OLIMPICA, ATLETA extensión fuente 3, DEPORTE/EVENTO extensión fuente 3, PARTICIPACION/RESULTADO fuente 3, reconciliación NOC, cross-check fuente 2).

| Tabla | Corrida solo fuente 1 (2026-09-12 mañana) | Esta corrida | Diferencia |
|---|---:|---:|---:|
| pais | 204 | 204 | +0 |
| poblacion_pais | 13026 | 13026 | +0 |
| noc | 235 | 236 | +1 |
| sede | 43 | 43 | +0 |
| atleta | 145500 | 153473 | +7973 |
| edicion_olimpica | 53 | 55 | +2 |
| deporte | 93 | 96 | +3 |
| evento | 1904 | 2103 | +199 |
| participacion | 299216 | 314108 | +14892 |
| resultado | 299731 | 314623 | +14892 |


## Corrida 2026-09-18: estado final (fuente 1 + fuente 2 sedes + fuente 3 2024, con auditoría de emparejamiento)

Se reemplaza `reference_editions.csv` como fuente primaria de SEDE/EDICION_OLIMPICA por columnas `City` reales de fuente 2 (1896-2016) y fuente 3 (2024); solo 3 ediciones (2018 Invierno, 2020 Verano, 2022 Invierno) siguen viniendo del archivo manual porque ninguna fuente real trae `City` para esos años. Se agrega la edición 2024 Verano (París) cargando fuente 3 filtrada a `Year==2024`. Esta corrida incluye además la corrección del criterio de emparejamiento de atletas (nombre plegando tildes + vivo + nacionalidad consistente, en vez de nombre exacto simple) y la canonicalización de EVENTO/DEPORTE entre fuente 1 y fuente 3, ambas resultado de la auditoría del 2026-09-13 documentada en DECISIONES.md. Frente a la integración inicial de fuente 2/3 (sin auditar, `atleta`=153,869 y `evento`=2,236), esta corrida queda en `atleta`=153443 y `evento`=2103 tras corregir falsos positivos/negativos verificados a mano. Ver detalle completo en las secciones de arriba (SEDE/EDICION_OLIMPICA, ATLETA extensión fuente 3, DEPORTE/EVENTO extensión fuente 3, PARTICIPACION/RESULTADO fuente 3, reconciliación NOC, cross-check fuente 2).

| Tabla | Corrida solo fuente 1 (2026-09-12 mañana) | Esta corrida | Diferencia |
|---|---:|---:|---:|
| pais | 204 | 204 | +0 |
| poblacion_pais | 13026 | 13026 | +0 |
| noc | 235 | 236 | +1 |
| sede | 43 | 47 | +4 |
| atleta | 145500 | 153443 | +7943 |
| edicion_olimpica | 53 | 61 | +8 |
| deporte | 93 | 96 | +3 |
| evento | 1904 | 2103 | +199 |
| participacion | 299216 | 319950 | +20734 |
| resultado | 299731 | 320465 | +20734 |


## Corrida 2026-09-18: estado final (fuente 1 + fuente 2 sedes + fuente 3 2024, con auditoría de emparejamiento y equivalencias de deportes)

Se reemplaza `reference_editions.csv` como fuente primaria de SEDE/EDICION_OLIMPICA por columnas `City` reales de fuente 2 (1896-2016) y fuente 3 (2024); solo 3 ediciones (2018 Invierno, 2020 Verano, 2022 Invierno) siguen viniendo del archivo manual porque ninguna fuente real trae `City` para esos años. Se agrega la edición 2024 Verano (París) cargando fuente 3 filtrada a `Year==2024`. Esta corrida incluye además la corrección del criterio de emparejamiento de atletas (nombre plegando tildes + vivo + nacionalidad consistente, en vez de nombre exacto simple), la canonicalización de EVENTO/DEPORTE entre fuente 1 y fuente 3, y la incorporación de la tabla `deporte_equivalencia` para mapear disciplinas genéricas o renombradas. Ver detalle completo en las secciones de arriba (SEDE/EDICION_OLIMPICA, ATLETA extensión fuente 3, DEPORTE/EVENTO extensión fuente 3, PARTICIPACION/RESULTADO fuente 3, reconciliación NOC, cross-check fuente 2).

| Tabla | Corrida solo fuente 1 (2026-09-12 mañana) | Esta corrida | Diferencia |
|---|---:|---:|---:|
| pais | 204 | 204 | +0 |
| poblacion_pais | 13026 | 13026 | +0 |
| noc | 235 | 236 | +1 |
| sede | 43 | 47 | +4 |
| atleta | 145500 | 153443 | +7943 |
| edicion_olimpica | 53 | 61 | +8 |
| deporte | 93 | 95 | +2 |
| evento | 1904 | 2103 | +199 |
| participacion | 299216 | 319950 | +20734 |
| resultado | 299731 | 320465 | +20734 |

