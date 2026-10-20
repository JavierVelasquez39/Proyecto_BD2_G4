"""Comparacion cruzada Postgres (fn_atleta_info, fn_pais_info) contra MongoDB (atleta.py, pais.py). Solo lectura.

Para cada entrada se ejecuta la funcion de Postgres de la Fase 1 y el script de consulta de MongoDB (como proceso real,
leyendo su salida) y se comparan: modo, candidatos, participaciones (fila por fila en atletas), medallas por atleta,
medallas por evento, NOC asociados y sedes. Las diferencias NO se corrigen: se reportan. Una diferencia esperada por
diseno (alias, entidades sin pais, busqueda parcial) se declara en la entrada y se etiqueta aparte.

Uso: python comparar_postgres_mongo.py
Salida: comparacion_postgres_mongo_<fecha>.md en esta carpeta y bitacora en 08_logs/.
"""
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
CONSULTAS = RAIZ / "07_consultas"
DSN = "postgresql://postgres:olimpiadas@localhost:55433/olimpiadas"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def trunca(s, n):
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[: n - 1] + "~"


# (tipo, argumentos, parametros, motivo de diferencia esperada o None)
ATL = "atleta"
PAI = "pais"
ENTRADAS = [
    (ATL, "Michael Phelps", {}, None), (ATL, "Usain Bolt", {}, None), (ATL, "Simone Biles", {}, None),
    (ATL, "Katie Ledecky", {}, None), (ATL, "Pawel Fajdek", {}, None), (ATL, "Summer McIntosh", {}, None),
    (ATL, "Shun Wang", {}, "alias de un atleta fusionado (fase 3): solo MongoDB lo resuelve"), (ATL, "Wang Shun", {}, None), (ATL, "Jack Robinson", {}, None), (ATL, "Jordan Thompson", {}, None),
    (ATL, "Jack Robinson", {"id": 6939}, None), (ATL, "Lotte Kopecky", {}, None), (ATL, "Kristen Faulkner", {}, None),
    (ATL, "Sharon van Rouwendaal", {}, None),
    (ATL, "Shiyu Lu", {}, "alias de un atleta fusionado: solo MongoDB lo resuelve (la funcion de Postgres busca nombre usado y completo)"),
    (ATL, "van Sharon", {}, "alias de un atleta fusionado: solo MongoDB lo resuelve"),
    (ATL, "Kate Foo", {}, None),
    (ATL, "Mariana Avitia", {}, None), (ATL, "Mariana Avitia", {"incluir_yog": True}, None),
    (ATL, "Michael Phelps", {"deporte": "Swimming (Aquatics)", "anio": 2008}, None),
    (ATL, "Katie Ledecky", {"pais": "United States"}, None),
    (ATL, "Pawel Fajdek", {"deporte": "Athletics", "anio": 2024}, None),
    (ATL, "Fajdek", {}, "busqueda parcial: Postgres usa subcadena (LIKE) y MongoDB palabras completas o prefijo; pueden diferir los candidatos"),
    (ATL, "Nadie Inexistente", {}, None),
    (PAI, "Germany", {}, None), (PAI, "Russian Federation", {}, None), (PAI, "United States", {}, None),
    (PAI, "France", {}, None), (PAI, "Guatemala", {"detalle": True}, None), (PAI, "China", {}, None),
    (PAI, "Japan", {}, None), (PAI, "Czechia", {}, None), (PAI, "Serbia", {}, None), (PAI, "Mexico", {}, None),
    (PAI, "Germany", {"anio": 1972}, None), (PAI, "Germany", {"anio": 1972, "detalle": True}, None), (PAI, "Serbia", {"detalle": True}, None), (PAI, "Germany", {"incluir_yog": True}, None),
    (PAI, "United States", {"anio": 2024, "deporte": "Swimming (Aquatics)"}, None),
    (PAI, "France", {"deporte": "Fencing"}, None),
    (PAI, "Taiwan", {}, "entidad sin pais (NOC TPE): MongoDB la ofrece como entidad; la funcion de Postgres responde PAIS_NO_ENCONTRADO"),
    (PAI, "Wakanda", {}, None),
]


