# Propuesta C1: columnas de tiempos_{tipo}_{persona}.csv

Estado: ACORDADO (pendiente de confirmación del equipo).
`[PENDIENTE: confirmar fecha de acuerdo]`

El formato final está copiado en la sección 4.10 de `GUIA_EQUIPO_FASE2.md`.

## Antecedentes (histórico)

**Guía, sección 4.10 anterior (12 columnas):**

```text
corrida,maquina,paso,operacion,n_cadena,etapa,inicio,fin,segundos,bytes,validacion,repeticion
```

- `etapa`: `total` en respaldos; `combinar`, `arranque`, `validacion`, `total` en restauraciones.

**Propuesta de Javier, versión original (descartada) (10 columnas):**

```text
persona,tipo_carga,ronda,operacion,etapa,inicio_iso,fin_iso,segundos,bytes,observacion
```

- `operacion` en {`backup_full`, `backup_incr`, `restore`}.
- `etapa` en {`basebackup`, `combine`, `arranque`, `recovery`, `validacion`}.

### Diferencias entre ambas versiones (histórico)

Esta tabla compara las dos versiones anteriores; no describe el formato final.

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
(aplicar el WAL incluido en el respaldo).

La recuperación se puede medir aparte con las marcas de tiempo del log del
servidor (`redo starts at` y `redo done at`). Son mensajes de nivel LOG y se
escriben con la configuración por defecto (`log_min_messages = warning`
incluye LOG en el log del servidor), así que no hace falta cambiar ningún
parámetro para verlos.

Decisión:

- En el ciclo oficial hay una sola etapa `arranque`, que incluye la
  recuperación, y así se explica en el PDF.
- `recovery` separada queda como medición informativa opcional del ensayo,
  leída del log del servidor. Nunca se escribe como etapa en `tiempos` ni se
  suma con las otras etapas.

## Formato final

Encabezado (14 columnas, igual en las 3 máquinas):

```text
persona,tipo_carga,maquina,paso,operacion,n_cadena,etapa,inicio_iso,fin_iso,segundos,bytes,validacion,repeticion,observacion
```

| Columna | Regla |
|---|---|
| `persona` | `pa`, `pb` o `pc` |
| `tipo_carga` | `anio`, `deporte` o `deportista` |
| `maquina` | `{persona}-{alias}`, fijo en todas las corridas (ej. `pc-laptop`) |
| `paso` | Texto de dos dígitos (`02`, `13`). Solo generan filas los pasos de respaldo y restauración: `02`, `04`, `06`, `08`, `12` a `15`. Leerlo como texto al analizar. |
| `operacion` | `backup_full`, `backup_incr` o `restore` |
| `n_cadena` | Respaldos: `0` para el FULL y `n` para el INCR n. Restauraciones: cuántos INCR se combinaron (0 a 3). |
| `etapa` | Respaldos: `basebackup`. Restauraciones: `combinar`, `arranque`, `validacion`, `total`. |
| `inicio_iso`, `fin_iso` | ISO 8601 con zona y milisegundos, generado con `date '+%Y-%m-%dT%H:%M:%S.%3N%:z'` |
| `segundos` | `fin - inicio`, 3 decimales |
| `bytes` | Respaldos: `du -sb` del directorio de ese respaldo (no acumulado), incluyendo `pg_wal`. Restauraciones: `du -sb $PGDATA` después de `combinar`, solo en las filas `combinar` y `total`. Vacío en el resto. |
| `validacion` | `OK` o `ALERTA`, solo en las filas `validacion` y `total`. Vacío en las demás. `OK` = el diff de `conteos.sql` coincide con el del paso de carga correspondiente. |
| `repeticion` | Solo las restauraciones se repiten (3 veces, cada una desde PGDATA vacío). Los respaldos llevan siempre `1`. |
| `observacion` | Vacía, o texto opcional que el script recibe como argumento. Sin comas ni saltos de línea. |

Reglas de formato y de scripts:

1. UTF-8 sin BOM, fin de línea LF, separador coma, punto decimal.
2. El script escribe el encabezado si el archivo no existe y agrega las filas. Nadie las llena a mano. Las notas manuales van al log con `# NOTA:`.
3. Ruta: `05_logs/tiempos_{tipo_carga}_{persona}.csv`, según la convención 1.8.
4. `total` es un agregado: va del inicio de `combinar` al fin de `validacion` y excluye el `rm -rf` de PGDATA y el `pg_ctl stop`. Nunca se suma con las otras etapas. Los gráficos apilados lo excluyen. La pregunta "tiempo según longitud de cadena" usa solo `etapa=='total'`.
5. Si un paso falla, el script escribe su fila con `ALERTA` antes de salir con código distinto de 0.
6. Se reporta la mediana de las 3 repeticiones. La repetición 1 es la que lleva captura. En el PDF se aclara que la caché del sistema operativo puede favorecer a las repeticiones posteriores.
7. Una sola etapa `arranque` en el ciclo oficial (`pg_ctl -w start` ya incluye la recuperación). `recovery` separada queda como medición informativa opcional del ensayo, leída del log del servidor, y nunca se suma.

Filas de EJEMPLO (datos ficticios):

```text
pc,deportista,pc-laptop,02,backup_full,0,basebackup,2026-10-12T15:00:01.000-06:00,2026-10-12T15:00:04.512-06:00,3.512,47185920,,1,
pc,deportista,pc-laptop,13,restore,1,combinar,2026-10-12T15:25:00.000-06:00,2026-10-12T15:25:02.600-06:00,2.600,47448064,,1,
pc,deportista,pc-laptop,13,restore,1,arranque,2026-10-12T15:25:02.650-06:00,2026-10-12T15:25:03.950-06:00,1.300,,,1,
pc,deportista,pc-laptop,13,restore,1,validacion,2026-10-12T15:25:03.970-06:00,2026-10-12T15:25:04.450-06:00,0.480,,OK,1,
pc,deportista,pc-laptop,13,restore,1,total,2026-10-12T15:25:00.000-06:00,2026-10-12T15:25:04.450-06:00,4.450,47448064,OK,1,
```

Conteo: por repetición, 4 filas de respaldo y 16 de restauración (4 restauraciones por 4 etapas); con 3 repeticiones de las restauraciones son 52 filas por corrida.
