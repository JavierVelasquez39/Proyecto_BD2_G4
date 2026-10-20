"""B2: busca atletas duplicados por nombre mal parseado (solo lectura).

Busca, entre los atletas creados desde la fuente 3 (atleta_id > 145500, es decir
los "nuevos" de Paris 2024) y todos los demas atletas, pares donde el nombre es
la misma persona escrita de otra forma:
  orden_invertido : mismos tokens en otro orden ("McINTOSH Summer" / "Summer McIntosh")
  particulas      : iguales al quitar particulas (van, de, da, di, del, von, mc, mac...)
  subconjunto     : los tokens de uno estan contenidos en el otro, >= 2 tokens
                    ("Kate Foo" / "Kate Foo Kune", "van Sharon" / "Sharon van Rouwendaal")
Para cada par calcula evidencia (sexo, NOC en comun, deporte en comun, anios,
fallecimiento, choque de evento en 2024) y un nivel de confianza.
NO modifica la base. Escribe b2_pares_candidatos.csv y una bitacora en 08_logs/.

Uso: python b2_candidatos_duplicados.py [--dsn DSN]
"""
import argparse
import csv
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import psycopg2
from text_unidecode import unidecode

DSN_DEFECTO = "postgresql://postgres:olimpiadas@localhost:55433/olimpiadas"
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
MAX_ID_F1 = 145500
PARTICULAS = {"van", "von", "de", "da", "di", "del", "della", "der", "den", "du", "le", "la", "el", "al",
              "dos", "das", "do", "bin", "ben", "ibn", "mc", "mac", "st", "ter", "ten", "het", "op", "y"}


