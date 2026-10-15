#!/usr/bin/env bash
# Fase 2 / B2: loader de CSV (carga base y rondas) hacia el esquema olimpiadas.
#
# Uso (dentro del contenedor, como usuario postgres):
#   cargar_ronda.sh <tipo> <persona> <carpeta>
#     tipo     : anio | deporte | deportista
#     persona  : pa | pb | pc
#     carpeta  : base | r1_<...> | r2_<...> | r3_<...>
#
# Desde el host (carpeta "Fase 2" montada en /fase2):
#   docker compose -p fase2_deporte exec -u postgres db \
#     bash /fase2/02_carga/cargar_ronda.sh deporte pb base
#
# Que hace:
#   * Por cada tabla, en el orden de las llaves foraneas, y solo si existe su CSV:
#     COPY a una tabla temporal (staging) -> INSERT ... ON CONFLICT (pk) DO NOTHING.
#   * Todo en UNA transaccion (psql -1 con ON_ERROR_STOP): si algo falla, no se
#     carga nada de esa ronda.
#   * Imprime por tabla en_csv (filas del CSV) e insertadas. Si insertadas < en_csv
#     son filas que ya existian (normal en atletas/eventos repetidos entre rondas;
#     en una segunda corrida de la misma ronda debe dar insertadas = 0).
#   * Sincroniza las secuencias (se insertan los IDs originales).
#   * Al final imprime la fecha y los conteos de las 11 tablas (conteos.sql de C).
#   * Guarda el log en 05_logs/<tipo>_<persona>/<tipo>_<persona>_<paso>_carga_<carpeta>.log
#
# Variables opcionales: FASE2_DIR (por defecto /fase2), DB (por defecto olimpiadas),
# DRY_RUN=1 (solo imprime el SQL que se ejecutaria, sin tocar la base).
#
# No usa pg_dump ni pg_restore. No hace DDL ni borra datos.

set -euo pipefail

FASE2_DIR="${FASE2_DIR:-/fase2}"
DB="${DB:-olimpiadas}"

if [ "$#" -ne 3 ]; then
  echo "Uso: $0 <anio|deporte|deportista> <pa|pb|pc> <base|r1_...|r2_...|r3_...>" >&2
  exit 2
fi
TIPO="$1"; PERSONA="$2"; CARPETA="$3"

case "$TIPO" in anio|deporte|deportista) ;; *) echo "ERROR: tipo invalido '$TIPO'" >&2; exit 2;; esac
case "$PERSONA" in pa|pb|pc) ;; *) echo "ERROR: persona invalida '$PERSONA'" >&2; exit 2;; esac

# Numero de paso segun la tabla 1.6 de la guia
case "$CARPETA" in
  base) PASO="01"; DIR="$FASE2_DIR/02_carga/datos/base" ;;
  r1_*) PASO="03"; DIR="$FASE2_DIR/02_carga/datos/$TIPO/$CARPETA" ;;
  r2_*) PASO="05"; DIR="$FASE2_DIR/02_carga/datos/$TIPO/$CARPETA" ;;
  r3_*) PASO="07"; DIR="$FASE2_DIR/02_carga/datos/$TIPO/$CARPETA" ;;
  *) echo "ERROR: carpeta invalida '$CARPETA' (use base, r1_..., r2_... o r3_...)" >&2; exit 2 ;;
esac

if [ ! -d "$DIR" ]; then
  echo "ERROR: no existe la carpeta de datos: $DIR" >&2
  exit 1
fi

# tabla:columna_pk (noc no tiene secuencia). Orden = orden de insercion por FK.
TABLAS=(
  pais:pais_id
  poblacion_pais:poblacion_id
  noc:codigo_noc
  sede:sede_id
  edicion_olimpica:edicion_id
  deporte:deporte_id
  deporte_equivalencia:equivalencia_id
  evento:evento_id
  atleta:atleta_id
  participacion:participacion_id
  resultado:resultado_id
)

# Debe haber al menos un CSV
hay_csv=0
for par in "${TABLAS[@]}"; do
  [ -f "$DIR/${par%%:*}.csv" ] && hay_csv=1
