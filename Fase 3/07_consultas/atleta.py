"""Fase D1: consulta por atleta en MongoDB.

Uso: python atleta.py "Nombre" [--deporte X] [--pais X] [--anio N] [--incluir-yog] [--id N] [--explain]

Modos (igual que fn_atleta_info de la Fase 1):
  CANDIDATO          varios atletas con ese nombre: lista para elegir (usar --id)
  DETALLE            un atleta: datos, alias, medallas y todas sus participaciones y resultados
  SIN_COINCIDENCIAS  ningun atleta
La busqueda ignora acentos y mayusculas. Orden de busqueda: nombre usado, nombre completo o alias exacto;
si no hay, todas las palabras en cualquier orden (coincidencia parcial); si no, prefijo del nombre.
El detalle sale de UN solo documento de la coleccion atletas. Por defecto no incluye Juegos de la Juventud (YOG).
"""
import argparse
import sys

from comunes import (ETIQ_ATLETA, Cronometro, conectar, configurar_salida, encabezado, explicar, fold, med_txt,
                     trunca)

LIMITE_CANDIDATOS = 50
PROY_CANDIDATO = {"nombre_usado": 1, "nombre_completo": 1, "sexo": 1, "nacionalidad": 1, "fecha_nacimiento": 1,
                  "pais_nacimiento": 1, "deportes": 1, "nocs": 1, "resumen_medallas": 1, "alias": 1, "n_participaciones": 1}


def filtros_de_busqueda(texto):
    import re
    k = fold(texto)
    toks = re.findall(r"[a-z0-9]+", k)
    return [("exacta (nombre usado, completo o alias)", {"claves": k}),
            ("todas las palabras", {"tokens": {"$all": toks}} if toks else None),
            ("prefijo del nombre", {"nombre_key": {"$regex": "^" + re.escape(k)}})]


def buscar(db, texto, cron, explain):
    ok = True
    for nombre, filtro in filtros_de_busqueda(texto):
        if filtro is None:
            continue
        docs = cron.medir(lambda: list(db.atletas.find(filtro, PROY_CANDIDATO).limit(LIMITE_CANDIDATOS + 1)))
        if explain:
            ok &= explicar(db, "atletas", filtro, proyeccion=PROY_CANDIDATO, limit=LIMITE_CANDIDATOS + 1, etiqueta="busqueda por " + nombre)
        if docs:
            return nombre, docs, ok
    return None, [], ok


def resolver_pais(db, texto, cron):
    """Codigos NOC de un pais (multi-NOC) para el filtro --pais."""
    k = fold(texto)
    d = cron.medir(lambda: db.paises.find_one({"$or": [{"nombre_key": k}, {"nocs.codigo": texto.upper()}]}, {"nocs": 1, "nombre": 1}))
    if not d:
        d = cron.medir(lambda: db.paises.find_one({"nombre_key": {"$regex": "^" + __import__("re").escape(k)}}, {"nocs": 1, "nombre": 1}))
    return d


def mostrar_candidatos(docs, nombre_busqueda):
    mas = len(docs) > LIMITE_CANDIDATOS
    docs = docs[:LIMITE_CANDIDATOS]
    print(f"MODO: CANDIDATO | {len(docs)}{'+' if mas else ''} atletas coinciden ({nombre_busqueda}). Use --id para ver el detalle.")
    print(f"{'id':>7}  {'nombre':<34} {'sexo':<4} {'nacionalidad':<16} {'nacimiento':<11} {'deportes':<30} {'medallas':<12}")
    for d in docs:
        m = d["resumen_medallas"]["total"]
        nac = d["fecha_nacimiento"].strftime("%Y-%m-%d") if d.get("fecha_nacimiento") else "-"
        print(f"{d['_id']:>7}  {trunca(d['nombre_usado'], 34):<34} {d.get('sexo') or '-':<4} {trunca(d.get('nacionalidad'), 16):<16} {nac:<11} "
              f"{trunca(', '.join(d['deportes']), 30):<30} {m['oro']}/{m['plata']}/{m['bronce']}")
        if d.get("alias"):
            print(f"{'':>9}alias: {', '.join(a['nombre'] for a in d['alias'])}")


