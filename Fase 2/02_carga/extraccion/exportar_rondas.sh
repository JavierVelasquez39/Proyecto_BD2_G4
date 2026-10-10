#!/usr/bin/env bash
# Fase 2 / B1: extraccion de CSV (carga base + 9 rondas) desde la BD de la Fase 1.
#
# SOLO LECTURA: unicamente COPY (SELECT ...) TO STDOUT.
# Ademas la sesion se fuerza a default_transaction_read_only=on, de modo que
# cualquier INSERT/UPDATE/DELETE/DDL que se cuele por error sea rechazado.
# No usa pg_dump.
#
# Uso:  bash exportar_rondas.sh
# Variable opcional:  CONTENEDOR=olimpiadas_pg  (valor por defecto)
#
# Los IDs (ediciones 61/59/55/45/47/51, evento 1025, atleta 104492) se
# verificaron en la BD olimpiadas_pg de la maquina de Javier.

set -euo pipefail

CONTENEDOR="${CONTENEDOR:-olimpiadas_pg}"

# Carpeta de destino: .../Fase 2/02_carga/datos (relativa a este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
D="$SCRIPT_DIR/../datos"

# Comprobar que el contenedor fuente esta corriendo
if [ "$(docker inspect -f '{{.State.Running}}' "$CONTENEDOR" 2>/dev/null)" != "true" ]; then
  echo "ERROR: el contenedor '$CONTENEDOR' no esta corriendo." >&2
  exit 1
fi

# q <archivo_destino> "<consulta>"
q() {
  docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$CONTENEDOR" \
    psql -U postgres -d olimpiadas -X -q -v ON_ERROR_STOP=1 \
    -c "COPY ($2) TO STDOUT WITH (FORMAT csv, HEADER true)" > "$1"
}

echo "Inicio: $(date '+%F %T')"

# ---------- Carga base ----------
mkdir -p "$D/base"
q "$D/base/pais.csv"                 "SELECT * FROM olimpiadas.pais ORDER BY 1"
q "$D/base/poblacion_pais.csv"       "SELECT * FROM olimpiadas.poblacion_pais ORDER BY 1"
q "$D/base/noc.csv"                  "SELECT * FROM olimpiadas.noc ORDER BY 1"
q "$D/base/deporte.csv"              "SELECT * FROM olimpiadas.deporte ORDER BY 1"
q "$D/base/deporte_equivalencia.csv" "SELECT * FROM olimpiadas.deporte_equivalencia ORDER BY 1"

# ---------- Rondas ----------
# ronda <carpeta> <edicion_id> "<filtro sobre participacion p>"
ronda() {
  local R="$D/$1" ED="$2" F="$3"
  mkdir -p "$R"
  q "$R/sede.csv"             "SELECT s.* FROM olimpiadas.sede s WHERE s.sede_id = (SELECT sede_id FROM olimpiadas.edicion_olimpica WHERE edicion_id = $ED)"
  q "$R/edicion_olimpica.csv" "SELECT * FROM olimpiadas.edicion_olimpica WHERE edicion_id = $ED"
  q "$R/evento.csv"           "SELECT e.* FROM olimpiadas.evento e WHERE e.evento_id IN (SELECT p.evento_id FROM olimpiadas.participacion p WHERE $F) ORDER BY 1"
  q "$R/atleta.csv"           "SELECT a.* FROM olimpiadas.atleta a WHERE a.atleta_id IN (SELECT p.atleta_id FROM olimpiadas.participacion p WHERE $F) ORDER BY 1"
  q "$R/participacion.csv"    "SELECT p.* FROM olimpiadas.participacion p WHERE $F ORDER BY 1"
  q "$R/resultado.csv"        "SELECT r.* FROM olimpiadas.resultado r JOIN olimpiadas.participacion p USING (participacion_id) WHERE $F ORDER BY 1"
}

ronda anio/r1_paris2024          61 "p.edicion_id = 61"
ronda anio/r2_tokio2020          59 "p.edicion_id = 59"
ronda anio/r3_rio2016            55 "p.edicion_id = 55"
ronda deporte/r1_paris2024       61 "p.edicion_id = 61 AND p.evento_id = 1025"
ronda deporte/r2_tokio2020       59 "p.edicion_id = 59 AND p.evento_id = 1025"
ronda deporte/r3_rio2016         55 "p.edicion_id = 55 AND p.evento_id = 1025"
ronda deportista/r1_atenas2004   45 "p.edicion_id = 45 AND p.atleta_id = 104492"
ronda deportista/r2_pekin2008    47 "p.edicion_id = 47 AND p.atleta_id = 104492"
ronda deportista/r3_londres2012  51 "p.edicion_id = 51 AND p.atleta_id = 104492"

echo "Fin: $(date '+%F %T')"

# ---------- Verificacion: filas por CSV (sin encabezado) ----------
echo
echo "== Filas por CSV (wc -l menos 1) =="
cnt() { echo $(( $(wc -l < "$1") - 1 )); }
echo "-- base --"
for f in pais poblacion_pais noc deporte deporte_equivalencia; do
  printf '%-24s %s\n' "$f" "$(cnt "$D/base/$f.csv")"
done
echo "-- rondas --"
printf '%-22s %14s %10s %8s %7s\n' carpeta participacion resultado atleta evento
for r in anio/r1_paris2024 anio/r2_tokio2020 anio/r3_rio2016 \
         deporte/r1_paris2024 deporte/r2_tokio2020 deporte/r3_rio2016 \
         deportista/r1_atenas2004 deportista/r2_pekin2008 deportista/r3_londres2012; do
  printf '%-22s %14s %10s %8s %7s\n' "$r" \
    "$(cnt "$D/$r/participacion.csv")" "$(cnt "$D/$r/resultado.csv")" \
    "$(cnt "$D/$r/atleta.csv")" "$(cnt "$D/$r/evento.csv")"
done
echo
echo "Total de archivos CSV: $(find "$D" -name '*.csv' | wc -l) (esperado: 59 = 5 base + 54 de rondas)"