#!/usr/bin/env bash
set -euo pipefail
TIPO=$1; P=$2; N=$3
LOGDIR="/fase2/05_logs/${TIPO}_${P}"
mkdir -p "$LOGDIR"

PASO=$(( N * 2 + 2 ))
PASO_FMT=$(printf "%02d" $PASO)
LOG="$LOGDIR/${TIPO}_${P}_${PASO_FMT}_backup_incr${N}.log"
DEST="/backups/incr${N}"

if [ "$N" -eq 1 ]; then
  BASE="/backups/full"
else
  BASE="/backups/incr$((N-1))"
fi

echo "Inicio: $(date '+%F %T %Z')" | tee -a "$LOG"
t0=$(date +%s.%N)
pg_basebackup -D "$DEST" -Fp -Xs -c fast --incremental="$BASE/backup_manifest" -v -P 2>&1 | tee -a "$LOG"
t1=$(date +%s.%N)

BYTES=$(du -sb "$DEST" | cut -f1)
psql -d olimpiadas -At -f /fase2/04_restauracion/conteos.sql > "/backups/conteos_incr${N}.txt"

SEGUNDOS=$(awk "BEGIN {print $t1 - $t0}")
echo "Fin: $(date '+%F %T %Z') segundos=$SEGUNDOS bytes=$BYTES" | tee -a "$LOG"
echo "${TIPO}_${P},${HOSTNAME},${PASO_FMT},backup_incr,${N},total,$(date '+%F %T'),$SEGUNDOS,$BYTES,OK,1" >> "/fase2/05_logs/tiempos_${TIPO}_${P}.csv"