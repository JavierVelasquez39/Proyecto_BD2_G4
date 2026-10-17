# Resumen del análisis comparativo (sección 4.10)

Generado por `07_documentacion/analisis/analizar.py` a partir de `05_logs/tiempos_*.csv`, de los logs de cada corrida y de `pg_wal_respaldos.csv`. Todos los números salen de esos archivos; no hay valores escritos a mano.

## Datos usados

- `tiempos_anio_pa.csv`: válido (formato y cruce con logs), máquina `pa-laptop`.
- `tiempos_deporte_pb.csv`: **excluido** (4 motivos, todos en `ESTADO_CSV.md`). Primero: fila 9 (restore n=0 rep 1, total 0.741 s, inicio 18:39:29.179): no coincide con `deporte_pb_12_restore_cadena0_rep1.log` (Total 2.444 s, inicio 2026-10-16 22:48:23); solo coincide con el log rotado `deporte_pb_12_restore_cadena0_rep1.20261016_222939.log`. La carga `deporte` queda cubierta por `deporte_pc`.
- `tiempos_deporte_pc.csv`: válido (formato y cruce con logs), máquina `pc-laptop`.
- `tiempos_deportista_pc.csv`: válido (formato y cruce con logs), máquina `pc-laptop`.

**Advertencia:** las máquinas del equipo son distintas. Entre máquinas se comparan razones (por ejemplo restore(n)/restore(0)), no segundos. Los tamaños en bytes sí se comparan entre corridas: dependen de los datos y de PostgreSQL, no de la máquina.

En `pc-laptop` hay 2 corridas (deporte_pc, deportista_pc): entre ellas la máquina es la misma, así que la diferencia de tiempos se atribuye al tipo de carga y sí se pueden comparar segundos, con la salvedad de la caché del sistema operativo.

Las corridas en máquinas distintas (anio_pa en pa-laptop, deporte_pc en pc-laptop, deportista_pc en pc-laptop) solo se comparan por razones; entre ellas no se puede separar el efecto de la carga del de la máquina.

## Medido

### Corrida `anio_pa` (máquina `pa-laptop`)

Respaldos (etapa `basebackup`):

- FULL: 1.927 s, 49973573 bytes (49.97 MB).
- INCR 1: 1.770 s, 27047530 bytes (27.05 MB).
- INCR 2: 1.722 s, 29153134 bytes (29.15 MB).
- INCR 3: 1.738 s, 29988752 bytes (29.99 MB).

Razón de tamaño incr(n).bytes / full.bytes:

- INCR 1: 27047530 / 49973573 = 0.541.
- INCR 2: 29153134 / 49973573 = 0.583.
- INCR 3: 29988752 / 49973573 = 0.600.

WAL dentro de cada respaldo:

- FULL: 1 segmento(s) según el log (16777216 bytes, 33.6 % del respaldo).
- INCR 1: 1 segmento(s) según el log (16777216 bytes, 62.0 % del respaldo).
- INCR 2: 1 segmento(s) según el log (16777216 bytes, 57.5 % del respaldo).
- INCR 3: 1 segmento(s) según el log (16777216 bytes, 55.9 % del respaldo).

Restauración, mediana de 3 repeticiones por etapa (sin `total`):

- n=0: combinar 0.272 s, arranque 1.549 s, validacion 0.250 s.
- n=1: combinar 1.566 s, arranque 1.347 s, validacion 0.291 s.
- n=2: combinar 1.601 s, arranque 1.346 s, validacion 0.311 s.
- n=3: combinar 1.580 s, arranque 1.366 s, validacion 0.318 s.

Restauración, `total` (mediana, mínimo y máximo) y razón restore(n) / restore(0):

- n=0: 2.238 s (2.224 a 2.255), razón 1.000.
- n=1: 3.393 s (3.379 a 3.475), razón 1.516.
- n=2: 3.447 s (3.376 a 3.481), razón 1.540.
- n=3: 3.430 s (3.419 a 3.638), razón 1.533.

`pg_verifybackup` dentro de `total` (de los logs de restauración):

- n=0: mediana 0.088 s, 3.9 % del total.
- n=1: mediana 0.095 s, 2.8 % del total.
- n=2: mediana 0.098 s, 2.8 % del total.
- n=3: mediana 0.095 s, 2.7 % del total.

