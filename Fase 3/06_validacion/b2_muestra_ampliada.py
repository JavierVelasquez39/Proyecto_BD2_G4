"""B2: muestra de verificacion adicional (semilla 2027): 10 orden_invertido con apellido comun y ~30
subconjunto enfocados en riesgo (apellido comun, equipo grande, ultimo anio 2012-2016, filtros b/a).
Excluye los pares ya auditados en b2_auditoria_alta.csv. Salida: b2_muestra_ampliada.csv
"""
import csv, random
from pathlib import Path
AQUI = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(AQUI / "b2_pares_clasificados.csv", encoding="utf-8")))
ya = {r["id_f3"] for r in csv.DictReader(open(AQUI / "b2_auditoria_alta.csv", encoding="utf-8"))}
rows = [r for r in rows if r["id_f3"] not in ya]
random.seed(2027)
def tomar(pool, n, usados):
    pool = [r for r in pool if r["id_f3"] not in usados]
    random.shuffle(pool)
    sel = pool[:n]
    usados.update(r["id_f3"] for r in sel)
    return sel
usados, out = set(), []
inv = [r for r in rows if r["tipo"] == "orden_invertido" and r["apellido_comun"]]
# prioriza apellidos chinos/coreanos mas frecuentes
pri = ("wang", "li", "zhang", "kim", "lee", "park", "chen", "liu", "yang", "xu", "zhou", "wu")
inv.sort(key=lambda r: (not any(p in r["apellido_comun"].split("|") for p in pri), random.random()))
for r in inv[:10]: usados.add(r["id_f3"]); out.append(("AP_COMUN_INV", r))
sub = [r for r in rows if r["tipo"] == "subconjunto"]
grupos = [
 ("SUB_AP_COMUN", [r for r in sub if r["apellido_comun"]], 9),
 ("SUB_EQUIPO", [r for r in sub if r["filtro_c_no_equipo"] == "False"], 10),
 ("SUB_2012_2016", [r for r in sub if 2012 <= int(r["ultimo_anio"]) < 2017], 8),
 ("SUB_FILTRO_B", [r for r in sub if r["filtro_b"] == "False"], 3),
]
for nom, pool, n in grupos:
    for r in tomar(pool, n, usados): out.append((nom, r))
with open(AQUI / "b2_muestra_ampliada.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["estrato", "tipo", "id_f3", "nombre_f3", "id_otro", "nombre_otro", "noc", "deporte", "anios_otro", "edad_2024", "apellido_comun"])
    for e, r in out: w.writerow([e, r["tipo"], r["id_f3"], r["nombre_f3"], r["id_otro"], r["nombre_otro"], r["noc_comun"], r["deporte_comun"], r["anios_otro"], r["edad_2024"], r["apellido_comun"]])
for i, (e, r) in enumerate(out, 1):
    print(i, e[:9], r["id_f3"], r["nombre_f3"], "|", r["id_otro"], r["nombre_otro"], r["noc_comun"], r["deporte_comun"][:14], r["anios_otro"][-9:], r["edad_2024"])
print("filtro_b fuera:", [(r["nombre_f3"], r["nombre_otro"], r["edad_2024"]) for r in csv.DictReader(open(AQUI / "b2_pares_clasificados.csv", encoding="utf-8")) if r["filtro_b"] == "False"])
