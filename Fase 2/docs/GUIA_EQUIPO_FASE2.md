# Guía del equipo, Fase 2: Respaldo y Restauración

Grupo 4, Sistemas de Bases de Datos 2, USAC, 2do semestre 2026.
Entrega: **sábado 17 de octubre de 2026** (meta interna: viernes 16).

| Rol | Integrante | Carga principal | Código en archivos |
|---|---|---|---|
| Persona A | Kimberly | Por año | `pa` |
| Persona B | Katherine | Por deporte | `pb` |
| Persona C | Javier | Por deportista | `pc` |

## Tabla de contenidos

- [0. Cómo usar esta guía con tu IA](#0-cómo-usar-esta-guía-con-tu-ia)
- [1. Contexto común](#1-contexto-común)
  - [1.1 Qué se pide](#11-qué-se-pide)
  - [1.2 Los 3 tipos de carga y conteos esperados](#12-los-3-tipos-de-carga-y-conteos-esperados)
  - [1.3 Restricciones críticas](#13-restricciones-críticas)
  - [1.4 Estrategia técnica](#14-estrategia-técnica)
  - [1.5 Infraestructura común](#15-infraestructura-común)
  - [1.6 Ciclo oficial paso a paso](#16-ciclo-oficial-paso-a-paso)
  - [1.7 Decisiones de trabajo del equipo](#17-decisiones-de-trabajo-del-equipo)
  - [1.8 Carpetas y convención de nombres](#18-carpetas-y-convención-de-nombres)
  - [1.9 Reglas de git](#19-reglas-de-git)
  - [1.10 Hitos del equipo](#110-hitos-del-equipo)
  - [1.11 Riesgos y mitigación](#111-riesgos-y-mitigación)
  - [1.12 Checklist para optar a calificación](#112-checklist-para-optar-a-calificación)
- [2. Persona A (Kimberly): infraestructura, backup/restore y corrida por año](#2-persona-a-kimberly-infraestructura-backuprestore-y-corrida-por-año)
- [3. Persona B (Katherine): extracción, loader, manual y corrida por deporte](#3-persona-b-katherine-extracción-loader-manual-y-corrida-por-deporte)
- [4. Persona C (Javier): validación, fragmentación, ER/DDL, análisis, PDF y corrida por deportista](#4-persona-c-javier-validación-fragmentación-erddl-análisis-pdf-y-corrida-por-deportista)
- [5. Preguntas abiertas para el auxiliar](#5-preguntas-abiertas-para-el-auxiliar)
- [6. Apéndice: discrepancias y cosas no verificadas](#6-apéndice-discrepancias-y-cosas-no-verificadas)

---

## 0. Cómo usar esta guía con tu IA

1. Copia la **Sección 1 completa** y **tu sección personal** (2, 3 o 4).
2. Pega primero el prompt inicial de abajo, llenando los huecos, y luego las dos secciones.
3. Trabaja una tarea a la vez, en el orden de tu tabla de tareas.
4. Todo lo marcado `[PENDIENTE]` no está verificado: confírmalo en el ensayo o con el equipo antes de darlo por hecho.
5. Si tu IA propone algo que contradice esta guía, gana la guía; avisa al equipo si crees que la guía está mal.

**Prompt inicial (copiar y llenar):**

```text
Soy [Kimberly/Katherine/Javier], Persona [A/B/C] del Grupo 4 de Sistemas de Bases de Datos 2 (USAC).
Trabajo en Windows con Docker Desktop, en mi propia máquina. Hoy es [FECHA].
Abajo te pego el "Contexto común" de nuestra guía y mi sección personal.

Reglas para ayudarme:
1. Guíame una tarea a la vez, en el orden de mi tabla de tareas. Antes de cada
   paso dime qué vamos a hacer y por qué, y espera a que te confirme que terminé
   (o te pegue la salida) antes de seguir.
2. Solo respaldos FÍSICOS de PostgreSQL 17 (pg_basebackup, pg_combinebackup).
   Nunca sugieras pg_dump, pg_dumpall ni pg_restore.
3. Solo línea de comandos. No sugieras herramientas gráficas (pgAdmin, DBeaver, etc.).
4. Recuérdame en cada captura que debe verse la fecha y hora del sistema operativo.
5. Nunca propongas comandos que toquen el contenedor olimpiadas_pg o su volumen
   (solo SELECT de lectura si mi sección lo pide), ni docker volume prune,
   docker system prune o docker rm -v.
6. Si algo está marcado [PENDIENTE] o no estás seguro, dilo y propón cómo
   verificarlo; no inventes rutas, IDs ni resultados.
7. Respóndeme en español.

Mi tarea actual es: [TAREA DE MI TABLA].

[PEGAR AQUÍ: Sección 1 completa]
[PEGAR AQUÍ: Mi sección personal]
```

---

## 1. Contexto común

### 1.1 Qué se pide

Fase 2 del proyecto: a partir de la base de datos de las Olimpiadas de la Fase 1, demostrar respaldo y restauración **físicos** desde consola y comparar tiempos.

Para **cada tipo de carga** (año, deporte, deportista), en una instancia nueva:

1. Carga base y luego respaldo **FULL**.
2. Ronda 1, luego **INCR 1**. Ronda 2, luego **INCR 2**. Ronda 3, luego **INCR 3**.
3. Después de cada carga: capturas de `SELECT *` y `SELECT COUNT(*)` de cada tabla.
4. Medir la fragmentación de las tablas.
5. Eliminar la base de datos.
6. Restaurar el FULL, luego FULL + INCR 1, luego + INCR 2, luego + INCR 3, midiendo el tiempo de cada restauración.
7. Validar después de cada restauración con SELECT y COUNT.
8. Análisis comparativo de tiempos y conclusión sobre qué estrategia conviene.

Fuente del enunciado: `docs/proyecto_2_respaldo_y_restauracion.md`, secciones 4.2, 6 y 8. Fase 1: `docs/Enunciado_proyecto_1.pdf`. Modelo ER: `docs/Modelo_ER_actualizado.xml` (draw.io). Ponderación: 24 pts. Rúbrica: 100 pts (ver 1.12 y secciones de persona).

> La interpretación "carga base + 3 rondas = 1 FULL + 3 INCR" es una propuesta del equipo: `[PENDIENTE]` confirmar con el auxiliar (pregunta 1 de la sección 5). Si dice que la carga inicial es la ronda 1, el ciclo queda 1 FULL + 2 INCR y se omite la carga base como paso separado (la base se carga junto con la ronda 1).

### 1.2 Los 3 tipos de carga y conteos esperados

Los IDs y conteos se verificaron con consultas de solo lectura sobre la BD de la Fase 1 (`olimpiadas_pg`, PostgreSQL 16.15) el 7 de octubre de 2026.

**Carga base** (igual para los 3 tipos; catálogos completos):

| Tabla | Filas |
|---|---:|
| pais | 204 |
| poblacion_pais | 13,026 |
| noc | 236 |
| deporte | 95 |
| deporte_equivalencia | 2 |

**Rondas:**

| Tipo | Ronda | Edición (`edicion_id`) | Sede (`sede_id`) | Filtro sobre `participacion` |
|---|---|---|---|---|
| Año | r1 París 2024 | 61 | 2 Paris (France) | `edicion_id = 61` |
| Año | r2 Tokio 2020 | 59 | 21 Tokyo (Japan) | `edicion_id = 59` |
| Año | r3 Río 2016 | 55 | 44 Rio de Janeiro (Brazil) | `edicion_id = 55` |
| Deporte | r1 2024 | 61 | 2 | `edicion_id = 61 AND evento_id = 1025` |
| Deporte | r2 2020 | 59 | 21 | `edicion_id = 59 AND evento_id = 1025` |
| Deporte | r3 2016 | 55 | 44 | `edicion_id = 55 AND evento_id = 1025` |
| Deportista | r1 Atenas 2004 | 45 | 1 Athina (Greece) | `edicion_id = 45 AND atleta_id = 104492` |
| Deportista | r2 Pekín 2008 | 47 | 39 Beijing (China) | `edicion_id = 47 AND atleta_id = 104492` |
| Deportista | r3 Londres 2012 | 51 | 4 London (United Kingdom) | `edicion_id = 51 AND atleta_id = 104492` |

- Evento 1025 = `100 metres, Women (Olympic)`, deporte Athletics. Está unificado en 2016, 2020 y 2024.
- Atleta 104492 = Usain Bolt (`Usain St. Leo Bolt`, nacido 1986-08-21, NOC JAM).

**Conteos acumulados esperados después de cada ronda** (además de la carga base, que no cambia):

| Tipo | Después de | edicion_olimpica | sede | evento | atleta | participacion | resultado |
|---|---|---:|---:|---:|---:|---:|---:|
| Año | r1 | 1 | 1 | 332 | 11,110 | 14,892 | 14,892 |
| Año | r2 | 2 | 2 | 546 | 19,187 | 28,842 | 28,843 |
| Año | r3 | 3 | 3 | 566 | 26,625 | 42,584 | 42,585 |
| Deporte | r1 | 1 | 1 | 1 | 91 | 91 | 91 |
| Deporte | r2 | 2 | 2 | 1 | 150 | 159 | 159 |
| Deporte | r3 | 3 | 3 | 1 | 206 | 239 | 239 |
| Deportista | r1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Deportista | r2 | 2 | 2 | 3 | 1 | 4 | 4 |
| Deportista | r3 | 3 | 3 | 3 | 1 | 7 | 7 |

Después del FULL (solo carga base) estas seis tablas deben estar en 0.

Datos que hay que explicar en las capturas y el PDF (no son errores de carga):

- Tokio 2020 tiene 1 resultado más que participaciones (13,951 contra 13,950), porque el modelo permite 1:N entre PARTICIPACION y RESULTADO.
- Los 214 eventos "nuevos" de Tokio aparecen porque la mayoría de los nombres de eventos de 2024 (fuente 3) no se unificaron con los de la fuente 1 en la Fase 1.
- Todas las filas de `resultado` de 2024 tienen `lugar` NULL (14,892), incluso las de medallistas: la fuente 3 solo trae medalla.
- Bolt en Pekín 2008, relevo 4x100: `lugar` y `medalla` NULL (la medalla fue retirada en 2017).
- Bolt también compitió en 2016, pero esa edición no se carga: el enunciado pide 2004, 2008 y 2012.

**Orden de inserción** (verificado contra las FK de `Fase 1/sql/ddl.sql`):

```text
pais -> poblacion_pais -> noc -> sede -> edicion_olimpica -> deporte
     -> deporte_equivalencia -> evento -> atleta -> participacion -> resultado
```

| Tabla | Depende de |
|---|---|
| poblacion_pais | pais |
| noc | pais (nullable) |
| sede | pais (nullable) |
| edicion_olimpica | sede (nullable) |
| deporte_equivalencia, evento | deporte |
| atleta | ninguna |
| participacion | atleta, edicion_olimpica, evento, noc (nullable) |
| resultado | participacion |

### 1.3 Restricciones críticas

- **Solo respaldos físicos.** Prohibido `pg_dump`, `pg_dumpall` y `pg_restore`. Los `.dump` de `Fase 1/backups/` (solo en la máquina de Javier, no están en git) son lógicos y **no** son evidencia de la Fase 2.
- **Solo consola.** Nada de pgAdmin, DBeaver ni otros clientes gráficos para respaldar o restaurar.
- **Fecha y hora del sistema operativo visibles en cada captura.** Deja visible el reloj de la barra de tareas de Windows y además usa el prompt de psql con hora (ver 1.5).
- **Almacenamiento persistente con volúmenes con nombre** (enunciado 8.3). Nada de PGDATA ni respaldos dentro de carpetas de OneDrive.
- **Una instancia nueva por tipo de carga** (proyecto de Docker Compose distinto por tipo).
- **No tocar `olimpiadas_pg` ni su volumen.** Es la base fuente de la Fase 1 y está en un volumen **anónimo**. Nunca uses `docker volume prune`, `docker system prune --volumes`, `docker rm -v olimpiadas_pg`, ni ejecutes `Fase 1/sql/ddl.sql` (ni su copia en `Fase 2/01_ddl/`) contra el puerto 55433 (ese script empieza con `DROP SCHEMA IF EXISTS olimpiadas CASCADE`).

### 1.4 Estrategia técnica

| Elemento | Decisión |
|---|---|
| Motor | PostgreSQL 17, imagen `postgres:17` |
| FULL | `pg_basebackup -Fp -Xs -c fast` |
| INCR N | `pg_basebackup --incremental=<backup_manifest del respaldo anterior>` |
| Restauración | `pg_combinebackup FULL [INCR1 ... INCRn] -o $PGDATA`, luego arranque con `pg_ctl` |
| Requisito | `summarize_wal=on` **antes** de tomar el FULL (sin esto, el incremental falla) |
| Integridad | `initdb --data-checksums` (vía `POSTGRES_INITDB_ARGS`) |
| Zona horaria | `TZ` local de cada quien (por defecto `America/Guatemala`) |
| Fragmentación | Extensión `pgstattuple` (contrib, viene en la imagen) |

Por qué PostgreSQL 17 y no 16: la Fase 1 corre en 16.15, que no tiene respaldos incrementales nativos. Los incrementales con `pg_basebackup` existen desde PostgreSQL 17. Como el enunciado pide una instancia nueva por tipo de carga, el cambio de versión no afecta a la base de la Fase 1. `[PENDIENTE]` confirmar con el auxiliar (pregunta 6).

**Limitación que se debe documentar en el PDF y el manual:** en PostgreSQL un respaldo incremental **no se aplica sobre un clúster vivo**. `pg_combinebackup` toma el FULL más la cadena de incrementales y reconstruye un directorio de datos completo; luego se arranca el servidor sobre ese directorio. Por eso "restaurar el INCR 2" significa reconstruir FULL + INCR 1 + INCR 2 desde cero. Si se pierde un eslabón de la cadena, los siguientes no sirven.

**Incremental contra diferencial:** el equipo usa **incremental encadenado** (cada INCR apunta al `backup_manifest` del respaldo inmediato anterior). Si cada INCR apuntara al manifiesto del FULL, el resultado sería un **diferencial**: solo se necesitaría FULL + el último, pero cada respaldo crecería con el tiempo. Hacer también diferenciales en una corrida es opcional y enriquece el análisis. `[PENDIENTE]` pregunta 3.

**Comandos de referencia** (se ejecutan dentro del contenedor como usuario `postgres`):

```bash
# FULL
pg_basebackup -D /backups/full -Fp -Xs -c fast -l "full_<tipo>_<persona>" -v -P

# INCR 1 (encadenado al FULL); INCR 2 apunta a /backups/incr1/backup_manifest, etc.
pg_basebackup -D /backups/incr1 -Fp -Xs -c fast --incremental=/backups/full/backup_manifest -v -P

# Restaurar la cadena hasta INCR 2
pg_combinebackup /backups/full /backups/incr1 /backups/incr2 -o "$PGDATA"
```

`[PENDIENTE]` verificar en el ensayo: (a) que `pg_basebackup` por socket local tiene permiso de replicación en el `pg_hba.conf` por defecto de la imagen; (b) que `pg_combinebackup` acepta un solo FULL (si no, para "restaurar solo el FULL" se usa `cp -a /backups/full/. "$PGDATA"/`); (c) si `pg_verifybackup` acepta directorios incrementales o solo el FULL y el resultado combinado.

### 1.5 Infraestructura común

Todo se ejecuta con el **mismo** `Fase 2/00_infraestructura/docker-compose.yml`, la misma imagen y los mismos scripts congelados (hito del domingo 11). La Persona A lo publica el jueves 8. Contenido acordado:

```yaml
# Fase 2/00_infraestructura/docker-compose.yml
# Una instancia por tipo de carga: docker compose -p fase2_<tipo> up -d
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_PASSWORD: fase2
      POSTGRES_DB: olimpiadas
      POSTGRES_INITDB_ARGS: "--data-checksums"
      PGDATA: /var/lib/postgresql/data/pgdata
      TZ: ${TZ_LOCAL:-America/Guatemala}
      PGTZ: ${TZ_LOCAL:-America/Guatemala}
    command:
      - postgres
      - -c
      - summarize_wal=on
      - -c
      - timezone=${TZ_LOCAL:-America/Guatemala}
      - -c
      - log_timezone=${TZ_LOCAL:-America/Guatemala}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d olimpiadas"]
      interval: 5s
      retries: 20
    volumes:
      - pgdata:/var/lib/postgresql/data   # volumen con nombre: fase2_<tipo>_pgdata
      - backups:/backups                  # volumen con nombre: fase2_<tipo>_backups
      - ../:/fase2                        # carpeta "Fase 2" del repo: scripts, CSV y logs
volumes:
  pgdata:
  backups:
```

Notas:

- No se publica ningún puerto: todo se hace con `docker compose exec`. Así no choca con `olimpiadas_pg` (55433) ni con otros contenedores.
- Con `-p fase2_anio` los volúmenes se llaman `fase2_anio_pgdata` y `fase2_anio_backups`. Cada tipo de carga es una instancia nueva con sus propios volúmenes.
- Se recomienda clonar el repo **fuera de OneDrive** (por ejemplo `C:\bd2\Proyecto`) porque `../` se monta en el contenedor. `[PENDIENTE]` verificar que el montaje funciona en las 3 máquinas.
- `[PENDIENTE]` el volumen `/backups` nuevo pertenece a `root`. En el ensayo, verificar si hace falta `docker compose -p fase2_<tipo> exec -u root db chown postgres:postgres /backups` antes del FULL.
- Ejecuta `docker compose` desde **PowerShell** (en Git Bash las rutas `/backups/...` se reescriben; si usas Git Bash, antepone `MSYS_NO_PATHCONV=1`).
- La carpeta `Fase 2` tiene un espacio en el nombre: en PowerShell y en Git Bash escríbela siempre entre comillas (`cd "Fase 2/00_infraestructura"`), y en los scripts de bash pon comillas en toda variable que contenga una ruta del host. Dentro del contenedor no hay problema: se monta como `/fase2`.

**Prompt de psql con hora** (en cada sesión que se capture):

```sql
\set PROMPT1 '%`date "+%F %T"` %n@%/%R%# '
```

**Comandos base** (PowerShell, desde `Fase 2/00_infraestructura`):

```powershell
docker compose -p fase2_anio up -d
docker compose -p fase2_anio ps
docker volume inspect fase2_anio_pgdata fase2_anio_backups
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -c "SHOW summarize_wal; SHOW data_checksums; SHOW timezone; SELECT version();"
```

### 1.6 Ciclo oficial paso a paso

El número de paso es el que va en el nombre de capturas y logs (1.8). `<P>` es `fase2_<tipo>`.

| Paso | Acción | Comando principal | Evidencia |
|---|---|---|---|
| 00 | Instancia nueva | `docker compose -p <P> up -d`; DDL y extensiones | Captura: `docker volume inspect`, `\dt olimpiadas.*`, `SHOW summarize_wal`, `SHOW data_checksums` |
| 01 | Carga base | `cargar_ronda.sh <tipo> <persona> base` | Captura: COUNT 11 tablas + SELECT; log de carga |
| 02 | FULL | `backup_full.sh <tipo> <persona>` | Captura del comando con hora; log; tamaño; fila en `tiempos` |
| 03 | Ronda 1 | `cargar_ronda.sh ... r1_...` | Captura COUNT + SELECT; log |
| 04 | INCR 1 | `backup_incremental.sh <tipo> <persona> 1` | Captura; log; tamaño; fila en `tiempos` |
| 05 / 06 | Ronda 2 / INCR 2 | igual | igual |
| 07 / 08 | Ronda 3 / INCR 3 | igual | igual |
| 09 | Fragmentación previa | `psql -f /fase2/04_restauracion/fragmentacion_tablas.sql` y `fragmentacion_indices.sql` | Captura + CSV |
| 10 | Eliminar la BD | `DROP DATABASE olimpiadas;` desde la BD `postgres`, luego `\l` | Captura con `\l` sin `olimpiadas` |
| 11 | Detener y vaciar PGDATA | `docker compose -p <P> stop db`; el script de restauración borra `$PGDATA` y lo lista vacío | Captura |
| 12 | Restaurar FULL | `restaurar.sh <tipo> <persona> 0` | Captura con tiempos y COUNT; log; fila en `tiempos` |
| 13 | Restaurar FULL + INCR 1 | `restaurar.sh <tipo> <persona> 1` | igual |
| 14 | Restaurar hasta INCR 2 | `restaurar.sh <tipo> <persona> 2` | igual |
| 15 | Restaurar hasta INCR 3 | `restaurar.sh <tipo> <persona> 3` | igual; los COUNT deben coincidir con el paso 07 |
| 16 | Fragmentación posterior | `docker compose -p <P> start db`; `fragmentacion_tablas.sql` y `fragmentacion_indices.sql` | Captura + CSV; debe coincidir con el paso 09 |

Ejecución de la restauración (con `db` detenido, PowerShell):

```powershell
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 0
```

Medición del tiempo: la toma el **script**, no una persona. Cada restauración registra tres etapas (combinar/copiar, arranque hasta aceptar conexiones, validación) y el total.

Cada restauración se repite 3 veces, cada una desde PGDATA vacío, y se reporta la mediana. La repetición 1 lleva captura; las demás quedan en el log.

### 1.7 Decisiones de trabajo del equipo

- Cada integrante hace **su corrida oficial en su propia máquina**.
- Las 3 máquinas usan el mismo `docker-compose.yml`, la misma imagen (`postgres:17`) y los mismos scripts congelados el domingo 11. Nadie cambia scripts después de esa fecha sin avisar a los otros dos.
- Los tiempos se comparan **dentro de cada corrida**. En el análisis se reportan **razones** además de segundos (por ejemplo "cadena completa = 1.4 veces el FULL"), porque los segundos absolutos entre máquinas distintas no son comparables directamente.
- Cada quien documenta las especificaciones de su máquina (CPU, RAM, disco, versión de Windows, Docker, recursos asignados a WSL2):

  ```powershell
  Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
  Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, TotalVisibleMemorySize
  Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size
  Get-PSDrive C
  docker version
  docker info --format "CPUs={{.NCPU}} Mem={{.MemTotal}} Kernel={{.KernelVersion}}"
  ```

- Además de su carga principal, **cada integrante corre la carga por deportista (Bolt)** como prueba de referencia común. Como es la misma carga en las 3 máquinas, permite estimar el efecto de la máquina. Para la Persona C, su corrida oficial ya es la de Bolt.
- Los CSV de las rondas se extraen **una sola vez** de la BD de la Fase 1 y se suben a git. Todos cargan desde esos CSV.

### 1.8 Carpetas y convención de nombres

```text
Fase 2/
  00_infraestructura/   docker-compose.yml, README.md
  01_ddl/               01_esquema.sql, 02_extensiones.sql
  02_carga/
    extraccion/         exportar_rondas.sh, consultas_extraccion.sql
    datos/
      base/             pais.csv, poblacion_pais.csv, noc.csv, deporte.csv, deporte_equivalencia.csv
      anio/             r1_paris2024/, r2_tokio2020/, r3_rio2016/
      deporte/          r1_paris2024/, r2_tokio2020/, r3_rio2016/
      deportista/       r1_atenas2004/, r2_pekin2008/, r3_londres2012/
    cargar_ronda.sh
  03_backup/            backup_full.sh, backup_incremental.sh
  04_restauracion/      restaurar.sh, conteos.sql, validar.sql, fragmentacion_tablas.sql, fragmentacion_indices.sql, README_04.md
  05_logs/
    {tipo}_{persona}/   logs de esa corrida
    tiempos_{tipo}_{persona}.csv
    tiempos.csv         consolidado (lo arma C)
  06_evidencias/
    {tipo}_{persona}/   capturas de esa corrida
  07_documentacion/     Documentacion_Tecnica.pdf, Manual_Usuario.pdf, graficos/
```

Cada carpeta de ronda tiene un CSV por tabla: `sede.csv`, `edicion_olimpica.csv`, `evento.csv`, `atleta.csv`, `participacion.csv`, `resultado.csv`.

**Convención de nombres:** `{tipo}_{persona}_{paso}_{descripcion}`

| Campo | Valores |
|---|---|
| `tipo` | `anio`, `deporte`, `deportista` |
| `persona` | `pa`, `pb`, `pc` |
| `paso` | dos dígitos según la tabla de 1.6 (`00` a `16`) |
| `descripcion` | corta, sin espacios ni tildes |

Ejemplos:

- `06_evidencias/anio_pa/anio_pa_04_incr1_comando.png`
- `06_evidencias/deportista_pb/deportista_pb_13_restore_cadena1_count.png`
- `05_logs/deporte_pb/deporte_pb_02_backup_full.log`
- `05_logs/tiempos_anio_pa.csv`

Las capturas en PNG. Los logs en texto UTF-8, generados por los scripts y con comentarios agregados a mano al final (prefijo `# NOTA:`).

### 1.9 Reglas de git

El repo tiene las ramas `main` y `develop` (locales y en `origin`); los commits son en español y sin convención formal. Propuesta simple:

- Cada persona trabaja en una rama desde `develop`: `fase2/a-infra`, `fase2/b-carga`, `fase2/c-analisis`.
- Se integra a `develop` con merge (o PR) al cerrar cada hito. `develop` pasa a `main` el viernes 16, antes de UEDI. `[PENDIENTE]` decidir quién hace ese merge.
- Mensajes: `fase2: <qué se hizo>` en español (ejemplo: `fase2: script de backup incremental con registro de tiempos`).
- Cada quien solo toca **sus** carpetas (`05_logs/{tipo}_{persona}`, `06_evidencias/{tipo}_{persona}`, `tiempos_{tipo}_{persona}.csv`) para evitar conflictos.

| Se sube | No se sube |
|---|---|
| Scripts (`.sh`, `.sql`), `docker-compose.yml` | Respaldos físicos (viven en el volumen `fase2_<tipo>_backups`) |
| CSV de `02_carga/datos/` (pequeños) | Contenido de PGDATA |
| Logs, `tiempos_*.csv`, capturas | `data_raw/` (ya está en `.gitignore`) |
| PDF y manual finales | `Fase 1/backups/`, `Fase 1/data_raw/`, `Fase 1/bitacoras/` (ignorados por `Fase 1/.gitignore`) |

### 1.10 Hitos del equipo

| Fecha | Hito | Quién |
|---|---|---|
| Jue 8 (mañana) | `docker-compose.yml` publicado | A |
| Jue 8 (noche) | `validar.sql`, `fragmentacion_tablas.sql`, `fragmentacion_indices.sql` y convención de nombres publicados | C |
| Vie 9 | Scripts de backup y restauración publicados | A |
| Vie 9 | CSV de base y de las 9 rondas, `cargar_ronda.sh` publicados | B |
| Sáb 10 | **Ensayo con Bolt** en las 3 máquinas; reportar fallos en el grupo | Todos |
| Dom 11 | **Scripts congelados** (tag o commit acordado en `develop`) | A coordina |
| Lun 12 | Corridas oficiales: año (A), deporte (B), deportista (C) | Todos |
| Mar 13 | Corridas oficiales pendientes; referencia Bolt de A y B | A, B |
| Mié 14 | Día de repetición y cierre de evidencias; revisión cruzada | Todos |
| Jue 15 | Análisis, gráficos, PDF y manual | C y B lideran |
| Vie 16 | **Entrega en UEDI de los 3 integrantes** | Todos |
| Sáb 17 | Solo contingencia (fecha límite) | |

### 1.11 Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Perder la BD fuente de la Fase 1 (volumen anónimo de `olimpiadas_pg`) | No usar `prune` ni `rm -v`; no correr `ddl.sql` contra el puerto 55433. Extraer los CSV una vez y subirlos a git. La BD fuente está en la máquina de Javier; respaldo extra o migración del volumen: `[PENDIENTE]` decisión de Javier |
| Hora del log distinta a la de la captura (la imagen usa UTC por defecto; `olimpiadas_pg` está en `Etc/UTC`) | `TZ`, `PGTZ` y `timezone` en el compose; verificar con `SHOW timezone` y `date` en el paso 00 |
| Cadena de incrementales rota | `summarize_wal=on` desde el arranque; no borrar ni mover respaldos hasta cerrar el miércoles 14; restaurar en orden |
| Tiempos sin registrar | Los scripts escriben `tiempos_*.csv`; revisar que tenga filas después de cada paso |
| Uso accidental de `pg_dump` | Prohibido en scripts y prompts; revisión cruzada lo verifica |
| ER desalineado con el DDL | Resuelto: ER alineado con el DDL en `Fase 2/07_documentacion/modelo_er/` (ver apéndice 6.1) |
| `lugar` NULL en todo 2024 | Documentarlo como limitación de la fuente 3 |
| `ddl.sql` empieza con `DROP SCHEMA ... CASCADE` | Ejecutarlo solo dentro de `fase2_<tipo>` con `docker compose exec` |
| Ensayo deja datos en la instancia | Antes de la corrida oficial: `docker compose -p fase2_<tipo> down -v` (solo con `-p fase2_...`) |
| Archivos con codificación incorrecta | Extraer CSV desde Git Bash, no con `>` de PowerShell 5.1 (escribe UTF-16) |

### 1.12 Checklist para optar a calificación

Si falta cualquiera, la nota es **cero** (enunciado 8.1):

- [ ] **Entrega formal:** todos los archivos y evidencias a tiempo.
- [ ] **Funcionamiento mínimo:** el ciclo obligatorio funciona (carga, FULL, INCR, eliminación, restauración, validación).
- [ ] **Originalidad:** sin plagio; fuentes de datos y documentación referenciadas.
- [ ] **Documentación:** manual técnico **y** manual de usuario.
- [ ] **Repositorio:** código ordenado y funcional.
- [ ] **Entrega en UEDI:** los 3 integrantes entregan.

Rúbrica 8.2 (100 pts): Documentación técnica 15, Manual de usuario 10, Código organizado 15, Carga masiva 15, Respaldos 15, Restauración y validación 15, Análisis comparativo 15.

---

## 2. Persona A (Kimberly): infraestructura, backup/restore y corrida por año

### 2.1 Resumen

- Prepara el entorno Docker común y los scripts de respaldo y restauración que usan los 3, y hace la corrida oficial por año.
- Es la base de todo: sin compose ni scripts nadie puede ensayar ni correr.
- Depende de B (CSV y loader, viernes 9) y de C (`validar.sql`, jueves 8).

### 2.2 Tareas

| # | Tarea | Horas | Entregable | Fecha límite |
|---|---|---:|---|---|
| A1 | Compose, volúmenes, TZ, checksums, `summarize_wal` | 1.5 | `00_infraestructura/docker-compose.yml`, `README.md` | Jue 8 mañana |
| A2 | Scripts de backup y restauración con tiempos y logs | 2.0 | `03_backup/backup_full.sh`, `03_backup/backup_incremental.sh`, `04_restauracion/restaurar.sh`, `01_ddl/*` | Vie 9 |
| A3 | Corrida oficial por año | 2.5 | `05_logs/anio_pa/`, `06_evidencias/anio_pa/`, `05_logs/tiempos_anio_pa.csv` | Lun 12 a mar 13 |
| A4 | Organización del repo y README de `Fase 2/` | 0.5 | `Fase 2/README.md` | Jue 15 |
| A5 | Su sección del PDF | 0.5 | Texto para C | Jue 15 mediodía |
| A6 | Revisión cruzada de las capturas de B | 0.5 | Lista de observaciones a B | Mié 14 |
| A7 | Entrega en UEDI | 0.25 | Comprobante | Vie 16 |
| | **Total** | **7.75** | | |
| ref | Corrida de referencia con Bolt | +0.5 | `05_logs/deportista_pa/`, `06_evidencias/deportista_pa/` | Mar 13 |

### 2.3 Paso a paso

**A1. Compose e instancia**

1. Crea `Fase 2/00_infraestructura/docker-compose.yml` con el contenido de la sección 1.5.
2. Verifica que la imagen existe: `docker image ls postgres`. Si no está `postgres:17`, `docker pull postgres:17`.
3. Levanta una instancia de prueba y valida:

   ```powershell
   cd "Fase 2/00_infraestructura"
   docker compose -p fase2_prueba up -d
   docker compose -p fase2_prueba ps
   docker compose -p fase2_prueba exec -u postgres db psql -d olimpiadas -c "SHOW summarize_wal; SHOW data_checksums; SHOW timezone;"
   docker compose -p fase2_prueba exec db date
   docker volume ls --filter name=fase2_prueba
   ```

4. Copia `Fase 1/sql/ddl.sql` a `Fase 2/01_ddl/01_esquema.sql` (sin cambios de lógica; C ajusta comentarios si hace falta). Crea `01_ddl/02_extensiones.sql`:

   ```sql
   CREATE EXTENSION IF NOT EXISTS pgstattuple;
   CREATE EXTENSION IF NOT EXISTS amcheck;   -- para pg_amcheck (opcional)
   ```

   Los stored procedures de la Fase 1 no son parte del alcance de la Fase 2. Si se cargan, también hace falta `CREATE EXTENSION unaccent` (`Fase 1/sql/procedures.sql:48`).
5. Prueba la persistencia: `docker compose -p fase2_prueba down` (sin `-v`), luego `up -d`, y comprueba que el esquema sigue.
6. Prueba los permisos de `/backups` y del montaje `/fase2` (`[PENDIENTE]` de 1.5):

   ```powershell
   docker compose -p fase2_prueba exec -u postgres db bash -c "touch /backups/x && rm /backups/x && touch /fase2/05_logs/x && rm /fase2/05_logs/x && echo OK"
   ```

7. Al terminar, `docker compose -p fase2_prueba down -v`.

**A2. Scripts**

Todos los scripts corren **dentro del contenedor** como `postgres`, con `set -euo pipefail`, y escriben:

- un log en `/fase2/05_logs/<tipo>_<persona>/`, con `date "+%F %T %Z"` al inicio y al final;
- una fila en `/fase2/05_logs/tiempos_<tipo>_<persona>.csv` con el formato final de la sección 4.10 (el script escribe el encabezado si el archivo no existe).

`backup_full.sh <tipo> <persona>`, esqueleto:

```bash
#!/usr/bin/env bash
# Respaldo FULL físico con pg_basebackup. Uso: backup_full.sh <tipo> <persona>
set -euo pipefail
TIPO=$1; P=$2
LOGDIR=/fase2/05_logs/${TIPO}_${P}; mkdir -p "$LOGDIR"
LOG=$LOGDIR/${TIPO}_${P}_02_backup_full.log
DEST=/backups/full
echo "Inicio: $(date '+%F %T %Z')" | tee -a "$LOG"
INI=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z'); t0=$(date +%s.%N)
pg_basebackup -D "$DEST" -Fp -Xs -c fast -l "full_${TIPO}_${P}" -v -P 2>&1 | tee -a "$LOG"
FIN=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z'); t1=$(date +%s.%N)
SEG=$(awk "BEGIN{printf \"%.3f\", $t1-$t0}")
BYTES=$(du -sb "$DEST" | cut -f1)
# Guarda los conteos al momento del respaldo para compararlos al restaurar
psql -d olimpiadas -At -f /fase2/04_restauracion/conteos.sql > /backups/conteos_full.txt
echo "Fin: $(date '+%F %T %Z')  segundos=$SEG  bytes=$BYTES" | tee -a "$LOG"
# Agregar fila (paso 02, backup_full, n_cadena 0, etapa basebackup, repeticion 1) según la sección 4.10
```

Verificado en la imagen `postgres:17`: `bc` no existe, por eso los segundos se calculan con `awk`; `date` con `%3N` sí funciona (GNU coreutils 9.7). `conteos.sql` es parte de `validar.sql` (lo entrega C): una sola consulta con el COUNT de las 11 tablas.

`backup_incremental.sh <tipo> <persona> <n>`: igual que el anterior, pero:

- `DEST=/backups/incr$n`.
- `BASE=/backups/full` si `n=1`; si no, `/backups/incr$((n-1))`.
- `pg_basebackup -D "$DEST" -Fp -Xs -c fast --incremental="$BASE/backup_manifest" ...`
- Guarda los conteos en `/backups/conteos_incr$n.txt`.
- El paso del log es `04`, `06` u `08` según `n`.

`restaurar.sh <tipo> <persona> <n>` (n = 0 solo FULL, n = 1 a 3 cadena):

1. Abortar si existe `$PGDATA/postmaster.pid` (el servicio `db` sigue corriendo).
2. `rm -rf "$PGDATA"` y listar `/var/lib/postgresql/data` para mostrar que quedó vacío.
3. Etapa **combinar**: medir `pg_combinebackup /backups/full [/backups/incr1 ... incrN] -o "$PGDATA"` (o `cp -a` si el `[PENDIENTE]` (b) de 1.4 falla con un solo FULL); luego `chmod 700 "$PGDATA"`.
4. Etapa **arranque**: medir `pg_ctl -D "$PGDATA" -l /tmp/pg_restore.log -w -t 900 -o "-c listen_addresses=''" start`.
5. Etapa **validación**: medir `psql -d olimpiadas -f /fase2/04_restauracion/validar.sql`.
6. Comparar `conteos.sql` contra `/backups/conteos_full.txt` o `conteos_incr$n.txt`; imprimir `VALIDACION OK` o `ALERTA: conteos distintos`. Si no coinciden, escribir antes sus filas en `tiempos` con `ALERTA` y luego salir con código distinto de 0.
7. `pg_ctl -D "$PGDATA" -m fast stop`.
8. Escribir 4 filas en `tiempos` (combinar, arranque, validación, total) y el log `<tipo>_<persona>_<12..15>_restore_*.log`.

Nota: `pg_ctl` imprime en pantalla y queda en el log; la captura debe mostrar la salida del script con el reloj de Windows.

**A3. Corrida oficial por año**

Sigue el ciclo de 1.6 con `fase2_anio` y `anio pa`. Instancia nueva:

```powershell
docker compose -p fase2_anio down -v      # solo si quedó algo del ensayo
docker compose -p fase2_anio up -d
docker compose -p fase2_anio exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/01_esquema.sql
docker compose -p fase2_anio exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/02_extensiones.sql
docker compose -p fase2_anio exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh anio pa base
docker compose -p fase2_anio exec -u postgres db bash /fase2/03_backup/backup_full.sh anio pa
docker compose -p fase2_anio exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh anio pa r1_paris2024
docker compose -p fase2_anio exec -u postgres db bash /fase2/03_backup/backup_incremental.sh anio pa 1
# ... r2_tokio2020 / incr 2, r3_rio2016 / incr 3
```

Eliminación y restauración:

```powershell
docker compose -p fase2_anio exec -u postgres db psql -d postgres -c "DROP DATABASE olimpiadas;" -c "\l"
docker compose -p fase2_anio stop db
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 0
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 1
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 2
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 3
docker compose -p fase2_anio start db
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/fragmentacion_indices.sql
```

**A4. Repo:** README de `Fase 2/` con el índice de carpetas (1.8), el orden de ejecución y un enlace al manual. Revisar que no queden archivos sueltos fuera de la estructura.

### 2.4 Criterios de terminado

| Tarea | Terminado cuando |
|---|---|
| A1 | `SHOW summarize_wal` = `on`, `SHOW data_checksums` = `on`, `SHOW timezone` = zona local, los volúmenes `fase2_<tipo>_*` aparecen en `docker volume ls` y los datos sobreviven a `down` + `up` |
| A2 | En la instancia de prueba: FULL + 2 INCR + restauración 0, 1 y 2 con `VALIDACION OK`, logs creados y filas en `tiempos` |
| A3 | Los 17 pasos (00 a 16) tienen captura y log; los COUNT coinciden con la tabla de 1.2; `tiempos_anio_pa.csv` tiene las 4 restauraciones; la fragmentación 09 y 16 coincide |
| A4 | Una persona externa entiende el orden de ejecución con solo leer el README |

### 2.5 Qué recibe y qué entrega

| Entrega | A quién | Cuándo |
|---|---|---|
| `docker-compose.yml` y `01_ddl/` | B y C | Jue 8 mañana |
| `backup_full.sh`, `backup_incremental.sh`, `restaurar.sh` | B y C | Vie 9 |
| Commit de scripts congelados | Todos | Dom 11 |
| Texto de su sección del PDF y especificaciones de su máquina | C | Jue 15 mediodía |

| Recibe | De quién | Cuándo |
|---|---|---|
| `validar.sql`, `conteos.sql`, `fragmentacion_tablas.sql`, `fragmentacion_indices.sql`, columnas de `tiempos` | C | Jue 8 noche |
| CSV y `cargar_ronda.sh` | B | Vie 9 |

### 2.6 Corrida oficial y referencia

**Oficial (año, `fase2_anio`)**, evidencias mínimas en `06_evidencias/anio_pa/`:

- `anio_pa_00_instancia_*.png` (volúmenes, `\dt`, `SHOW`).
- `anio_pa_01_base_count.png`, `anio_pa_01_base_select.png`.
- `anio_pa_02_full_comando.png` y de igual forma `04`, `06`, `08` para INCR 1 a 3.
- `anio_pa_03/05/07_r{1,2,3}_count.png` y `_select.png`.
- `anio_pa_09_fragmentacion.png`.
- `anio_pa_10_drop_database.png`, `anio_pa_11_pgdata_vacio.png`.
- `anio_pa_12..15_restore_*.png` (tiempos + COUNT + SELECT).
- `anio_pa_16_fragmentacion_post.png`.

En `05_logs/anio_pa/`: un log por paso con notas `# NOTA:` agregadas a mano. En `05_logs/tiempos_anio_pa.csv`: todas las filas.

**Referencia (Bolt, `fase2_deportista`, código `deportista_pa`):** mismo ciclo con los CSV de deportista. Se usa para comparar máquinas.

### 2.7 Trabajo transversal

- **PDF (su parte):** infraestructura (compose, volúmenes, persistencia), plan de respaldo (FULL + INCR encadenados, `summarize_wal`, limitación de PostgreSQL), descripción de los scripts y especificaciones de su máquina.
- **Revisión cruzada:** revisa las capturas y logs de **B** (`deporte_pb`) el miércoles 14: que estén los 17 pasos, el reloj visible, COUNT iguales a 1.2 y filas en `tiempos`.
- **UEDI:** entrega individual el viernes 16.

### 2.8 Errores típicos

- Tomar el FULL antes de verificar `summarize_wal=on`: el INCR 1 falla.
- Ejecutar `rm -rf` sobre `/var/lib/postgresql/data` (el punto de montaje) en lugar de `$PGDATA` (`.../pgdata`).
- Restaurar con el servicio `db` encendido: dos procesos sobre el mismo directorio.
- Usar `docker compose down -v` sin `-p fase2_...`, o cualquier `prune`.
- Ejecutar los comandos en Git Bash sin `MSYS_NO_PATHCONV=1`: las rutas del contenedor se convierten en rutas de Windows.
- Cambiar un script después del domingo 11 sin avisar: las 3 corridas dejan de ser comparables.

### 2.9 Preguntas para tu IA

1. "Revisa este docker-compose.yml para PostgreSQL 17 y dime si cumple: volúmenes con nombre, summarize_wal=on, data checksums, zona horaria America/Guatemala y sin puertos publicados."
2. "Ayúdame a escribir backup_incremental.sh siguiendo el esqueleto de backup_full.sh de mi guía, encadenando cada INCR al backup_manifest del anterior."
3. "Escribe restaurar.sh con las 3 etapas medidas (combinar, arranque, validación) y que aborte si existe postmaster.pid."
4. "pg_basebackup me dio este error: [PEGAR]. ¿Es pg_hba, permisos de /backups o summarize_wal?"
5. "Con esta salida de restaurar.sh [PEGAR], ¿los conteos coinciden con la tabla de conteos esperados para año r2?"

---

## 3. Persona B (Katherine): extracción, loader, manual y corrida por deporte

### 3.1 Resumen

- Extrae de la BD de la Fase 1 los CSV de la carga base y de las 9 rondas, escribe el loader, redacta el manual de usuario y hace la corrida oficial por deporte.
- Sin los CSV y el loader ninguna corrida puede cargar datos; el manual vale 10 pts.
- Depende de A (compose y scripts, jueves 8 y viernes 9) y de C (convención de nombres y `validar.sql`, jueves 8).

### 3.2 Tareas

| # | Tarea | Horas | Entregable | Fecha límite |
|---|---|---:|---|---|
| B1 | Extracción de CSV (base + 9 rondas) | 1.25 | `02_carga/extraccion/*`, `02_carga/datos/**.csv` | Vie 9 |
| B2 | Loader | 1.25 | `02_carga/cargar_ronda.sh` | Vie 9 |
| B3 | Corrida oficial por deporte | 2.0 | `05_logs/deporte_pb/`, `06_evidencias/deporte_pb/`, `05_logs/tiempos_deporte_pb.csv` | Lun 12 a mar 13 |
| B4 | Manual de usuario | 2.0 | `07_documentacion/Manual_Usuario.pdf` | Jue 15 |
| B5 | Su sección del PDF | 0.5 | Texto para C | Jue 15 mediodía |
| B6 | Revisión cruzada de las capturas de C | 0.5 | Observaciones a C | Mié 14 |
| B7 | Entrega en UEDI | 0.25 | Comprobante | Vie 16 |
| | **Total** | **7.75** | | |
| ref | Corrida de referencia con Bolt | +0.5 | `05_logs/deportista_pb/`, `06_evidencias/deportista_pb/` | Mar 13 |

### 3.3 Paso a paso

**B1. Extracción**

> **Quién extrae:** los IDs de esta guía (ediciones 61/59/55/45/47/51, evento 1025, atleta 104492) se verificaron en la BD `olimpiadas_pg` de la máquina de **Javier**. Si se reconstruye la BD con el ETL en otra máquina, los IDs pueden cambiar. Propuesta: Katherine escribe `exportar_rondas.sh`, Javier lo ejecuta en su máquina y sube los CSV. `[PENDIENTE]` confirmarlo entre Katherine y Javier.

Reglas:

- Solo lectura: únicamente `COPY (SELECT ...) TO STDOUT`. Nada de `INSERT`, `UPDATE`, `DELETE`, DDL ni `pg_dump`.
- Ejecutar desde **Git Bash** (la redirección `>` de PowerShell 5.1 escribe UTF-16 y rompe el CSV).
- Columnas en el orden de la tabla (`SELECT t.*`), con encabezado.

Plantilla (Git Bash, desde la raíz del repo):

```bash
q() {  # q <archivo_destino> "<consulta>"
  docker exec -i olimpiadas_pg psql -U postgres -d olimpiadas -X -q \
    -c "COPY ($2) TO STDOUT WITH (FORMAT csv, HEADER true)" > "$1"
}
D="Fase 2/02_carga/datos"   # la ruta tiene espacio: siempre entre comillas
mkdir -p "$D/base"
q "$D/base/pais.csv"                 "SELECT * FROM olimpiadas.pais ORDER BY 1"
q "$D/base/poblacion_pais.csv"       "SELECT * FROM olimpiadas.poblacion_pais ORDER BY 1"
q "$D/base/noc.csv"                  "SELECT * FROM olimpiadas.noc ORDER BY 1"
q "$D/base/deporte.csv"              "SELECT * FROM olimpiadas.deporte ORDER BY 1"
q "$D/base/deporte_equivalencia.csv" "SELECT * FROM olimpiadas.deporte_equivalencia ORDER BY 1"
```

Por cada ronda, con `ED` = edición y `F` = filtro de la tabla de 1.2:

```bash
ronda() {  # ronda <carpeta> <edicion_id> "<filtro sobre p>"
  R="$D/$1"; ED=$2; F=$3; mkdir -p "$R"
  q "$R/sede.csv"             "SELECT s.* FROM olimpiadas.sede s WHERE s.sede_id = (SELECT sede_id FROM olimpiadas.edicion_olimpica WHERE edicion_id = $ED)"
  q "$R/edicion_olimpica.csv" "SELECT * FROM olimpiadas.edicion_olimpica WHERE edicion_id = $ED"
  q "$R/evento.csv"           "SELECT e.* FROM olimpiadas.evento e WHERE e.evento_id IN (SELECT p.evento_id FROM olimpiadas.participacion p WHERE $F) ORDER BY 1"
  q "$R/atleta.csv"           "SELECT a.* FROM olimpiadas.atleta a WHERE a.atleta_id IN (SELECT p.atleta_id FROM olimpiadas.participacion p WHERE $F) ORDER BY 1"
  q "$R/participacion.csv"    "SELECT p.* FROM olimpiadas.participacion p WHERE $F ORDER BY 1"
  q "$R/resultado.csv"        "SELECT r.* FROM olimpiadas.resultado r JOIN olimpiadas.participacion p USING (participacion_id) WHERE $F ORDER BY 1"
}
ronda anio/r1_paris2024          61 "p.edicion_id = 61"
ronda anio/r2_tokio2020          59 "p.edicion_id = 59"
ronda anio/r3_rio2016            55 "p.edicion_id = 55"
ronda deporte/r1_paris2024       61 "p.edicion_id = 61 AND p.evento_id = 1025"
ronda deporte/r2_tokio2020       59 "p.edicion_id = 59 AND p.evento_id = 1025"
ronda deporte/r3_rio2016         55 "p.edicion_id = 55 AND p.evento_id = 1025"
ronda deportista/r1_atenas2004   45 "p.edicion_id = 45 AND p.atleta_id = 104492"
ronda deportista/r2_pekin2008    47 "p.edicion_id = 47 AND p.atleta_id = 104492"
ronda deportista/r3_londres2012  51 "p.edicion_id = 51 AND p.atleta_id = 104492"
```

Guarda esto como `02_carga/extraccion/exportar_rondas.sh`. Los CSV de cada ronda **no** son acumulados: el loader ignora lo que ya existe.

Verificación de filas, sin contar el encabezado (`wc -l` menos 1):

| Carpeta | participacion | resultado | atleta | evento |
|---|---:|---:|---:|---:|
| anio/r1_paris2024 | 14,892 | 14,892 | 11,110 | 332 |
| anio/r2_tokio2020 | 13,950 | 13,951 | 10,953 | 347 |
| anio/r3_rio2016 | 13,742 | 13,742 | 11,197 | 317 |
| deporte/r1 | 91 | 91 | 91 | 1 |
| deporte/r2 | 68 | 68 | `[PENDIENTE]` contar | 1 |
| deporte/r3 | 80 | 80 | `[PENDIENTE]` contar | 1 |
| deportista/r1 | 1 | 1 | 1 | 1 |
| deportista/r2 | 3 | 3 | 1 | 3 |
| deportista/r3 | 3 | 3 | 1 | 3 |

Los acumulados finales deben coincidir con la tabla de 1.2.

**B2. Loader `cargar_ronda.sh <tipo> <persona> <carpeta>`**

Corre dentro del contenedor como `postgres`. `<carpeta>` es `base` o `r1_...`; la ruta es `/fase2/02_carga/datos/base` o `/fase2/02_carga/datos/<tipo>/<carpeta>`. Por cada tabla, **en el orden de 1.2** y solo si existe su CSV:

```sql
-- dentro de una sola transacción (psql -v ON_ERROR_STOP=1 -1)
SET search_path TO olimpiadas;
CREATE TEMP TABLE stg_atleta (LIKE atleta) ON COMMIT DROP;
COPY stg_atleta FROM '/fase2/02_carga/datos/anio/r1_paris2024/atleta.csv' WITH (FORMAT csv, HEADER true);
WITH ins AS (
  INSERT INTO atleta SELECT * FROM stg_atleta ON CONFLICT DO NOTHING RETURNING 1
)
SELECT 'atleta' AS tabla, (SELECT count(*) FROM stg_atleta) AS en_csv, count(*) AS insertadas FROM ins;
```

Al final, sincronizar las secuencias porque se insertan los IDs originales:

```sql
SELECT setval(pg_get_serial_sequence('olimpiadas.atleta','atleta_id'), COALESCE(MAX(atleta_id),1)) FROM atleta;
-- igual para pais, poblacion_pais, sede, edicion_olimpica, deporte, deporte_equivalencia, evento, participacion, resultado
-- noc no tiene secuencia (PK codigo_noc)
```

El script genera el SQL con las rutas (bash) y lo pasa a `psql -d olimpiadas -v ON_ERROR_STOP=1 -1`. Al terminar imprime la fecha, ejecuta el COUNT de las 11 tablas (`conteos.sql` de C) y guarda la salida en `05_logs/<tipo>_<persona>/<tipo>_<persona>_<paso>_carga_<carpeta>.log`. `COPY ... FROM '<archivo>'` lo lee el servidor; funciona porque `/fase2` está montado en el contenedor y se corre como superusuario.

**B3. Corrida oficial por deporte:** el ciclo de 1.6 con `fase2_deporte`, `deporte pb` y las carpetas `deporte/r1_paris2024`, `r2_tokio2020`, `r3_rio2016`. Los comandos son los mismos que en A3, cambiando `anio`/`pa` por `deporte`/`pb`.

**B4. Manual de usuario** (rúbrica 1.2, 10 pts). Contenido mínimo:

1. Requisitos (Docker Desktop, imagen `postgres:17`, clonar el repo fuera de OneDrive).
2. Levantar una instancia (`docker compose -p fase2_<tipo> up -d`) y verificar la configuración.
3. Crear el esquema y cargar la base y las rondas.
4. Respaldo FULL y respaldo incremental: comando exacto, salida real de ejemplo copiada de un log.
5. Eliminar la BD y restaurar FULL y cadena: comando exacto y salida real.
6. **Interpretación de logs:** qué significa cada línea importante (inicio/fin, `pg_basebackup: base backup completed`, etapas y segundos, `VALIDACION OK` o `ALERTA`).
7. **Validación posterior a la restauración:** COUNT esperado, SELECT, fragmentación, qué hacer si sale `ALERTA`.
8. Problemas frecuentes (los de 1.11 y 2.8).

Usa salidas reales de la corrida de deporte como ejemplos.

### 3.4 Criterios de terminado

| Tarea | Terminado cuando |
|---|---|
| B1 | 5 CSV base + 54 CSV de ronda (9 x 6); filas iguales a la tabla de B1; los CSV abren en UTF-8 con encabezado |
| B2 | En una instancia de prueba, `base` + las 3 rondas de deportista dan exactamente los conteos de 1.2; correrlo dos veces no duplica nada (`insertadas = 0`) |
| B3 | Los 17 pasos con captura y log; COUNT iguales a 1.2 (deporte); `tiempos_deporte_pb.csv` completo |
| B4 | Otra persona del equipo restaura una cadena siguiendo solo el manual |

### 3.5 Qué recibe y qué entrega

| Entrega | A quién | Cuándo |
|---|---|---|
| `exportar_rondas.sh` listo para ejecutar (propuesta, `[PENDIENTE]` confirmar) | C (Javier) | Jue 8 noche |
| CSV base + 9 rondas en `develop` | A y C | Vie 9 (lo antes posible: A y C los necesitan para probar) |
| `cargar_ronda.sh` | A y C | Vie 9 |
| Borrador del manual para revisión | A y C | Mié 14 |
| Texto de su sección del PDF y especificaciones de su máquina | C | Jue 15 mediodía |

| Recibe | De quién | Cuándo |
|---|---|---|
| `docker-compose.yml` y `01_ddl/` | A | Jue 8 mañana |
| `conteos.sql` y convención de nombres | C | Jue 8 noche |
| Scripts de backup y restauración | A | Vie 9 |

### 3.6 Corrida oficial y referencia

**Oficial (deporte, `fase2_deporte`, código `deporte_pb`):** las mismas evidencias que la lista de 2.6 con prefijo `deporte_pb_`, en `06_evidencias/deporte_pb/`, logs en `05_logs/deporte_pb/` y `05_logs/tiempos_deporte_pb.csv`.

Validación especial: el evento siempre es 1025 (1 fila en `evento` en las 3 rondas) y los atletas acumulados son 91, 150 y 206.

**Referencia (Bolt, `fase2_deportista`, código `deportista_pb`):** mismo ciclo con los CSV de deportista.

### 3.7 Trabajo transversal

- **PDF (su parte):** origen de los datos (BD de la Fase 1), método de extracción, carga con staging y `ON CONFLICT`, orden de inserción, conteos esperados, especificaciones de su máquina.
- **Revisión cruzada:** revisa las capturas y logs de **C** (`deportista_pc`) el miércoles 14.
- **UEDI:** entrega individual el viernes 16.

### 3.8 Errores típicos

- Extraer con PowerShell `>` (UTF-16) en lugar de Git Bash.
- Usar `pg_dump` para "sacar los datos": está prohibido incluso como paso intermedio.
- Ejecutar algo distinto de `SELECT`/`COPY TO STDOUT` contra `olimpiadas_pg`.
- Cargar las tablas fuera de orden (falla la FK).
- Olvidar el `setval`: un `INSERT` posterior sin ID chocaría con la PK.
- Usar `ON CONFLICT DO NOTHING` y no mirar `en_csv` contra `insertadas`: un error de datos quedaría oculto.
- Copiar los CSV acumulados en lugar de por ronda: los incrementales dejarían de reflejar solo la ronda nueva.

### 3.9 Preguntas para tu IA

1. "Revisa mi exportar_rondas.sh: ¿todas las consultas son de solo lectura y el orden de columnas coincide con el DDL?"
2. "Escribe cargar_ronda.sh que genere el SQL con staging, ON CONFLICT DO NOTHING y RETURNING para las 11 tablas en este orden: [ORDEN]."
3. "Mis conteos después de deporte r2 son [PEGAR]; los esperados son [PEGAR]. ¿Qué tabla está mal y por qué?"
4. "Arma el índice del manual de usuario con base en la rúbrica: comandos específicos, ejemplos, interpretación de logs y validación de integridad."
5. "Con este log de pg_basebackup [PEGAR], explícame línea por línea qué significa para la sección 'Interpretación de logs' del manual."

---

## 4. Persona C (Javier): validación, fragmentación, ER/DDL, análisis, PDF y corrida por deportista

### 4.1 Resumen

- Escribe los scripts de validación y fragmentación, alinea el ER con el DDL, hace la corrida por deportista, arma el análisis comparativo y compila la documentación técnica.
- El análisis (15 pts) y la documentación técnica (15 pts) dependen de C, y las validaciones son lo que demuestra que la restauración funcionó.
- Depende de A (compose y scripts) y de B (CSV), y al final de los `tiempos_*.csv` y las secciones de A y B.

### 4.2 Tareas

| # | Tarea | Horas | Entregable | Fecha límite |
|---|---|---:|---|---|
| C1 | `validar.sql`, `conteos.sql`, `fragmentacion_tablas.sql`, `fragmentacion_indices.sql`, columnas de `tiempos`, convención de nombres | 1.0 | `04_restauracion/*.sql`, sección 1.8 confirmada | Jue 8 noche |
| C2 | Corrida oficial por deportista (también es la referencia común) | 2.0 | `05_logs/deportista_pc/`, `06_evidencias/deportista_pc/`, `05_logs/tiempos_deportista_pc.csv` | Lun 12 |
| C3 | Alinear ER y DDL + compilar la documentación técnica | 2.0 | ER corregido; `07_documentacion/Documentacion_Tecnica.pdf` | ER: dom 11; PDF: vie 16 temprano |
| C4 | Análisis comparativo: tablas y gráficos | 1.5 | `05_logs/tiempos.csv`, `07_documentacion/graficos/` | Jue 15 |
| C5 | Su sección del PDF | 0.5 | Texto | Jue 15 |
| C6 | Revisión cruzada de las capturas de A | 0.5 | Observaciones a A | Mié 14 |
| C7 | Entrega en UEDI | 0.25 | Comprobante | Vie 16 |
| | **Total** | **7.75** | | |

### 4.3 Paso a paso

**C1. Scripts de validación**

`04_restauracion/conteos.sql` (una línea por tabla, salida estable para comparar con `diff`):

```sql
SELECT 'pais', count(*) FROM olimpiadas.pais
UNION ALL SELECT 'poblacion_pais', count(*) FROM olimpiadas.poblacion_pais
UNION ALL SELECT 'noc', count(*) FROM olimpiadas.noc
UNION ALL SELECT 'sede', count(*) FROM olimpiadas.sede
UNION ALL SELECT 'edicion_olimpica', count(*) FROM olimpiadas.edicion_olimpica
UNION ALL SELECT 'deporte', count(*) FROM olimpiadas.deporte
UNION ALL SELECT 'deporte_equivalencia', count(*) FROM olimpiadas.deporte_equivalencia
UNION ALL SELECT 'evento', count(*) FROM olimpiadas.evento
UNION ALL SELECT 'atleta', count(*) FROM olimpiadas.atleta
UNION ALL SELECT 'participacion', count(*) FROM olimpiadas.participacion
UNION ALL SELECT 'resultado', count(*) FROM olimpiadas.resultado;
```

`04_restauracion/validar.sql`:

1. `SELECT now();` y el prompt con hora.
2. `\i /fase2/04_restauracion/conteos.sql`.
3. `SELECT * FROM olimpiadas.<tabla> ORDER BY <pk> LIMIT :limite;` para cada una de las 11 tablas. La variable se pasa con `-v limite=10` (captura) o `-v limite=ALL` (log completo); si no se define, vale 10. `[PENDIENTE]` pregunta 4: si el auxiliar exige `SELECT *` sin límite, la salida completa va al log y la captura muestra el inicio y el final.
4. Consultas de muestra con sentido: Bolt con sus 7 participaciones, el top 3 de 100 m femenino por edición, el medallero por NOC de la edición cargada.
5. Opcional: `pg_amcheck -d olimpiadas` (alertas de integridad).

Fragmentación, en dos archivos de una sola consulta cada uno (pensados para `psql --csv`; el SQL y los comandos completos están en `04_restauracion/README_04.md`):

- `04_restauracion/fragmentacion_tablas.sql`: `pgstattuple` por tabla del esquema `olimpiadas` (`table_len`, `tuple_count`, `tuple_percent`, `dead_tuple_count`, `dead_tuple_percent`, `free_space`, `free_percent`).
- `04_restauracion/fragmentacion_indices.sql`: `pgstatindex` por índice B-tree (`tree_level`, `index_size`, `avg_leaf_density`, `leaf_fragmentation`).

Ninguno incluye la hora de medición, para que las salidas de los pasos 09 y 16 se puedan comparar con `diff`.

Guardar la salida también como CSV para el análisis:

```powershell
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_tablas.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_tablas.csv"
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_indices.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_indices.csv"
```

Verificado el 8 de octubre de 2026 en una instancia temporal de PostgreSQL 17 (ver `05_logs/c1_prueba_instancia_temporal.md`): con las tablas vacías, `pgstattuple` devuelve ceros y `pgstatindex` devuelve `NaN` en `avg_leaf_density` y `leaf_fragmentation`, sin error.

**C2. Corrida oficial por deportista:** el ciclo de 1.6 con `fase2_deportista`, `deportista pc` y las carpetas `deportista/r1_atenas2004`, `r2_pekin2008`, `r3_londres2012`. Los comandos son los de A3 cambiando `anio`/`pa` por `deportista`/`pc`.

**C3. ER y DDL + documentación técnica**

1. Hecho: el modelo ER se alineó con el DDL real (el DDL es la fuente de verdad). A partir de `Fase 2/docs/Modelo_ER_actualizado.xml` se generó `Fase 2/07_documentacion/modelo_er/Modelo_ER_fase2.xml` (draw.io); la matriz de diferencias está en `DISCREPANCIAS_ER_DDL.md` y la versión Mermaid en `modelo_er.mmd`, en la misma carpeta. `[PENDIENTE: exportar desde draw.io a PNG/PDF]` el diagrama final hacia `07_documentacion/`.
2. `[PENDIENTE]` A aplica en la copia `01_ddl/01_esquema.sql` el texto propuesto para el comentario de `Fase 1/sql/ddl.sql:152-156` (está en `DISCREPANCIAS_ER_DDL.md`). `Fase 1/sql/ddl.sql` no se modifica.
3. Estructura del PDF (rúbrica 1.1 y entregables 4.4):
   1. Introducción y objetivo.
   2. Metodología (fases y cronograma real).
   3. Modelo entidad-relación utilizado.
   4. Plan de respaldo (A): estrategia, rutas, volúmenes, `summarize_wal`, limitación del incremental.
   5. Especificaciones técnicas de las 3 máquinas (tabla).
   6. Carga de datos (B): rondas, orden, conteos.
   7. Resultados por corrida: tablas de tiempos, tamaños, fragmentación.
   8. Análisis comparativo con gráficos (C4).
   9. Conclusiones y recomendación.
   10. Anexos: índice de capturas y logs.

**C4. Análisis comparativo:** ver 4.10.

### 4.4 Criterios de terminado

| Tarea | Terminado cuando |
|---|---|
| C1 | `conteos.sql`, `validar.sql`, `fragmentacion_tablas.sql` y `fragmentacion_indices.sql` corren sin error en una instancia vacía y en una con datos |
| C2 | Los 17 pasos con captura y log; COUNT iguales a 1.2 (deportista); `tiempos_deportista_pc.csv` completo |
| C3 | El ER y el DDL ya no se contradicen (o la diferencia está explicada); el PDF tiene todas las secciones de la rúbrica 1.1 |
| C4 | `tiempos.csv` consolidado sin huecos; tablas y gráficos de 4.10 generados; cada conclusión cita un número |

### 4.5 Qué recibe y qué entrega

| Entrega | A quién | Cuándo |
|---|---|---|
| `conteos.sql`, `validar.sql`, `fragmentacion_tablas.sql`, `fragmentacion_indices.sql`, columnas de `tiempos` | A y B | Jue 8 noche |
| Convención de nombres confirmada (1.8) | A y B | Jue 8 |
| CSV extraídos con `exportar_rondas.sh` desde `olimpiadas_pg` (propuesta, `[PENDIENTE]` confirmar) | B (Katherine) para verificar filas | Vie 9 mañana |
| ER corregido | Todos | Dom 11 |
| Borrador del PDF para revisión | A y B | Jue 15 noche |
| PDF final | Todos (para UEDI) | Vie 16 temprano |

| Recibe | De quién | Cuándo |
|---|---|---|
| Compose y `01_ddl/` | A | Jue 8 mañana |
| CSV y loader | B | Vie 9 |
| Scripts de backup y restauración | A | Vie 9 |
| `tiempos_*.csv`, secciones del PDF y especificaciones | A y B | Jue 15 mediodía |

### 4.6 Corrida oficial

**Oficial (deportista, `fase2_deportista`, código `deportista_pc`):** las evidencias de la lista de 2.6 con prefijo `deportista_pc_`, en `06_evidencias/deportista_pc/`, logs en `05_logs/deportista_pc/` y `05_logs/tiempos_deportista_pc.csv`.

Validación especial: 1 atleta (104492) en todo momento; participaciones acumuladas 1, 4 y 7; el relevo de 2008 sin lugar ni medalla.

**Referencia:** la corrida oficial de C **es** la corrida de Bolt de su máquina. Se compara con `deportista_pa` y `deportista_pb`.

C también dirige el **ensayo del sábado 10** (todos corren Bolt en su máquina con los scripts de ese momento) y junta los problemas encontrados en una lista para A y B.

### 4.7 Trabajo transversal

- **PDF:** compila las secciones de A y B, escribe ER, análisis, conclusiones y las especificaciones de su máquina.
- **Revisión cruzada:** revisa las capturas y logs de **A** (`anio_pa`) el miércoles 14.
- **UEDI:** entrega individual el viernes 16.

### 4.8 Errores típicos

- Comparar segundos absolutos entre máquinas como si fueran el mismo equipo.
- Sacar conclusiones con una sola medición sin decirlo (si no hay repeticiones, aclarar que es una medición única).
- Medir la fragmentación con las tablas de la carga base vacías y reportarla como "0% de fragmentación" sin explicar por qué.
- Usar el `SELECT *` sin `ORDER BY`: el orden cambia y la comparación antes/después no se ve.
- Dejar el ER desalineado con el DDL en el PDF.

### 4.9 Preguntas para tu IA

1. "Revisa mi fragmentacion.sql: ¿pgstattuple y pgstatindex miden lo que el enunciado llama 'nivel de fragmentación'? ¿Cómo lo explico en el PDF?"
2. "Este es el DDL [PEGAR] y estas son las diferencias con el ER [PEGAR]; ayúdame a decidir qué corregir en el diagrama y qué documentar."
3. "Con este tiempos.csv [PEGAR], calcula para cada corrida la razón de cada restauración contra la del FULL y arma la tabla comparativa."
4. "Escribe un script en Python (pandas + matplotlib) que lea tiempos.csv y genere los 4 gráficos de la sección 4.10."
5. "Con estos resultados [PEGAR], redacta las conclusiones citando números, sin comparar segundos absolutos entre máquinas."

### 4.10 Análisis comparativo

**Formato final de `tiempos_{tipo_carga}_{persona}.csv`** (el mismo en las 3 máquinas; detalle y antecedentes en `PROPUESTA_C1_tiempos.md`).

Encabezado (14 columnas):

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

**Tablas que debe tener el PDF:**

1. Por corrida: tamaño y tiempo de cada respaldo (FULL, INCR 1 a 3).
2. Por corrida: tiempo de cada restauración (n = 0 a 3) desglosado por etapa (`combinar`, `arranque`, `validacion`; sin `total`), mediana de las 3 repeticiones.
3. **Razones dentro de cada corrida:** `restore(n) / restore(0)` e `incr(n).bytes / full.bytes`; las de restauración usan solo `etapa=='total'` y la mediana.
4. Comparación de máquinas con Bolt (`deportista_pa`, `deportista_pb`, `deportista_pc`): mismas razones; los segundos absolutos solo como referencia.
5. Fragmentación antes (paso 09) y después (paso 16): debe ser idéntica porque la copia física conserva las páginas.
6. Especificaciones de cada máquina.

**Gráficos mínimos** (`07_documentacion/graficos/`):

1. Barras apiladas por etapa: restauración FULL contra cadenas 1, 2 y 3, uno por corrida (excluye `total`).
2. Barras: tamaño de cada respaldo por corrida.
3. Líneas: razón `restore(n) / restore(0)` contra n (`etapa=='total'`), una línea por corrida.
4. Barras: Bolt en las 3 máquinas (razones).

**Cómo redactar las conclusiones:**

- Cada afirmación cita un número de las tablas ("en la corrida por año, restaurar la cadena completa tomó 1.4 veces lo que el FULL").
- Separar lo que se midió de lo que se interpreta.
- Explicar el piso fijo de los respaldos físicos: cada respaldo incluye al menos un segmento de WAL de 16 MB y los archivos del sistema, así que en cargas pequeñas (Bolt, 100 m) el INCR pesa casi lo mismo que el FULL. Esto es una hipótesis hasta verla en los datos.
- Recomendación final por escenario: cuándo conviene FULL frecuente, cuándo incremental, cuándo diferencial, según volumen de datos y tiempo de restauración aceptable.
- Aclarar explícitamente que las máquinas son distintas y por eso se comparan razones y no segundos entre equipos.

---

## 5. Preguntas abiertas para el auxiliar

Redactadas para enviar tal cual:

1. **Carga inicial.** Para cada tipo de carga proponemos una carga base de catálogos (país, población, NOC, deporte) seguida del respaldo completo, y luego 3 rondas (por ejemplo París 2024, Tokio 2020 y Río 2016), cada una seguida de un respaldo incremental. ¿Es correcto, o la carga inicial debe ser la primera ronda (quedando 1 completo y 2 incrementales por tipo)?
2. **Cantidad de respaldos.** La rúbrica pide "3 respaldos completos y 3 incrementales/diferenciales". ¿Es en total (uno de cada uno por tipo de carga) o por tipo de carga?
3. **Incremental o diferencial.** ¿Podemos elegir entre incremental y diferencial según el motor? ¿Suma hacer ambos en alguna corrida?
4. **SELECT \*.** En tablas con miles de filas (por ejemplo 42,584 participaciones), ¿es válido capturar `SELECT * ... LIMIT` junto con el `COUNT(*)`, y dejar la salida completa en el log?
5. **Versión del motor.** En la Fase 1 usamos PostgreSQL 16. Para la Fase 2 queremos usar PostgreSQL 17 porque es la primera versión con respaldos incrementales nativos (`pg_basebackup --incremental`). ¿Es aceptable?
6. **Eliminar la base de datos.** ¿Basta con `DROP DATABASE`, o hay que eliminar la instancia completa (directorio de datos)? Planeamos hacer ambas cosas.
7. **Calificación.** ¿El día de la calificación se pedirá ejecutar o demostrar algo en vivo, o se califica solo con los entregables?
8. **Máquinas distintas.** Trabajamos en máquinas distintas y cada integrante hace una de las tres cargas. ¿Es aceptable comparar los tiempos dentro de cada corrida y documentar las especificaciones de cada equipo? Además, los tres corremos la carga por deportista como referencia común.
9. **Días de carga.** El cronograma del enunciado pone cada tipo de carga en un día distinto. ¿Es obligatorio, o pueden hacerse en paralelo el mismo día en máquinas distintas?

---

## 6. Apéndice: discrepancias y cosas no verificadas

### 6.1 Modelo ER contra DDL real

Estado: alineado. El modelo ER original (`Fase 2/docs/Modelo_ER_actualizado.xml`, 11 entidades) coincidía con `Fase 1/sql/ddl.sql` en tablas y nombres de atributos, pero no en relaciones ni marcas de FK. Se corrigió el diagrama, no el DDL: el resultado es `Fase 2/07_documentacion/modelo_er/Modelo_ER_fase2.xml`, con la matriz completa (16 puntos) y el cruce FK contra aristas en `DISCREPANCIAS_ER_DDL.md` y una versión Mermaid en `modelo_er.mmd`.

| # | Elemento | Modelo ER original | DDL / BD real | Estado |
|---|---|---|---|---|
| 1 | PARTICIPACION → RESULTADO | 1 a 0..1 | 1:N (sin `UNIQUE(participacion_id)`); la BD tiene 320,465 resultados contra 319,950 participaciones | Corregido: 1 a 0..N |
| 2 | NOC → ATLETA | Relación dibujada | No hay FK; ATLETA no tiene `codigo_noc` (decisión documentada en `Fase 1/sql/ddl.sql:13-16`) | Corregido: arista eliminada, explicado en la leyenda |
| 3 | `edicion_olimpica.anio` | Marcado FK | No es FK | Corregido |
| 4 | `sede.pais_id` | Sin marca FK | Es FK a `pais` | Corregido |
| 5 | `participacion.codigo_noc` | Obligatoria | NULLABLE, `ON DELETE SET NULL` | Corregido: extremo 0..1 del lado NOC |
| 6 | `edicion_olimpica.sede_id` | Obligatoria | NULLABLE | Corregido: extremo 0..1 del lado SEDE |
| 7 | Comentario `Fase 1/sql/ddl.sql:152` | | Dice que el ER declara 1 a N (coincide con el ER corregido), pero afirma que la fuente 1 es 1:1, lo que ya no es cierto | `[PENDIENTE]` texto propuesto en `DISCREPANCIAS_ER_DDL.md`, a aplicar en `01_ddl/01_esquema.sql` |
| 8 | Tipos, UNIQUE, CHECK, índices | No aparecen en el diagrama | Definidos en el DDL | Documentado en `DISCREPANCIAS_ER_DDL.md` y en `modelo_er.mmd` |

Además se corrigieron `noc.pais_id` y `sede.pais_id` (también admiten NULL), la cardinalidad PAIS → POBLACION_PAIS, tres aristas que no estaban conectadas a sus tablas y cuatro que salían o llegaban a columnas equivocadas.

### 6.2 Verificado el 7 de octubre de 2026 (solo lectura)

- `olimpiadas_pg`: PostgreSQL 16.15, `TimeZone=Etc/UTC`, `data_checksums=off`, `wal_level=replica`, volumen anónimo, política de reinicio `no`, BD de 113 MB.
- IDs y conteos de las secciones 1.2 y B1.
- Imágenes locales en esa máquina: `postgres:16`, `postgres:17`, `postgres:17-alpine`, `postgres:18`.
- Máquina de Javier: Docker 29.5.2, WSL2 kernel 6.6.87.2, 16 CPU y unos 6.7 GiB de RAM asignados a Docker, disco C: con unos 88 GB libres.

### 6.3 No verificado

- `[PENDIENTE]` Permiso de replicación por socket local en el `pg_hba.conf` por defecto de `postgres:17`.
- `[PENDIENTE]` `pg_combinebackup` con un solo FULL.
- `[PENDIENTE]` `pg_verifybackup` sobre directorios incrementales.
- `[PENDIENTE]` Propietario y permisos del volumen `/backups` y del montaje `/fase2` en cada máquina.
- `[PENDIENTE]` Disponibilidad de `bc` en la imagen `postgres:17`.
- Verificado el 8 de octubre de 2026: `pgstattuple`/`pgstatindex` sobre tablas vacías no fallan (ceros y `NaN`; ver `05_logs/c1_prueba_instancia_temporal.md`).
- `[PENDIENTE]` Atletas distintos en deporte r2 y r3 por ronda (no acumulados).
- `[PENDIENTE]` Especificaciones de las máquinas de los otros dos integrantes, y si tienen la BD de la Fase 1 con los mismos IDs.
- `[PENDIENTE]` Respaldo adicional o migración del volumen anónimo de `olimpiadas_pg` (decisión de Javier, en cuya máquina está).
- `[PENDIENTE]` Quién hace el merge final `develop` → `main`.
- Documentos de referencia en `docs/`: `proyecto_2_respaldo_y_restauracion.md` (Fase 2), `Enunciado_proyecto_1.pdf` (Fase 1, solo existe en PDF) y `Modelo_ER_actualizado.xml` (draw.io).