`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): FULL 0.083 s, INCR 1 0.081 s, INCR 2 0.081 s, INCR 3 0.078 s.

### Corrida `deporte_pc` (máquina `pc-laptop`)

Respaldos (etapa `basebackup`):

- FULL: 1.516 s, 49973476 bytes (49.97 MB).
- INCR 1: 0.845 s, 21730223 bytes (21.73 MB).
- INCR 2: 0.948 s, 21730975 bytes (21.73 MB).
- INCR 3: 0.921 s, 21747383 bytes (21.75 MB).

Razón de tamaño incr(n).bytes / full.bytes:

- INCR 1: 21730223 / 49973476 = 0.435.
- INCR 2: 21730975 / 49973476 = 0.435.
- INCR 3: 21747383 / 49973476 = 0.435.

WAL dentro de cada respaldo:

- FULL: 1 segmento(s) según el log (16777216 bytes, 33.6 % del respaldo); medido en el volumen: 16777216 bytes, coincide.
- INCR 1: 1 segmento(s) según el log (16777216 bytes, 77.2 % del respaldo); medido en el volumen: 16777216 bytes, coincide.
- INCR 2: 1 segmento(s) según el log (16777216 bytes, 77.2 % del respaldo); medido en el volumen: 16777216 bytes, coincide.
- INCR 3: 1 segmento(s) según el log (16777216 bytes, 77.1 % del respaldo); medido en el volumen: 16777216 bytes, coincide.

Restauración, mediana de 3 repeticiones por etapa (sin `total`):

- n=0: combinar 0.351 s, arranque 0.980 s, validacion 0.287 s.
- n=1: combinar 0.854 s, arranque 0.731 s, validacion 0.187 s.
- n=2: combinar 0.937 s, arranque 0.639 s, validacion 0.193 s.
- n=3: combinar 0.809 s, arranque 0.634 s, validacion 0.190 s.

Restauración, `total` (mediana, mínimo y máximo) y razón restore(n) / restore(0):

- n=0: 1.837 s (1.580 a 1.926), razón 1.000.
- n=1: 1.898 s (1.853 a 2.005), razón 1.033.
- n=2: 1.960 s (1.772 a 1.979), razón 1.067.
- n=3: 1.764 s (1.741 a 1.916), razón 0.960.

`pg_verifybackup` dentro de `total` (de los logs de restauración):

- n=0: mediana 0.094 s, 5.3 % del total.
- n=1: mediana 0.058 s, 3.0 % del total.
- n=2: mediana 0.065 s, 3.3 % del total.
- n=3: mediana 0.060 s, 3.2 % del total.

`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): FULL 0.066 s, INCR 1 0.047 s, INCR 2 0.092 s, INCR 3 0.079 s.

### Corrida `deportista_pc` (máquina `pc-laptop`)

Respaldos (etapa `basebackup`):

- FULL: 0.975 s, 50006396 bytes (50.01 MB).
- INCR 1: 0.920 s, 21992494 bytes (21.99 MB).
- INCR 2: 0.784 s, 22033700 bytes (22.03 MB).
- INCR 3: 0.758 s, 21820787 bytes (21.82 MB).

Razón de tamaño incr(n).bytes / full.bytes:

- INCR 1: 21992494 / 50006396 = 0.440.
- INCR 2: 22033700 / 50006396 = 0.441.
- INCR 3: 21820787 / 50006396 = 0.436.

WAL dentro de cada respaldo:

- FULL: 1 segmento(s) según el log (16777216 bytes, 33.6 % del respaldo); medido en el volumen: 16777216 bytes, coincide.
- INCR 1: 1 segmento(s) según el log (16777216 bytes, 76.3 % del respaldo); medido en el volumen: 16777216 bytes, coincide.
- INCR 2: 1 segmento(s) según el log (16777216 bytes, 76.1 % del respaldo); medido en el volumen: 16777216 bytes, coincide.
- INCR 3: 1 segmento(s) según el log (16777216 bytes, 76.9 % del respaldo); medido en el volumen: 16777216 bytes, coincide.

Restauración, mediana de 3 repeticiones por etapa (sin `total`):

- n=0: combinar 0.249 s, arranque 0.736 s, validacion 0.152 s.
- n=1: combinar 0.713 s, arranque 0.533 s, validacion 0.162 s.
- n=2: combinar 0.753 s, arranque 0.532 s, validacion 0.157 s.
- n=3: combinar 0.761 s, arranque 0.629 s, validacion 0.150 s.

Restauración, `total` (mediana, mínimo y máximo) y razón restore(n) / restore(0):

- n=0: 1.267 s (1.256 a 1.409), razón 1.000.
- n=1: 1.524 s (1.455 a 1.595), razón 1.203.
- n=2: 1.551 s (1.515 a 1.712), razón 1.224.
- n=3: 1.647 s (1.496 a 1.909), razón 1.300.

`pg_verifybackup` dentro de `total` (de los logs de restauración):

- n=0: mediana 0.055 s, 4.3 % del total.
- n=1: mediana 0.055 s, 3.6 % del total.
- n=2: mediana 0.055 s, 3.5 % del total.
- n=3: mediana 0.053 s, 3.5 % del total.