def mostrar_detalle(d, f, db, cron):
    print(f"MODO: DETALLE | atleta_id {d['_id']}")
    print(f"Nombre: {d['nombre_usado']}" + (f"  (completo: {d['nombre_completo']})" if d.get("nombre_completo") and d["nombre_completo"] != d["nombre_usado"] else ""))
    nac = d["fecha_nacimiento"].strftime("%Y-%m-%d") if d.get("fecha_nacimiento") else "-"
    fal = d["fecha_fallecimiento"].strftime("%Y-%m-%d") if d.get("fecha_fallecimiento") else None
    print(f"Sexo: {d.get('sexo') or '-'} | Nacionalidad: {d.get('nacionalidad') or '-'} | Nacimiento: {nac}"
          f"{' en ' + d['ciudad_nacimiento'] if d.get('ciudad_nacimiento') else ''}{', ' + d['pais_nacimiento'] if d.get('pais_nacimiento') else ''}"
          f"{' | Fallecimiento: ' + fal if fal else ''}")
    if d.get("alias"):
        print("Alias (nombres con que aparecia en otra fuente): " + ", ".join(a["nombre"] for a in d["alias"]))
    print(f"Deportes: {', '.join(d['deportes']) or '-'} | NOC: {', '.join(d['nocs']) or '-'}")

    # filtros
    partes = d["participaciones"]
    nocs_pais = None
    if f.pais:
        pd = resolver_pais(db, f.pais, cron)
        if not pd:
            print(f"AVISO: el pais '{f.pais}' no existe; el filtro --pais no devuelve participaciones.")
            nocs_pais = set()
        else:
            nocs_pais = {n["codigo"] for n in pd["nocs"]}
    dep = fold(f.deporte) if f.deporte else None
    sel = []
    for p in partes:
        if p["es_yog"] and not f.incluir_yog:
            continue
        if f.anio and p["anio"] != f.anio:
            continue
        if dep and not (fold(p["deporte"]) == dep or fold(p["deporte"]).startswith(dep)):
            continue
        if nocs_pais is not None and p["noc"] not in nocs_pais:
            continue
        sel.append(p)
    ocultas = sum(1 for p in partes if p["es_yog"]) if not f.incluir_yog else 0
    m = {"oro": 0, "plata": 0, "bronce": 0}
    for p in sel:
        for r in p["resultados"]:
            if r["medalla"]:
                m[r["medalla"].lower()] += 1
    filtrado = any([f.anio, f.deporte, f.pais])
    print(f"Medallas {'(participaciones mostradas) ' if filtrado else ''}{ETIQ_ATLETA}: {med_txt(m)}")
    if not filtrado:
        t = d["resumen_medallas"]
        print(f"   desglose: sin YOG {med_txt(t['sin_yog'])} | YOG {med_txt(t['yog'])}")
    print(f"Participaciones: {len(sel)}" + (f" ({ocultas} de Juegos de la Juventud ocultas; use --incluir-yog)" if ocultas else ""))
    if sel:
        print(f"{'año':<5} {'tipo':<11} {'sede':<14} {'deporte':<22} {'evento':<40} {'NOC':<4} {'equipo':<14} {'lugar':<6} medalla")
    for p in sel:
        for r in (p["resultados"] or [{"lugar": None, "empatado": False, "medalla": None}]):
            lugar = ("-" if r["lugar"] is None else str(r["lugar"])) + ("=" if r["empatado"] else "")
            print(f"{p['anio']:<5} {p['tipo']:<11} {trunca(p['sede'], 14):<14} {trunca(p['deporte'], 22):<22} {trunca(p['evento'], 40):<40} "
                  f"{p['noc'] or '-':<4} {trunca(p['equipo'], 14):<14} {lugar:<6} {r['medalla'] or ''}")


def main():
    configurar_salida()
    ap = argparse.ArgumentParser(description="Informacion de un atleta (MongoDB)")
    ap.add_argument("nombre", nargs="?", default="")
    ap.add_argument("--deporte")
    ap.add_argument("--pais")
    ap.add_argument("--anio", type=int)
    ap.add_argument("--incluir-yog", action="store_true", help="incluye Juegos Olimpicos de la Juventud")
    ap.add_argument("--id", type=int, help="atleta_id exacto (salta la busqueda por nombre)")
    ap.add_argument("--explain", action="store_true", help="muestra el plan de ejecucion de las consultas")
    f = ap.parse_args()
    if not f.nombre and f.id is None:
        ap.error("indique un nombre o --id")
    db = conectar()
    encabezado("CONSULTA POR ATLETA", {"nombre": f.nombre, "deporte": f.deporte, "pais": f.pais, "anio": f.anio,
                                       "incluir-yog": f.incluir_yog, "id": f.id})
    cron = Cronometro()
    ok = True
    if f.id is not None:
        docs = cron.medir(lambda: list(db.atletas.find({"_id": f.id}, PROY_CANDIDATO)))
        if f.explain:
            ok &= explicar(db, "atletas", {"_id": f.id}, etiqueta="busqueda por _id")
        modo_busqueda = "por id"
    else:
        modo_busqueda, docs, ok = buscar(db, f.nombre, cron, f.explain)
    if not docs:
        print("MODO: SIN_COINCIDENCIAS | ningun atleta coincide" + (f" con '{f.nombre}'" if f.nombre else ""))
    elif len(docs) > 1 and f.id is None:
        mostrar_candidatos(docs, modo_busqueda)
    else:
        d = cron.medir(lambda: db.atletas.find_one({"_id": docs[0]["_id"]}))
        if f.explain:
            ok &= explicar(db, "atletas", {"_id": docs[0]["_id"]}, etiqueta="detalle (un solo documento)")
        mostrar_detalle(d, f, db, cron)
    cron.pie()
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