done
if [ "$hay_csv" -eq 0 ]; then
  echo "ERROR: no hay ningun CSV de tablas en $DIR" >&2
  exit 1
fi

# Genera el SQL de la carga (stdout)
generar_sql() {
  local par t pk
  for par in "${TABLAS[@]}"; do
    t="${par%%:*}"; pk="${par#*:}"
    [ -f "$DIR/$t.csv" ] || continue
    # ON CONFLICT solo sobre la PK: una fila con otro ID y la misma clave
    # natural viola su uq_* y revierte la ronda en vez de descartarse.
    cat <<SQL
\echo '--- $t ---'
CREATE TEMP TABLE stg_$t (LIKE olimpiadas.$t) ON COMMIT DROP;
COPY stg_$t FROM '$DIR/$t.csv' WITH (FORMAT csv, HEADER true);
WITH ins AS (
  INSERT INTO olimpiadas.$t SELECT * FROM stg_$t ON CONFLICT ($pk) DO NOTHING RETURNING 1
)
SELECT '$t' AS tabla, (SELECT count(*) FROM stg_$t) AS en_csv, count(*) AS insertadas FROM ins;
SQL
  done

  echo "\\echo '--- sincronizar secuencias ---'"
  for par in "${TABLAS[@]}"; do
    t="${par%%:*}"; pk="${par#*:}"
    [ -f "$DIR/$t.csv" ] || continue
    # noc usa codigo_noc (texto) como PK, no tiene secuencia
    [ "$t" = noc ] && continue
    # is_called = false si la tabla esta vacia, para que el siguiente ID sea 1
    cat <<SQL
SELECT '$t' AS tabla, setval(pg_get_serial_sequence('olimpiadas.$t','$pk'), COALESCE(max($pk),1), max($pk) IS NOT NULL) AS ultimo_id FROM olimpiadas.$t;
SQL
  done
}

if [ "${DRY_RUN:-0}" = "1" ]; then
  generar_sql
  exit 0
fi

main() {
  set -euo pipefail
  echo "============================================================"
  echo "cargar_ronda.sh  tipo=$TIPO  persona=$PERSONA  carpeta=$CARPETA  paso=$PASO"
  echo "Inicio: $(date '+%F %T %Z')"
  echo "Origen: $DIR"
  echo "============================================================"

  generar_sql | psql -X -q -d "$DB" -v ON_ERROR_STOP=1 -1 -f -

  echo
  echo "== Conteos de las 11 tablas despues de la carga =="
  echo "Fecha: $(date '+%F %T %Z')"
  local conteos="$FASE2_DIR/04_restauracion/conteos.sql"
  if [ -f "$conteos" ]; then
    psql -X -At -d "$DB" -f "$conteos"
  else
    echo "AVISO: no se encontro $conteos; conteos omitidos"
  fi
  echo "Fin: $(date '+%F %T %Z')"
  echo "CARGA OK"
}

LOGDIR="$FASE2_DIR/05_logs/${TIPO}_${PERSONA}"
LOG="$LOGDIR/${TIPO}_${PERSONA}_${PASO}_carga_${CARPETA}.log"

# Sin log no hay evidencia: se aborta antes de tocar la base.
if ! { mkdir -p "$LOGDIR" && : >> "$LOG"; } 2>/dev/null; then
  echo "CARGA FALLIDA: no se puede crear o escribir el log en $LOG (permisos del montaje). No se cargo nada."
  exit 1
fi

set +e
main 2>&1 | tee -a "$LOG"
st=("${PIPESTATUS[@]}")
set -e
rc="${st[0]}"; rc_tee="${st[1]}"

if [ "$rc" -eq 0 ] && [ "$rc_tee" -ne 0 ]; then
  echo "CARGA FALLIDA (codigo $rc_tee): los datos si se cargaron, pero el log $LOG quedo incompleto."
  exit "$rc_tee"
fi

if [ "$rc" -ne 0 ]; then
  echo "CARGA FALLIDA (codigo $rc). La transaccion se revirtio: no se cargo nada de esta ronda."
  exit "$rc"
fi