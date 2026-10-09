# Propuesta C1: columnas de tiempos_{tipo}_{persona}.csv

Estado: propuesta para revisar en el equipo. No reemplaza la sección 4.10 de
`GUIA_EQUIPO_FASE2.md` hasta que se acuerde.

## Las dos versiones

**Guía, sección 4.10 (12 columnas):**

```text
corrida,maquina,paso,operacion,n_cadena,etapa,inicio,fin,segundos,bytes,validacion,repeticion
```

- `etapa`: `total` en respaldos; `combinar`, `arranque`, `validacion`, `total` en restauraciones.

**Propuesta de Javier (10 columnas):**

```text
persona,tipo_carga,ronda,operacion,etapa,inicio_iso,fin_iso,segundos,bytes,observacion
```

- `operacion` en {`backup_full`, `backup_incr`, `restore`}.
- `etapa` en {`basebackup`, `combine`, `arranque`, `recovery`, `validacion`}.

## Diferencias

| Tema | Guía 4.10 | Propuesta | Comentario |
|---|---|---|---|
| Identificación de la corrida | `corrida` (`anio_pa`) | `persona` + `tipo_carga` | Equivalentes. Dos columnas separadas facilitan agrupar en el análisis. |
| Máquina | `maquina` | no está | Hace falta para la comparación de Bolt en las 3 máquinas (tabla 4 y gráfico 4 de 4.10). |
| Paso del ciclo | `paso` (`00` a `16`) | no está | Enlaza cada fila con su captura y su log (convención 1.8). |
| Cadena restaurada | `n_cadena` (0 a 3) | `ronda` | No son lo mismo: la ronda es una carga de datos y la cadena es cuántos INCR entran en la restauración. Para los respaldos coinciden (INCR n se toma tras la ronda n), pero para las restauraciones `n_cadena` es más claro. |
| Etapas | `combinar`, `arranque`, `validacion`, `total` | `basebackup`, `combine`, `arranque`, `recovery`, `validacion` | La propuesta separa `recovery` y nombra la etapa del respaldo. No tiene fila `total`. |
| Horas | `inicio`, `fin` (hora local) | `inicio_iso`, `fin_iso` | Mejor ISO 8601 con zona (`2026-10-12T15:30:01.123-06:00`) para que no haya duda de la zona horaria. |
| Resultado de la validación | `validacion` (`OK` / `ALERTA`) | no está (podría ir en `observacion`) | Conviene una columna propia: el análisis filtra por ella. |
| Repetición | `repeticion` | no está | Necesaria si se repiten las restauraciones 3 veces y se reporta la mediana. |
| Texto libre | no está | `observacion` | Útil; sin comas o entre comillas dobles. |

## Sobre la etapa `recovery`

En `restaurar.sh` la etapa de arranque es `pg_ctl ... -w start`, que espera
hasta que el servidor acepta conexiones. Ese tiempo ya incluye la recuperación
(aplicar el WAL incluido en el respaldo). Para separar `arranque` y `recovery`
habría que leer las marcas de tiempo del log del servidor (`redo starts at` y
`redo done at`), lo que solo funciona con `log_min_messages` en un nivel que
las muestre y complica el script. Opciones:

1. Dejar una sola etapa `arranque` (incluye recovery) y explicarlo en el PDF.
2. Agregar `recovery` como etapa calculada a partir del log del servidor, sin
   restarla de `arranque`.

Se recomienda la opción 1 para el ciclo oficial, salvo que A confirme en el
ensayo que la opción 2 es sencilla.

## Versión unificada recomendada

```text
persona,tipo_carga,maquina,paso,operacion,n_cadena,etapa,inicio_iso,fin_iso,segundos,bytes,validacion,repeticion,observacion
```

| Columna | Valores | Ejemplo |
|---|---|---|
| `persona` | `pa`, `pb`, `pc` | `pc` |
| `tipo_carga` | `anio`, `deporte`, `deportista` | `deportista` |
| `maquina` | identificador corto | `pc-laptop` |
| `paso` | `00` a `16` (sección 1.6) | `13` |
| `operacion` | `backup_full`, `backup_incr`, `restore` | `restore` |
| `n_cadena` | 0 = solo FULL; 1 a 3 = INCR incluidos | `1` |
| `etapa` | respaldos: `basebackup`; restauraciones: `combinar`, `arranque`, `validacion`, `total` | `combinar` |
| `inicio_iso`, `fin_iso` | ISO 8601 con zona, milisegundos | `2026-10-12T15:30:01.123-06:00` |
| `segundos` | `fin - inicio`, 3 decimales | `4.812` |
| `bytes` | respaldos: tamaño del directorio; restauraciones: tamaño de PGDATA (solo en `combinar` y `total`) | `51234816` |
| `validacion` | `OK`, `ALERTA` o vacío si no aplica | `OK` |
| `repeticion` | 1, 2, 3 | `1` |
| `observacion` | texto libre, sin comas | `primera corrida` |

`inicio_iso` y `fin_iso` se pueden generar en bash con
`date '+%Y-%m-%dT%H:%M:%S.%3N%:z'`.

Si el equipo acepta esta versión, hay que actualizar la sección 4.10 de la guía
y el esqueleto de los scripts de A (que escriben las filas).
