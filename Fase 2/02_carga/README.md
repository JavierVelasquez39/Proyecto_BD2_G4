# 02_carga: extracción y carga de rondas

Esta carpeta contiene dos scripts:

| Script | Dónde se ejecuta | Qué hace |
|---|---|---|
| `extraccion/exportar_rondas.sh` | Host, contra `olimpiadas_pg` (BD de la Fase 1) | Genera los CSV de la carga base y de las 9 rondas en `datos/` |
| `cargar_ronda.sh` | Dentro del contenedor de la Fase 2, como `postgres` | Carga una carpeta de `datos/` en la base `olimpiadas` |

## 1. Extracción: `extraccion/exportar_rondas.sh`

```bash
bash "Fase 2/02_carga/extraccion/exportar_rondas.sh"
# Variable opcional: CONTENEDOR=olimpiadas_pg (valor por defecto)
```

- Solo lectura: usa únicamente `COPY (SELECT ...) TO STDOUT` y fuerza la sesión con `default_transaction_read_only=on`. No usa `pg_dump`.
- Genera 59 CSV (5 de la carga base y 6 por cada una de las 9 rondas), con encabezado y las columnas en el mismo orden que el DDL de la Fase 1.
- Al final imprime las filas por CSV para revisarlas.

## 2. Carpetas y contenido de `datos/`

Filas por CSV (sin contar el encabezado), verificadas sobre los archivos generados:

| Carpeta | sede | edicion_olimpica | evento | atleta | participacion | resultado |
|---|---:|---:|---:|---:|---:|---:|
| `anio/r1_paris2024` | 1 | 1 | 332 | 11110 | 14892 | 14892 |
| `anio/r2_tokio2020` | 1 | 1 | 347 | 10953 | 13950 | 13951 |
| `anio/r3_rio2016` | 1 | 1 | 317 | 11197 | 13742 | 13742 |
| `deporte/r1_paris2024` | 1 | 1 | 1 | 91 | 91 | 91 |
| `deporte/r2_tokio2020` | 1 | 1 | 1 | 68 | 68 | 68 |
| `deporte/r3_rio2016` | 1 | 1 | 1 | 80 | 80 | 80 |
| `deportista/r1_atenas2004` | 1 | 1 | 1 | 1 | 1 | 1 |
| `deportista/r2_pekin2008` | 1 | 1 | 3 | 1 | 3 | 3 |
| `deportista/r3_londres2012` | 1 | 1 | 3 | 1 | 3 | 3 |

`datos/base/` (igual para los 3 tipos): `pais.csv` (204), `poblacion_pais.csv` (13026), `noc.csv` (236), `deporte.csv` (95), `deporte_equivalencia.csv` (2).

Qué contiene cada CSV de ronda:

- `sede.csv`: la sede de la edición de la ronda.
- `edicion_olimpica.csv`: la edición de la ronda.
- `evento.csv`: los eventos que aparecen en las participaciones de la ronda.
- `atleta.csv`: los atletas que aparecen en las participaciones de la ronda.
- `participacion.csv`: las participaciones que cumplen el filtro de la ronda (sección 1.2 de la guía).
- `resultado.csv`: los resultados de esas participaciones.

Los IDs son los originales de la Fase 1, por eso un atleta o evento que se repite entre rondas tiene el mismo ID.

## 3. Carga: `cargar_ronda.sh`

### 3.1 Uso

```bash
cargar_ronda.sh <anio|deporte|deportista> <pa|pb|pc> <base|ronda>
```

Desde el host (carpeta `Fase 2` montada en `/fase2`):

```bash
docker compose -p fase2_deportista exec -u postgres db \
  bash /fase2/02_carga/cargar_ronda.sh deportista pc base
docker compose -p fase2_deportista exec -u postgres db \
  bash /fase2/02_carga/cargar_ronda.sh deportista pc r1_atenas2004
```

La ronda se indica con el **nombre completo de la carpeta** (`r1_atenas2004`, `r2_pekin2008`, `r3_londres2012`, `r1_paris2024`, etc.). Con `r1` a secas el script responde `ERROR: carpeta invalida 'r1'` y sale con código 2 sin tocar la base.

### 3.2 Qué hace

1. Recorre las 11 tablas en el orden de las llaves foráneas: `pais`, `poblacion_pais`, `noc`, `sede`, `edicion_olimpica`, `deporte`, `deporte_equivalencia`, `evento`, `atleta`, `participacion`, `resultado`. Solo procesa las que tienen CSV en la carpeta.
2. Por cada tabla: `COPY` a una tabla temporal (staging) y luego `INSERT ... ON CONFLICT (<llave primaria>) DO NOTHING`.
3. Todo va en **una sola transacción** (`psql -1` con `ON_ERROR_STOP`): si algo falla, no se carga nada de esa ronda.
4. Imprime por tabla `en_csv` e `insertadas`. Si `insertadas` es menor que `en_csv`, son filas cuya llave primaria ya existía (normal en atletas y eventos repetidos entre rondas). Al repetir la misma ronda, `insertadas` debe ser 0 en todas las tablas.
5. Sincroniza las secuencias con `setval` al ID máximo de cada tabla (`noc` no tiene secuencia).
6. Al final imprime la fecha y los conteos de las 11 tablas (`04_restauracion/conteos.sql`).

