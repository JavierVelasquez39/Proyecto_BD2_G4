# Resumen del análisis comparativo (sección 4.10)

Generado por `07_documentacion/analisis/analizar.py` a partir de `05_logs/tiempos_*.csv`. Todos los números salen de los CSV y de los logs; no hay valores escritos a mano.

## Datos usados

- `tiempos_anio_pa.csv`: excluido: el encabezado no es el de 14 columnas de la 4.10; tiene 20 líneas y se esperan 53; 4 líneas no tienen 14 campos (líneas 1, 2, 3, 4).
- `tiempos_deportista_pc.csv`: válido.
- `tiempos_deporte_pb.csv`: no existe. [PENDIENTE]

Detalle en `ESTADO_CSV.md`.

**Advertencia:** las máquinas del equipo son distintas. Entre máquinas se comparan razones (por ejemplo restore(n)/restore(0)), no segundos. Los segundos absolutos solo sirven dentro de una misma corrida.

## Medido

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

[PENDIENTE] Solo hay una máquina con CSV válido de deportista (pc-laptop). La tabla (d) y el gráfico 4 se generan cuando existan `tiempos_deportista_pa.csv` y `tiempos_deportista_pb.csv` válidos.

### Gráficos

- `graficos/grafico1_etapas_restauracion_deportista_pc.png`
- `graficos/grafico2_tamano_respaldos.png`
- `graficos/grafico3_razon_restauracion.png`
- Gráfico 4 (comparación entre máquinas): [PENDIENTE]

## Interpretación

Esta sección interpreta los números de arriba. No son mediciones nuevas.

- **Costo fijo en la carga de Bolt.** Las rondas de Bolt agregan muy pocas filas, pero cada INCR pesa entre 0.436 y 0.441 veces el FULL (21.82 a 22.03 MB). La hipótesis de la 4.10 es que ese tamaño lo domina un piso fijo (al menos un segmento de WAL de 16 MB y archivos del sistema) y no los datos nuevos. Falta confirmarlo midiendo `pg_wal` dentro de cada respaldo. [PENDIENTE]
- **Restauración.** La cadena completa (n=3) tomó 1.30 veces lo que el FULL. `combinar` sube de 0.249 s con n=0 a 0.713 a 0.761 s con n=1 a 3, mientras `arranque` baja de 0.736 s a 0.532 a 0.629 s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el `total` cambia de 1.524 a 1.647 s. Con tres repeticiones y diferencias de décimas de segundo, no se interpreta la causa de la baja de `arranque`.
- **Alcance.** Con Bolt domina el costo fijo de cada respaldo y de cada restauración: el tiempo medido más largo de la corrida es 1.647 s (respaldos y `total` mediano). Estos números **no** sirven para concluir en general si conviene el respaldo incremental o el FULL frecuente: esa comparación necesita las corridas con más volumen (por año y por deporte). [PENDIENTE]
- **Repeticiones.** Se reporta la mediana de 3 repeticiones. La caché del sistema operativo puede favorecer a las repeticiones 2 y 3.
- **pg_verifybackup** pesó entre 3.5 % y 4.3 % del `total` de restauración (mediana por n).

## Pendiente

- [PENDIENTE] CSV válidos de `anio_pa`, `deporte_pb`, `deportista_pa` y `deportista_pb`.
- [PENDIENTE] Tabla (d) y gráfico 4 (requieren más de una máquina).
- [PENDIENTE] Recomendación por escenario (FULL, incremental, diferencial): requiere las corridas con más volumen.
- [PENDIENTE] Tamaño de `pg_wal` dentro de cada respaldo, para confirmar el piso fijo.
