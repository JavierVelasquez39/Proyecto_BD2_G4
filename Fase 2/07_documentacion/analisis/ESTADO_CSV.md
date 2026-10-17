# Estado de los CSV de tiempos

Generado por `analizar.py`. Un CSV entra al análisis si cumple el formato de la sección 4.10 (53 líneas, 14 campos por línea, UTF-8 sin BOM, LF, 0 ALERTA, 1 FULL, 3 INCR y 12 filas por etapa de restauración, `paso` como texto) y si sus filas coinciden con los logs actuales de la corrida: `segundos` y `bytes` de cada respaldo, y `Total:` y hora de inicio de cada restauración. Los logs rotados (`.AAAAMMDD_HHMMSS.log`) no cuentan como respaldo de una fila.

| Archivo | Estado | Logs rotados | Motivo |
|---|---|---:|---|
| `tiempos_anio_pa.csv` | válido | 0 |  |
| `tiempos_deporte_pb.csv` | excluido | 37 | fila 9 (restore n=0 rep 1, total 0.741 s, inicio 18:39:29.179): no coincide con `deporte_pb_12_restore_cadena0_rep1.log` (Total 2.444 s, inicio 2026-10-16 22:48:23); solo coincide con el log rotado `deporte_pb_12_restore_cadena0_rep1.20261016_222939.log`<br>fila 13 (restore n=1 rep 1, total 2.102 s, inicio 18:39:41.027): no coincide con `deporte_pb_13_restore_cadena1_rep1.log` (Total 8.431 s, inicio 2026-10-16 22:48:26); solo coincide con el log rotado `deporte_pb_13_restore_cadena1_rep1.20261016_224658.log`<br>fila 17 (restore n=2 rep 1, total 2.215 s, inicio 18:40:03.584): no coincide con `deporte_pb_14_restore_cadena2_rep1.log` (Total 3.840 s, inicio 2026-10-16 22:48:45); solo coincide con el log rotado `deporte_pb_14_restore_cadena2_rep1.20261016_224731.log`<br>fila 21 (restore n=3 rep 1, total 2.107 s, inicio 18:40:24.928): no coincide con `deporte_pb_15_restore_cadena3_rep1.log` (Total 3.768 s, inicio 2026-10-16 22:48:50); solo coincide con el log rotado `deporte_pb_15_restore_cadena3_rep1.20261016_224737.log` |
| `tiempos_deporte_pc.csv` | válido | 0 |  |
| `tiempos_deportista_pc.csv` | válido | 0 |  |

Cobertura de los tres tipos de carga del enunciado:

- `anio`: `anio_pa`
- `deporte`: `deporte_pc`
- `deportista`: `deportista_pc`