def comando(tipo, arg, p):
    c = [sys.executable, str(CONSULTAS / (tipo + ".py")), arg]
    if p.get("deporte"): c += ["--deporte", p["deporte"]]
    if p.get("anio"): c += ["--anio", str(p["anio"])]
    if p.get("pais"): c += ["--pais", p["pais"]]
    if p.get("id"): c += ["--id", str(p["id"])]
    if p.get("incluir_yog"): c += ["--incluir-yog"]
    if p.get("detalle"): c += ["--detalle", "--tam", "100000"]
    return c


def ms_mongo(salida):
    m = re.search(r"consultas a MongoDB ([\d.]+) ms", salida)
    return float(m.group(1)) if m else None


def medallas_en(texto):
    m = re.findall(r"oro (\d+) / plata (\d+) / bronce (\d+)", texto)
    return m


# ------------------------------------------------------------------ atletas
def pg_atleta(cur, arg, p):
    cur.execute("SELECT * FROM olimpiadas.fn_atleta_info(%s, %s, %s, %s, %s::smallint, %s)",
                (arg, p.get("id"), p.get("deporte"), p.get("pais"), p.get("anio"), bool(p.get("incluir_yog"))))
    cols = [d[0] for d in cur.description]
    filas = [dict(zip(cols, r)) for r in cur.fetchall()]
    modo = filas[0]["modo"]
    if modo == "SIN_COINCIDENCIAS":
        return {"modo": modo}
    if modo == "CANDIDATO":
        return {"modo": modo, "ids": sorted(f["atleta_id"] for f in filas)}
    reales = [f for f in filas if f["edicion_anio"] is not None]
    filas_t = sorted((f["edicion_anio"], f["edicion_tipo"], trunca(f["deporte_nombre"], 22), trunca(f["evento_nombre"], 40),
                      f["codigo_noc"] or "-", trunca(f["equipo"], 14),
                      ("-" if f["lugar"] is None else str(f["lugar"])) + ("=" if f["empatado"] else ""), f["medalla"] or "") for f in reales)
    distintas = {(f["edicion_anio"], f["edicion_tipo"], f["deporte_nombre"], f["evento_nombre"]) for f in reales}
    med = {"oro": 0, "plata": 0, "bronce": 0}
    for f in reales:
        if f["medalla"]:
            med[f["medalla"].lower()] += 1
    return {"modo": modo, "id": filas[0]["atleta_id"], "participaciones": len(distintas), "medallas": med, "filas": filas_t}


def mongo_atleta(salida):
    modo = re.search(r"MODO: (\w+)", salida)
    if not modo:
        return {"modo": "?"}
    modo = modo.group(1)
    if modo == "SIN_COINCIDENCIAS":
        return {"modo": modo}
    lineas = salida.splitlines()
    if modo == "CANDIDATO":
        ids = sorted(int(m.group(1)) for l in lineas if (m := re.match(r"^\s*(\d+)\s{2}\S", l)))
        return {"modo": modo, "ids": ids}
    mid = int(re.search(r"atleta_id (\d+)", salida).group(1))
    n = int(re.search(r"^Participaciones: (\d+)", salida, re.M).group(1))
    mm = medallas_en(next(l for l in lineas if l.startswith("Medallas")))[0]
    filas = []
    en_tabla = False
    for l in lineas:
        if l.startswith("año "):
            en_tabla = True
            continue
        if l.startswith("-" * 20):
            en_tabla = False
        if en_tabla and re.match(r"^\d{4} ", l):
            filas.append((int(l[0:5]), l[6:17].strip(), l[33:55].strip(), l[56:96].strip(), l[97:101].strip(),
                          l[102:116].strip(), l[117:123].strip(), l[124:].strip()))
    return {"modo": modo, "id": mid, "participaciones": n, "medallas": dict(zip(("oro", "plata", "bronce"), map(int, mm))),
            "filas": sorted(filas)}


