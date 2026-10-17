# Resumen del análisis comparativo (sección 4.10)

Generado por `07_documentacion/analisis/analizar.py` a partir de `05_logs/tiempos_*.csv` y de los logs de cada corrida. Todos los números salen de esos archivos; no hay valores escritos a mano.

## Datos usados

- `tiempos_anio_pa.csv`: válido (formato y cruce con logs).
- `tiempos_deporte_pb.csv`: **excluido** (4 motivos, todos en `ESTADO_CSV.md`). Primero: fila 9 (restore n=0 rep 1, total 0.741 s, inicio 18:39:29.179): no coincide con `deporte_pb_12_restore_cadena0_rep1.log` (Total 2.444 s, inicio 2026-10-16 22:48:23); solo coincide con el log rotado `deporte_pb_12_restore_cadena0_rep1.20261016_222939.log`.
- `tiempos_deportista_pc.csv`: válido (formato y cruce con logs).
- `tiempos_deportista_pa.csv`: no existe. [PENDIENTE]
- `tiempos_deportista_pb.csv`: no existe. [PENDIENTE]

Detalle en `ESTADO_CSV.md`.

**Advertencia:** las máquinas del equipo son distintas. Entre máquinas se comparan razones (por ejemplo restore(n)/restore(0)), no segundos. Los segundos absolutos solo sirven dentro de una misma corrida.

Las corridas válidas (anio_pa, deportista_pc) difieren a la vez en el tipo de carga y en la máquina (pa-laptop, pc-laptop). Entre ellas solo se comparan razones, y aun así no se puede separar el efecto de la carga del de la máquina.

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

Restauración, mediana de 3 repeticiones por etapa (sin `total`):

- n=0: combinar 0.272 s, arranque 1.549 s, validacion 0.250 s.
- n=1: combinar 1.566 s, arranque 1.347 s, validacion 0.291 s.
- n=2: combinar 1.601 s, arranque 1.346 s, validacion 0.311 s.
- n=3: combinar 1.580 s, arranque 1.366 s, validacion 0.318 s.

Restauración, `total` (mediana) y razón restore(n) / restore(0):

- n=0: 2.238 s, razón 1.000.
- n=1: 3.393 s, razón 1.516.
- n=2: 3.447 s, razón 1.540.
- n=3: 3.430 s, razón 1.533.

`pg_verifybackup` dentro de `total` (de los logs de restauración):

- n=0: mediana 0.088 s, 3.9 % del total.
- n=1: mediana 0.095 s, 2.8 % del total.
- n=2: mediana 0.098 s, 2.8 % del total.
- n=3: mediana 0.095 s, 2.7 % del total.

`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): FULL 0.083 s, INCR 1 0.081 s, INCR 2 0.081 s, INCR 3 0.078 s.

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

Restauración, mediana de 3 repeticiones por etapa (sin `total`):

- n=0: combinar 0.249 s, arranque 0.736 s, validacion 0.152 s.
- n=1: combinar 0.713 s, arranque 0.533 s, validacion 0.162 s.
- n=2: combinar 0.753 s, arranque 0.532 s, validacion 0.157 s.
- n=3: combinar 0.761 s, arranque 0.629 s, validacion 0.150 s.

Restauración, `total` (mediana) y razón restore(n) / restore(0):

- n=0: 1.267 s, razón 1.000.
- n=1: 1.524 s, razón 1.203.
- n=2: 1.551 s, razón 1.224.
- n=3: 1.647 s, razón 1.300.

`pg_verifybackup` dentro de `total` (de los logs de restauración):

- n=0: mediana 0.055 s, 4.3 % del total.
- n=1: mediana 0.055 s, 3.6 % del total.
- n=2: mediana 0.055 s, 3.5 % del total.
- n=3: mediana 0.053 s, 3.5 % del total.

`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): FULL 0.053 s, INCR 1 0.050 s, INCR 2 0.044 s, INCR 3 0.046 s.