def tokens(nombre):
    s = unidecode(nombre or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\bmc\s+", "mc", s)  # "mc intosh" -> "mcintosh"
    return [t for t in s.split() if t]


def sin_particulas(tk):
    return [t for t in tk if t not in PARTICULAS]


def tipo_coincidencia(ta, tb):
    sa, sb = set(ta), set(tb)
    if sorted(ta) == sorted(tb):
        return "orden_invertido" if ta != tb else None  # igual y mismo orden: ya lo ve el emparejamiento normal
    pa, pb = sorted(sin_particulas(ta)), sorted(sin_particulas(tb))
    if pa and pa == pb:
        return "particulas"
    if len(sa) >= 2 and len(sb) >= 2 and (sa < sb or sb < sa):
        return "subconjunto"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN_DEFECTO)
    args = ap.parse_args()
    inicio = datetime.now()
    t0 = time.perf_counter()
    log = [f"B2 candidatos a duplicado - inicio {inicio:%Y-%m-%d %H:%M:%S} (solo lectura)"]

    con = psycopg2.connect(args.dsn)
    con.set_session(readonly=True)
    cur = con.cursor()
    cur.execute("SET search_path TO olimpiadas")
    cur.execute("""
        SELECT a.atleta_id, a.nombre_usado, a.nombre_completo, a.sexo, a.nacionalidad,
               a.fecha_nacimiento, a.fecha_fallecimiento,
               COALESCE(array_agg(DISTINCT p.codigo_noc) FILTER (WHERE p.codigo_noc IS NOT NULL), '{}'),
               COALESCE(array_agg(DISTINCT d.nombre) FILTER (WHERE d.nombre IS NOT NULL), '{}'),
               COALESCE(array_agg(DISTINCT o.anio) FILTER (WHERE o.anio IS NOT NULL), '{}'),
               COALESCE(array_agg(DISTINCT p.evento_id) FILTER (WHERE o.anio = 2024), '{}')
        FROM atleta a
        LEFT JOIN participacion p ON p.atleta_id = a.atleta_id
        LEFT JOIN edicion_olimpica o ON o.edicion_id = p.edicion_id
        LEFT JOIN evento e ON e.evento_id = p.evento_id
        LEFT JOIN deporte d ON d.deporte_id = e.deporte_id
        GROUP BY a.atleta_id""")
    atl = {}
    indice = defaultdict(set)  # token -> atleta_ids
    for (i, nu, nc, sx, nac, fn, ff, nocs, deps, anios, ev24) in cur.fetchall():
        tk = tokens(nu)
        atl[i] = dict(id=i, nombre=nu, completo=nc, sexo=sx, nac=nac, nac_fecha=fn, falle=ff,
                      nocs=set(nocs), deps=set(deps), anios=sorted(anios), ev24=set(ev24), tk=tk)
        for t in set(tk):
            indice[t].add(i)
    con.close()
    log.append(f"Atletas leidos: {len(atl):,}; nuevos de fuente 3 (id > {MAX_ID_F1}): "
               f"{sum(1 for i in atl if i > MAX_ID_F1):,}")

    pares = []
    for ia, A in atl.items():
        if ia <= MAX_ID_F1 or len(A["tk"]) < 2:
            continue
        # candidatos: comparten el token menos frecuente de A
        raro = min(A["tk"], key=lambda t: len(indice[t]))
        cand = set(indice[raro]) - {ia}
        for ib in cand:
            B = atl[ib]
            if ib > MAX_ID_F1 and ib < ia:
                continue  # par F3-F3 se reporta una sola vez
            tc = tipo_coincidencia(A["tk"], B["tk"])
            if not tc:
                continue
            # un subconjunto de 2 tokens donde el que sobra es mucho mas largo no aporta: se exige >=2 tokens comunes
            if len(set(A["tk"]) & set(B["tk"])) < 2:
                continue
            sexo_ok = (A["sexo"] == B["sexo"]) if A["sexo"] and B["sexo"] else None
            noc_comun = sorted(A["nocs"] & B["nocs"])
            dep_comun = sorted(A["deps"] & B["deps"])
            fallecido = B["falle"] is not None
            choque = sorted(A["ev24"] & B["ev24"])  # mismo evento 2024 en ambos: personas distintas
            pares.append(dict(A=A, B=B, tipo=tc, sexo_ok=sexo_ok, noc_comun=noc_comun, dep_comun=dep_comun,
                              fallecido=fallecido, choque=choque))

    # candidatos por atleta A, para medir unicidad
    por_a = defaultdict(list)
    for p in pares:
        por_a[p["A"]["id"]].append(p)

    def confianza(p):
        if p["sexo_ok"] is False or p["fallecido"] or p["choque"]:
            return "DESCARTADO"
        fuertes = [q for q in por_a[p["A"]["id"]] if q["sexo_ok"] is not False and not q["fallecido"]
                   and not q["choque"] and q["noc_comun"] and q["dep_comun"]]
        if p["noc_comun"] and p["dep_comun"] and len(fuertes) == 1:
            return "ALTA"
        if p["noc_comun"] and (p["dep_comun"] or len(por_a[p["A"]["id"]]) == 1):
            return "MEDIA"
        return "BAJA"

    ruta = AQUI / "b2_pares_candidatos.csv"
    cuenta = defaultdict(int)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["confianza", "tipo", "id_f3", "nombre_f3", "id_otro", "nombre_otro", "nombre_completo_otro",
                    "sexo_ok", "noc_comun", "deporte_comun", "anios_f3", "anios_otro", "fallecido_otro",
                    "choque_evento_2024", "n_candidatos_del_f3"])
        orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "DESCARTADO": 3}
        filas = sorted(((confianza(p), p) for p in pares), key=lambda x: (orden[x[0]], x[1]["A"]["id"]))
        for c, p in filas:
            cuenta[(c, p["tipo"])] += 1
            A, B = p["A"], p["B"]
            w.writerow([c, p["tipo"], A["id"], A["nombre"], B["id"], B["nombre"], B["completo"] or "",
                        p["sexo_ok"], "|".join(p["noc_comun"]), "|".join(p["dep_comun"]),
                        "|".join(map(str, A["anios"])), "|".join(map(str, B["anios"])),
                        p["fallecido"], "|".join(map(str, p["choque"])), len(por_a[A["id"]])])

    log.append(f"Pares candidatos: {len(pares):,} (detalle en {ruta.name})")
    for (c, t), n in sorted(cuenta.items(), key=lambda x: (orden[x[0][0]], x[0][1])):
        log.append(f"  {c:11s} {t:16s} {n:5d}")
    fin = datetime.now()
    log.append(f"Fin: {fin:%Y-%m-%d %H:%M:%S} | duracion {time.perf_counter() - t0:.1f} s")
    print("\n".join(log))
    logs = RAIZ / "08_logs"
    logs.mkdir(exist_ok=True)
    (logs / f"b2_candidatos_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
