"""Genera datos/pares_aprobados.csv a partir de la clasificacion y la auditoria de B2 (solo lectura).

Reglas aprobadas el 2026-10-19:
  Fase 1: orden_invertido ALTA que pasa el filtro (d); si el par fue auditado solo entra si es CORRECTO;
          el apellido Wang entra solo con pares verificados; mas el par de particulas y Sharon van Rouwendaal.
  Fase 2: subconjunto ALTA que pasa (a), (b), (c), (d); los pares auditados NO_VERIFICABLE o INCORRECTO
          quedan fuera; se agregan Lee Bo-Na y Ni Xia Lian (verificadas individualmente).
  Fuera siempre: pares de equipos grandes (c), MEDIA y BAJA (salvo Sharon), pares donde el "otro" es de la fuente 3.
"""
import csv
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VAL = AQUI.parent / "06_validacion"
clas = list(csv.DictReader(open(VAL / "b2_pares_clasificados.csv", encoding="utf-8")))
aud = {r["id_f3"]: r for r in csv.DictReader(open(VAL / "b2_auditoria_alta.csv", encoding="utf-8"))}
GEN = {"orden_invertido": "Nombre en orden distinto; mismo sexo, NOC y deporte en comun, candidato unico, pasa filtros (a)-(d); sin auditoria individual (muestra de orden invertido: 35 correctos, 1 incorrecto atrapado por el filtro d)",
       "subconjunto": "Nombre truncado o abreviado; mismo sexo, NOC y deporte en comun, candidato unico, pasa filtros (a)-(d); sin auditoria individual (muestra de subconjunto: 49 correctos, 3 incorrectos atrapados por los filtros a/b)"}


def toks(r):
    return set(re.sub(r"[^a-z ]", " ", (r["nombre_f3"] + " " + r["nombre_otro"]).lower()).split())


# Excepciones verificadas individualmente despues del cierre de las fases 1 y 2: se fusionan en la fase 3
EXCEPCIONES_FASE3 = {"151102"}  # Shun Wang -> Wang Shun (re-verificado el 2026-10-20)

salida = []
for r in clas:
    if int(r["id_otro"]) > 145500:
        continue
    a = aud.get(r["id_f3"])
    if a and a["veredicto"] != "CORRECTO":
        continue
    if r["tipo"] == "orden_invertido":
        if r["en_bloque"] != "True":
            continue
        if "wang" in toks(r) and not a:
            continue
        tipo, fase = "ORDEN_INVERTIDO", 1
    elif r["tipo"] == "particulas":
        tipo, fase = "PARTICULAS", 1
    else:
        if r["en_bloque"] != "True":
            continue
        tipo, fase = "SUBCONJUNTO", 2
    ev = a["evidencia"] if a else GEN[r["tipo"]]
    if r["id_f3"] in EXCEPCIONES_FASE3:
        fase = 3
    salida.append((fase, r["id_f3"], r["id_otro"], tipo, "ALTA", ev, r["nombre_f3"], r["nombre_otro"]))

# Pares verificados individualmente que los filtros automaticos dejaron fuera
for idf in ("147787", "147012"):  # Lee Bo-Na (filtro a), Ni Xia Lian (filtro b)
    r = next(x for x in clas if x["id_f3"] == idf)
    salida.append((2, idf, r["id_otro"], "SUBCONJUNTO", "ALTA", aud[idf]["evidencia"] + " (verificado individualmente; excepcion al filtro automatico)", r["nombre_f3"], r["nombre_otro"]))
# MEDIA manual
salida.append((1, "152796", "123522", "MEDIA_MANUAL", "MEDIA",
               "Sharon van Rouwendaal (NED, n. 1993-09-09): oro en 10 km de aguas abiertas en Paris 2024 (Wikipedia: Swimming at the 2024 Summer Olympics, Women's marathon 10 kilometre). El registro 'van Sharon' (NED, mujer, maraton de natacion) es la misma persona; el apellido se perdio en la fuente 3",
               "van Sharon", "Sharon van Rouwendaal"))

dup = [s[1] for s in salida]
con = [s[2] for s in salida]
assert len(dup) == len(set(dup)), "duplicado repetido"
assert not set(dup) & set(con), "cadena: un conservado es tambien duplicado"
assert len(con) == len(set(con)), "dos duplicados apuntan al mismo conservado"
with open(AQUI / "datos" / "pares_aprobados.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["fase", "id_duplicado", "id_conservado", "tipo", "confianza", "evidencia", "nombre_duplicado", "nombre_conservado"])
    for s in sorted(salida, key=lambda x: (x[0], x[3], int(x[1]))):
        w.writerow(s)
import collections
print(collections.Counter((s[0], s[3]) for s in salida), "total", len(salida))
