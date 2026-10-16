# Manual de Operación y Estructura - Persona A (Kimberly)

**Proyecto:** Fase 2 - Respaldo y Restauración de Bases de Datos
**Rol:** Persona A (`pa`)
**Carga asignada:** Corrida oficial Por Año (`anio_pa`) y Corrida de referencia común (`deportista_pa`)

---

## 1. Estructura del Repositorio (`Fase 2/`)

```text
Fase 2/
├── 00_infraestructura/
│   ├── docker-compose.yml       # Definición del contenedor PostgreSQL 17
│   └── README.md                # Indicaciones de despliegue
├── 01_ddl/
│   ├── 01_esquema.sql           # Tablas del modelo relacional
│   └── 02_extensiones.sql       # Extensiones pgstattuple y amcheck
├── 02_carga/
│   ├── cargar_ronda.sh          # Loader de datos masivos
│   └── datos/                   # Archivos CSV por tipo de carga y ronda
├── 03_backup/
│   ├── backup_full.sh           # Respaldo físico FULL (pg_basebackup)
│   └── backup_incremental.sh    # Respaldo físico Incremental encadenado
├── 04_restauracion/
│   ├── restaurar.sh             # Reconstrucción física (pg_combinebackup)
│   ├── conteos.sql              # Conteo general de las 11 tablas
│   ├── validar.sql              # Validación de integridad post-restauración
│   └── fragmentacion_tablas.sql # Medición de espacio y páginas
├── 05_logs/
│   ├── anio_pa/                 # Logs de la corrida oficial por año
│   ├── deportista_pa/           # Logs de la corrida de referencia por deportista
│   └── tiempos_anio_pa.csv      # Consolidado de tiempos de ejecución
└── 06_evidencias/
    ├── anio_pa/                 # Capturas PNG del ciclo oficial
    └── deportista_pa/           # Capturas PNG del ciclo de referencia
```

---

## 2. Guía Paso a Paso de Ejecución

### Paso 1. Preparación del Entorno (PowerShell)

Navega al directorio de infraestructura y normaliza los finales de línea de todos los scripts Bash a formato Linux (LF):

```powershell
cd "C:\Users\usuario\Documents\fiusac2026\2semestre\bases2\laboratorio\PROYECTO\Proyecto_BD2_G4\Fase 2\00_infraestructura"

Get-ChildItem -Path ".." -Recurse -Filter *.sh | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $content = $content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($_.FullName, $content)
}
```

### Paso 2. Secuencia de la Corrida Oficial por Año (`-p fase2_anio`)



#### [Paso 00] Despliegue e Inicialización

```powershell
# Reiniciar instancia limpia
docker compose -p fase2_anio down -v
docker compose -p fase2_anio up -d

# Asignar permisos al volumen de respaldos
docker compose -p fase2_anio exec -u root db chown -R postgres:postgres /backups

# Cargar esquema y extensiones
docker compose -p fase2_anio exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/01_esquema.sql
docker compose -p fase2_anio exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/02_extensiones.sql

# Validar configuraciones del servidor
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -c "SHOW summarize_wal; SHOW data_checksums; SHOW timezone;"
```

#### [Pasos 01 y 02] Carga Base y Respaldo FULL

```powershell
# Cargar datos base (catálogos)
docker compose -p fase2_anio exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh anio pa base
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Generar Respaldo FULL
docker compose -p fase2_anio exec -u postgres db bash /fase2/03_backup/backup_full.sh anio pa
```

#### [Pasos 03 y 04] Ronda 1 (París 2024) y Respaldo INCR 1

```powershell
# Cargar Ronda 1
docker compose -p fase2_anio exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh anio pa r1_paris2024
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Respaldo Incremental 1
docker compose -p fase2_anio exec -u postgres db bash /fase2/03_backup/backup_incremental.sh anio pa 1
```

#### [Pasos 05 y 06] Ronda 2 (Tokio 2020) y Respaldo INCR 2

```powershell
# Cargar Ronda 2
docker compose -p fase2_anio exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh anio pa r2_tokio2020
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Respaldo Incremental 2
docker compose -p fase2_anio exec -u postgres db bash /fase2/03_backup/backup_incremental.sh anio pa 2
```

#### [Pasos 07 y 08] Ronda 3 (Río 2016) y Respaldo INCR 3

```powershell
# Cargar Ronda 3
docker compose -p fase2_anio exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh anio pa r3_rio2016
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Respaldo Incremental 3
docker compose -p fase2_anio exec -u postgres db bash /fase2/03_backup/backup_incremental.sh anio pa 3
```

#### [Pasos 09 y 10] Fragmentación Previa y Eliminación de BD

```powershell
# Medición de fragmentación previa
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql

# Eliminar la base de datos
docker compose -p fase2_anio exec -u postgres db psql -d postgres -c "DROP DATABASE olimpiadas;" -c "\l"
```

#### [Pasos 11 a 15] Ciclo de Restauraciones Medidas

```powershell
# Detener el servicio para restaurar sobre PGDATA limpio
docker compose -p fase2_anio stop db

# Restauración N=0 (FULL)
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 0

# Restauración N=1 (FULL + INCR 1)
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 1

# Restauración N=2 (FULL + INCR 1 + INCR 2)
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 2

# Restauración N=3 (FULL + INCR 1 + INCR 2 + INCR 3)
docker compose -p fase2_anio run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh anio pa 3
```

#### [Paso 16] Fragmentación Posterior

```powershell
# Iniciar motor y verificar estado posterior
docker compose -p fase2_anio start db
docker compose -p fase2_anio exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql
```

### Paso 3. Corrida de Referencia Común (`deportista_pa`)

Ejecuta exactamente la misma secuencia descrita en el Paso 2, adaptando los comandos a la instancia de referencia:

- **Proyecto Compose:** `-p fase2_deportista`
- **Rondas de Carga:** `deportista pa base`, `r1_atenas2004`, `r2_pekin2008`, `r3_londres2012`
- **Parámetros de Backup y Restauración:** `deportista pa`
- **Ubicación de evidencias y logs:** `06_evidencias/deportista_pa/` y `05_logs/deportista_pa/`
