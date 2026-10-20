"""Fase C3: carga los .jsonl exportados a MongoDB con insert_many por lotes de 5,000 (ordered=False).

Uso: python cargar.py [--uri mongodb://localhost:57017] [--db olimpiadas_mongo] [--datos ../02_exportar/data]
Las colecciones deben existir con validadores (03_colecciones/crear_colecciones.js). Vacia cada coleccion antes de
cargarla para que la corrida sea repetible. Deja bitacora con fecha y hora de inicio/fin, conteos y duracion en 08_logs/.
Los indices se crean despues (05_indices/crear_indices.js).
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import BulkWriteError

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
LOTE = 5000
COLECCIONES = [("deportes", "deportes.jsonl"), ("ediciones", "ediciones.jsonl"), ("paises", "paises.jsonl"),
               ("participaciones", "participaciones.jsonl"), ("atletas", "atletas.jsonl")]


def a_fecha(s):
    return datetime.strptime(s, "%Y-%m-%d") if s else None


def convertir(nombre, doc):
    if nombre == "atletas":
        doc["fecha_nacimiento"] = a_fecha(doc.get("fecha_nacimiento"))
        doc["fecha_fallecimiento"] = a_fecha(doc.get("fecha_fallecimiento"))
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="mongodb://localhost:57017")
    ap.add_argument("--db", default="olimpiadas_mongo")
    ap.add_argument("--datos", default=str(AQUI.parent / "02_exportar" / "data"))
    a = ap.parse_args()
    inicio = datetime.now()
    t0 = time.perf_counter()
    log = [f"C3 cargar - inicio {inicio:%Y-%m-%d %H:%M:%S} | base {a.db}"]
    p = lambda m: (print(m, flush=True), log.append(m))
    db = MongoClient(a.uri)[a.db]
    datos = Path(a.datos)
    errores_total = 0
    for nombre, archivo in COLECCIONES:
        col = db[nombre]
        col.delete_many({})
        t = time.perf_counter()
        n = err = 0
        lote = []

        def vaciar():
            nonlocal n, err, lote
            if not lote:
                return
            try:
                col.insert_many(lote, ordered=False)
                n += len(lote)
            except BulkWriteError as e:
                err += len(e.details["writeErrors"])
                n += len(lote) - len(e.details["writeErrors"])
                p(f"  ERRORES en {nombre}: {e.details['writeErrors'][0]['errmsg'][:200]}")
            lote = []

        with open(datos / archivo, encoding="utf-8") as f:
            for linea in f:
                lote.append(convertir(nombre, json.loads(linea)))
                if len(lote) >= LOTE:
                    vaciar()
        vaciar()
        errores_total += err
        p(f"{nombre}: {n:,} documentos cargados, {err} rechazados por el validador, {time.perf_counter() - t:.1f} s")
    fin = datetime.now()
    p(f"Fin: {fin:%Y-%m-%d %H:%M:%S} | duracion {time.perf_counter() - t0:.1f} s | rechazados: {errores_total}")
    (RAIZ / "08_logs").mkdir(exist_ok=True)
    (RAIZ / "08_logs" / f"cargar_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    raise SystemExit(1 if errores_total else 0)


if __name__ == "__main__":
    main()