def normaliza_fila(f):
    return (f[0], f[1], f[2].strip(), f[3].strip(), f[4], f[5].strip(), f[6], f[7])


# ------------------------------------------------------------------ paises
def pg_pais(cur, arg, p):
    cur.execute("SELECT * FROM olimpiadas.fn_pais_info(%s, %s::smallint, %s, %s)",
                (arg, p.get("anio"), p.get("deporte"), bool(p.get("incluir_yog"))))
    cols = [d[0] for d in cur.description]
    filas = [dict(zip(cols, r)) for r in cur.fetchall()]
    sec = {}
    for f in filas:
        sec.setdefault(f["seccion"], []).append(f)
    if "PAIS_NO_ENCONTRADO" in sec:
        return {"modo": "PAIS_NO_ENCONTRADO"}
    part = sec.get("PARTICIPACION", [])
    med = {"oro": 0, "plata": 0, "bronce": 0}
    for f in sec.get("RESUMEN_MEDALLAS", []):
        med[f["medalla"].lower()] = int(f["cantidad"])
    ev = set()
    for f in part:
        if f["medalla"]:
            ev.add((f["edicion_anio"], f["edicion_tipo"], f["deporte_nombre"], f["evento_nombre"], f["codigo_noc"], f["medalla"]))
    me = {"oro": 0, "plata": 0, "bronce": 0}
    for e in ev:
        me[e[5].lower()] += 1
    distintas = {(f["atleta_id"], f["edicion_anio"], f["edicion_tipo"], f["deporte_nombre"], f["evento_nombre"]) for f in part}
    sedes = sorted((f["edicion_anio"], f["edicion_tipo"], f["sede_ciudad"]) for f in sec.get("SEDE", []))
    filas_d = sorted((f["edicion_anio"], f["edicion_tipo"], trunca(f["deporte_nombre"], 22), trunca(f["evento_nombre"], 36),
                      f["codigo_noc"] or "-", trunca(f["nombre_atleta"], 26),
                      ("-" if f["lugar"] is None else str(f["lugar"])) + ("=" if f["empatado"] else ""), f["medalla"] or "") for f in part)
    return {"modo": "PAIS", "nocs": sorted(f["codigo_noc"] for f in sec.get("NOC_ASOCIADO", [])), "medallas": med, "por_evento": me,
            "participaciones": len(distintas), "sedes": sedes, "nunca_sede": "NUNCA_SEDE" in sec, "filas": filas_d}


def mongo_pais(salida, p):
    if "PAIS_NO_ENCONTRADO" in salida:
        return {"modo": "PAIS_NO_ENCONTRADO"}
    nocs = re.search(r"NOC asociados: (.*)", salida).group(1)
    nocs = sorted(re.findall(r"([A-Z0-9]{3}) \[", nocs))
    sedes, nunca = [], "NUNCA_SEDE" in salida
    m = re.search(r"^SEDE: .*? edicion\(es\)[^:]*: (.*)$", salida, re.M)
    if m:
        sedes = sorted((int(a), b, c) for a, b, c in re.findall(r"(\d{4}) ([\w-]+) \(([^)]*)\)", m.group(1)))
    por_atl = [l for l in salida.splitlines() if "MEDALLAS por atleta" in l]
    por_evt = [l for l in salida.splitlines() if "MEDALLAS por evento" in l]

    def suma(lineas):
        t = [0, 0, 0]
        for l in lineas:
            for g in medallas_en(l.split("):", 1)[-1])[:1]:
                t = [t[i] + int(g[i]) for i in range(3)]
        return dict(zip(("oro", "plata", "bronce"), t))
    r = {"modo": "PAIS", "nocs": nocs, "medallas": suma(por_atl), "por_evento": suma(por_evt), "sedes": sedes, "nunca_sede": nunca}
    mm = re.search(r"DETALLE: ([\d,]+) participaciones", salida)
    if mm:
        r["participaciones"] = int(mm.group(1).replace(",", ""))
        filas, en = [], False
        for l in salida.splitlines():
            if l.startswith("año "):
                en = True
                continue
            if l.startswith("-" * 20):
                en = False
            if en and re.match(r"^\d{4} ", l):
                filas.append((int(l[0:5]), l[6:17].strip(), l[18:40].strip(), l[41:77].strip(), l[78:82].strip(), l[83:109].strip(), l[110:116].strip(), l[117:].strip()))
        r["filas"] = sorted(filas)
    return r


