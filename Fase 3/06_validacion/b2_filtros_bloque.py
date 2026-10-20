"""B2: clasifica los pares ALTA con los filtros automaticos del bloque (solo lectura).

Filtros (aprobados 2026-10-19):
  (a) ultimo anio historico >= 2012
  (b) plausibilidad de edad en 2024 si hay fecha de nacimiento (14..50; 14..60 en tiro,
      ecuestre, vela y tiro con arco)
  (c) deportes de equipo grandes (futbol, hockey, baloncesto, voleibol, balonmano, waterpolo,
      rugby 7) no entran al bloque (solo para subconjunto): verificacion individual
  (d) atletismo: la disciplina (carrera, marcha, saltos, lanzamientos, vallas, fondo, combinada)
      de los dos registros debe coincidir en al menos una (agregado tras el caso Wang Zhen:
      saltador de altura de 2001 emparejado con marchista de 1991)
Ademas marca 'apellido_comun' si algun token del nombre esta entre los 100 tokens mas
frecuentes de toda la base. Escribe b2_pares_clasificados.csv y bitacora en 08_logs/.
"""
import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg2
from text_unidecode import unidecode

AQUI = Path(__file__).resolve().parent
PART = {"van", "von", "de", "da", "di", "del", "der", "den", "du", "le", "la", "el", "al", "dos", "das", "do", "bin", "mc", "mac", "st"}
EQUIPO = ("Football", "Hockey", "Basketball (Basketball)", "Volleyball (Volleyball)", "Handball", "Water Polo", "Rugby Sevens")
EDAD_ALTA = ("Shooting", "Equestrian", "Sailing", "Archery")


DISC = [("marcha", r"walk"), ("saltos", r"high jump|long jump|triple jump|pole vault"),
        ("lanzamientos", r"shot put|discus|hammer|javelin"), ("vallas", r"hurdle|steeplechase"),
        ("combinada", r"decathlon|heptathlon|pentathlon"), ("maraton", r"marathon"),
        ("fondo", r"(800|1,?500|3,?000|5,?000|10,?000) ?m|metres.*(800|1,?500|5,?000|10,?000)|cross"),
        ("velocidad", r"(100|200|400) ?m|relay|sprint")]


def disciplinas(evs):
    g = set()
    for e in evs:
        for nom, rx in DISC:
            if re.search(rx, e.lower()):
                g.add(nom)
    return g


def toks(n):
    return [t for t in re.sub(r"[^a-z ]", " ", unidecode(n or "").lower()).split() if t not in PART]


def main():
    inicio = datetime.now()
    con = psycopg2.connect("postgresql://postgres:olimpiadas@localhost:55433/olimpiadas")
    cur = con.cursor(); cur.execute("SET search_path TO olimpiadas")
    cur.execute("SELECT atleta_id, nombre_usado, fecha_nacimiento FROM atleta")
    frec = Counter(); dob = {}
    for i, n, fn in cur.fetchall():
        frec.update(set(toks(n))); dob[i] = fn
    top = {t for t, _ in frec.most_common(100)}
    cur.execute("""SELECT p.atleta_id, array_agg(DISTINCT e.nombre) FROM participacion p JOIN evento e USING(evento_id)
                   JOIN deporte d USING(deporte_id) WHERE d.nombre = 'Athletics' GROUP BY 1""")
    evs = {i: e for i, e in cur.fetchall()}
    rows = [r for r in csv.DictReader(open(AQUI / "b2_pares_candidatos.csv", encoding="utf-8")) if r["confianza"] == "ALTA"]
    out = []
    for r in rows:
        anios = [int(x) for x in r["anios_otro"].split("|") if x]
        ult = max(anios) if anios else 0
        fa = ult >= 2012
        fn = dob.get(int(r["id_otro"]))
        dep = r["deporte_comun"]
        if fn:
            edad = 2024 - fn.year
            lim = 60 if any(s in dep for s in EDAD_ALTA) else 50
            fb = 14 <= edad <= lim
        else:
            edad, fb = None, True
        fc = not any(e in dep for e in EQUIPO)
        fd = True
        if "Athletics" in dep:
            ga, gb = disciplinas(evs.get(int(r["id_f3"]), [])), disciplinas(evs.get(int(r["id_otro"]), []))
            fd = (not ga or not gb) or bool(ga & gb)
        comun = sorted(set(toks(r["nombre_f3"]) + toks(r["nombre_otro"])) & top)
        out.append({**r, "ultimo_anio": ult, "edad_2024": edad if edad is not None else "", "filtro_a": fa, "filtro_b": fb,
                    "filtro_c_no_equipo": fc, "filtro_d_disciplina": fd,
                    "en_bloque": fa and fb and fd and (fc or r["tipo"] == "orden_invertido"), "apellido_comun": "|".join(comun)})
    campos = list(out[0].keys())
    with open(AQUI / "b2_pares_clasificados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos); w.writeheader(); w.writerows(out)
    log = [f"B2 filtros de bloque - {inicio:%Y-%m-%d %H:%M:%S}", "Top 25 tokens frecuentes: " + ", ".join(f"{t}({n})" for t, n in frec.most_common(25))]
    for t in ("orden_invertido", "particulas", "subconjunto"):
        x = [o for o in out if o["tipo"] == t]
        log.append(f"{t}: {len(x)} ALTA | en bloque {sum(o['en_bloque'] for o in x)} | fuera por (a) {sum(not o['filtro_a'] for o in x)} "
                   f"(b) {sum(not o['filtro_b'] for o in x)} (c) {sum(not o['filtro_c_no_equipo'] for o in x)} (d) {sum(not o['filtro_d_disciplina'] for o in x)} | con apellido comun {sum(bool(o['apellido_comun']) for o in x)}")
    print("\n".join(log))
    (AQUI.parent / "08_logs" / f"b2_filtros_bloque_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")


main()
