#!/usr/bin/env bash
# Restauración de cadena física PostgreSQL 17 con pg_combinebackup y registro de tiempos
# Uso: restaurar.sh <tipo> <persona> <n_cadena> (0=FULL, 1=FULL+INCR1, 2=FULL+INCR1+INCR2, 3=Cadena completa)
set -euo pipefail

TIPO=$1
P=$2
N=$3

LOGDIR=/fase2/05_logs/${TIPO}_${P}
mkdir -p "$LOGDIR"

PASO=$((12 + N))
PASO_STR=$(printf "%02d" "$PASO")
LOG=$LOGDIR/${TIPO}_${P}_${PASO_STR}_restore_cadena${N}.log
CSV=/fase2/05_logs/tiempos_${TIPO}_${P}.csv
MAQUINA="${P}-laptop"

echo "=== Inicio de Restauración Cadena N=$N: $(date '+%F %T %Z') ===" | tee -a "$LOG"

# 1. Abortar si el servidor sigue corriendo
if [ -f "$PGDATA/postmaster.pid" ]; then
  echo "ERROR: PostgreSQL sigue activo en $PGDATA (postmaster.pid existe)." | tee -a "$LOG"
  exit 1
fi

# 2. Limpiar $PGDATA
echo "Limpiando directorio $PGDATA..." | tee -a "$LOG"
rm -rf "${PGDATA:?}"/*
ls -la "$PGDATA" | tee -a "$LOG"

# 3. Etapa COMBINAR (pg_combinebackup)
echo "Etapa 1: Combinando respaldos (pg_combinebackup)..." | tee -a "$LOG"
INI_COMB=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z')
t0=$(date +%s.%N)

if [ "$N" -eq 0 ]; then
  cp -a /backups/full/. "$PGDATA"/ 2>&1 | tee -a "$LOG"
else
  CADENA="/backups/full"
  for i in $(seq 1 "$N"); do
    CADENA="$CADENA /backups/incr$i"
  done
  pg_combinebackup $CADENA -o "$PGDATA" 2>&1 | tee -a "$LOG"
fi

chmod 700 "$PGDATA"
FIN_COMB=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z')
t1=$(date +%s.%N)
SEG_COMB=$(awk "BEGIN{printf \"%.3f\", $t1-$t0}")
BYTES=$(du -sb "$PGDATA" | cut -f1)

# 4. Etapa ARRANQUE (pg_ctl start)
echo "Etapa 2: Arrancando servidor PostgreSQL (pg_ctl)..." | tee -a "$LOG"
INI_ARR=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z')
t2=$(date +%s.%N)

pg_ctl -D "$PGDATA" -l /tmp/pg_restore.log -w -t 900 -o "-c listen_addresses=''" start 2>&1 | tee -a "$LOG"

FIN_ARR=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z')
t3=$(date +%s.%N)
SEG_ARR=$(awk "BEGIN{printf \"%.3f\", $t3-$t2}")

# 5. Etapa VALIDACIÓN (validar.sql y comparación de conteos)
echo "Etapa 3: Validando datos restaurados..." | tee -a "$LOG"
INI_VAL=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z')
t4=$(date +%s.%N)

psql -d olimpiadas -v limite=10 -f /fase2/04_restauracion/validar.sql 2>&1 | tee -a "$LOG"
psql -d olimpiadas -At -f /fase2/04_restauracion/conteos.sql > /tmp/conteos_actual.txt

IF_FILE="/backups/conteos_full.txt"
if [ "$N" -gt 0 ]; then
  IF_FILE="/backups/conteos_incr${N}.txt"
fi

STATUS_VAL="OK"
if ! diff -u "$IF_FILE" /tmp/conteos_actual.txt >> "$LOG" 2>&1; then
  STATUS_VAL="ALERTA"
  echo "ALERTA: Los conteos no coinciden con el respaldo original!" | tee -a "$LOG"
else
  echo "VALIDACION OK: Los conteos coinciden perfectamente." | tee -a "$LOG"
fi

FIN_VAL=$(date '+%Y-%m-%dT%H:%M:%S.%3N%:z')
t5=$(date +%s.%N)
SEG_VAL=$(awk "BEGIN{printf \"%.3f\", $t5-$t4}")

# Apagar servidor para dejar el entorno listo
pg_ctl -D "$PGDATA" -m fast stop 2>&1 | tee -a "$LOG"

# 6. Escribir filas en tiempos.csv si la tabla existe/es requerida
SEG_TOTAL=$(awk "BEGIN{printf \"%.3f\", $t5-$t0}")

if [ ! -f "$CSV" ]; then
  echo "persona,tipo_carga,maquina,paso,operacion,n_cadena,etapa,inicio_iso,fin_iso,segundos,bytes,validacion,repeticion,observacion" > "$CSV"
fi

echo "${P},${TIPO},${MAQUINA},${PASO_STR},restore,${N},combinar,${INI_COMB},${FIN_COMB},${SEG_COMB},${BYTES},,1," >> "$CSV"
echo "${P},${TIPO},${MAQUINA},${PASO_STR},restore,${N},arranque,${INI_ARR},${FIN_ARR},${SEG_ARR},,,1," >> "$CSV"
echo "${P},${TIPO},${MAQUINA},${PASO_STR},restore,${N},validacion,${INI_VAL},${FIN_VAL},${SEG_VAL},,${STATUS_VAL},1," >> "$CSV"
echo "${P},${TIPO},${MAQUINA},${PASO_STR},restore,${N},total,${INI_COMB},${FIN_VAL},${SEG_TOTAL},${BYTES},${STATUS_VAL},1," >> "$CSV"

echo "=== Restauración N=$N finalizada con estado: $STATUS_VAL (Total: ${SEG_TOTAL} s) ===" | tee -a "$LOG"

if [ "$STATUS_VAL" != "OK" ]; then
  exit 1
fi