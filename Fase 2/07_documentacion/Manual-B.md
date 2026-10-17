# Manual de Operación y Estructura - Kath

**Proyecto:** Fase 2 - Respaldo y Restauración de Bases de Datos  
**Rol:** Persona B (`pb`)  
**Carga asignada:** Corrida oficial Por Deporte (`deporte_pb`) — evento 1025 (Atletismo)

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
│   ├── deporte_pb/              # Logs de la corrida oficial por deporte
│   ├── anio_pa/                 # Logs de la corrida de Persona A
│   ├── deportista_pa/           # Logs de la corrida de referencia
│   └── tiempos_deporte_pb.csv   # Consolidado de tiempos de ejecución (deporte)
└── 06_evidencias/
    ├── deporte_pb/              # Capturas PNG del ciclo oficial (deporte)
    ├── anio_pa/                 # Capturas PNG del ciclo de Persona A
    └── deportista_pa/           # Capturas PNG del ciclo de referencia
```

---

## 2. Guía Paso a Paso de Ejecución

### Paso 1. Preparación del Entorno (PowerShell o Bash)

Navega al directorio de infraestructura y normaliza los finales de línea de todos los scripts Bash a formato Linux (LF):

**PowerShell (Windows):**
```powershell
cd "C:\Users\usuario\Documents\fiusac2026\2semestre\bases2\laboratorio\PROYECTO\Proyecto_BD2_G4\Fase 2\00_infraestructura"

Get-ChildItem -Path ".." -Recurse -Filter *.sh | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $content = $content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($_.FullName, $content)
}
```

**Bash (Linux/Mac):**
```bash
cd ~/proyectos/Proyecto_BD2_G4/Fase\ 2/00_infraestructura
find .. -name "*.sh" -exec dos2unix {} \;
```

---

### Paso 2. Secuencia de la Corrida Oficial Por Deporte (`-p fase2_deporte`)

#### [Paso 00] Despliegue e Inicialización

```powershell
# Reiniciar instancia limpia
docker compose -p fase2_deporte down -v
docker compose -p fase2_deporte up -d

# Asignar permisos al volumen de respaldos
docker compose -p fase2_deporte exec -u root db chown -R postgres:postgres /backups

# Cargar esquema y extensiones
docker compose -p fase2_deporte exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/01_esquema.sql
docker compose -p fase2_deporte exec -u postgres db psql -v ON_ERROR_STOP=1 -d olimpiadas -f /fase2/01_ddl/02_extensiones.sql

# Validar configuraciones del servidor
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -c "SHOW summarize_wal; SHOW data_checksums; SHOW timezone;"
```

**Salida esperada (paso 00):**
```
summarize_wal: on
data_checksums: on
timezone: UTC
```

---

#### [Pasos 01 y 02] Carga Base y Respaldo FULL

```powershell
# Cargar datos base (catálogos: pais, poblacion_pais, noc, deporte, deporte_equivalencia)
docker compose -p fase2_deporte exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deporte pb base

# Verificar conteos post-carga
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Generar Respaldo FULL (physicò con pg_basebackup)
docker compose -p fase2_deporte exec -u postgres db bash /fase2/03_backup/backup_full.sh deporte pb
```

**Salida esperada (Respaldo FULL):**
```
FULL backup completado en: 2.030 segundos
Tamaño del respaldo: ~50 MB
Archivo base: /backups/deporte_pb_full_base.tar.zst
```

---

#### [Pasos 03 y 04] Ronda 1 (París 2024) y Respaldo INCR 1

```powershell
# Cargar Ronda 1: Evento 1025 (Atletismo) en París 2024
# (evento_id = 1025, edicion_id = 61)
docker compose -p fase2_deporte exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deporte pb r1_paris2024

# Verificar conteos post-carga (debe mostrar nuevos atletas/participaciones de Ronda 1)
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Respaldo Incremental 1 (encadenado al FULL)
docker compose -p fase2_deporte exec -u postgres db bash /fase2/03_backup/backup_incremental.sh deporte pb 1
```

**Salida esperada (Respaldo INCR 1):**
```
INCR 1 backup completado en: 1.961 segundos
Tamaño del respaldo: ~22 MB
Archivo incremental: /backups/deporte_pb_incr_1.tar.zst
```

---

#### [Pasos 05 y 06] Ronda 2 (Tokio 2020) y Respaldo INCR 2

```powershell
# Cargar Ronda 2: Evento 1025 en Tokio 2020
# (evento_id = 1025, edicion_id = 59)
docker compose -p fase2_deporte exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deporte pb r2_tokio2020

