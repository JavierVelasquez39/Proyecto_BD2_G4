# Runbook: corrida oficial por deportista (`deportista_pc`)

Corrida de la Persona C con la carga por deportista (Usain Bolt, atleta 104492),
proyecto de Docker Compose `fase2_deportista`, base `olimpiadas`, persona `pc`.
Sigue el ciclo de la sección 1.6 de `GUIA_EQUIPO_FASE2.md` con los scripts de
`develop` en `fc349af` (respaldos y restauración con el formato de tiempos de la
sección 4.10). La evidencia se commitea en la rama `fase2/c-evidencias`.

## Decisiones cerradas

1. **Restauración con ALERTA.** Si una restauración termina con `ALERTA` o con
   código distinto de 0, se para, se diagnostica y se repite **toda** la corrida
   desde cero con el procedimiento de reinicio (sección R). Un CSV con `ALERTA`
   no se entrega.
2. **Capturas partidas.** Si una salida no cabe en una pantalla, se toman varias
   capturas con sufijo `_a`, `_b`, `_c` al final del nombre de la sección 1.8,
   después de la descripción: `deportista_pc_09_fragmentacion_a.png`,
   `deportista_pc_09_fragmentacion_b.png`.
3. **Rama de evidencia.** `fase2/c-evidencias`, creada desde `develop`. El PR y
   el merge los hace Javier.
4. **Logs rotados.** Antes de la corrida oficial se borran
   `05_logs/deportista_pc/` y `05_logs/tiempos_deportista_pc.csv` (paso P2), así
   la corrida oficial no genera logs rotados (`*.AAAAMMDD_HHMMSS.log`). Si
   aparece alguno, un paso se ejecutó dos veces y se reinicia la corrida
   (sección R). Los rotados no se commitean.
5. **`down -v`.** No se ejecuta hasta después de la calificación: los volúmenes
   y los respaldos son evidencia de persistencia. Para liberar recursos se usa
   `docker compose -p fase2_deportista stop`. Única excepción: el reinicio de
   la decisión 1 (sección R).
6. **Recursos de Docker/WSL2.** No se cambian. Se registran antes de la corrida
   (paso P3) en una captura y en un archivo de texto para la tabla de
   especificaciones del PDF.

## Convenciones

- Todos los comandos son de **PowerShell** y se ejecutan desde
  `Fase 2/00_infraestructura` (ahí está el `docker-compose.yml`). En Git Bash
  funcionan igual si antes se ejecuta `export MSYS_NO_PATHCONV=1`.
- Antes de cada comando que lleva captura se ejecuta en la misma ventana:

  ```powershell
  Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
  ```

  y la captura debe incluir esa línea, el comando, su salida y el reloj de la
  barra de tareas de Windows.
- Las salidas que van a archivo se redirigen **dentro** del contenedor con
  `bash -c`, porque `>` en PowerShell 5.1 escribe UTF-16.
- No se toca `olimpiadas_pg` (puerto 55433) ni su volumen. El compose no publica
  puertos, así que no hay choque.

## P. Preparación (antes del paso 00)

### P1. Repo y entorno (sin captura)

```powershell
cd "C:\Users\javie\OneDrive\Desktop\Segundo Semestre 2026\BASES2\Proyecto\Fase 2\00_infraestructura"
git status -sb
git log --oneline -1
git ls-files --eol -- "../03_backup" "../04_restauracion/restaurar.sh" "../02_carga/cargar_ronda.sh"
docker image ls postgres
docker volume ls --filter name=fase2_deportista
```

Qué debe salir:

- La rama `fase2/c-evidencias` sin cambios pendientes, que contenga `fc349af`.
- Todos los `.sh` con `i/lf w/lf`.
- La imagen `postgres` con etiqueta `17`.
- Ningún volumen `fase2_deportista_*`. Si aparecen, son de un ensayo anterior: aplica la sección R antes de seguir.

Además:

- **Pausa OneDrive.** El repo está dentro de OneDrive y `../` se monta en el contenedor como `/fase2`.
- Deja visible el reloj de Windows.

