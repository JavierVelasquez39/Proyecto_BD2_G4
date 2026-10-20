"""Fase C1: exporta la base PostgreSQL (ya corregida) a archivos JSON Lines para MongoDB.

Solo lectura. Genera en data/: atletas.jsonl, participaciones.jsonl, paises.jsonl,
ediciones.jsonl y deportes.jsonl. Las participaciones se leen en streaming (cursor del servidor,
agrupadas por atleta), sin cargar la tabla completa en memoria; solo se retienen en memoria las
tablas chicas y los acumuladores de medallero por pais.

Criterios que se conservan de la Fase 1:
  * Medallas "por atleta": una medalla por fila de RESULTADO (criterio de fn_pais_info). Campos principales.
  * Medallas "por evento": medallero_por_evento, conteo oficial = medallas distintas por
    (edicion, evento, medalla, NOC). Se etiqueta aparte en todas las salidas.
  * Un pais agrega todos sus NOC historicos (pais_id propio, o mismo nombre_region que un NOC del pais;
    asi URS y EUN van a Rusia aunque su pais_id sea NULL, igual que fn_noc_por_pais).
  * YOG se marca con es_yog; los consultores lo excluyen por defecto.
  * nombre_key = name_match_key() de la Fase 1: unidecode(espacios normalizados).casefold().
  * Los nombres originales de los atletas fusionados (atleta_fusion_log) viajan como alias,
    claves y tokens del atleta conservado.

Uso: python exportar_postgres.py [--dsn DSN] [--salida data]
"""
import argparse
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras
from text_unidecode import unidecode

DSN_DEFECTO = "postgresql://postgres:olimpiadas@localhost:55433/olimpiadas"
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
MEDALLAS = ("Oro", "Plata", "Bronce")
ORDEN_MEDALLA = {"Oro": 0, "Plata": 1, "Bronce": 2}


def normalize_ws(s):
    return re.sub(r"\s+", " ", str(s).replace("•", " ")).strip()


def name_match_key(s):
    """Misma logica que etl.py de la Fase 1."""
    if not isinstance(s, str):
        return s
    return unidecode(normalize_ws(s)).casefold()


def tokens_de(*nombres):
    t = set()
    for n in nombres:
        if n:
            t.update(re.findall(r"[a-z0-9]+", name_match_key(n)))
    return sorted(t)


def dump(o):
    return json.dumps(o, ensure_ascii=False, default=lambda x: float(x) if isinstance(x, Decimal) else str(x),
                      separators=(",", ":"))


def cuenta_vacia():
    return {"oro": 0, "plata": 0, "bronce": 0}


def sumar(cuenta, medalla):
    cuenta[medalla.lower()] += 1


class AcumPais:
    def __init__(self):
        self.med = {"sin_yog": cuenta_vacia(), "yog": cuenta_vacia()}
        self.med_ev = {"sin_yog": set(), "yog": set()}
        self.part = 0
        self.atletas = set()
        self.por_ed = defaultdict(lambda: {"participaciones": 0, "atletas": set(), "med": cuenta_vacia(), "ev": set()})
        self.por_dep = defaultdict(lambda: {"participaciones": 0, "med": cuenta_vacia(), "ev": set()})

    def agregar(self, p, medallas):
        k = "yog" if p["es_yog"] else "sin_yog"
        self.part += 1
        self.atletas.add(p["atleta_id"])
        e = self.por_ed[(p["anio"], p["tipo"])]
        e["participaciones"] += 1
        e["atletas"].add(p["atleta_id"])
        d = self.por_dep[(p["deporte"], p["es_yog"])]
        d["participaciones"] += 1
        for m in medallas:
            sumar(self.med[k], m)
            sumar(e["med"], m)
            sumar(d["med"], m)
            clave = (p["edicion_id"], p["evento_id"], m, p["noc"])
            self.med_ev[k].add(clave)
            e["ev"].add(clave)
            d["ev"].add(clave)


