"""Fase E2: arma el paquete de entrega entrega_fase3_<fecha>.zip (scripts, .jsonl y respaldo de Postgres como archivo fuente).

Exporta un pg_dump nuevo (olimpiadas_fase3_postgres.dump) a entrega/fuente/ y comprime la carpeta Fase 3
sin respaldos intermedios ni la propia carpeta entrega.
"""
import os
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1"}
destino = RAIZ / "entrega" / "fuente"
destino.mkdir(parents=True, exist_ok=True)
dump = destino / "olimpiadas_fase3_postgres.dump"
subprocess.run(["docker", "exec", "olimpiadas_pg", "pg_dump", "-U", "postgres", "-Fc", "-d", "olimpiadas", "-f", "/tmp/fase3.dump"], check=True, env=ENV)
subprocess.run(["docker", "cp", "olimpiadas_pg:/tmp/fase3.dump", str(dump)], check=True, env=ENV)
zpath = RAIZ / "entrega" / f"entrega_fase3_{datetime.now():%Y-%m-%d}.zip"
omitir = ("__pycache__", "backups", "entrega")
n = 0
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for ruta in sorted(RAIZ.rglob("*")):
        rel = ruta.relative_to(RAIZ)
        if ruta.is_dir() or any(p in omitir for p in rel.parts) or ruta.suffix == ".pyc":
            continue
        z.write(ruta, "Fase 3/" + rel.as_posix())
        n += 1
    z.write(dump, "Fase 3/fuente/" + dump.name)
print(f"{zpath.name}: {n + 1} archivos, {zpath.stat().st_size / 1e6:.1f} MB; respaldo {dump.stat().st_size / 1e6:.1f} MB")
