#!/usr/bin/env bash
set -euo pipefail
TIPO=$1; P=$2; N=$3
LOGDIR="/fase2/05_logs/${TIPO}_${P}"
mkdir -p "$LOGDIR"

PASO=$(( 12 + N ))
LOG="$LOGDIR/${TIPO}_${P}_${PASO}_restore_cadena${N}.log"

if [ -f "$PGDATA/postmaster.pid" ]; then
  echo "Error: PostgreSQL sigue en ejecución. Deténgalo antes de restaurar." | tee -a "$LOG"
  exit 1
fi

rm -rf "${PGDATA:?}"/*

# Etapa 1: Combinar respaldos
t0=$(date +%s.%N)
if [ "$N" -eq 0 ]; then
  cp -a /backups/full/. "$PGDATA"/
else
  CADENA="/backups/full"
  for i in $(seq 1 $N); do CADENA="$CADENA /backups/incr$i"; done
  pg_combinebackup $CADENA -o "$PGDATA"
fi
chmod 700 "$PGDATA"
t1=$(date +%s.%N)
SEG_COMBINE=$(awk "BEGIN {print $t1 - $t0}")

# Etapa 2: Arranque
t2=$(date +%s.%N)
pg_ctl -D "$PGDATA" -l /tmp/pg_restore.log -w -t 900 -o "-c listen_addresses=''" start
t3=$(date +%s.%N)
SEG_START=$(awk "BEGIN {print $t3 - $t2}")

# Etapa 3: Validación
t4=$(date +%s.%N)
psql -d olimpiadas -f /fase2/04_restauracion/validar.sql >> "$LOG" 2>&1
psql -d olimpiadas -At -f /fase2/04_restauracion/conteos.sql > /tmp/conteos_restaurados.txt

REF="/backups/conteos_full.txt"
[ "$N" -gt 0 ] && REF="/backups/conteos_incr${N}.txt"

VAL_STATUS="OK"
if ! diff -q /tmp/conteos_restaurados.txt "$REF" > /dev/null; then
  VAL_STATUS="ALERTA"
fi
t5=$(date +%s.%N)
SEG_VAL=$(awk "BEGIN {print $t5 - $t4}")
SEG_TOTAL=$(awk "BEGIN {print $SEG_COMBINE + $SEG_START + $SEG_VAL}")

pg_ctl -D "$PGDATA" -m fast stop

echo "Restauración N=$N finalizada con estado: $VAL_STATUS (Total: $SEG_TOTAL s)" | tee -a "$LOG"
echo "${TIPO}_${P},${HOSTNAME},${PASO},restore,${N},combinar,$(date '+%F %T'),$SEG_COMBINE,0,$VAL_STATUS,1" >> "/fase2/05_logs/tiempos_${TIPO}_${P}.csv"
echo "${TIPO}_${P},${HOSTNAME},${PASO},restore,${N},arranque,$(date '+%F %T'),$SEG_START,0,$VAL_STATUS,1" >> "/fase2/05_logs/tiempos_${TIPO}_${P}.csv"
echo "${TIPO}_${P},${HOSTNAME},${PASO},restore,${N},validacion,$(date '+%F %T'),$SEG_VAL,0,$VAL_STATUS,1" >> "/fase2/05_logs/tiempos_${TIPO}_${P}.csv"
echo "${TIPO}_${P},${HOSTNAME},${PASO},restore,${N},total,$(date '+%F %T'),$SEG_TOTAL,0,$VAL_STATUS,1" >> "/fase2/05_logs/tiempos_${TIPO}_${P}.csv"