`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): FULL 0.053 s, INCR 1 0.050 s, INCR 2 0.044 s, INCR 3 0.046 s.

### Gráficos

- `graficos/grafico1_etapas_restauracion_anio_pa.png`
- `graficos/grafico1_etapas_restauracion_deporte_pc.png`
- `graficos/grafico1_etapas_restauracion_deportista_pc.png`
- `graficos/grafico2_tamano_respaldos.png`
- `graficos/grafico3_razon_restauracion.png`

## Interpretación

Esta sección interpreta los números de arriba. No son mediciones nuevas.

### `anio_pa`

- **Tamaño de los respaldos.** Cada INCR pesa entre 0.541 y 0.600 veces el FULL (27.05 a 29.99 MB, FULL 49.97 MB). El WAL ocupa entre 55.9 % y 62.0 % de cada INCR; sin él, cada INCR pesa 10.27 a 13.21 MB.
- **Restauración.** La cadena completa (n=3) tomó 1.53 veces lo que el FULL. `combinar` pasa de 0.272 s con n=0 a 1.566 a 1.601 s con n=1 a 3, y `arranque` pasa de 1.549 s a 1.346 a 1.366 s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el `total` va de 3.393 a 3.430 s.

### `deporte_pc`

- **Tamaño de los respaldos.** Cada INCR pesa 0.435 veces el FULL (21.73 a 21.75 MB, FULL 49.97 MB). El WAL ocupa entre 77.1 % y 77.2 % de cada INCR; sin él, cada INCR pesa 4.95 a 4.97 MB.
- **Restauración.** La cadena completa (n=3) tomó 0.96 veces lo que el FULL. `combinar` pasa de 0.351 s con n=0 a 0.809 a 0.937 s con n=1 a 3, y `arranque` pasa de 0.980 s a 0.634 a 0.731 s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el `total` va de 1.898 a 1.764 s. Las 3 repeticiones de n=0 (1.580 a 1.926 s) y de n=3 (1.741 a 1.916 s) se solapan: la diferencia entre el FULL y la cadena completa está dentro de la variación entre repeticiones y no se interpreta.

### `deportista_pc`

- **Tamaño de los respaldos.** Cada INCR pesa entre 0.436 y 0.441 veces el FULL (21.82 a 22.03 MB, FULL 50.01 MB). El WAL ocupa entre 76.1 % y 76.9 % de cada INCR; sin él, cada INCR pesa 5.04 a 5.26 MB. Bolt agrega muy pocas filas por ronda, así que el tamaño del INCR es casi todo piso fijo: el segmento de WAL y los archivos del sistema.
- **Restauración.** La cadena completa (n=3) tomó 1.30 veces lo que el FULL. `combinar` pasa de 0.249 s con n=0 a 0.713 a 0.761 s con n=1 a 3, y `arranque` pasa de 0.736 s a 0.532 a 0.629 s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el `total` va de 1.524 a 1.647 s.

### Entre corridas

- **Tamaño sin WAL** (comparable entre máquinas): `anio_pa` 10.27 a 13.21 MB, `deporte_pc` 4.95 a 4.97 MB, `deportista_pc` 5.04 a 5.26 MB por INCR. El FULL pesa casi lo mismo en todas porque la carga base es la misma.

## Recomendación para el volumen de datos manejado

Base: FULL de 49.97 a 50.01 MB y rondas de unas pocas a decenas de miles de filas.

- **En ninguna corrida restaurar la cadena fue claramente más rápido que restaurar el FULL.** Cadena completa contra FULL: `anio_pa` 1.53 veces, `deporte_pc` 0.96 veces (dentro de la variación entre repeticiones), `deportista_pc` 1.30 veces. Donde la cadena tarda más, el aumento viene de `combinar` (`pg_combinebackup`).
- **Cada INCR ahorra espacio, pero menos de lo que parece.** Cada INCR ahorra entre 40 % y 56 % del tamaño de un FULL, y de lo que sí ocupa, una parte grande es el segmento fijo de WAL de 16 MiB.
- **Recomendación.** Con este volumen conviene el **FULL frecuente** (por ejemplo, uno después de cada carga) cuando lo prioritario es el tiempo de restauración: el FULL es pequeño, se toma en segundos y se restaura sin combinar. El **incremental** conviene cuando lo prioritario es el espacio o la ventana de respaldo, con un FULL periódico para que la cadena sea corta, porque restaurar exige combinar toda la cadena.
- **Diferencial.** El enunciado pide FULL más incremental **o** diferencial; el equipo eligió incremental (`pg_basebackup --incremental`, cada INCR encadenado al anterior), así que el diferencial no se midió y la recomendación no lo compara con datos.

## Limitaciones

- Se reporta la mediana de 3 repeticiones; la caché del sistema operativo puede favorecer a las repeticiones 2 y 3.
- Las conclusiones valen para el volumen manejado (FULL de unos 50 MB); no se extrapolan a bases más grandes.
- El WAL de cada respaldo se midió en el volumen en deporte_pc, deportista_pc y coincide con el cálculo desde el log; en anio_pa se toma del log con el mismo método.
- `pg_verifybackup` pesó entre 2.7 % y 5.3 % del `total` de restauración (mediana por n).
