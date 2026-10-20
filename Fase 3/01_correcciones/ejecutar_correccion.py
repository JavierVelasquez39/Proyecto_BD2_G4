"""Ejecuta un script de correccion SQL contra Postgres (contenedor Docker).

Pasos: (1) pg_dump previo en 00_infraestructura/backups/ (salvo --sin-dump),
(2) copia el .sql y el .csv al contenedor, (3) corre psql con ON_ERROR_STOP,
(4) deja bitacora con fecha y hora de inicio/fin y la salida de psql en 08_logs/.

Uso: python ejecutar_correccion.py B1_medallas_paris2024.sql datos/correcciones_paris2024.csv [--db olimpiadas]
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CONTENEDOR = "olimpiadas_pg"
RAIZ = Path(__file__).resolve().parent.parent
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=ENV, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sql")
    ap.add_argument("csv")
    ap.add_argument("--db", default="olimpiadas")
    ap.add_argument("--sin-dump", action="store_true", help="solo para bases de prueba")
    ap.add_argument("--var", action="append", default=[], help="variable psql, p. ej. --var fase=1")
    a = ap.parse_args()

    inicio = datetime.now()
    t0 = time.perf_counter()
    sql, csv = Path(a.sql).resolve(), Path(a.csv).resolve()
    log = [f"Correccion {sql.name} sobre base '{a.db}' - inicio {inicio:%Y-%m-%d %H:%M:%S}"]

    if not a.sin_dump:
        sufijo = "".join("_" + v.replace("=", "") for v in a.var)
        dump = f"olimpiadas_pre_{sql.stem}{sufijo}_{inicio:%Y-%m-%d_%H%M%S}.dump"
        r = run(["docker", "exec", CONTENEDOR, "pg_dump", "-U", "postgres", "-Fc", "-d", a.db, "-f", f"/tmp/{dump}"])
        if r.returncode:
            sys.exit("pg_dump fallo, no se ejecuta nada:\n" + r.stderr)
        destino = RAIZ / "00_infraestructura" / "backups" / dump
        r = run(["docker", "cp", f"{CONTENEDOR}:/tmp/{dump}", str(destino)])
        if r.returncode or destino.stat().st_size == 0:
            sys.exit("No se pudo copiar el respaldo, no se ejecuta nada:\n" + r.stderr)
        log.append(f"Respaldo previo: {destino.name} ({destino.stat().st_size:,} bytes)")

    run(["docker", "exec", CONTENEDOR, "mkdir", "-p", "/tmp/corr/datos"])
    run(["docker", "cp", str(sql), f"{CONTENEDOR}:/tmp/corr/{sql.name}"])
    run(["docker", "cp", str(csv), f"{CONTENEDOR}:/tmp/corr/datos/{csv.name}"])
    r = run(["docker", "exec", "-w", "/tmp/corr", CONTENEDOR, "psql", "-U", "postgres", "-d", a.db,
             "-v", "ON_ERROR_STOP=1", *[x for v in a.var for x in ("-v", v)], "-f", sql.name])
    log.append("--- salida psql ---")
    log.append((r.stdout + r.stderr).strip())
    fin = datetime.now()
    log.append(f"Resultado: {'OK' if r.returncode == 0 else 'ERROR (transaccion revertida)'}")
    log.append(f"Fin: {fin:%Y-%m-%d %H:%M:%S} | duracion {time.perf_counter() - t0:.1f} s")

    logs = RAIZ / "08_logs"
    logs.mkdir(exist_ok=True)
    ruta = logs / f"{sql.stem}{''.join('_' + v.replace('=', '') for v in a.var)}_{a.db}_{inicio:%Y-%m-%d_%H%M%S}.log"
    ruta.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