def comparar(pg, mg, p, tipo):
    difs = []
    if pg["modo"] != mg["modo"]:
        return [f"modo: Postgres {pg['modo']} / MongoDB {mg['modo']}"]
    modo = pg["modo"]
    if modo == "CANDIDATO":
        if pg["ids"] != mg["ids"]:
            difs.append(f"candidatos: Postgres {pg['ids'][:12]} / MongoDB {mg['ids'][:12]}")
    elif tipo == ATL and modo == "DETALLE":
        if pg["id"] != mg["id"]: difs.append(f"atleta_id: {pg['id']} / {mg['id']}")
        if pg["participaciones"] != mg["participaciones"]: difs.append(f"participaciones: {pg['participaciones']} / {mg['participaciones']}")
        if pg["medallas"] != mg["medallas"]: difs.append(f"medallas por atleta: {pg['medallas']} / {mg['medallas']}")
        a, b = pg["filas"], [normaliza_fila(f) for f in mg["filas"]]
        if a != b:
            solo_pg = [f for f in a if f not in b][:3]
            solo_mg = [f for f in b if f not in a][:3]
            difs.append(f"filas de participacion: {len(a)} / {len(b)}; solo Postgres {solo_pg}; solo MongoDB {solo_mg}")
    elif modo == "PAIS":
        if pg["nocs"] != mg["nocs"]: difs.append(f"NOC: {pg['nocs']} / {mg['nocs']}")
        if pg["medallas"] != mg["medallas"]: difs.append(f"medallas por atleta: {pg['medallas']} / {mg['medallas']}")
        if pg["por_evento"] != mg["por_evento"]: difs.append(f"medallas por evento: {pg['por_evento']} / {mg['por_evento']}")
        if not p.get("anio"):  # la funcion de Postgres no filtra sedes por anio
            if pg["sedes"] != mg["sedes"] or pg["nunca_sede"] != mg["nunca_sede"]:
                difs.append(f"sedes: Postgres {pg['sedes']} (nunca={pg['nunca_sede']}) / MongoDB {mg['sedes']} (nunca={mg['nunca_sede']})")
        if "participaciones" in mg:
            if pg["participaciones"] != mg["participaciones"]: difs.append(f"participaciones: {pg['participaciones']} / {mg['participaciones']}")
            if pg["filas"] != mg["filas"]: difs.append(f"filas de detalle: {len(pg['filas'])} / {len(mg['filas'])}")
    return difs


def resumen(r, tipo):
    if r["modo"] in ("SIN_COINCIDENCIAS", "PAIS_NO_ENCONTRADO"):
        return r["modo"]
    if r["modo"] == "CANDIDATO":
        return f"CANDIDATO {len(r['ids'])} atletas"
    if tipo == ATL:
        m = r["medallas"]
        return f"DETALLE id {r['id']}, {r['participaciones']} part., medallas {m['oro']}/{m['plata']}/{m['bronce']}"
    m, e = r["medallas"], r["por_evento"]
    return (f"{len(r['nocs'])} NOC, por atleta {m['oro']}/{m['plata']}/{m['bronce']}, por evento {e['oro']}/{e['plata']}/{e['bronce']}, "
            f"sedes {'nunca' if r['nunca_sede'] else len(r['sedes'])}" + (f", {r['participaciones']} part." if "participaciones" in r else ""))


