"""B2: genera la muestra estratificada de pares ALTA para auditoria manual (solo lectura).

Estratos: 10 orden_invertido, 5 particulas/otros (el unico 'particulas' ALTA mas pares
subconjunto cuyo nombre de fuente 3 empieza con una particula), 25 subconjunto.
Prioriza pares donde el atleta historico tiene fecha de nacimiento (permite cruzar con Wikipedia).
Salida: b2_auditoria_muestra.csv (semilla fija 2026, reproducible).
"""
import csv
import random
import re
from pathlib import Path

import psycopg2

AQUI = Path(__file__).resolve().parent
PART = re.compile(r"^(van|von|de|da|di|del|der|den|du|le|la|al|st\.?|dos|das)\s", re.I)
rows = [r for r in csv.DictReader(open(AQUI / "b2_pares_candidatos.csv", encoding="utf-8")) if r["confianza"] == "ALTA"]
con = psycopg2.connect("postgresql://postgres:olimpiadas@localhost:55433/olimpiadas")
cur = con.cursor(); cur.execute("SET search_path TO olimpiadas")
cur.execute("""SELECT atleta_id, nombre_completo, fecha_nacimiento, pais_nacimiento, nacionalidad, sexo FROM atleta WHERE atleta_id = ANY(%s)""",
            ([int(r["id_otro"]) for r in rows],))
info = {r[0]: r for r in cur.fetchall()}
cur.execute("""SELECT p.atleta_id, string_agg(DISTINCT e.nombre, ' | '), string_agg(DISTINCT p.equipo, ' | ') FROM participacion p
               JOIN evento e USING(evento_id) WHERE p.atleta_id = ANY(%s) GROUP BY 1""", ([int(r["id_f3"]) for r in rows],))
ev3 = {r[0]: r for r in cur.fetchall()}
for r in rows:
    r["fn"] = info[int(r["id_otro"])][2]
    r["pn"] = info[int(r["id_otro"])][3]

random.seed(2026)
def pick(pool, n):
    con_fn = [r for r in pool if r["fn"]]
    sin_fn = [r for r in pool if not r["fn"]]
    random.shuffle(con_fn); random.shuffle(sin_fn)
    return (con_fn + sin_fn)[:n]

inv = [r for r in rows if r["tipo"] == "orden_invertido"]
part = [r for r in rows if r["tipo"] == "particulas"] 
sub = [r for r in rows if r["tipo"] == "subconjunto"]
sub_part = [r for r in sub if PART.match(r["nombre_f3"])]
sub_norm = [r for r in sub if not PART.match(r["nombre_f3"])]
muestra = [("orden_invertido", r) for r in pick(inv, 10)]
muestra += [("particulas/otros", r) for r in part + pick(sub_part, 5 - len(part))]
muestra += [("subconjunto", r) for r in pick(sub_norm, 25)]

with open(AQUI / "b2_auditoria_muestra.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["estrato", "tipo", "id_f3", "nombre_f3", "id_otro", "nombre_otro", "nombre_completo_otro",
                "fecha_nac_otro", "pais_nac_otro", "noc", "deporte", "anios_otro", "eventos_2024_f3", "equipo_f3"])
    for est, r in muestra:
        e = ev3.get(int(r["id_f3"]), (None, "", ""))
        w.writerow([est, r["tipo"], r["id_f3"], r["nombre_f3"], r["id_otro"], r["nombre_otro"], r["nombre_completo_otro"],
                    r["fn"] or "", r["pn"] or "", r["noc_comun"], r["deporte_comun"], r["anios_otro"], e[1], e[2]])
print(len(muestra), "pares;", sum(1 for _, r in muestra if r["fn"]), "con fecha de nacimiento")