### Comparación entre máquinas (tabla d, gráfico 4)

[PENDIENTE] Solo hay una máquina con corrida válida de deportista (pc-laptop). La tabla (d) y el gráfico 4 se generan cuando haya corridas válidas de deportista en otra máquina.

### Gráficos

- `graficos/grafico1_etapas_restauracion_anio_pa.png`
- `graficos/grafico1_etapas_restauracion_deportista_pc.png`
- `graficos/grafico2_tamano_respaldos.png`
- `graficos/grafico3_razon_restauracion.png`
- Gráfico 4 (comparación entre máquinas): [PENDIENTE]

## Interpretación

Esta sección interpreta los números de arriba. No son mediciones nuevas.

### `anio_pa`

- **Tamaño de los respaldos.** Cada INCR pesa entre 0.541 y 0.600 veces el FULL (27.05 a 29.99 MB, FULL 49.97 MB). La parte del INCR que corresponde a datos nuevos y la que corresponde al piso fijo (WAL y archivos del sistema) no se pueden separar con estos números. Falta medir `pg_wal` dentro de cada respaldo para confirmarlo. [PENDIENTE]
- **Restauración.** La cadena completa (n=3) tomó 1.53 veces lo que el FULL. `combinar` pasa de 0.272 s con n=0 a 1.566 a 1.601 s con n=1 a 3, y `arranque` pasa de 1.549 s a 1.346 a 1.366 s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el `total` va de 3.393 a 3.430 s.
- **Escala.** El tiempo medido más largo de la corrida es 3.447 s (respaldos y `total` mediano).

### `deportista_pc`

- **Tamaño de los respaldos.** Cada INCR pesa entre 0.436 y 0.441 veces el FULL (21.82 a 22.03 MB, FULL 50.01 MB). Las rondas de Bolt agregan muy pocas filas, así que la hipótesis de la 4.10 es que ese tamaño lo domina un piso fijo (al menos un segmento de WAL de 16 MB y archivos del sistema) y no los datos nuevos. Falta medir `pg_wal` dentro de cada respaldo para confirmarlo. [PENDIENTE]
- **Restauración.** La cadena completa (n=3) tomó 1.30 veces lo que el FULL. `combinar` pasa de 0.249 s con n=0 a 0.713 a 0.761 s con n=1 a 3, y `arranque` pasa de 0.736 s a 0.532 a 0.629 s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el `total` va de 1.524 a 1.647 s.
- **Escala.** El tiempo medido más largo de la corrida es 1.647 s (respaldos y `total` mediano). Con tan pocas filas por ronda, estos tiempos reflejan sobre todo el costo fijo de cada operación y no sirven para hablar del costo por volumen de datos.

### Alcance

- Se reporta la mediana de 3 repeticiones. La caché del sistema operativo puede favorecer a las repeticiones 2 y 3.
- Estos números no bastan para concluir en general si conviene el FULL frecuente, el incremental o el diferencial: las corridas válidas difieren en carga y en máquina a la vez, y el piso fijo de cada respaldo (`pg_wal`) no está medido. [PENDIENTE]
- `pg_verifybackup` pesó entre 2.7 % y 4.3 % del `total` de restauración (mediana por n) en anio_pa, deportista_pc.

## Pendiente

- [PENDIENTE] Corrida válida de `deporte_pb` (excluida; ver `ESTADO_CSV.md`).
- [PENDIENTE] `tiempos_deportista_pa.csv` no existe.
- [PENDIENTE] `tiempos_deportista_pb.csv` no existe.
- [PENDIENTE] Tabla (d) y gráfico 4 (requieren corridas válidas de deportista en más de una máquina).
- [PENDIENTE] Tamaño de `pg_wal` dentro de cada respaldo, para confirmar el piso fijo.
- [PENDIENTE] Recomendación por escenario (FULL, incremental, diferencial).