Una fila con la misma clave natural que otra ya cargada pero con distinto ID (por ejemplo, misma ciudad y país en `sede`) no se descarta: viola la restricción `uq_*` correspondiente, la ronda falla y la transacción se revierte completa.

No usa `pg_dump` ni `pg_restore`, no hace DDL y no borra datos.

### 3.3 `DRY_RUN=1`

```bash
docker compose -p fase2_deportista exec -u postgres -e DRY_RUN=1 db \
  bash /fase2/02_carga/cargar_ronda.sh deportista pc r2_pekin2008
```

Imprime el SQL que se ejecutaría y sale con código 0, sin conectarse a la base ni escribir log.

### 3.4 Logs

- Ruta: `05_logs/<tipo>_<persona>/<tipo>_<persona>_<paso>_carga_<carpeta>.log`, con el paso de la tabla 1.6 de la guía (`01` base, `03` r1, `05` r2, `07` r3). Ejemplo: `05_logs/deportista_pc/deportista_pc_03_carga_r1_atenas2004.log`.
- La carga base también queda bajo `<tipo>_<persona>` (por ejemplo `deportista_pc_01_carga_base.log`), igual que las rondas.
- Cada ejecución escribe su propio log. Si el archivo ya existe, el anterior se renombra a `<nombre>.<AAAAMMDD_HHMMSS>.log` (hora local del contenedor) antes de escribir el nuevo, así no se mezclan corridas ni se pierden las notas `# NOTA:` agregadas a mano.
- Si no se puede crear la carpeta o escribir el log, el script imprime `CARGA FALLIDA` y sale con código distinto de 0 **antes** de tocar la base.

### 3.5 Supuestos

- Se ejecuta dentro del servicio `db` del compose, con la carpeta `Fase 2` montada en `/fase2` (variable `FASE2_DIR`).
- Se conecta por socket local como el usuario `postgres` a la base `olimpiadas` (variable `DB`).
- El `COPY ... FROM '<archivo>'` es del lado del servidor: requiere superusuario (o `pg_read_server_files`) y que los CSV sean visibles dentro del contenedor.
- La base `olimpiadas` ya existe y tiene aplicado el DDL de la Fase 1 (esquema `olimpiadas`).
- `05_logs/` debe ser escribible por el usuario `postgres` dentro del contenedor.

`[PENDIENTE]`: el `docker-compose.yml` (`Fase 2/00_infraestructura/`) todavía no existe en `develop`. Falta confirmar que el nombre del servicio, el montaje, el usuario y la base coincidan con estos supuestos.

## 4. Conteos acumulados esperados

Después de la carga base: `pais` 204, `poblacion_pais` 13026, `noc` 236, `deporte` 95, `deporte_equivalencia` 2. Estos no cambian con las rondas.

| Tipo | Después de | edicion_olimpica | sede | evento | atleta | participacion | resultado |
|---|---|---:|---:|---:|---:|---:|---:|
| anio | r1_paris2024 | 1 | 1 | 332 | 11110 | 14892 | 14892 |
| anio | r2_tokio2020 | 2 | 2 | 546 | 19187 | 28842 | 28843 |
| anio | r3_rio2016 | 3 | 3 | 566 | 26625 | 42584 | 42585 |
| deporte | r1_paris2024 | 1 | 1 | 1 | 91 | 91 | 91 |
| deporte | r2_tokio2020 | 2 | 2 | 1 | 150 | 159 | 159 |
| deporte | r3_rio2016 | 3 | 3 | 1 | 206 | 239 | 239 |
| deportista | r1_atenas2004 | 1 | 1 | 1 | 1 | 1 | 1 |
| deportista | r2_pekin2008 | 2 | 2 | 3 | 1 | 4 | 4 |
| deportista | r3_londres2012 | 3 | 3 | 3 | 1 | 7 | 7 |

## 5. Nota sobre Tokio 2020: 13950 participaciones y 13951 resultados

No es un error de carga. La participación `300652` (Campbell Stewart, NZL, `Madison, Men (Olympic)`, edición 59) tiene dos resultados, `301166` y `301167`, ambos con `lugar` 11, sin medalla y `empatado` falso.

Origen: en la fuente 1 (`Fase 1/data_raw/Olympics-Dataset/clean-data/results.csv`, líneas 304001 y 304002) esa fila viene duplicada de forma idéntica. El ETL de la Fase 1 deduplica `participacion` por clave natural (atleta, edición, evento) y conserva una fila de `resultado` por cada fila de origen, porque el modelo permite 1:N entre PARTICIPACION y RESULTADO (ver comentario de `uq_participacion` en `Fase 1/sql/ddl.sql`). Es el único caso en la edición 59.

Verificado con consultas de solo lectura sobre `olimpiadas_pg`.
