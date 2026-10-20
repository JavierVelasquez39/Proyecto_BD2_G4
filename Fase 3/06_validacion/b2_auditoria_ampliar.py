"""B2: agrega a b2_auditoria_alta.csv los veredictos de la ronda ampliada (2026-10-19, no sobrescribe).
Fuente de verificacion: Wikipedia (URL por fila). Mismos criterios que b2_auditoria_registrar.py;
en deportes de equipo y nombres truncados la identidad se apoya ademas en la plantilla oficial.
Ronda 2: 10 orden_invertido con apellido comun, 29 subconjunto de riesgo, 11 pares Wang adicionales.
"""
import collections
import csv
from pathlib import Path

W = "https://en.wikipedia.org/wiki/"
C, I, N = "CORRECTO", "INCORRECTO", "NO_VERIFICABLE"
aqui = Path(__file__).resolve().parent
amp = list(csv.DictReader(open(aqui / "b2_muestra_ampliada.csv", encoding="utf-8")))
V = {  # indice (1..39) en b2_muestra_ampliada.csv -> (veredicto, evidencia, pagina)
    1: (C, "Nac. 26-oct-1997 (igual); judo 48 kg; categoria Paris 2024", "Lin_Chen-hao"),
    2: (C, "Nac. 31-oct-1996 (igual); piraguismo; categoria Paris 2024", "Wang_Congkang"),
    3: (C, "Nac. 3-mar-2002 (igual); bronce 4x200 libre en Paris 2024", "Li_Bingjie"),
    4: (C, "Nac. 8-oct-1997 (igual segun el texto); waterpolo; categoria Paris 2024", "Wang_Huan_(water_polo)"),
    5: (C, "Nac. 5-dic-1995 (igual); remo; categoria Paris 2024", "Chen_Yunxia"),
    6: (C, "Nac. 23-jul-1995 (igual); rugby 7; seleccionada para Paris 2024", "Chen_Keyi"),
    7: (I, "El registro historico es el marchista Wang Zhen (n. 1991, 20 km marcha 2012/2016), que no esta en la 20 km marcha de Paris 2024 (China: Zhang Jun, Li Yandong, Wang Zhaozhao). El de 2024 es salto de altura: Wang Zhen (n. 2001), categoria Paris 2024. Personas distintas, mismo deporte (atletismo)", "Athletics_at_the_2024_Summer_Olympics_%E2%80%93_Men%27s_20_kilometres_walk"),
    8: (C, "Nac. 8-sep-1992 (igual); baloncesto 3x3; categoria Paris 2024", "Wang_Lili_(basketball)"),
    9: (N, "La pagina no existe con ese titulo. Evidencia interna: mismos eventos (kayak individual 1000 m, K4 500 m) y NOC, pero sin verificacion externa", ""),
    10: (C, "Nac. 14-jul-1997 (igual); voleibol; represento a China en 2020 y 2024", "Wang_Yuanyuan_(volleyball)"),
    11: (C, "Jean Pierre Brol aparece en tiro (foso) de Guatemala en Paris 2024, bronce; fecha de nacimiento no verificada", "Guatemala_at_the_2024_Summer_Olympics"),
    12: (C, "Maria Schutzmeier (Nicaragua) 100 m mariposa en Paris 2024 (la pagina omite Victoria); fecha de nacimiento no verificada", "Nicaragua_at_the_2024_Summer_Olympics"),
    13: (C, "Nac. 7-jun-1997 (igual); salto de altura; 2020 y 2024", "Luis_Enrique_Zayas"),
    14: (C, "Nac. 10-abr-1997 (igual); remo; bronce skiff en Paris 2024", "Simon_van_Dorp"),
    15: (C, "Nac. 27-jun-1999 (igual); 400 m y relevo en Paris 2024", "Jean_Paul_Bredau"),
    16: (I, "Registro historico: Maria de Souza, salto triple 1996, n. 1971 (53 anios). El de 2024 es 800 m. La plantilla de atletismo de Brasil en Paris no incluye a Maria de Souza", "Brazil_at_the_2024_Summer_Olympics"),
    17: (C, "Nac. 7-abr-2001 (igual); clavados; plata y bronce en Paris 2024", "Kim_Mi-rae"),
    18: (C, "Nac. 12-nov-1995 (igual); judo -73 kg en Paris 2024", "Andrew_Mlugu"),
    19: (N, "No se pudo leer la plantilla de balonmano de Argentina (pagina truncada)", "Argentina_at_the_2024_Summer_Olympics"),
    20: (C, "Nac. 13-sep-1991 (igual); rugby 7 de Gran Bretania en Paris 2024", "Amy_Wilson-Hardy"),
    21: (C, "Nac. 15-feb-1992 (igual); voleibol; oro en Paris 2024", "Nicolas_Le_Goff"),
    22: (C, "Nac. 18-may-1989 (igual); futbol; plantilla de Francia en Paris 2024", "Eug%C3%A9nie_Le_Sommer"),
    23: (C, "Nac. 8-ene-1987 (igual); voleibol; oro en Paris 2024", "Monica_De_Gennaro"),
    24: (C, "Nac. 15-abr-1994 (igual); futbol; convocada a Paris 2024", "Katie_Bowen"),
    25: (C, "Nac. 30-mar-1980 (igual); balonmano; oro en Paris 2024", "Katrine_Lunde"),
    26: (C, "Nac. 29-nov-1991 (igual); voleibol; plantilla de Canada en Paris 2024", "Lucas_Van_Berkel"),
    27: (C, "Nac. 20-jun-1991 (igual); balonmano; oro en Paris 2024", "Rasmus_Lauge"),
    28: (C, "Nac. 25-oct-1991 (igual); hockey; plantilla de Belgica en Paris 2024", "Florent_van_Aubel"),
    29: (C, "Nac. 19-jul-1995 (igual); hockey; plantilla de Sudafrica en Paris 2024", "Ryan_Julius"),
    30: (C, "Nac. 20-abr-1989 (igual); piraguismo; Paris 2024", "Ana_Paula_Vergutz"),
    31: (N, "Nac. 11-feb-1987 (igual) pero la pagina leida no cubre Paris 2024 (truncada)", "Ellen_van_Dijk"),
    32: (C, "Nac. 30-ene-1993 (igual); gimnasia; cuota individual a Paris 2024", "Andrei_Muntean"),
    33: (C, "Nac. 16-mar-1990 (igual); judo 78 kg en Paris 2024", "Moira_de_Villiers"),
    34: (C, "Nac. 20-ago-1994 (igual); remo; categoria Paris 2024", "Chiu_Hin_Chun"),
    35: (N, "Desambiguacion: tiradora n. 1981 (igual anio) pero la pagina no menciona Paris 2024", "Lin_Yi-chun"),
    36: (C, "Nac. 24-ene-1991 (igual); esgrima; categoria Paris 2024", "John_%C3%89dison_Rodr%C3%ADguez"),
    37: (C, "Nac. 26-ago-1990 (igual); tenis; Paris 2024 individual y dobles", "Irina_Begu"),
    38: (I, "Registro historico: remero n. 1951 (73 anios, 1976). En Paris 2024 el remero neerlandes es Gert-Jan van Doorn (ocho masculino), persona distinta", "Netherlands_at_the_2024_Summer_Olympics"),
    39: (C, "Nac. 4-jul-1963 (igual); tenis de mesa; compitio en Paris 2024 a los 61 anios (falso positivo del filtro de edad)", "Ni_Xia_Lian"),
}
# Pares Wang adicionales: (id_f3, id_otro, nombre_f3, nombre_otro, veredicto, evidencia, pagina)
WANG = [
    (146987, 143216, "Chi-lin Wang", "Wang Chi-Lin", C, "Nac. 18-ene-1995 (igual); badminton; oro dobles masculino en Paris 2024", "Wang_Chi-lin"),
    (148352, 138439, "Zongyuan Wang", "Wang Zongyuan", C, "Nac. 24-oct-2001 (igual); clavados; oro sincronizado 3 m en Paris 2024", "Wang_Zongyuan"),
    (148391, 138246, "Siyu Wang", "Wang Siyu", N, "Pagina con ese titulo no existe; sin verificacion externa", ""),
    (148431, 138386, "Manyu Wang", "Wang Manyu", C, "Nac. 9-feb-1999 (igual); tenis de mesa; oro por equipos en Paris 2024", "Wang_Manyu"),
    (148451, 138451, "Zijie Wang", "Wang Zijie", C, "Nac. 15-jul-1996 (igual); esgrima; categoria Paris 2024", "Wang_Zijie"),
    (148872, 138369, "Qianyi Wang", "Wang Qianyi", C, "Nac. 16-ene-1997 (igual); natacion artistica; oro en Paris 2024", "Wang_Qianyi"),
    (149173, 138388, "Mengjie Wang", "Wang Mengjie", C, "Nac. 14-nov-1995 (igual); voleibol; categoria Paris 2024", "Wang_Mengjie"),
    (149477, 113807, "Zheng Wang", "Wang Zheng", C, "Nac. 14-dic-1987 (igual); martillo; 28 en Paris 2024", "Wang_Zheng_(athlete)"),
    (149926, 133677, "Jianan Wang", "Wang Jianan", N, "Desambiguacion: saltador de longitud n. 1996 (igual anio); la pagina no menciona Paris 2024", "Wang_Jianan"),
    (151095, 127238, "Xueer Wang", "Wang Xueer", C, "Nac. 15-ene-1998 (igual); espalda; bronce relevo 4x100 combinado en Paris 2024", "Wang_Xueer"),
    (151102, 120437, "Shun Wang", "Wang Shun", N, "Pagina con ese titulo no existe; sin verificacion externa", ""),
]
ruta = aqui / "b2_auditoria_alta.csv"
existentes = {r["id_f3"] for r in csv.DictReader(open(ruta, encoding="utf-8"))}
nuevas = []
for i, r in enumerate(amp, 1):
    v, ev, pag = V[i]
    nuevas.append((r["id_f3"], f'{r["nombre_f3"]} ({r["id_f3"]}) -> {r["nombre_otro"]} ({r["id_otro"]})', r["tipo"], v, ev,
                   W + pag if pag else "", r["id_otro"]))
for a, b, na, nb, v, ev, pag in WANG:
    nuevas.append((str(a), f"{na} ({a}) -> {nb} ({b})", "orden_invertido", v, ev, W + pag if pag else "", str(b)))
n = 0
with open(ruta, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for idf3, par, tipo, v, ev, url, ido in nuevas:
        if idf3 in existentes:
            continue
        w.writerow([par, tipo, v, ev, url, idf3, ido])
        n += 1
print("filas agregadas:", n)
todas = list(csv.DictReader(open(ruta, encoding="utf-8")))
for k, x in sorted(collections.Counter((r["tipo"], r["veredicto"]) for r in todas).items()):
    print(k, x)
print("total filas:", len(todas))