### P2. Carpetas limpias (decisión 4)

```powershell
Remove-Item -Recurse -Force "..\05_logs\deportista_pc" -ErrorAction SilentlyContinue
Remove-Item -Force "..\05_logs\tiempos_deportista_pc.csv" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "..\06_evidencias\deportista_pc" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "..\06_evidencias\deportista_pc" | Out-Null
Test-Path "..\05_logs\deportista_pc", "..\05_logs\tiempos_deportista_pc.csv"
```

Las dos líneas de `Test-Path` deben dar `False`. La carpeta `05_logs/deportista_pc/` la crea el primer script.

### P3. Especificaciones de la máquina (decisión 6)

Captura `deportista_pc_00_maquina.png`, y la misma salida en texto en `05_logs/deportista_pc/deportista_pc_00_maquina.txt` (UTF-8 sin BOM, LF) para la tabla de especificaciones del PDF:

```powershell
Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
$spec = @(
  Get-ComputerInfo -Property CsName, CsProcessors, CsNumberOfLogicalProcessors, CsTotalPhysicalMemory, OsName, OsVersion, OsBuildNumber | Format-List | Out-String
  Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, Size | Format-Table -AutoSize | Out-String
  Get-PSDrive C | Format-Table -AutoSize | Out-String
  docker version --format "Docker cliente {{.Client.Version}} / servidor {{.Server.Version}}"
  docker info --format "CPUs={{.NCPU}} Mem={{.MemTotal}} Kernel={{.KernelVersion}} SO={{.OperatingSystem}}"
) -join "`n"
$spec
New-Item -ItemType Directory -Force "..\05_logs\deportista_pc" | Out-Null
[System.IO.File]::WriteAllText("$PWD\..\05_logs\deportista_pc\deportista_pc_00_maquina.txt", ($spec -replace "`r`n", "`n"))
```

`docker info` muestra los CPU y la memoria que Docker Desktop ve dentro de WSL2. Son los recursos que se reportan; no se ajustan.

## 1. Comandos en orden

### Paso 00. Instancia nueva

```powershell
docker compose -p fase2_deportista up -d --wait
docker compose -p fase2_deportista ps
docker compose -p fase2_deportista exec -u root db chown -R postgres:postgres /backups
docker compose -p fase2_deportista exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/01_esquema.sql
docker compose -p fase2_deportista exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/02_extensiones.sql
```

`01_esquema.sql` muestra `NOTICE: schema "olimpiadas" does not exist, skipping`. Es normal en una base nueva.

Evidencia del paso 00, con captura:

```powershell
Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
docker volume inspect fase2_deportista_pgdata fase2_deportista_backups
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -c "\dt olimpiadas.*" -c "\dx" -c "SHOW summarize_wal" -c "SHOW data_checksums" -c "SHOW timezone" -c "SELECT version();"
docker compose -p fase2_deportista exec -u postgres db bash -c "touch /backups/x && rm /backups/x && touch /fase2/05_logs/x && rm /fase2/05_logs/x && echo PERMISOS_OK"
```

### Paso 01. Carga base

```powershell
docker compose -p fase2_deportista exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deportista pc base
docker compose -p fase2_deportista exec -u postgres db psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -v limite=10 -f /fase2/04_restauracion/validar.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas -v limite=ALL -f /fase2/04_restauracion/validar.sql > /fase2/05_logs/deportista_pc/deportista_pc_01_validar_completo.log 2>&1"
```

### Paso 02. Respaldo FULL

```powershell
docker compose -p fase2_deportista exec -u postgres db bash /fase2/03_backup/backup_full.sh deportista pc
```

### Pasos 03 y 04. Ronda 1 (Atenas 2004) e INCR 1

```powershell
docker compose -p fase2_deportista exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deportista pc r1_atenas2004
docker compose -p fase2_deportista exec -u postgres db psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -v limite=10 -f /fase2/04_restauracion/validar.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas -v limite=ALL -f /fase2/04_restauracion/validar.sql > /fase2/05_logs/deportista_pc/deportista_pc_03_validar_completo.log 2>&1"
docker compose -p fase2_deportista exec -u postgres db bash /fase2/03_backup/backup_incremental.sh deportista pc 1
```

### Pasos 05 y 06. Ronda 2 (Pekín 2008) e INCR 2

```powershell
docker compose -p fase2_deportista exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deportista pc r2_pekin2008
docker compose -p fase2_deportista exec -u postgres db psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -v limite=10 -f /fase2/04_restauracion/validar.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas -v limite=ALL -f /fase2/04_restauracion/validar.sql > /fase2/05_logs/deportista_pc/deportista_pc_05_validar_completo.log 2>&1"
docker compose -p fase2_deportista exec -u postgres db bash /fase2/03_backup/backup_incremental.sh deportista pc 2
```

### Pasos 07 y 08. Ronda 3 (Londres 2012) e INCR 3

```powershell
docker compose -p fase2_deportista exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deportista pc r3_londres2012
docker compose -p fase2_deportista exec -u postgres db psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -v limite=10 -f /fase2/04_restauracion/validar.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas -v limite=ALL -f /fase2/04_restauracion/validar.sql > /fase2/05_logs/deportista_pc/deportista_pc_07_validar_completo.log 2>&1"
docker compose -p fase2_deportista exec -u postgres db bash /fase2/03_backup/backup_incremental.sh deportista pc 3
```

Conteos esperados (secciones 1.2 de la guía y 02_carga/README.md). La carga base no cambia: pais 204, poblacion_pais 13026, noc 236, deporte 95, deporte_equivalencia 2.

| Después de | sede | edicion_olimpica | evento | atleta | participacion | resultado |
|---|---:|---:|---:|---:|---:|---:|
| base (paso 01) | 0 | 0 | 0 | 0 | 0 | 0 |
| r1 (paso 03) | 1 | 1 | 1 | 1 | 1 | 1 |
| r2 (paso 05) | 2 | 2 | 3 | 1 | 4 | 4 |
| r3 (paso 07) | 3 | 3 | 3 | 1 | 7 | 7 |

En `validar.sql` el relevo 4x100 de 2008 sale sin lugar ni medalla (medalla retirada en 2017). No es un error.

Si cualquier comando de los pasos 00 a 08 falla (`CARGA FALLIDA`, `ALERTA` o código distinto de 0), se para y se aplica la sección R.

### Paso 09. Fragmentación previa

```powershell
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -f /fase2/04_restauracion/fragmentacion_indices.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_tablas.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_tablas.csv"
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_indices.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_indices.csv"
```

### Paso 10. Eliminar la base

```powershell
docker compose -p fase2_deportista exec -u postgres db psql -X -d postgres -c "DROP DATABASE olimpiadas;" -c "\l"
```

### Paso 11. Detener el servicio y vaciar PGDATA

```powershell
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista ps -a
```

`ps -a` debe mostrar el contenedor `db` en estado `Exited`. PGDATA lo vacía `restaurar.sh` al inicio de cada restauración (`04_restauracion/restaurar.sh:43-46`):

1. Imprime `Limpiando directorio /var/lib/postgresql/data/pgdata...`.
2. Ejecuta `find "$PGDATA" -mindepth 1 -delete`, que borra también los archivos ocultos y conserva el directorio. PGDATA no es el punto de montaje: el volumen se monta en `/var/lib/postgresql/data`.
3. Ejecuta `ls -la "$PGDATA"`, que muestra `total 8` y solo `.` y `..`.

La pantalla de la primera restauración se desplaza enseguida con la salida de `validar.sql`. Por eso la captura del paso 11 se toma **después** de la restauración n=0, repetición 1, leyendo su log, que conserva el listado:

```powershell
Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
docker compose -p fase2_deportista ps -a
Get-Content "..\05_logs\deportista_pc\deportista_pc_12_restore_cadena0_rep1.log" -TotalCount 6
```

Debe verse la línea `=== Inicio de Restauración Cadena N=0 repetición 1: <fecha> ===`, `Limpiando directorio ...` y el `ls -la` con solo `.` y `..`. No hace falta vaciar PGDATA a mano.

### Pasos 12 a 15. Restauraciones, 3 repeticiones cada una

Comportamiento de `restaurar.sh` con respecto al servidor:

- **`db` detenido**: `docker compose stop` apaga PostgreSQL de forma ordenada y se borra `postmaster.pid`. El script pasa la comprobación de `restaurar.sh:37-41` y sigue.
- **`db` corriendo**: el contenedor `run` comparte el volumen `pgdata`, ve el `postmaster.pid` del servidor vivo y aborta en `restaurar.sh:38-40` con `ERROR: PostgreSQL sigue activo en ... (postmaster.pid existe).` y código 1. Lo hace **antes** de borrar PGDATA, así que no daña nada. Esa salida es un `exit 1` explícito: no pasa por el `trap ERR` y no escribe fila en el CSV. Sí deja creados su log y su log de servidor (`restaurar.sh:24-25`), y al repetirla aparecerían logs rotados. Por la decisión 4, se reinicia la corrida (sección R).
- **`postmaster.pid` huérfano** (por ejemplo, un contenedor terminado a la fuerza): el script no distingue un archivo huérfano de un servidor vivo. Aborta igual en `restaurar.sh:38-40` y no lo borra. Se trata como fallo: se diagnostica y se aplica la sección R.
- **Al terminar cada restauración**, el propio script detiene el servidor que arrancó con `pg_ctl -m fast stop`, después de escribir las filas. Si algo falla con el servidor arriba, `al_fallar_extra` (`restaurar.sh:28-32`) lo detiene.

Aun así, antes de cada restauración se ejecuta `docker compose -p fase2_deportista stop db`. Si `db` ya está detenido no hace nada, y evita el caso "db corriendo" si alguien lo levantó entre una ejecución y otra.

Cada ejecución:

1. Vacía PGDATA.
2. Combina (o copia el FULL si n=0).
3. Corre `pg_verifybackup`.
4. Arranca el servidor.
5. Ejecuta `validar.sql` (10 filas) y compara `conteos.sql` con `diff` contra `/backups/conteos_full.txt` o `conteos_incr<n>.txt`.
6. Escribe 4 filas en el CSV y apaga el servidor.

En este orden:

```powershell
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 0 1
# Aquí: captura del paso 12 (salida anterior) y del paso 11 (Get-Content del log, ver paso 11)
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 0 2
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 0 3
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 1 1
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 1 2
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 1 3
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 2 1
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 2 2
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 2 3
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 3 1
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 3 2
docker compose -p fase2_deportista stop db
docker compose -p fase2_deportista run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deportista pc 3 3
```

Después de cada `run`, en PowerShell, `$LASTEXITCODE` debe valer 0. La salida debe terminar con `VALIDACION OK: Los conteos coinciden perfectamente.` y `finalizada con estado: OK`. El `diff` de conteos queda en el log de la repetición: si no hay diferencias, no agrega líneas.

Si alguna sale con `ALERTA`, con `ERROR` o con código distinto de 0, se para y se aplica la sección R (decisión 1).

### Paso 16. Fragmentación posterior y comprobación final

```powershell
docker compose -p fase2_deportista start db
docker compose -p fase2_deportista exec -u postgres db psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql | diff /backups/conteos_incr3.txt - && echo CONTEOS_IGUALES_AL_PASO_07"
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -f /fase2/04_restauracion/fragmentacion_indices.sql
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_tablas.sql > /fase2/05_logs/deportista_pc/deportista_pc_16_fragmentacion_tablas.csv"
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_indices.sql > /fase2/05_logs/deportista_pc/deportista_pc_16_fragmentacion_indices.csv"
docker compose -p fase2_deportista exec -u postgres db bash -c "cd /fase2/05_logs/deportista_pc && diff deportista_pc_09_fragmentacion_tablas.csv deportista_pc_16_fragmentacion_tablas.csv && diff deportista_pc_09_fragmentacion_indices.csv deportista_pc_16_fragmentacion_indices.csv && echo FRAGMENTACION_IDENTICA"
```

Al terminar, después de la verificación final (sección 3), se liberan recursos sin borrar volúmenes (decisión 5):

```powershell
docker compose -p fase2_deportista stop
```

## R. Reinicio de la corrida (decisiones 1 y 4)

Se aplica si sale una `ALERTA`, un `ERROR`, un código distinto de 0 o un log rotado en cualquier paso. Antes, anota la causa: revisa el log del paso y, si es una restauración, su `..._servidor.log`. Luego, desde `Fase 2/00_infraestructura`:

```powershell
docker compose -p fase2_deportista down -v
Remove-Item -Recurse -Force "..\05_logs\deportista_pc" -ErrorAction SilentlyContinue
Remove-Item -Force "..\05_logs\tiempos_deportista_pc.csv" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "..\06_evidencias\deportista_pc" -ErrorAction SilentlyContinue
docker volume ls --filter name=fase2_deportista
Test-Path "..\05_logs\deportista_pc", "..\05_logs\tiempos_deportista_pc.csv", "..\06_evidencias\deportista_pc"
```

- `down -v` borra solo los volúmenes del proyecto `fase2_deportista`, no los de `olimpiadas_pg` ni los de otros proyectos.
- `docker volume ls` no debe listar nada, y las tres líneas de `Test-Path` deben dar `False`.
- Luego se vuelve a P2 (recrea la carpeta de capturas), P3 y el paso 00.

## 2. Capturas

Carpeta: `Fase 2/06_evidencias/deportista_pc/`, PNG, nombres según la sección 1.8 (`{tipo}_{persona}_{paso}_{descripcion}`). Si una salida no cabe, se agrega `_a`, `_b`, `_c` después de la descripción (decisión 2). En cada captura deben verse la línea de `Get-Date`, el comando, su salida y el reloj de Windows.

| Paso | Archivo | Comando | Qué debe verse |
|---|---|---|---|
| 00 | `deportista_pc_00_maquina.png` | P3 | Procesador, núcleos lógicos, RAM, Windows, discos con `MediaType`, Docker y `docker info` |
| 00 | `deportista_pc_00_instancia.png` | Bloque de evidencia del paso 00 | Volúmenes `fase2_deportista_pgdata` y `_backups`, 11 tablas en `\dt`, `pgstattuple` en `\dx`, `summarize_wal` on, `data_checksums` on, zona `America/Guatemala`, PostgreSQL 17, `PERMISOS_OK` |
| 01 | `deportista_pc_01_base_count.png` | `cargar_ronda.sh ... base` y `conteos.sql` | `CARGA OK`; 204, 13026, 236, 95, 2 y el resto en 0 |
| 01 | `deportista_pc_01_base_select.png` | `validar.sql` con `limite=10` | `SELECT` ordenados por PK y `FIN DE LA VALIDACION` |
| 02 | `deportista_pc_02_full_comando.png` | `backup_full.sh deportista pc` | Inicio con hora, `base backup completed`, `backup successfully verified`, Fin con `segundos=` y `bytes=` |
| 03 | `deportista_pc_03_r1_count.png` | Carga r1 y `conteos.sql` | sede 1, edicion 1, evento 1, atleta 1, participacion 1, resultado 1 |
| 03 | `deportista_pc_03_r1_select.png` | `validar.sql` con `limite=10` | Bolt con 1 participación (Atenas 2004) |
| 04 | `deportista_pc_04_incr1_comando.png` | `backup_incremental.sh deportista pc 1` | `base backup completed`, `backup successfully verified`, segundos y bytes |
| 05 | `deportista_pc_05_r2_count.png` | Carga r2 y `conteos.sql` | 2, 2, 3, 1, 4, 4 |
| 05 | `deportista_pc_05_r2_select.png` | `validar.sql` con `limite=10` | Relevo 2008 sin lugar ni medalla |
| 06 | `deportista_pc_06_incr2_comando.png` | `backup_incremental.sh deportista pc 2` | Igual que el paso 04 |
| 07 | `deportista_pc_07_r3_count.png` | Carga r3 y `conteos.sql` | 3, 3, 3, 1, 7, 7 |
| 07 | `deportista_pc_07_r3_select.png` | `validar.sql` con `limite=10` | Bolt con 7 participaciones |
| 08 | `deportista_pc_08_incr3_comando.png` | `backup_incremental.sh deportista pc 3` | Igual que el paso 04 |
| 09 | `deportista_pc_09_fragmentacion.png` | `fragmentacion_tablas.sql` y `_indices.sql` (sin `--csv`) | Una fila por tabla y por índice |
| 10 | `deportista_pc_10_drop_database.png` | `DROP DATABASE` y `\l` | `DROP DATABASE` y la lista sin `olimpiadas` |
| 11 | `deportista_pc_11_pgdata_vacio.png` | `ps -a` y `Get-Content` del log de `restaurar.sh ... 0 1` (paso 11) | `db` en `Exited`; inicio con fecha, `Limpiando directorio` y `ls -la` solo con `.` y `..` |
| 12 | `deportista_pc_12_restore_full.png` | `restaurar.sh deportista pc 0 1` | `backup successfully verified`, arranque, COUNT, SELECT, `VALIDACION OK`, `Total: ... s` |
| 13 | `deportista_pc_13_restore_cadena1.png` | `restaurar.sh deportista pc 1 1` | Igual que el paso 12, con `pg_combinebackup` |
| 14 | `deportista_pc_14_restore_cadena2.png` | `restaurar.sh deportista pc 2 1` | Igual que el paso 13 |
| 15 | `deportista_pc_15_restore_cadena3.png` | `restaurar.sh deportista pc 3 1` | Igual que el paso 13; COUNT igual al paso 07 |
| 16 | `deportista_pc_16_fragmentacion_post.png` | `start db`, `conteos.sql`, `diff` y fragmentación | `CONTEOS_IGUALES_AL_PASO_07`, tablas de fragmentación, `FRAGMENTACION_IDENTICA` |

Son 22 capturas base, más las partes `_a`/`_b`/`_c` que hagan falta. Las salidas de los pasos 12 a 16 suelen ocupar más de una pantalla: por ejemplo `deportista_pc_12_restore_full_a.png` (verificación y arranque) y `deportista_pc_12_restore_full_b.png` (`VALIDACION OK` y `Total`). Solo la repetición 1 de cada restauración lleva captura (sección 1.6). Las repeticiones 2 y 3 quedan en su log.

## 3. Verificación final

Desde Git Bash, en la carpeta `Fase 2`:

```bash
F=05_logs/tiempos_deportista_pc.csv
head -1 "$F"                                  # encabezado de 14 columnas (4.10)
wc -l < "$F"                                  # 53 = encabezado + 52 filas
awk -F, '{print NF}' "$F" | sort | uniq -c    # 53 líneas con 14 campos
awk -F, 'NR>1{print $5, $7}' "$F" | sort | uniq -c
#   1 backup_full basebackup | 3 backup_incr basebackup
#  12 restore combinar | 12 restore arranque | 12 restore validacion | 12 restore total
grep -c ALERTA "$F"                           # 0
awk -F, 'NR>1 && $5=="restore"{print $6, $13}' "$F" | sort | uniq -c   # 4 filas por cada n y repetición
grep -L "VALIDACION OK" 05_logs/deportista_pc/*_restore_cadena?_rep?.log   # sin salida
grep -l "^[-+][a-z]" 05_logs/deportista_pc/*_restore_cadena?_rep?.log     # sin salida: ningún diff de conteos
ls 05_logs/deportista_pc | grep -E '\.[0-9]{8}_[0-9]{6}\.log$'           # sin salida: ningún log rotado
diff 05_logs/deportista_pc/deportista_pc_09_fragmentacion_tablas.csv 05_logs/deportista_pc/deportista_pc_16_fragmentacion_tablas.csv
diff 05_logs/deportista_pc/deportista_pc_09_fragmentacion_indices.csv 05_logs/deportista_pc/deportista_pc_16_fragmentacion_indices.csv
ls 05_logs/deportista_pc
ls 06_evidencias/deportista_pc
```

El 52 sale de la sección 4.10: 4 filas de respaldo (FULL e INCR 1 a 3, `etapa=basebackup`, `repeticion=1`) más 16 de restauración por repetición (4 cadenas por 4 etapas), por 3 repeticiones, o sea 4 + 48. Si cualquier comprobación falla, se aplica la sección R.

Archivos esperados en `05_logs/deportista_pc/`:

- Especificaciones: `deportista_pc_00_maquina.txt`.
- Carga (los escribe `cargar_ronda.sh`): `deportista_pc_01_carga_base.log`, `deportista_pc_03_carga_r1_atenas2004.log`, `deportista_pc_05_carga_r2_pekin2008.log`, `deportista_pc_07_carga_r3_londres2012.log`.
- Validación completa: `deportista_pc_01_validar_completo.log`, `_03_`, `_05_` y `_07_`.
- Respaldos: `deportista_pc_02_backup_full.log`, `deportista_pc_04_backup_incr1.log`, `deportista_pc_06_backup_incr2.log`, `deportista_pc_08_backup_incr3.log`.
- Restauraciones: `deportista_pc_<12..15>_restore_cadena<0..3>_rep<1..3>.log` (12 archivos), cada uno con su `..._servidor.log` (12 más).
- Fragmentación: `deportista_pc_09_fragmentacion_tablas.csv`, `_09_fragmentacion_indices.csv`, `_16_fragmentacion_tablas.csv` y `_16_fragmentacion_indices.csv`.

No hay log propio para los pasos 10, 11 y 16: su evidencia son las capturas y, en el 16, los CSV de fragmentación.

## 4. Dónde queda cada cosa y qué se commitea

| Qué | Ruta (host) | Dentro del contenedor |
|---|---|---|
| Logs por paso y especificaciones | `Fase 2/05_logs/deportista_pc/` | `/fase2/05_logs/deportista_pc/` |
| CSV de tiempos | `Fase 2/05_logs/tiempos_deportista_pc.csv` | `/fase2/05_logs/tiempos_deportista_pc.csv` |
| Capturas | `Fase 2/06_evidencias/deportista_pc/` | (no aplica) |
| Respaldos y conteos de cada respaldo | volumen `fase2_deportista_backups` | `/backups/full`, `/backups/incr1..3`, `/backups/conteos_*.txt` |
| PGDATA | volumen `fase2_deportista_pgdata` | `/var/lib/postgresql/data/pgdata` |

Se commitean en `fase2/c-evidencias`:

- Los logs de `05_logs/deportista_pc/`, con las notas `# NOTA:` agregadas a mano al final de cada log.
- `05_logs/tiempos_deportista_pc.csv`.
- `06_evidencias/deportista_pc/`.
- Este runbook.

No se commitean los volúmenes (respaldos y PGDATA) ni ningún log rotado.

**Advertencia:** estos comandos se ejecutan **solo** después de terminar la corrida y de que la sección 3 salga completa. Desde la raíz del repo:

```powershell
cd "C:\Users\javie\OneDrive\Desktop\Segundo Semestre 2026\BASES2\Proyecto"
git branch --show-current
Get-ChildItem "Fase 2\05_logs\deportista_pc" -Name | Select-String '\.\d{8}_\d{6}\.log$'
git add "Fase 2/05_logs/deportista_pc" "Fase 2/05_logs/tiempos_deportista_pc.csv" "Fase 2/06_evidencias/deportista_pc" "Fase 2/docs/RUNBOOK_deportista_pc.md"
git status --short
```

- `git branch --show-current` debe mostrar `fase2/c-evidencias`.
- `Select-String` no debe imprimir nada. Si imprime algo, hay un log rotado: no se commitea y se aplica la sección R.
- Después, `git commit` con mensaje en español; el push, el PR a `develop` y el merge los hace Javier (decisión 3).
