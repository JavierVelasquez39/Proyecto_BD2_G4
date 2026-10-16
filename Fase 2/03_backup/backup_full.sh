#!/usr/bin/env bash
set -euo pipefail
TIPO=$1; P=$2
LOGDIR="/fase2/05_logs/${TIPO}_${P}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/${TIPO}_${P}_02_backup_full.log"
DEST="/backups/full"

echo "Inicio: $(date '+%F %T %Z')" | tee -a "$LOG"
t0=$(date +%s.%N)
pg_basebackup -D "$DEST" -Fp -Xs -c fast -l "full_${TIPO}_${P}" -v -P 2>&1 | tee -a "$LOG"
t1=$(date +%s.%N)

BYTES=$(du -sb "$DEST" | cut -f1)
psql -d olimpiadas -At -f /fase2/04_restauracion/conteos.sql > /backups/conteos_full.txt

SEGUNDOS=$(awk "BEGIN {print $t1 - $t0}")
echo "Fin: $(date '+%F %T %Z') segundos=$SEGUNDOS bytes=$BYTES" | tee -a "$LOG"
echo "${TIPO}_${P},${HOSTNAME},02,backup_full,0,total,$(date '+%F %T'),$SEGUNDOS,$BYTES,OK,1" >> "/fase2/05_logs/tiempos_${TIPO}_${P}.csv"