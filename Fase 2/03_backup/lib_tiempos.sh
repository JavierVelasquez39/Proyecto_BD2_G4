#!/usr/bin/env bash
# Funciones comunes de tiempos y logs para backup_full.sh,
# backup_incremental.sh y restaurar.sh. Se carga con "source", no se ejecuta.
#
# CSV de tiempos: formato de la seccion 4.10 de la guia (14 columnas, UTF-8,
# LF, separador coma). El encabezado se escribe solo si el archivo no existe.
#
# Variables opcionales:
#   MAQUINA_ALIAS  alias fijo de la maquina (por defecto "laptop"); la columna
#                  maquina queda como {persona}-{alias}, igual en los 3 scripts.

TIEMPOS_ENCABEZADO="persona,tipo_carga,maquina,paso,operacion,n_cadena,etapa,inicio_iso,fin_iso,segundos,bytes,validacion,repeticion,observacion"

# Hora ISO 8601 con milisegundos y zona (ej. 2026-10-16T15:00:01.000-06:00)
ahora_iso() { date '+%Y-%m-%dT%H:%M:%S.%3N%:z'; }

# Marca en segundos con fraccion, solo para restar
ahora_seg() { date '+%s.%N'; }

# Segundos entre dos marcas, 3 decimales (la imagen no trae bc)
segundos_entre() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.3f", b - a }'; }

# Bytes de un directorio
bytes_de() { du -sb "$1" | cut -f1; }

# Valor fijo de la columna maquina
maquina_de() { echo "${1}-${MAQUINA_ALIAS:-laptop}"; }

# Escribe el encabezado si el CSV no existe
tiempos_init() { [ -e "$1" ] || echo "$TIEMPOS_ENCABEZADO" > "$1"; }

# tiempos_fila <csv> <persona> <tipo_carga> <maquina> <paso> <operacion>
#              <n_cadena> <etapa> <inicio_iso> <fin_iso> <segundos> <bytes>
#              <validacion> <repeticion> <observacion>
# Exige las 14 columnas; la observacion se limpia de comas y saltos de linea.
tiempos_fila() {
  local csv=$1; shift
  if [ "$#" -ne 14 ]; then
    echo "tiempos_fila: se esperaban 14 columnas y llegaron $#" >&2
    return 1
  fi
  local obs=${14//,/;}
  obs=${obs//$'\n'/ }
  tiempos_init "$csv"
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "$obs" >> "$csv"
}

# Un log por ejecucion, como cargar_ronda.sh: si ya existe, el anterior se
# renombra con la hora local (<nombre>.<AAAAMMDD_HHMMSS>.log).
log_nuevo() {
  local log=$1
  mkdir -p "$(dirname "$log")"
  [ ! -e "$log" ] || mv "$log" "${log%.log}.$(date '+%Y%m%d_%H%M%S').log"
  : > "$log"
}

# Fila ALERTA ante cualquier error (trap ERR). Cada script mantiene:
#   CSV PERSONA TIPO MAQUINA PASO OPERACION N_CADENA REPETICION OBS LOG
#   ETAPA ETAPA_INI ETAPA_T0   etapa en curso, su inicio ISO y su marca
#   TOTAL_INI TOTAL_T0         (solo restauracion) inicio de la etapa combinar
# Si existe la funcion al_fallar_extra (ej. detener el servidor), se llama.
alerta_al_fallar() {
  local rc=$? linea=$1
  # En subshells (sustitucion de comandos) solo se sale: la fila la escribe
  # el proceso principal cuando le llega el error.
  [ "$BASHPID" = "$$" ] || exit "$rc"
  trap - ERR
  set +e
  local fin t
  fin=$(ahora_iso); t=$(ahora_seg)
  echo "ALERTA: fallo en la etapa ${ETAPA} (linea ${linea}, codigo ${rc}) $(date '+%F %T %Z')" | tee -a "$LOG" >&2
  if [ -n "${ETAPA_T0:-}" ]; then
    tiempos_fila "$CSV" "$PERSONA" "$TIPO" "$MAQUINA" "$PASO" "$OPERACION" "$N_CADENA" \
      "$ETAPA" "$ETAPA_INI" "$fin" "$(segundos_entre "$ETAPA_T0" "$t")" "" ALERTA "$REPETICION" "$OBS"
  fi
  if [ -n "${TOTAL_T0:-}" ]; then
    tiempos_fila "$CSV" "$PERSONA" "$TIPO" "$MAQUINA" "$PASO" "$OPERACION" "$N_CADENA" \
      total "$TOTAL_INI" "$fin" "$(segundos_entre "$TOTAL_T0" "$t")" "" ALERTA "$REPETICION" "$OBS"
  fi
  if declare -F al_fallar_extra > /dev/null; then al_fallar_extra; fi
  [ "$rc" -ne 0 ] || rc=1
  exit "$rc"
}