def main():
    inicio = datetime.now()
    t0 = time.perf_counter()
    con = psycopg2.connect(DSN)
    con.set_session(readonly=True)
    cur = con.cursor()
    cur.execute("SET search_path TO olimpiadas")
    filas_md, n_igual = [], {"IGUAL": 0, "ESPERADA": 0, "DIFERENCIA": 0}
    detalle_dif = []
    for i, (tipo, arg, p, esperada) in enumerate(ENTRADAS, 1):
        cmd = comando(tipo, arg, p)
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=CONSULTAS)
        salida = r.stdout
        if r.returncode not in (0,):
            pg = {"modo": "?"}
            difs = [f"el script de MongoDB termino con codigo {r.returncode}: {r.stderr.strip()[-200:]}"]
            mg = {"modo": "ERROR"}
        else:
            pg = pg_atleta(cur, arg, p) if tipo == ATL else pg_pais(cur, arg, p)
            mg = mongo_atleta(salida) if tipo == ATL else mongo_pais(salida, p)
            difs = comparar(pg, mg, p, tipo)
        estado = "IGUAL" if not difs else ("ESPERADA" if esperada else "DIFERENCIA")
        n_igual[estado] += 1
        params = " ".join(f"--{k.replace('_', '-')} {v}" if v is not True else f"--{k.replace('_', '-')}" for k, v in p.items())
        etiqueta = {"IGUAL": "IGUAL", "ESPERADA": "DIFERENCIA ESPERADA", "DIFERENCIA": "**DIFERENCIA**"}[estado]
        filas_md.append(f"| {i} | {tipo}.py `{arg}` {params} | {resumen(pg, tipo) if pg['modo'] != '?' else '-'} | {resumen(mg, tipo) if mg['modo'] not in ('?', 'ERROR') else mg['modo']} | {etiqueta} | {ms_mongo(salida) or '-'} |")
        if difs:
            detalle_dif.append(f"**{i}. {tipo}.py `{arg}` {params}** ({'esperada: ' + esperada if esperada else 'NO esperada'})\n" + "\n".join(f"- {d}" for d in difs))
        print(f"{i:>2}. {estado:<10} {tipo}.py {arg} {params}")
    fin = datetime.now()
    md = [f"# Comparacion cruzada Postgres vs MongoDB", "",
          f"Ejecutada el {inicio:%Y-%m-%d %H:%M:%S} (fin {fin:%H:%M:%S}, {time.perf_counter() - t0:.0f} s). Postgres: `fn_atleta_info` y `fn_pais_info` de la Fase 1 sobre la base corregida; MongoDB: `atleta.py` y `pais.py` ejecutados como procesos.",
          "Se comparan modo, candidatos, participaciones (fila por fila en atletas), medallas por atleta, medallas por evento (calculadas en Postgres como medallas distintas por edicion, evento y NOC a partir de las filas de participacion), NOC y sedes.", "",
          f"**Resultado: {n_igual['IGUAL']} iguales, {n_igual['ESPERADA']} con diferencia esperada por diseno, {n_igual['DIFERENCIA']} diferencias no esperadas** de {len(ENTRADAS)} entradas.", "",
          "| # | Consulta | Postgres | MongoDB | Resultado | MongoDB (ms) |", "|---|---|---|---|---|---:|"] + filas_md
    if detalle_dif:
        md += ["", "## Detalle de las diferencias", ""] + detalle_dif
    ruta = AQUI / f"comparacion_postgres_mongo_{inicio:%Y-%m-%d_%H%M%S}.md"
    ruta.write_text("\n".join(md) + "\n", encoding="utf-8")
    (RAIZ / "08_logs" / f"comparar_postgres_mongo_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nIGUAL {n_igual['IGUAL']} | ESPERADA {n_igual['ESPERADA']} | DIFERENCIA {n_igual['DIFERENCIA']} | {ruta.name}")
    sys.exit(1 if n_igual["DIFERENCIA"] else 0)


if __name__ == "__main__":
    main()