# Verificar conteos post-carga
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Respaldo Incremental 2
docker compose -p fase2_deporte exec -u postgres db bash /fase2/03_backup/backup_incremental.sh deporte pb 2
```

**Salida esperada (Respaldo INCR 2):**
```
INCR 2 backup completado en: 1.971 segundos
Tamaño del respaldo: ~22 MB
Archivo incremental: /backups/deporte_pb_incr_2.tar.zst
```

---

#### [Pasos 07 y 08] Ronda 3 (Río 2016) y Respaldo INCR 3

```powershell
# Cargar Ronda 3: Evento 1025 en Río 2016
# (evento_id = 1025, edicion_id = 55)
docker compose -p fase2_deporte exec -u postgres db bash /fase2/02_carga/cargar_ronda.sh deporte pb r3_rio2016

# Verificar conteos post-carga
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/conteos.sql

# Respaldo Incremental 3
docker compose -p fase2_deporte exec -u postgres db bash /fase2/03_backup/backup_incremental.sh deporte pb 3
```

**Salida esperada (Respaldo INCR 3):**
```
INCR 3 backup completado en: 1.918 segundos
Tamaño del respaldo: ~22 MB
Archivo incremental: /backups/deporte_pb_incr_3.tar.zst
```

---

#### [Pasos 09 y 10] Fragmentación Previa y Eliminación de BD

```powershell
# Medición de fragmentación PREVIA (antes de restauraciones)
# Genera CSV con dead_tuples, live_tuples, pages, free_space por tabla
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql

# Eliminar la base de datos
docker compose -p fase2_deporte exec -u postgres db psql -d postgres -c "DROP DATABASE olimpiadas;" -c "\l"
```

---

#### [Pasos 11 a 15] Ciclo de Restauraciones Medidas

Detener el servicio, luego ejecutar cuatro restauraciones en secuencia:

```powershell
# Detener el contenedor (PGDATA debe estar limpio para cada restauración)
docker compose -p fase2_deporte stop db
```

**Restauración N=0: FULL ONLY**
```powershell
docker compose -p fase2_deporte run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deporte pb 0
```

**Salida esperada:**
```
Restauracion FULL completada en: 0.741 segundos
Base de datos olimpiadas lista.
VALIDACION OK (11 tablas, conteos coinciden)
```

**Restauración N=1: FULL + INCR 1**
```powershell
docker compose -p fase2_deporte run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deporte pb 1
```

**Salida esperada:**
```
Restauracion FULL + INCR 1 completada en: 2.102 segundos
Base de datos olimpiadas lista.
VALIDACION OK (11 tablas, conteos coinciden)
```

**Restauración N=2: FULL + INCR 1 + INCR 2**
```powershell
docker compose -p fase2_deporte run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deporte pb 2
```

**Salida esperada:**
```
Restauracion FULL + INCR 1 + INCR 2 completada en: 2.215 segundos
Base de datos olimpiadas lista.
VALIDACION OK (11 tablas, conteos coinciden)
```

**Restauración N=3: FULL + INCR 1 + INCR 2 + INCR 3**
```powershell
docker compose -p fase2_deporte run --rm --no-deps -u postgres --entrypoint bash db /fase2/04_restauracion/restaurar.sh deporte pb 3
```

**Salida esperada:**
```
Restauracion FULL + INCR 1 + INCR 2 + INCR 3 completada en: 2.107 segundos
Base de datos olimpiadas lista.
VALIDACION OK (11 tablas, conteos coinciden)
```

---

#### [Paso 16] Fragmentación Posterior

```powershell
# Reiniciar el motor después de las restauraciones
docker compose -p fase2_deporte start db

# Esperar a que esté listo (~5 segundos)
Start-Sleep -Seconds 5

