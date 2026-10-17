#!/usr/bin/env bash
# RestauraciÃ³n de cadena fÃ­sica PostgreSQL 17 con pg_combinebackup y registro de tiempos
# Uso: restaurar.sh <tipo> <persona> <n_cadena> [repeticion] [observacion]
#   n_cadena: 0=FULL, 1=FULL+INCR1, 2=FULL+INCR1+INCR2, 3=Cadena completa
#   repeticion: 1 a 3 (por defecto 1); cada repeticiÃ³n parte de PGDATA vacÃ­o
set -Eeuo pipefail

TIPO=$1
P=$2
N=$3
REP=${4:-1}
OBS=${5:-}
FASE2_DIR="${FASE2_DIR:-/fase2}"
source "$FASE2_DIR/03_backup/lib_tiempos.sh"

LOGDIR=$FASE2_DIR/05_logs/${TIPO}_${P}
PASO=$((12 + N))
PASO_STR=$(printf "%02d" "$PASO")
LOG=$LOGDIR/${TIPO}_${P}_${PASO_STR}_restore_cadena${N}_rep${REP}.log
LOG_SRV=$LOGDIR/${TIPO}_${P}_${PASO_STR}_restore_cadena${N}_rep${REP}_servidor.log
CSV=$FASE2_DIR/05_logs/tiempos_${TIPO}_${P}.csv
MAQUINA=$(maquina_de "$P")
PERSONA=$P; PASO=$PASO_STR; OPERACION=restore; N_CADENA=$N; REPETICION=$REP
log_nuevo "$LOG"
log_nuevo "$LOG_SRV"

# Si algo falla con el servidor arriba, se detiene antes de salir
al_fallar_extra() {
  if pg_ctl -D "$PGDATA" status > /dev/null 2>&1; then
    pg_ctl -D "$PGDATA" -m fast stop 2>&1 | tee -a "$LOG"
  fi
}
trap 'alerta_al_fallar $LINENO' ERR

echo "=== Inicio de RestauraciÃ³n Cadena N=$N repeticiÃ³n $REP: $(date '+%F %T %Z') ===" | tee -a "$LOG"

# 1. Abortar si el servidor sigue corriendo
if [ -f "$PGDATA/postmaster.pid" ]; then
  echo "ERROR: PostgreSQL sigue activo en $PGDATA (postmaster.pid existe)." | tee -a "$LOG"
  exit 1
fi

# 2. Vaciar $PGDATA (incluye archivos ocultos; el directorio se conserva)
echo "Limpiando directorio $PGDATA..." | tee -a "$LOG"
find "$PGDATA" -mindepth 1 -delete
ls -la "$PGDATA" | tee -a "$LOG"

# 3. Etapa COMBINAR (pg_combinebackup)
echo "Etapa 1: Combinando respaldos (pg_combinebackup)..." | tee -a "$LOG"
ETAPA=combinar; ETAPA_INI=$(ahora_iso); ETAPA_T0=$(ahora_seg)
TOTAL_INI=$ETAPA_INI; TOTAL_T0=$ETAPA_T0
INI_COMB=$ETAPA_INI; t0=$ETAPA_T0

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
FIN_COMB=$(ahora_iso)
t1=$(ahora_seg)
SEG_COMB=$(segundos_entre "$t0" "$t1")
BYTES=$(bytes_de "$PGDATA")

# VerificaciÃ³n del directorio combinado, antes de arrancar (queda dentro de total)
ETAPA=verificacion; ETAPA_T0=
v0=$(ahora_seg)
pg_verifybackup "$PGDATA" 2>&1 | tee -a "$LOG"
echo "pg_verifybackup: $(segundos_entre "$v0" "$(ahora_seg)") s" | tee -a "$LOG"

# 4. Etapa ARRANQUE (pg_ctl start)
echo "Etapa 2: Arrancando servidor PostgreSQL (pg_ctl)..." | tee -a "$LOG"
ETAPA=arranque; ETAPA_INI=$(ahora_iso); ETAPA_T0=$(ahora_seg)
INI_ARR=$ETAPA_INI; t2=$ETAPA_T0

pg_ctl -D "$PGDATA" -l "$LOG_SRV" -w -t 900 -o "-c listen_addresses=''" start 2>&1 | tee -a "$LOG"

FIN_ARR=$(ahora_iso)
t3=$(ahora_seg)
SEG_ARR=$(segundos_entre "$t2" "$t3")

# 5. Etapa VALIDACIÃ“N (validar.sql y comparaciÃ³n de conteos)
echo "Etapa 3: Validando datos restaurados..." | tee -a "$LOG"
ETAPA=validacion; ETAPA_INI=$(ahora_iso); ETAPA_T0=$(ahora_seg)
INI_VAL=$ETAPA_INI; t4=$ETAPA_T0

psql -d olimpiadas -v limite=10 -f "$FASE2_DIR/04_restauracion/validar.sql" 2>&1 | tee -a "$LOG"
psql -d olimpiadas -At -f "$FASE2_DIR/04_restauracion/conteos.sql" > /tmp/conteos_actual.txt

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

FIN_VAL=$(ahora_iso)
t5=$(ahora_seg)
SEG_VAL=$(segundos_entre "$t4" "$t5")

# 6. Filas en tiempos (combinar, arranque, validacion, total)
SEG_TOTAL=$(segundos_entre "$t0" "$t5")
ETAPA=detener; ETAPA_T0=; TOTAL_T0=

tiempos_fila "$CSV" "$P" "$TIPO" "$MAQUINA" "$PASO_STR" restore "$N" combinar "$INI_COMB" "$FIN_COMB" "$SEG_COMB" "$BYTES" "" "$REP" "$OBS"
tiempos_fila "$CSV" "$P" "$TIPO" "$MAQUINA" "$PASO_STR" restore "$N" arranque "$INI_ARR" "$FIN_ARR" "$SEG_ARR" "" "" "$REP" "$OBS"
tiempos_fila "$CSV" "$P" "$TIPO" "$MAQUINA" "$PASO_STR" restore "$N" validacion "$INI_VAL" "$FIN_VAL" "$SEG_VAL" "" "$STATUS_VAL" "$REP" "$OBS"
tiempos_fila "$CSV" "$P" "$TIPO" "$MAQUINA" "$PASO_STR" restore "$N" total "$INI_COMB" "$FIN_VAL" "$SEG_TOTAL" "$BYTES" "$STATUS_VAL" "$REP" "$OBS"

# Apagar servidor para dejar el entorno listo
pg_ctl -D "$PGDATA" -m fast stop 2>&1 | tee -a "$LOG"

echo "=== RestauraciÃ³n N=$N repeticiÃ³n $REP finalizada con estado: $STATUS_VAL (Total: ${SEG_TOTAL} s) ===" | tee -a "$LOG"

if [ "$STATUS_VAL" != "OK" ]; then
  exit 1
fi
