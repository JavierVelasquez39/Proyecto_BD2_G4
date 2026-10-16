#!/usr/bin/env bash
# Respaldo INCR fisico encadenado al anterior. Uso: backup_incremental.sh <tipo> <persona> <n> [observacion]
set -euo pipefail
TIPO=$1; P=$2; N=$3; OBS=${4:-}
FASE2_DIR="${FASE2_DIR:-/fase2}"
source "$FASE2_DIR/03_backup/lib_tiempos.sh"

LOGDIR="$FASE2_DIR/05_logs/${TIPO}_${P}"
PASO=$(( N * 2 + 2 ))
PASO_FMT=$(printf "%02d" $PASO)
LOG="$LOGDIR/${TIPO}_${P}_${PASO_FMT}_backup_incr${N}.log"
CSV="$FASE2_DIR/05_logs/tiempos_${TIPO}_${P}.csv"
DEST="/backups/incr${N}"
PERSONA=$P; MAQUINA=$(maquina_de "$P"); PASO=$PASO_FMT; OPERACION=backup_incr; N_CADENA=$N; REPETICION=1
log_nuevo "$LOG"

if [ "$N" -eq 1 ]; then
  BASE="/backups/full"
else
  BASE="/backups/incr$((N-1))"
fi

echo "Inicio: $(date '+%F %T %Z')" | tee -a "$LOG"
ETAPA=basebackup; ETAPA_INI=$(ahora_iso); ETAPA_T0=$(ahora_seg)
pg_basebackup -D "$DEST" -Fp -Xs -c fast --incremental="$BASE/backup_manifest" -v -P 2>&1 | tee -a "$LOG"
FIN=$(ahora_iso); t1=$(ahora_seg)
SEGUNDOS=$(segundos_entre "$ETAPA_T0" "$t1")
BYTES=$(bytes_de "$DEST")

# Verificacion del respaldo (fuera del tiempo medido); si falla, ALERTA
v0=$(ahora_seg)
pg_verifybackup "$DEST" 2>&1 | tee -a "$LOG"
echo "pg_verifybackup: $(segundos_entre "$v0" "$(ahora_seg)") s" | tee -a "$LOG"

psql -d olimpiadas -At -f "$FASE2_DIR/04_restauracion/conteos.sql" > "/backups/conteos_incr${N}.txt"

echo "Fin: $(date '+%F %T %Z') segundos=$SEGUNDOS bytes=$BYTES" | tee -a "$LOG"
tiempos_fila "$CSV" "$P" "$TIPO" "$MAQUINA" "$PASO" "$OPERACION" "$N_CADENA" \
  basebackup "$ETAPA_INI" "$FIN" "$SEGUNDOS" "$BYTES" "" "$REPETICION" "$OBS"
