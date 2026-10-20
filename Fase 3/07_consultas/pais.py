"""Fase D2: consulta por pais en MongoDB.

Uso: python pais.py "Pais" [--anio N] [--deporte X] [--incluir-yog] [--detalle] [--pagina N] [--tam N] [--explain]

El resumen sale de UN documento de la coleccion paises (participaciones, medallas, anios, sedes, NOC).
Con --detalle se consulta la coleccion participaciones con indice y paginacion (sin $lookup ni agregaciones).
El pais se busca por nombre (ingles, convencion del Banco Mundial: "Russian Federation", "United States"),
por codigo NOC ("GER") o por prefijo; ignora acentos y mayusculas. Un pais agrega todos sus NOC historicos
(Alemania = GER, FRG, GDR, SAA). Por defecto no incluye Juegos de la Juventud (YOG).
Las dos cifras de medallas van etiquetadas: "por atleta" (criterio de la Fase 1) y "por evento" (oficial).
"""
import argparse
import re
import sys

from comunes import (ETIQ_ATLETA, ETIQ_EVENTO, Cronometro, conectar, configurar_salida, encabezado, explicar, fold,
                     med_txt, trunca)


def buscar_pais(db, texto, cron, explain):
    k = fold(texto)
    ok = True
    intentos = [("nombre exacto", {"nombre_key": k}),
                ("codigo NOC", {"nocs.codigo": texto.strip().upper()}),
                ("prefijo del nombre", {"nombre_key": {"$regex": "^" + re.escape(k)}}),
                ("todas las palabras", {"tokens": {"$all": re.findall(r"[a-z0-9]+", k)}})]
    for nombre, filtro in intentos:
        if not filtro or filtro.get("tokens", {}).get("$all") == []:
            continue
        docs = cron.medir(lambda: list(db.paises.find(filtro).limit(10)))
        if explain:
            ok &= explicar(db, "paises", filtro, limit=10, etiqueta="busqueda por " + nombre)
        if docs:
            docs.sort(key=lambda d: (len(d["nombre"]), d["tipo"] != "PAIS"))  # el nombre mas corto, como fn_noc_por_pais
            return nombre, docs, ok
    return None, [], ok


def fila_ed(e):
    return (f"{e['anio']:<5} {e['tipo']:<11} {e['participaciones']:>7} {e['atletas']:>7}  "
            f"{med_txt(e['por_atleta']):<34} {med_txt(e['por_evento'])}")