# Medición de fragmentación POSTERIOR (después de restauraciones)
# Comparar con pre-fragmentación para análisis de compresión
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -f /fase2/04_restauracion/fragmentacion_tablas.sql
```

---

## 3. Interpretación de Resultados

### Tiempos de Ejecución Reales (deporte_pb)

| Paso | Operación | Tiempo (s) | Tamaño |
|------|-----------|-----------|--------|
| 02 | FULL backup | 2.030 | 50 MB |
| 04 | INCR 1 | 1.961 | 22 MB |
| 06 | INCR 2 | 1.971 | 22 MB |
| 08 | INCR 3 | 1.918 | 22 MB |
| 12 | Restaurar FULL | 0.741 | — |
| 13 | Restaurar FULL+I1 | 2.102 | — |
| 14 | Restaurar FULL+I1+I2 | 2.215 | — |
| 15 | Restaurar FULL+I1+I2+I3 | 2.107 | — |

### Validaciones Esperadas

Todas las restauraciones deben imprimir **`VALIDACION OK`** al final, lo que significa:
- ✓ Conteos de las 11 tablas coinciden con el estado pre-restauración
- ✓ No hay corrupción de datos verificada por pg_checksums
- ✓ Las secuencias están sincronizadas correctamente

---

## 4. Estructura de Logs

Los logs de cada paso se guardan automáticamente en:

```
Fase 2/05_logs/deporte_pb/
├── deporte_pb_01_carga_base.log          # Paso 1: Carga base
├── deporte_pb_02_backup_full.log         # Paso 2: FULL backup
├── deporte_pb_03_carga_r1_paris2024.log  # Paso 3: Ronda 1
├── deporte_pb_04_backup_incr_1.log       # Paso 4: INCR 1
├── deporte_pb_05_carga_r2_tokio2020.log  # Paso 5: Ronda 2
├── deporte_pb_06_backup_incr_2.log       # Paso 6: INCR 2
├── deporte_pb_07_carga_r3_rio2016.log    # Paso 7: Ronda 3
├── deporte_pb_08_backup_incr_3.log       # Paso 8: INCR 3
├── deporte_pb_09_fragmentacion_pre.log   # Paso 9: Fragmentación pre
├── deporte_pb_10_drop_database.log       # Paso 10: DROP DATABASE
├── deporte_pb_12_restaurar_full.log      # Paso 12: Restaurar FULL
├── deporte_pb_13_restaurar_incr1.log     # Paso 13: Restaurar +INCR1
├── deporte_pb_14_restaurar_incr2.log     # Paso 14: Restaurar +INCR2
├── deporte_pb_15_restaurar_incr3.log     # Paso 15: Restaurar +INCR3
└── deporte_pb_16_fragmentacion_post.log  # Paso 16: Fragmentación post
```

---

## 5. Solución de Problemas Frecuentes

### Problema: "Permission denied" al crear volumen de backups

**Causa:** El volumen `/backups` fue creado como `root`, PostgreSQL no puede escribir.

**Solución:**
```powershell
docker compose -p fase2_deporte exec -u root db chown -R postgres:postgres /backups
```

---

### Problema: "SELinux permission denied" en Fedora

**Causa:** SELinux bloquea el montaje `/fase2` en el contenedor.

**Solución:** Editar `docker-compose.yml` y cambiar:
```yaml
# De:
- ../:/fase2

# A:
- ../:/fase2:Z
```

---

### Problema: "CARGA FALLIDA: duplicate key value violates unique constraint"

**Causa:** Los datos ya existen en la tabla (ON CONFLICT no se aplicó correctamente).

**Solución:** Verificar que `cargar_ronda.sh` use `ON CONFLICT DO NOTHING` y que se ejecute en UNA sola transacción (`-1` flag en psql).

---

### Problema: Restauración lenta o incompleta

**Causa:** PGDATA no está limpio entre restauraciones.

**Solución:** Asegurarse de ejecutar `docker compose stop` antes de cada restauración y que el script `restaurar.sh` limpie `/var/lib/postgresql/data` al inicio.

---

## 6. Verificación Final de la Corrida

Al completar todos los 16 pasos, debe existir:

1. **En `/fase2/05_logs/deporte_pb/`:** 14 archivos `.log` (uno por paso, excepto paso 11 que es transición)
2. **En `/fase2/03_backup/`:** 4 archivos de respaldo
   - `deporte_pb_full_base.tar.zst` (FULL)
   - `deporte_pb_incr_1.tar.zst` (INCR 1)
   - `deporte_pb_incr_2.tar.zst` (INCR 2)
   - `deporte_pb_incr_3.tar.zst` (INCR 3)
3. **En los logs:** Mensajes finales de `VALIDACION OK` en restauraciones

**Comando para verificar:**
```powershell
docker compose -p fase2_deporte exec -u postgres db psql -d olimpiadas -c "SELECT * FROM olimpiadas.medallero_deporte ORDER BY cantidad DESC LIMIT 5;"
```

**Salida esperada (medallero de atletismo):**
```
 pais_id |         pais          | oro | plata | bronce | cantidad
---------+-----------------------+-----+-------+--------+----------
 104501  | Usain Bolt (Jamaica)  |  10 |     2 |      0 |       12
 104502  | Michael Johnson (USA) |   4 |     0 |      0 |        4
 ...
```

---

## 7. Notas Importantes

- **Idempotencia:** `cargar_ronda.sh` puede ejecutarse múltiples veces en la misma ronda sin duplicar datos (gracias a `ON CONFLICT DO NOTHING`).
- **Integridad de respaldos:** Los respaldos incrementales dependen del `backup_manifest` del FULL anterior; nunca mover o eliminar el FULL sin los INCR.
- **Fragmentación:** Comparar fragmentación pre y post para analizar el impacto de la compresión WAL en el tamaño del respaldo incremental.
- **Verificación de checksums:** PostgreSQL 17 con `data_checksums=on` detecta corrupción automáticamente durante lectura.

---