def por_evento(conjunto):
    c = cuenta_vacia()
    for (_, _, m, _) in conjunto:
        sumar(c, m)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN_DEFECTO)
    ap.add_argument("--salida", default=str(AQUI / "data"))
    args = ap.parse_args()
    inicio = datetime.now()
    t0 = time.perf_counter()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    log = [f"C1 exportar_postgres - inicio {inicio:%Y-%m-%d %H:%M:%S}"]
    p = lambda m: (print(m, flush=True), log.append(m))

    con = psycopg2.connect(args.dsn)
    con.set_session(readonly=True)
    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SET search_path TO olimpiadas")

    # --- tablas chicas -------------------------------------------------------
    cur.execute("SELECT pais_id, nombre FROM pais")
    paises = {r["pais_id"]: r["nombre"] for r in cur.fetchall()}
    cur.execute("SELECT codigo_noc, nombre_region, notas, pais_id FROM noc")
    nocs = {r["codigo_noc"]: dict(r) for r in cur.fetchall()}
    cur.execute("""SELECT o.edicion_id, o.anio, o.tipo, s.sede_id, s.ciudad, s.pais_id
                   FROM edicion_olimpica o LEFT JOIN sede s ON s.sede_id = o.sede_id ORDER BY o.anio, o.tipo""")
    ediciones = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT d.deporte_id, d.nombre, count(e.evento_id) AS n_eventos FROM deporte d LEFT JOIN evento e USING (deporte_id) GROUP BY 1, 2 ORDER BY 1")
    deportes = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT atleta_id, nombre_completo, nombre_usado, sexo, nacionalidad, fecha_nacimiento, ciudad_nacimiento, "
                "pais_nacimiento, fecha_fallecimiento FROM atleta")
    atletas = {r["atleta_id"]: dict(r) for r in cur.fetchall()}
    cur.execute("SELECT id_conservado, id_duplicado, nombre_original_duplicado, tipo FROM atleta_fusion_log ORDER BY id_duplicado")
    alias = defaultdict(list)
    for r in cur.fetchall():
        alias[r["id_conservado"]].append({"nombre": r["nombre_original_duplicado"], "tipo": r["tipo"], "id_duplicado": r["id_duplicado"]})
    p(f"Tablas chicas: {len(paises)} paises, {len(nocs)} NOC, {len(ediciones)} ediciones, {len(deportes)} deportes, "
      f"{len(atletas):,} atletas, {sum(len(v) for v in alias.values())} alias de fusion")

    # --- regla multi-NOC (igual que fn_noc_por_pais) ---------------------------
    regiones_de = defaultdict(set)
    for c, n in nocs.items():
        if n["pais_id"] is not None:
            regiones_de[n["pais_id"]].add(n["nombre_region"])
    noc_de_pais = defaultdict(list)
    pais_de_noc = {}
    for pid in paises:
        for c, n in sorted(nocs.items()):
            if n["pais_id"] == pid or n["nombre_region"] in regiones_de.get(pid, ()):
                noc_de_pais[pid].append(c)
    for pid, lista in noc_de_pais.items():
        for c in lista:
            if nocs[c]["pais_id"] == pid:
                pais_de_noc[c] = pid
    for pid, lista in noc_de_pais.items():
        for c in lista:
            pais_de_noc.setdefault(c, pid)
    sin_pais = sorted(c for c in nocs if c not in pais_de_noc)
    p(f"NOC atribuidos a un pais: {len(pais_de_noc)}; sin pais (entidades): {sin_pais}")

    # --- participaciones en streaming ------------------------------------------
    ed_por_id = {e["edicion_id"]: e for e in ediciones}
    sql = """
        SELECT p.participacion_id, p.atleta_id, p.edicion_id, o.anio, o.tipo, d.deporte_id, d.nombre AS deporte,
               ev.evento_id, ev.nombre AS evento, p.codigo_noc, p.equipo, p.edad, p.altura_cm, p.peso_kg,
               COALESCE(json_agg(json_build_object('lugar', r.lugar, 'empatado', r.empatado, 'medalla', r.medalla)
                                 ORDER BY r.resultado_id) FILTER (WHERE r.resultado_id IS NOT NULL), '[]'::json) AS resultados
        FROM participacion p
        JOIN edicion_olimpica o ON o.edicion_id = p.edicion_id
        JOIN evento ev ON ev.evento_id = p.evento_id
        JOIN deporte d ON d.deporte_id = ev.deporte_id
        LEFT JOIN resultado r ON r.participacion_id = p.participacion_id
        GROUP BY p.participacion_id, o.anio, o.tipo, d.deporte_id, d.nombre, ev.evento_id, ev.nombre
        ORDER BY p.atleta_id, o.anio, ev.nombre, p.participacion_id"""
    named = con.cursor(name="exp_part", cursor_factory=psycopg2.extras.DictCursor)
    named.itersize = 20000
    named.execute(sql)

    acum = defaultdict(AcumPais)  # clave: pais_id o "NOC:XXX"
    f_atl = open(salida / "atletas.jsonl", "w", encoding="utf-8")
    f_par = open(salida / "participaciones.jsonl", "w", encoding="utf-8")
    emitidos = set()
    n_part = n_res = n_atl = 0

    def clave_pais(noc):
        if noc is None:
            return None, None
        pid = pais_de_noc.get(noc)
        return (pid, pid) if pid is not None else (None, f"NOC:{noc}")

    def emitir_atleta(aid, parts):
        nonlocal n_atl
        a = atletas[aid]
        nombres = [a["nombre_usado"]] + [x["nombre"] for x in alias.get(aid, [])]
        claves = {name_match_key(n) for n in nombres if n}
        if a["nombre_completo"]:
            claves.add(name_match_key(a["nombre_completo"]))
        resumen = {"total": cuenta_vacia(), "sin_yog": cuenta_vacia(), "yog": cuenta_vacia()}
        for pp in parts:
            for r in pp["resultados"]:
                if r["medalla"]:
                    sumar(resumen["total"], r["medalla"])
                    sumar(resumen["yog" if pp["es_yog"] else "sin_yog"], r["medalla"])
        doc = {
            "_id": aid,
            "nombre_usado": a["nombre_usado"],
            "nombre_completo": a["nombre_completo"],
            "nombre_key": name_match_key(a["nombre_usado"]),
            "claves": sorted(claves),
            "tokens": tokens_de(a["nombre_usado"], a["nombre_completo"], *[x["nombre"] for x in alias.get(aid, [])]),
            "alias": alias.get(aid, []),
            "sexo": a["sexo"],
            "nacionalidad": a["nacionalidad"],
            "fecha_nacimiento": a["fecha_nacimiento"].isoformat() if a["fecha_nacimiento"] else None,
            "ciudad_nacimiento": a["ciudad_nacimiento"],
            "pais_nacimiento": a["pais_nacimiento"],
            "fecha_fallecimiento": a["fecha_fallecimiento"].isoformat() if a["fecha_fallecimiento"] else None,
            "deportes": sorted({pp["deporte"] for pp in parts}),
            "nocs": sorted({pp["noc"] for pp in parts if pp["noc"]}),
            "n_participaciones": len(parts),
            "resumen_medallas": resumen,
            "participaciones": parts,
        }
        f_atl.write(dump(doc) + "\n")
        emitidos.add(aid)
        n_atl += 1

    actual, buf = None, []
    for r in named:
        n_part += 1
        res = r["resultados"]
        n_res += len(res)
        pid, clave = clave_pais(r["codigo_noc"])
        ed = ed_por_id[r["edicion_id"]]
        es_yog = "YOG" in r["tipo"]
        medallas = [x["medalla"] for x in res if x["medalla"]]
        mejor = min(medallas, key=ORDEN_MEDALLA.get) if medallas else None
        part = {
            "participacion_id": r["participacion_id"], "atleta_id": r["atleta_id"], "edicion_id": r["edicion_id"],
            "anio": r["anio"], "tipo": r["tipo"], "es_yog": es_yog, "sede": ed["ciudad"],
            "deporte_id": r["deporte_id"], "deporte": r["deporte"], "evento_id": r["evento_id"], "evento": r["evento"],
            "noc": r["codigo_noc"], "pais_id": pid, "pais": paises.get(pid) if pid is not None else None,
            "equipo": r["equipo"], "edad": r["edad"],
            "altura_cm": float(r["altura_cm"]) if r["altura_cm"] is not None else None,
            "peso_kg": float(r["peso_kg"]) if r["peso_kg"] is not None else None,
            "resultados": res, "medalla": mejor, "medallas": medallas,
        }
        flat = dict(part)
        flat["_id"] = flat.pop("participacion_id")
        flat["atleta_nombre"] = atletas[r["atleta_id"]]["nombre_usado"]
        flat["atleta_nombre_key"] = name_match_key(atletas[r["atleta_id"]]["nombre_usado"])
        f_par.write(dump(flat) + "\n")
        if r["codigo_noc"] is not None:
            acum[clave if clave is not None else pid].agregar(part, medallas)
        if r["atleta_id"] != actual:
            if actual is not None:
                emitir_atleta(actual, buf)
            actual, buf = r["atleta_id"], []
        buf.append(part)
        if n_part % 50000 == 0:
            p(f"  {n_part:,} participaciones...")
    if actual is not None:
        emitir_atleta(actual, buf)
    sin_part = [aid for aid in atletas if aid not in emitidos]
    for aid in sin_part:
        emitir_atleta(aid, [])
    f_atl.close()
    f_par.close()
    p(f"Participaciones: {n_part:,} | resultados: {n_res:,} | atletas: {n_atl:,} (sin participaciones: {len(sin_part)})")

    # --- paises -----------------------------------------------------------------
    sedes_de = defaultdict(list)
    for e in ediciones:
        if e["pais_id"] is not None:
            sedes_de[e["pais_id"]].append({"anio": e["anio"], "tipo": e["tipo"], "es_yog": "YOG" in e["tipo"], "ciudad": e["ciudad"]})

    def doc_acum(a):
        return {
            "total": {k: a.med["sin_yog"][k] + a.med["yog"][k] for k in ("oro", "plata", "bronce")},
            "sin_yog": a.med["sin_yog"], "yog": a.med["yog"],
        }

    def doc_ev(a):
        t = por_evento(a.med_ev["sin_yog"] | a.med_ev["yog"])
        return {"total": t, "sin_yog": por_evento(a.med_ev["sin_yog"]), "yog": por_evento(a.med_ev["yog"])}

    def resto_doc(a):
        por_ed = []
        for (anio, tipo), e in sorted(a.por_ed.items()):
            por_ed.append({"anio": anio, "tipo": tipo, "es_yog": "YOG" in tipo, "participaciones": e["participaciones"],
                           "atletas": len(e["atletas"]), "por_atleta": e["med"], "por_evento": por_evento(e["ev"])})
        por_dep = []
        for (dep, yog), d in sorted(a.por_dep.items()):
            por_dep.append({"deporte": dep, "es_yog": yog, "participaciones": d["participaciones"], "por_atleta": d["med"],
                            "por_evento": por_evento(d["ev"])})
        return por_ed, por_dep

    n_pais = 0
    with open(salida / "paises.jsonl", "w", encoding="utf-8") as f:
        for pid, nombre in sorted(paises.items()):
            a = acum.get(pid, AcumPais())
            por_ed, por_dep = resto_doc(a)
            f.write(dump({
                "_id": pid, "tipo": "PAIS", "nombre": nombre, "nombre_key": name_match_key(nombre),
                "tokens": tokens_de(nombre),
                "nocs": [{"codigo": c, "nombre_region": nocs[c]["nombre_region"],
                          "categoria": "PAIS_ACTUAL" if nocs[c]["pais_id"] is not None else "ENTIDAD_HISTORICA_NO_ATRIBUIDA"}
                         for c in noc_de_pais.get(pid, [])],
                "sedes": sorted(sedes_de.get(pid, []), key=lambda s: (s["anio"], s["tipo"])),
                "total_participaciones": a.part, "total_atletas": len(a.atletas),
                "medallero": doc_acum(a), "medallero_por_evento": doc_ev(a),
                "por_edicion": por_ed, "por_deporte": por_dep,
            }) + "\n")
            n_pais += 1
        # entidades sin pais (NOC no atribuidos): se pueden consultar por nombre de region o codigo NOC
        for c in sin_pais:
            a = acum.get(f"NOC:{c}", AcumPais())
            por_ed, por_dep = resto_doc(a)
            nombre = nocs[c]["nombre_region"]
            f.write(dump({
                "_id": f"NOC:{c}", "tipo": "ENTIDAD", "nombre": nombre, "nombre_key": name_match_key(nombre),
                "tokens": tokens_de(nombre, c),
                "nocs": [{"codigo": c, "nombre_region": nombre, "categoria": "ENTIDAD_SIN_PAIS"}],
                "sedes": [], "total_participaciones": a.part, "total_atletas": len(a.atletas),
                "medallero": doc_acum(a), "medallero_por_evento": doc_ev(a),
                "por_edicion": por_ed, "por_deporte": por_dep,
            }) + "\n")
            n_pais += 1
    p(f"Paises/entidades: {n_pais}")

    with open(salida / "ediciones.jsonl", "w", encoding="utf-8") as f:
        for e in ediciones:
            f.write(dump({"_id": e["edicion_id"], "anio": e["anio"], "tipo": e["tipo"], "es_yog": "YOG" in e["tipo"],
                          "sede": {"sede_id": e["sede_id"], "ciudad": e["ciudad"], "pais_id": e["pais_id"],
                                   "pais": paises.get(e["pais_id"])}}) + "\n")
    with open(salida / "deportes.jsonl", "w", encoding="utf-8") as f:
        for d in deportes:
            f.write(dump({"_id": d["deporte_id"], "nombre": d["nombre"], "nombre_key": name_match_key(d["nombre"]),
                          "n_eventos": d["n_eventos"]}) + "\n")
    con.close()
    fin = datetime.now()
    p(f"Fin: {fin:%Y-%m-%d %H:%M:%S} | duracion {time.perf_counter() - t0:.1f} s")
    for n in ("atletas", "participaciones", "paises", "ediciones", "deportes"):
        p(f"  {n}.jsonl: {(salida / (n + '.jsonl')).stat().st_size / 1e6:,.1f} MB")
    (RAIZ / "08_logs").mkdir(exist_ok=True)
    (RAIZ / "08_logs" / f"exportar_postgres_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
