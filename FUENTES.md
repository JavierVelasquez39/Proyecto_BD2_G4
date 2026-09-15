# Fuentes de datos: licencias y atribución

> Verificado el 2026-09-12 contra las páginas reales de cada fuente (no
> asumido), según la regla 6 de `CLAUDE.md`. Ver método de verificación en
> cada entrada.

## Fuente 1: GitHub, KeithGalli/Olympics-Dataset

- **Origen real:** datos scrapeados de olympedia.org (ver `README.md` del
  repo clonado en `data_raw/Olympics-Dataset/`).
- **Licencia:** **MIT License**, Copyright (c) 2024 Keith Galli.
  Verificado leyendo `data_raw/Olympics-Dataset/LICENSE` directamente
  (archivo clonado localmente el 2026-09-12).
- **Obligaciones:** conservar el aviso de copyright y el texto de la
  licencia en copias o porciones sustanciales del software/datos. Sin
  restricción de uso comercial ni obligación de compartir bajo la misma
  licencia.
- **Estado de carga:** cargada por completo en esta corrida (columna
  vertebral 1896–2022).
- **Texto de atribución a usar en el entregable final:**
  > Datos de atletas y resultados olímpicos (1896–2022) obtenidos de
  > Keith Galli, *Olympics-Dataset* (GitHub), a su vez recolectados de
  > [olympedia.org](https://www.olympedia.org/). Distribuido bajo
  > licencia MIT.

## Fuente 2: Kaggle, "120 years of Olympic history: athletes and results" (heesoo37)

- **Origen real:** sports-reference.com, cobertura moderna hasta Río
  2016.
- **Licencia:** **CC0: Public Domain** (dominio público). Verificado
  extrayendo el bloque de metadatos de la página real de Kaggle
  (`https://www.kaggle.com/datasets/heesoo37/120-years-of-olympic-history-athletes-and-results`),
  campo `license` → `"CC0: Public Domain"`,
  `licenseUrl: https://creativecommons.org/publicdomain/zero/1.0/`.
- **Obligaciones:** ninguna legal (dominio público); se recomienda como
  buena práctica atribuir el origen real de los datos (sports-reference.com)
  aunque no sea exigible.
- **Estado de carga (actualizado 2026-09-12):** archivo real ya
  disponible en `data_raw/fuente2_kaggle120/` (`athlete_events.csv` +
  `noc_regions.csv`). Se usa para dos cosas, **ninguna es carga directa
  de `PARTICIPACION`**:
  1. Deriva `SEDE`/`EDICION_OLIMPICA` reales (columna `City`,
     1896-2016), en reemplazo del archivo manual `reference_editions.csv`
     (ver `DECISIONES.md`).
  2. Cross-check de fuente 1: confirma el patrón multi-NOC y compara
     `Height`/`Weight` de atletas coincidentes por nombre (ver
     `etl/REPORTE.md`, sección de cross-check).
  Su `noc_regions.csv` se comparó columna por columna contra el de
  fuente 1: **son idénticos** (230/230 códigos, mismos nombres de
  región); ver `DECISIONES.md`.
- **Texto de atribución a usar en el entregable final:**
  > Dataset "120 years of Olympic history: athletes and results"
  > (Kaggle, usuario heesoo37), datos originales de sports-reference.com.
  > Publicado bajo CC0 (dominio público).

## Fuente 3: Kaggle, "Summer Olympics medals 1896-2024" (stefanydeoliveira)

- **Origen real:** fusión de datos históricos + resultados de París
  2024.
- **Licencia:** **CC BY-NC-SA 4.0**. Verificado extrayendo el bloque de
  metadatos de la página real de Kaggle
  (`https://www.kaggle.com/datasets/stefanydeoliveira/summer-olympics-medals-1896-2024`),
  `licenseUrl: https://creativecommons.org/licenses/by-nc-sa/4.0/`.
- **Obligaciones (las tres letras importan):**
  - **BY**: atribución obligatoria a la autora original.
  - **NC**: prohibido el uso **comercial** de los datos o de cualquier
    obra derivada.
  - **SA**: cualquier obra derivada (incluida esta base de datos
    unificada, si incorpora datos de esta fuente) debe compartirse bajo
    **la misma licencia** CC BY-NC-SA 4.0.
- **Implicación para el proyecto:** si finalmente se cargan filas de
  esta fuente (ej. para completar París 2024), el entregable final que
  incorpore esos datos **debe** licenciarse también como CC BY-NC-SA 4.0
  y **no puede** ofrecerse con fines comerciales.
- **Estado de carga (actualizado 2026-09-12):** archivo real ya
  disponible en `data_raw/fuente3_kaggle2024/olympics_dataset.csv`
  (252,565 filas, 1896–2024, solo Verano). Se confirmó que **sí trae
  todas las participaciones, no solo medallistas** (86% de las filas de
  2024 tienen `Medal='No medal'`), lo que corrige la suposición sin confirmar
  del enunciado original. Se cargó **exclusivamente el subconjunto
  `Year==2024`** (14,892 filas → 14,892 participaciones nuevas): es la
  única edición que fuente 1 no cubre. El resto del archivo (1896–2020)
  se descarta explícitamente para no duplicar `PARTICIPACION` y, sobre
  todo, para minimizar cuánto del dataset final queda bajo esta licencia
  más restrictiva que la de fuente 2 (ver regla completa en
  `DECISIONES.md`). No se usa para cross-check general por el mismo
  motivo de licencia.
- **Texto de atribución exacto a usar en el entregable final** (obligatorio
  por la cláusula BY, no opcional):
  > Contiene datos de "Summer Olympics Medals (1896-2024)" por
  > stefanydeoliveira (Kaggle), con licencia
  > [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
  > Este trabajo derivado se distribuye bajo la misma licencia
  > (CC BY-NC-SA 4.0) y no está autorizado para uso comercial.

## Fuente 4: DataCamp, "r-olympics" (datalab)

- **Origen real (según enunciado):** mismo linaje que la fuente 2
  (sports-reference.com), hasta Río 2016.
- **Licencia:** **no verificada.** La plataforma de DataCamp devolvió
  HTTP 403 al intentar acceder sin sesión autenticada desde este
  entorno; no se pudo confirmar el texto de licencia real.
- **Por qué no se usa:** se documenta en `DECISIONES.md`. Se trata como
  equivalente a la fuente 2 por instrucción del proyecto, pero esa
  equivalencia **tampoco está verificada de forma independiente** (no se
  tuvo acceso a los archivos de ninguna de las dos plataformas en este
  entorno). No se carga ningún dato de esta fuente. Si en el futuro se
  obtiene acceso, corresponde verificar tanto el contenido como la
  licencia antes de usarla.
- **Estado de carga:** no cargada; no prevista para cargarse mientras se
  mantenga como redundante de la fuente 2.

## Detalle: los 6 códigos NOC agregados manualmente en el ETL

`noc_regions.csv` (230 filas, idéntico en fuente 1 y fuente 2, ver
`DECISIONES.md`) no incluye estos 6 códigos porque son posteriores a la
publicación de ese archivo o corresponden a designaciones especiales. Se
agregan a mano en `NOC_SUPPLEMENTARY` (`etl/etl.py`) porque `results.csv`
(fuente 1) y `olympics_dataset.csv` (fuente 3) sí los usan como valor de
NOC en filas reales. Verificado el 2026-09-13, con la fila exacta donde
aparece cada uno por primera vez:

| Código | Nombre asignado | Origen exacto | Primera aparición verificada |
|---|---|---|---|
| `LBN` | Lebanon | `results.csv` (fuente 1), alias moderno de `LIB`, que sí está en `noc_regions.csv` pero con **0 participaciones** (la fuente nunca usa `LIB`) | índice de fila 2356, `year=1996`, `event='Singles, Women (Olympic)'`, `athlete_id=941` (377 filas en total con este código) |
| `SGP` | Singapore | `results.csv` (fuente 1), alias moderno de `SIN`, también con 0 participaciones | índice de fila 5239, `year=1992`, `event='Singles, Women (Olympic)'`, `athlete_id=2549` (397 filas en total) |
| `ROC` | Russian Olympic Committee | `results.csv` (fuente 1), equipo bajo sanción de la AMA/COI, sin código propio en `noc_regions.csv` (archivo anterior a Tokyo 2020) | índice de fila 198816, `year=2020`, `event='Trap, Team, Mixed (Olympic)'`, `athlete_id=93139` (1,128 filas en total) |
| `EOR` | Refugee Olympic Team | `results.csv` (fuente 1), acrónimo francés del equipo de refugiados (el código `ROT`, en inglés, sí está en `noc_regions.csv` con 0 filas en `results.csv`) | índice de fila 270883, `year=2020`, `event='Lightweight, Men (Olympic)'`, `athlete_id=126861` (47 filas en total) |
| `COR` | Corea unificada | `results.csv` (fuente 1), equipo conjunto Corea del Norte + Corea del Sur (hockey sobre hielo femenino, PyeongChang 2018) | índice de fila 291405, `year=2018`, `event='Ice Hockey, Women (Olympic)'`, `athlete_id=137570` (26 filas en total) |
| `AIN` | Individual Neutral Athletes | `olympics_dataset.csv` (fuente 3), atletas rusos/bielorrusos neutrales, París 2024 (sucesor de `ROC`, código nuevo en 2024, no existe en `noc_regions.csv` de ninguna de las dos fuentes) | índice de fila 237987, `Year=2024`, `Event="Women's 100m Breaststroke"`, `Name='Alina Zmushka'`, `Team='AIN'` (46 filas en total) |

Los primeros 5 se agregaron en la corrida del 2026-09-12 (fuente 1
únicamente); `AIN` se agregó en la corrida del 2026-09-13 al integrar
fuente 3.
