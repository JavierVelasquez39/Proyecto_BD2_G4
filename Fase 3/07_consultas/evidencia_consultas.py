"""Fase E1: calentamiento y evidencia de --explain y tiempos de 10 consultas de muestra.

Ejecuta cada consulta una vez para calentar (cache de MongoDB) y otra para medir con --explain; guarda en
08_logs/evidencia_consultas_<fecha>.md el plan (debe ser IXSCAN/IDHACK, nunca COLLSCAN), los tiempos de
MongoDB y el tiempo total del proceso. Sale con codigo 1 si alguna consulta usa COLLSCAN o falla.
"""
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LOGS = AQUI.parent / "08_logs"
PY = sys.executable
CONSULTAS = [
    ("Atleta conocido", "atleta.py", ["Michael Phelps"]),
    ("Atleta conocido con medallas recientes", "atleta.py", ["Summer McIntosh"]),
    ("Atleta fusionado (busqueda por alias)", "atleta.py", ["Shiyu Lu"]),
    ("Homonimos (modo CANDIDATO)", "atleta.py", ["Jack Robinson"]),
    ("Homonimos (modo CANDIDATO)", "atleta.py", ["Jordan Thompson"]),
    ("Atleta con filtros combinados", "atleta.py", ["Pawel Fajdek", "--deporte", "Athletics", "--anio", "2024"]),
    ("Pais grande, resumen", "pais.py", ["United States"]),
    ("Pais multi-NOC, resumen", "pais.py", ["Germany"]),
    ("Pais grande, detalle paginado", "pais.py", ["Russian Federation", "--detalle", "--tam", "30"]),
    ("Pais con filtros combinados, detalle", "pais.py", ["Germany", "--anio", "1972", "--deporte", "Athletics", "--detalle"]),
]


def correr(script, args):
    t = time.perf_counter()
    r = subprocess.run([PY, str(AQUI / script), *args], capture_output=True, text=True, encoding="utf-8", cwd=AQUI,
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return r, (time.perf_counter() - t) * 1000


def main():
    inicio = datetime.now()
    md = [f"# Evidencia de consultas (Fase E1)", "", f"Ejecutado el {inicio:%Y-%m-%d %H:%M:%S}. Cada consulta se corre una vez para calentar y otra para medir.",
          "Tiempo MongoDB = consultas al servidor; tiempo del proceso incluye el arranque de Python.", ""]
    resumen, fallos = [], 0
    for i, (titulo, script, args) in enumerate(CONSULTAS, 1):
        correr(script, args)  # calentamiento
        r, ms = correr(script, args + ["--explain"])
        salida = r.stdout
        planes = [l.strip() for l in salida.splitlines() if "[explain" in l]
        tiempo = next((l for l in salida.splitlines() if l.startswith("Tiempo de respuesta")), "")
        m = re.search(r"consultas a MongoDB ([\d.]+) ms \| total con formato ([\d.]+) ms", tiempo)
        colscan = any("COLLSCAN" in p for p in planes)
        estado = "OK" if r.returncode == 0 and planes and not colscan else "FALLA"
        fallos += estado != "OK"
        resumen.append((i, titulo, " ".join([script] + args), estado, m.group(1) if m else "?", m.group(2) if m else "?", f"{ms:.0f}"))
        md += [f"## {i}. {titulo}", "", f"`python {script} {' '.join(repr(a) if ' ' in a else a for a in args)} --explain`  ", f"Estado: **{estado}**, "
               f"MongoDB {m.group(1) if m else '?'} ms, total {m.group(2) if m else '?'} ms, proceso completo {ms:.0f} ms", "", "```"]
        md += planes + ["```", ""]
    md += ["## Resumen", "", "| # | Consulta | Comando | Estado | MongoDB (ms) | Total con formato (ms) | Proceso (ms) |", "|---|---|---|---|---:|---:|---:|"]
    md += [f"| {a} | {b} | `{c}` | {d} | {e} | {f} | {g} |" for a, b, c, d, e, f, g in resumen]
    LOGS.mkdir(exist_ok=True)
    ruta = LOGS / f"evidencia_consultas_{inicio:%Y-%m-%d_%H%M%S}.md"
    ruta.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[-(len(resumen) + 4):]))
    print(f"\nEvidencia: {ruta}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
