"""B1 (diagnostico, solo lectura): completitud de Paris 2024.

Comprueba (1) que la base coincide con la fuente 3 en filas y medallas por NOC,
(2) cuenta los eventos que solo existen en 2024 (los "199"), (3) compara las
medallas por evento contra el medallero oficial (datos/medallero_oficial_paris2024.txt,
tomado de Wikipedia "2024 Summer Olympics medal table", consultado el 2026-10-19).
Se puede re-ejecutar despues de aplicar B1: las diferencias deben quedar en 0.

Uso: python b1_diagnostico_paris2024.py [--dsn DSN]
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2

DSN_DEFECTO = "postgresql://postgres:olimpiadas@localhost:55433/olimpiadas"
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
F3 = RAIZ.parent / "Fase 1" / "data_raw" / "fuente3_kaggle2024" / "olympics_dataset.csv"
ALIAS = {"Great Britain":"GBR","South Korea":"KOR","North Korea":"PRK","Individual Neutral Athletes":"AIN","Refugee Olympic Team":"EOR","Hong Kong":"HKG","Ivory Coast":"CIV","Cape Verde":"CPV","Czech Republic":"CZE","United States":"USA","Netherlands":"NED","Chinese Taipei":"TPE","Iran":"IRI","Saint Lucia":"LCA","Moldova":"MDA","Kyrgyzstan":"KGZ","Philippines":"PHI","Puerto Rico":"PUR","Dominican Republic":"DOM","Germany":"GER","Croatia":"CRO","Slovenia":"SLO","Bulgaria":"BUL","Denmark":"DEN","Switzerland":"SUI","Algeria":"ALG","Indonesia":"INA","Greece":"GRE","Chile":"CHI","Uganda":"UGA","Mongolia":"MGL","Zambia":"ZAM","Singapore":"SGP","Pakistan":"PAK","Albania":"ALB","Tajikistan":"TJK","Malaysia":"MAS","Grenada":"GRN","Bahrain":"BRN","Azerbaijan":"AZE","Botswana":"BOT","Panama":"PAN","Cyprus":"CYP","Fiji":"FIJ","Jordan":"JOR","Peru":"PER","Qatar":"QAT","Slovakia":"SVK","Lithuania":"LTU","Kosovo":"KOS","India":"IND","Dominica":"DMA","Spain":"ESP","Portugal":"POR","Guatemala":"GUA","Morocco":"MAR","Egypt":"EGY","Tunisia":"TUN","Argentina":"ARG","Ecuador":"ECU","Ethiopia":"ETH","Thailand":"THA","Jamaica":"JAM","South Africa":"RSA","Kazakhstan":"KAZ","Poland":"POL","Israel":"ISR","Ireland":"IRL","Kenya":"KEN","Sweden":"SWE","Norway":"NOR","Uzbekistan":"UZB","New Zealand":"NZL","Brazil":"BRA","Ukraine":"UKR","Romania":"ROU","Georgia":"GEO","Belgium":"BEL","Serbia":"SRB","Cuba":"CUB","Austria":"AUT","Hungary":"HUN","Armenia":"ARM","Colombia":"COL","Mexico":"MEX","Turkey":"TUR","Italy":"ITA","Canada":"CAN","Australia":"AUS","France":"FRA","Japan":"JPN","China":"CHN"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN_DEFECTO)
    a = ap.parse_args()
    inicio = datetime.now(); t0 = time.perf_counter()
    log = [f"B1 diagnostico Paris 2024 - inicio {inicio:%Y-%m-%d %H:%M:%S} (solo lectura)"]
    p = lambda m: (print(m), log.append(m))
    con = psycopg2.connect(a.dsn); con.set_session(readonly=True)
    cur = con.cursor(); cur.execute("SET search_path TO olimpiadas")
    q = lambda sql, *x: (cur.execute(sql, x), cur.fetchall())[1]

    s = pd.read_csv(F3); s = s[s.Year == 2024]
    db = q("""SELECT count(DISTINCT p.participacion_id), count(r.resultado_id),
              count(*) FILTER (WHERE r.medalla='Oro'), count(*) FILTER (WHERE r.medalla='Plata'),
              count(*) FILTER (WHERE r.medalla='Bronce')
              FROM participacion p JOIN edicion_olimpica o USING(edicion_id) LEFT JOIN resultado r USING(participacion_id)
              WHERE o.anio=2024 AND o.tipo='Verano'""")[0]
    p(f"1) Base 2024 Verano: participaciones {db[0]:,}, resultados {db[1]:,}, medallas por atleta oro/plata/bronce {db[2]}/{db[3]}/{db[4]}")
    p(f"   Fuente 3 2024: filas {len(s):,}, medallas {(s.Medal=='Gold').sum()}/{(s.Medal=='Silver').sum()}/{(s.Medal=='Bronze').sum()}")
    comp = s[s.Sport.str.contains(",")]
    p(f"   Filas con Sport compuesto en fuente 3: {len(comp)} ({comp.player_id.nunique()} atletas), medallas en ellas: {(comp.Medal!='No medal').sum()}")

    n199 = q("""SELECT count(*) FROM evento e WHERE EXISTS (SELECT 1 FROM participacion p JOIN edicion_olimpica o USING(edicion_id)
              WHERE p.evento_id=e.evento_id AND o.anio=2024) AND NOT EXISTS (SELECT 1 FROM participacion p JOIN edicion_olimpica o USING(edicion_id)
              WHERE p.evento_id=e.evento_id AND o.anio<>2024)""")[0][0]
    p(f"2) Eventos que solo existen en 2024: {n199}")

    por = q("""SELECT p.codigo_noc, r.medalla, count(DISTINCT p.evento_id) FROM participacion p JOIN edicion_olimpica o USING(edicion_id)
               JOIN resultado r USING(participacion_id) WHERE o.anio=2024 AND o.tipo='Verano' AND r.medalla IS NOT NULL GROUP BY 1,2""")
    d = {}
    for noc, m, n in por: d.setdefault(noc, {})[m] = n
    tot = {m: sum(v.get(m, 0) for v in d.values()) for m in ("Oro", "Plata", "Bronce")}
    p(f"3) Medallas por evento en la base: {tot} (oficial: Oro 329, Plata 330, Bronce 385; sin AIN contado aparte)")
    reg = dict(q("SELECT nombre_region, codigo_noc FROM noc WHERE pais_id IS NOT NULL OR codigo_noc IN ('AIN','EOR')"))
    difs = []
    for linea in open(AQUI / "datos" / "medallero_oficial_paris2024.txt", encoding="utf-8"):
        n, g, pl, b = linea.strip().split("|"); g, pl, b = int(g), int(pl), int(b)
        c = ALIAS.get(n)
        x = d.get(c, {})
        obt = (x.get("Oro", 0), x.get("Plata", 0), x.get("Bronce", 0))
        if obt != (g, pl, b): difs.append((n, c, (g, pl, b), obt))
    p(f"   NOC con diferencia contra el oficial: {len(difs)}")
    for r in difs: p(f"     {r[0]} ({r[1]}): oficial {r[2]}, base {r[3]}")
    fin = datetime.now()
    p(f"Fin: {fin:%Y-%m-%d %H:%M:%S} | duracion {time.perf_counter()-t0:.1f} s")
    (RAIZ / "08_logs").mkdir(exist_ok=True)
    (RAIZ / "08_logs" / f"b1_diagnostico_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
