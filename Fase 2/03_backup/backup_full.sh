#!/usr/bin/env bash
# Respaldo FULL fisico con pg_basebackup. Uso: backup_full.sh <tipo> <persona> [observacion]
set -euo pipefail
TIPO=$1; P=$2; OBS=${3:-}
FASE2_DIR="${FASE2_DIR:-/fase2}"
source "$FASE2_DIR/03_backup/lib_tiempos.sh"

LOGDIR="$FASE2_DIR/05_logs/${TIPO}_${P}"
LOG="$LOGDIR/${TIPO}_${P}_02_backup_full.log"
CSV="$FASE2_DIR/05_logs/tiempos_${TIPO}_${P}.csv"
DEST="/backups/full"
PERSONA=$P; MAQUINA=$(maquina_de "$P"); PASO=02; OPERACION=backup_full; N_CADENA=0; REPETICION=1
log_nuevo "$LOG"

echo "Inicio: $(date '+%F %T %Z')" | tee -a "$LOG"
ETAPA=basebackup; ETAPA_INI=$(ahora_iso); ETAPA_T0=$(ahora_seg)
pg_basebackup -D "$DEST" -Fp -Xs -c fast -l "full_${TIPO}_${P}" -v -P 2>&1 | tee -a "$LOG"
FIN=$(ahora_iso); t1=$(ahora_seg)
SEGUNDOS=$(segundos_entre "$ETAPA_T0" "$t1")
BYTES=$(bytes_de "$DEST")

# Verificacion del respaldo (fuera del tiempo medido); si falla, ALERTA
v0=$(ahora_seg)
pg_verifybackup "$DEST" 2>&1 | tee -a "$LOG"
echo "pg_verifybackup: $(segundos_entre "$v0" "$(ahora_seg)") s" | tee -a "$LOG"

psql -d olimpiadas -At -f "$FASE2_DIR/04_restauracion/conteos.sql" > /backups/conteos_full.txt

echo "Fin: $(date '+%F %T %Z') segundos=$SEGUNDOS bytes=$BYTES" | tee -a "$LOG"
tiempos_fila "$CSV" "$P" "$TIPO" "$MAQUINA" "$PASO" "$OPERACION" "$N_CADENA" \
  basebackup "$ETAPA_INI" "$FIN" "$SEGUNDOS" "$BYTES" "" "$REPETICION" "$OBS"