def main():
    configurar_salida()
    ap = argparse.ArgumentParser(description="Informacion de un pais (MongoDB)")
    ap.add_argument("pais")
    ap.add_argument("--anio", type=int)
    ap.add_argument("--deporte")
    ap.add_argument("--incluir-yog", action="store_true", help="incluye Juegos Olimpicos de la Juventud")
    ap.add_argument("--detalle", action="store_true", help="lista participaciones y resultados (paginado)")
    ap.add_argument("--pagina", type=int, default=1)
    ap.add_argument("--tam", type=int, default=40, help="filas por pagina del detalle")
    ap.add_argument("--explain", action="store_true")
    f = ap.parse_args()
    db = conectar()
    encabezado("CONSULTA POR PAIS", {"pais": f.pais, "anio": f.anio, "deporte": f.deporte, "incluir-yog": f.incluir_yog,
                                     "detalle": f.detalle, "pagina": f.pagina if f.detalle else None})
    cron = Cronometro()
    modo, docs, ok = buscar_pais(db, f.pais, cron, f.explain)
    if not docs:
        print(f"PAIS_NO_ENCONTRADO | '{f.pais}' no coincide con ningun pais ni NOC (use el nombre en ingles, p. ej. 'Germany')")
        cron.pie()
        sys.exit(0)
    d = docs[0]
    es_yog_ok = (lambda y: True) if f.incluir_yog else (lambda y: not y)
    dep = fold(f.deporte) if f.deporte else None
    dep_ok = (lambda n: fold(n) == dep or fold(n).startswith(dep)) if dep else (lambda n: True)

    print(f"{'PAIS' if d['tipo'] == 'PAIS' else 'ENTIDAD (NOC sin pais)'}: {d['nombre']} (id {d['_id']}, encontrado por {modo})"
          + (f" | otros candidatos: {', '.join(x['nombre'] for x in docs[1:])}" if len(docs) > 1 else ""))
    print("NOC asociados: " + ", ".join(f"{n['codigo']} [{n['categoria']}]" for n in d["nocs"]))

    # --- sedes ---
    sedes = [s for s in d["sedes"] if es_yog_ok(s["es_yog"])]
    if f.anio:
        sedes = [s for s in sedes if s["anio"] == f.anio]
    if d["tipo"] == "PAIS":
        if sedes:
            print(f"SEDE: {len(sedes)} edicion(es)" + (f" en {f.anio}" if f.anio else "") + ": "
                  + "; ".join(f"{s['anio']} {s['tipo']} ({s['ciudad']})" for s in sedes))
        elif any(es_yog_ok(s["es_yog"]) for s in d["sedes"]):
            print(f"SEDE: sin sede en {f.anio} (si fue sede en otros anios: " + ", ".join(str(s['anio']) for s in d["sedes"] if es_yog_ok(s['es_yog'])) + ")")
        else:
            print("NUNCA_SEDE: el pais nunca ha sido sede de unos Juegos" + ("" if f.incluir_yog else " (sin contar Juegos de la Juventud)"))

    # --- resumen: participaciones y medallas segun filtros ---
    n_pais_id = d["_id"] if d["tipo"] == "PAIS" else None
    filtro_part = {"pais_id": n_pais_id} if n_pais_id is not None else {"noc": {"$in": [n["codigo"] for n in d["nocs"]]}}
    if not f.incluir_yog:
        filtro_part["es_yog"] = False
    if f.anio:
        filtro_part["anio"] = f.anio
    if f.deporte:
        filtro_part["deporte"] = {"$in": [x["deporte"] for x in d["por_deporte"] if dep_ok(x["deporte"])]}

    print()
    if not (f.anio or f.deporte):
        m, me = d["medallero"], d["medallero_por_evento"]
        k = "total" if f.incluir_yog else "sin_yog"
        print(f"RESUMEN{'' if f.incluir_yog else ' (sin YOG)'}: {sum(1 for e in d['por_edicion'] if es_yog_ok(e['es_yog']))} ediciones con participacion | "
              f"{d['total_participaciones']:,} participaciones totales | {d['total_atletas']:,} atletas distintos (total historico)")
        print(f"MEDALLAS {ETIQ_ATLETA}: {med_txt(m[k])}")
        print(f"MEDALLAS {ETIQ_EVENTO}: {med_txt(me[k])}")
        if not f.incluir_yog:
            print(f"   (YOG aparte: por atleta {med_txt(m['yog'])}; por evento {med_txt(me['yog'])})")
    elif f.anio and not f.deporte:
        eds = [e for e in d["por_edicion"] if e["anio"] == f.anio and es_yog_ok(e["es_yog"])]
        if not eds:
            print(f"El pais no participo en {f.anio}" + ("" if f.incluir_yog else " (sin contar YOG)"))
        for e in eds:
            print(f"EDICION {e['anio']} {e['tipo']}: {e['participaciones']:,} participaciones, {e['atletas']:,} atletas")
            print(f"  MEDALLAS {ETIQ_ATLETA}: {med_txt(e['por_atleta'])}")
            print(f"  MEDALLAS {ETIQ_EVENTO}: {med_txt(e['por_evento'])}")
    elif f.deporte and not f.anio:
        ds = [x for x in d["por_deporte"] if dep_ok(x["deporte"]) and es_yog_ok(x["es_yog"])]
        if not ds:
            print(f"Sin participaciones en el deporte '{f.deporte}'")
        tot_p = sum(x["participaciones"] for x in ds)
        tot = {c: sum(x["por_atleta"][c] for x in ds) for c in ("oro", "plata", "bronce")}
        tot_e = {c: sum(x["por_evento"][c] for x in ds) for c in ("oro", "plata", "bronce")}
        print(f"DEPORTE '{f.deporte}': {tot_p:,} participaciones en {', '.join(sorted({x['deporte'] for x in ds})) or '-'}")
        print(f"  MEDALLAS {ETIQ_ATLETA}: {med_txt(tot)}")
        print(f"  MEDALLAS {ETIQ_EVENTO}: {med_txt(tot_e)}")
    else:  # anio + deporte: consulta indexada y acotada sobre participaciones
        proy = {"atleta_id": 1, "medallas": 1, "resultados.medalla": 1, "edicion_id": 1, "evento_id": 1, "noc": 1}
        rows = cron.medir(lambda: list(db.participaciones.find(filtro_part, proy)))
        if f.explain:
            ok &= explicar(db, "participaciones", filtro_part, proyeccion=proy, etiqueta="resumen anio+deporte")
        m = {"oro": 0, "plata": 0, "bronce": 0}
        ev = set()
        for r in rows:
            for x in r["medallas"]:
                m[x.lower()] += 1
                ev.add((r["edicion_id"], r["evento_id"], x, r["noc"]))
        me = {"oro": 0, "plata": 0, "bronce": 0}
        for (_, _, x, _) in ev:
            me[x.lower()] += 1
        print(f"FILTRO anio={f.anio}, deporte='{f.deporte}': {len(rows):,} participaciones, {len({r['atleta_id'] for r in rows}):,} atletas")
        print(f"  MEDALLAS {ETIQ_ATLETA}: {med_txt(m)}")
        print(f"  MEDALLAS {ETIQ_EVENTO}: {med_txt(me)}")

    # --- tablas por edicion y deporte (del documento del pais) ---
    if not f.detalle:
        eds = [e for e in d["por_edicion"] if es_yog_ok(e["es_yog"]) and (not f.anio or e["anio"] == f.anio)]
        if eds and not f.deporte:
            print(f"\nPARTICIPACION POR EDICION ({len(eds)}):")
            print(f"{'año':<5} {'tipo':<11} {'partic.':>7} {'atletas':>7}  {'medallas por atleta':<34} medallas por evento")
            for e in eds:
                print(fila_ed(e))
        ds = [x for x in d["por_deporte"] if es_yog_ok(x["es_yog"]) and dep_ok(x["deporte"])]
        if ds and not f.anio:
            ds.sort(key=lambda x: (-(x["por_atleta"]["oro"] * 1000 + x["por_atleta"]["plata"] * 10 + x["por_atleta"]["bronce"]), -x["participaciones"]))
            print(f"\nDEPORTES ({len(ds)}; se muestran {min(len(ds), 15)}, ordenados por medallas):")
            for x in ds[:15]:
                print(f"  {trunca(x['deporte'], 34):<34} {x['participaciones']:>7,} partic. | por atleta {med_txt(x['por_atleta'])}")
    else:
        pag, tam = max(f.pagina, 1), max(f.tam, 1)
        orden = [("anio", 1)]
        total = cron.medir(lambda: db.participaciones.count_documents(filtro_part))
        rows = cron.medir(lambda: list(db.participaciones.find(filtro_part).sort(orden).skip((pag - 1) * tam).limit(tam).allow_disk_use(True)))
        if f.explain:
            ok &= explicar(db, "participaciones", filtro_part, sort=orden, limit=tam, etiqueta="detalle paginado")
        print(f"\nDETALLE: {total:,} participaciones | pagina {pag} de {max((total + tam - 1) // tam, 1)} ({tam} por pagina; --pagina N para avanzar)")
        print(f"{'año':<5} {'tipo':<11} {'deporte':<22} {'evento':<36} {'NOC':<4} {'atleta':<26} {'lugar':<6} medalla")
        for p in rows:
            for r in (p["resultados"] or [{"lugar": None, "empatado": False, "medalla": None}]):
                lugar = ("-" if r["lugar"] is None else str(r["lugar"])) + ("=" if r["empatado"] else "")
                print(f"{p['anio']:<5} {p['tipo']:<11} {trunca(p['deporte'], 22):<22} {trunca(p['evento'], 36):<36} {p['noc'] or '-':<4} "
                      f"{trunca(p['atleta_nombre'], 26):<26} {lugar:<6} {r['medalla'] or ''}")
    cron.pie()
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
