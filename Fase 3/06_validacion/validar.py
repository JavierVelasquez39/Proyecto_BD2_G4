"""Fase C5: valida la base MongoDB contra la linea base y contra si misma (solo lectura).

Comprobaciones:
  1. Conteos y medalleros contra linea_base_fase3.json (Fase 1 + correcciones B1 y B2), y que las
     diferencias contra linea_base_fase1.json sean exactamente las explicadas por B1 y B2.
  2. atletas.participaciones coincide con la coleccion participaciones (conteo de participaciones
     y de resultados, total y por atleta).
  3. paises.medallero y paises.medallero_por_evento coinciden con una agregacion sobre participaciones
     para TODOS los paises y entidades.
  4. Sedes: Estados Unidos 8, Francia 6, Guatemala 0 (sin YOG).
  5. Paris 2024: medallas por evento 329/330/385 (medallero oficial).
  6. Alias: los 394 nombres de atletas fusionados estan presentes y son buscables.
Sale con codigo 1 y un reporte claro si algo no cuadra. Bitacora con fecha y hora en 08_logs/.

Uso: python validar.py [--uri mongodb://localhost:57017] [--db olimpiadas_mongo]
"""
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
ESPERADO_PARIS_EVENTO = {"Oro": 329, "Plata": 330, "Bronce": 385}
CAMBIOS = {"atleta": -394, "participacion": 11, "resultado": 11}  # B2 y B1 respecto a la Fase 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="mongodb://localhost:57017")
    ap.add_argument("--db", default="olimpiadas_mongo")
    a = ap.parse_args()
    inicio = datetime.now()
    t0 = time.perf_counter()
    db = MongoClient(a.uri)[a.db]
    log, fallos = [f"C5 validar - inicio {inicio:%Y-%m-%d %H:%M:%S} | base {a.db}"], []

    def ok(msg):
        print("  OK   " + msg); log.append("  OK   " + msg)

    def mal(msg):
        print("  FALLA " + msg); log.append("  FALLA " + msg); fallos.append(msg)

    def comprobar(cond, msg):
        (ok if cond else mal)(msg)

    f3 = json.load(open(AQUI / "linea_base_fase3.json", encoding="utf-8"))
    f1 = json.load(open(AQUI / "linea_base_fase1.json", encoding="utf-8"))
    ref = f3["referencia"]

    # 1. conteos
    print("1. Conteos contra la linea base")
    n_atl = db.atletas.count_documents({})
    n_par = db.participaciones.count_documents({})
    n_res = next(db.participaciones.aggregate([{"$group": {"_id": None, "n": {"$sum": {"$size": "$resultados"}}}}]))["n"]
    comprobar(n_atl == ref["tablas"]["atleta"], f"atletas = {n_atl:,} (linea base Fase 3: {ref['tablas']['atleta']:,})")
    comprobar(n_par == ref["tablas"]["participacion"], f"participaciones = {n_par:,} (linea base Fase 3: {ref['tablas']['participacion']:,})")
    comprobar(n_res == ref["tablas"]["resultado"], f"resultados = {n_res:,} (linea base Fase 3: {ref['tablas']['resultado']:,})")
    for t, d in CAMBIOS.items():
        base = f1["tablas"][t]
        obt = {"atleta": n_atl, "participacion": n_par, "resultado": n_res}[t]
        comprobar(obt == base + d, f"{t}: Fase 1 {base:,} {d:+d} (B1/B2) = {base + d:,}; MongoDB {obt:,}")

    for pais, esp in ref["medallero"].items():
        d = db.paises.find_one({"nombre": pais})
        obt = {"Oro": d["medallero"]["sin_yog"]["oro"], "Plata": d["medallero"]["sin_yog"]["plata"], "Bronce": d["medallero"]["sin_yog"]["bronce"]}
        comprobar(obt == esp, f"medallero por atleta {pais} (sin YOG) = {obt} (esperado {esp})")

    # 4. sedes
    print("4. Sedes")
    for pais, esp in ref["sedes"].items():
        d = db.paises.find_one({"nombre": pais})
        n = sum(1 for s in d["sedes"] if not s["es_yog"])
        comprobar(n == esp, f"sedes {pais} = {n} (esperado {esp})")

    # 2. atletas vs participaciones
    print("2. atletas.participaciones contra la coleccion participaciones")
    emb = next(db.atletas.aggregate([{"$group": {"_id": None, "p": {"$sum": {"$size": "$participaciones"}},
                                                 "r": {"$sum": {"$sum": {"$map": {"input": "$participaciones", "as": "x", "in": {"$size": "$$x.resultados"}}}}},
                                                 "np": {"$sum": "$n_participaciones"}}}], allowDiskUse=True))
    comprobar(emb["p"] == n_par, f"participaciones embebidas {emb['p']:,} = coleccion plana {n_par:,}")
    comprobar(emb["r"] == n_res, f"resultados embebidos {emb['r']:,} = coleccion plana {n_res:,}")
    comprobar(emb["np"] == n_par, f"suma de n_participaciones {emb['np']:,} = {n_par:,}")
    plano = {d["_id"]: d["n"] for d in db.participaciones.aggregate([{"$group": {"_id": "$atleta_id", "n": {"$sum": 1}}}], allowDiskUse=True)}
    dif = [(d["_id"], d["n_participaciones"], plano.get(d["_id"], 0))
           for d in db.atletas.find({}, {"n_participaciones": 1}) if plano.get(d["_id"], 0) != d["n_participaciones"]]
    comprobar(not dif, f"conteo de participaciones por atleta coincide para los {n_atl:,} atletas" + (f" (diferencias: {dif[:5]})" if dif else ""))
    mal_emb = db.atletas.count_documents({"$expr": {"$ne": [{"$size": "$participaciones"}, "$n_participaciones"]}})
    comprobar(mal_emb == 0, f"n_participaciones = tamano del arreglo en todos los atletas ({mal_emb} diferencias)")

    # 3. paises vs agregacion sobre participaciones
    print("3. paises.medallero contra agregacion sobre participaciones (todos los paises y entidades)")
    clave = {"$ifNull": ["$pais_id", {"$concat": ["NOC:", "$noc"]}]}
    agg = defaultdict(lambda: {"sin_yog": {"oro": 0, "plata": 0, "bronce": 0}, "yog": {"oro": 0, "plata": 0, "bronce": 0}})
    for d in db.participaciones.aggregate([
        {"$match": {"noc": {"$ne": None}}}, {"$unwind": "$resultados"}, {"$match": {"resultados.medalla": {"$ne": None}}},
        {"$group": {"_id": {"k": clave, "y": "$es_yog", "m": "$resultados.medalla"}, "n": {"$sum": 1}}}], allowDiskUse=True):
        agg[d["_id"]["k"]]["yog" if d["_id"]["y"] else "sin_yog"][d["_id"]["m"].lower()] = d["n"]
    agg_ev = defaultdict(lambda: {"sin_yog": {"oro": 0, "plata": 0, "bronce": 0}, "yog": {"oro": 0, "plata": 0, "bronce": 0}})
    for d in db.participaciones.aggregate([
        {"$match": {"noc": {"$ne": None}}}, {"$unwind": "$medallas"},
        {"$group": {"_id": {"k": clave, "y": "$es_yog", "e": "$edicion_id", "v": "$evento_id", "m": "$medallas", "n": "$noc"}}},
        {"$group": {"_id": {"k": "$_id.k", "y": "$_id.y", "m": "$_id.m"}, "n": {"$sum": 1}}}], allowDiskUse=True):
        agg_ev[d["_id"]["k"]]["yog" if d["_id"]["y"] else "sin_yog"][d["_id"]["m"].lower()] = d["n"]
    malos, n_docs = [], 0
    for d in db.paises.find({}, {"medallero": 1, "medallero_por_evento": 1, "nombre": 1}):
        n_docs += 1
        for campo, fuente in (("medallero", agg), ("medallero_por_evento", agg_ev)):
            esp = fuente[d["_id"]] if d["_id"] in fuente else {"sin_yog": {"oro": 0, "plata": 0, "bronce": 0}, "yog": {"oro": 0, "plata": 0, "bronce": 0}}
            doc = d[campo]
            tot = {k: esp["sin_yog"][k] + esp["yog"][k] for k in ("oro", "plata", "bronce")}
            if doc["sin_yog"] != esp["sin_yog"] or doc["yog"] != esp["yog"] or doc["total"] != tot:
                malos.append((d["nombre"], campo))
    comprobar(not malos, f"medallero y medallero_por_evento coinciden con la agregacion en {n_docs} paises/entidades" + (f" (diferencias: {malos[:5]})" if malos else ""))
    sin_doc = [k for k in agg if db.paises.count_documents({"_id": k}) == 0]
    comprobar(not sin_doc, f"todo NOC con medallas pertenece a algun pais o entidad (sin documento: {sin_doc[:5]})")

    # 5. Paris 2024 por evento
    print("5. Paris 2024")
    por_ev = {"Oro": set(), "Plata": set(), "Bronce": set()}
    for d in db.participaciones.aggregate([{"$match": {"anio": 2024, "tipo": "Verano"}}, {"$unwind": "$medallas"},
                                           {"$group": {"_id": {"v": "$evento_id", "m": "$medallas", "n": "$noc"}}}]):
        por_ev[d["_id"]["m"]].add((d["_id"]["v"], d["_id"]["n"]))
    obt = {m: len(s) for m, s in por_ev.items()}
    comprobar(obt == ESPERADO_PARIS_EVENTO, f"medallas por evento Paris 2024 = {obt} (oficial {ESPERADO_PARIS_EVENTO})")

    # 6. alias
    print("6. Alias de atletas fusionados")
    n_alias = next(db.atletas.aggregate([{"$group": {"_id": None, "n": {"$sum": {"$size": "$alias"}}}}]))["n"]
    comprobar(n_alias == 394, f"alias cargados = {n_alias} (fusiones registradas: 394)")
    for nombre, esperado in (("shiyu lu", "Lu Shiyu"), ("van sharon", "Sharon van Rouwendaal"), ("kate foo", "Kate Foo Kune"), ("shun wang", "Wang Shun")):
        d = db.atletas.find_one({"claves": nombre}, {"nombre_usado": 1})
        comprobar(d is not None and d["nombre_usado"] == esperado, f"'{nombre}' se resuelve a {d['nombre_usado'] if d else None} (esperado {esperado})")
    fin = datetime.now()
    log.append(f"Resultado: {'OK' if not fallos else str(len(fallos)) + ' FALLAS'} | fin {fin:%Y-%m-%d %H:%M:%S} | duracion {time.perf_counter() - t0:.1f} s")
    print(log[-1])
    (RAIZ / "08_logs").mkdir(exist_ok=True)
    (RAIZ / "08_logs" / f"validar_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    raise SystemExit(1 if fallos else 0)


if __name__ == "__main__":
    main()
