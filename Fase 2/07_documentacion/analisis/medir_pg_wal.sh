#!/usr/bin/env bash
# Mide cuánto ocupa pg_wal dentro de cada respaldo de una corrida.
# Monta el volumen de respaldos en modo solo lectura (:ro) en un contenedor
# temporal; no levanta el proyecto ni modifica nada.
#
# Uso (Git Bash, en la máquina donde están los volúmenes):
#   bash medir_pg_wal.sh deportista_pc:fase2_deportista_backups deporte_pc:fase2_deporte_pc_backups
#
# Escribe pg_wal_respaldos.csv junto a este script (UTF-8, LF). analizar.py lo
# usa solo si el total de cada respaldo coincide con la columna bytes del CSV
# de tiempos de esa corrida.
set -euo pipefail
export MSYS_NO_PATHCONV=1
SALIDA="$(cd "$(dirname "$0")" && pwd)/pg_wal_respaldos.csv"

[ "$#" -ge 1 ] || { echo "Uso: $0 <corrida>:<volumen> [...]" >&2; exit 2; }
echo "corrida,respaldo,bytes_total,bytes_pg_wal,segmentos_wal" > "$SALIDA"
for par in "$@"; do
  corrida=${par%%:*}; volumen=${par#*:}
  docker volume inspect "$volumen" > /dev/null
  docker run --rm --network none -v "$volumen:/b:ro" postgres:17 bash -c '
    for d in full incr1 incr2 incr3; do
      printf "%s,%s,%s,%s\n" "$d" "$(du -sb /b/$d | cut -f1)" "$(du -sb /b/$d/pg_wal | cut -f1)" \
        "$(ls /b/$d/pg_wal | grep -cE "^[0-9A-F]{24}$")"
    done' | sed "s/^/$corrida,/" >> "$SALIDA"
done
cat "$SALIDA"
