"""B2: combina la muestra estratificada con los veredictos de la auditoria manual (2026-10-19).

Criterio. CORRECTO: la pagina de Wikipedia de la persona coincide con la fecha de nacimiento
del registro historico (o, si no hay fecha, es la unica persona de ese pais y deporte) Y la
persona compitio en Paris 2024 en ese deporte (texto o categoria 'at the 2024 Summer Olympics').
INCORRECTO: Wikipedia muestra que son personas distintas. NO_VERIFICABLE: la pagina no permite
confirmar la participacion en Paris 2024 o la identidad.
Salida: b2_auditoria_alta.csv (par, tipo, veredicto, evidencia, url).
"""
import csv
from pathlib import Path

W = "https://en.wikipedia.org/wiki/"
C, I, N = "CORRECTO", "INCORRECTO", "NO_VERIFICABLE"
V = {
 1: (C, "Nac. 19-sep-1990 (igual); hockey; categoria Paris 2024. Apellido compuesto en orden distinto (Webb-Pearne)", W+"Hollie_Webb"),
 2: (C, "Nac. 14-feb-1997 (igual); rugby 7; Paris 2024 torneo femenino", W+"Wang_Wanyu"),
 3: (C, "Nac. 3-may-2002 (igual); 200 m en Paris 2024", W+"Li_Yuting"),
 4: (C, "Nac. 15-mar-1997 (igual); listada en judo +78 kg de Paris 2024", W+"Judo_at_the_2024_Summer_Olympics_%E2%80%93_Women%27s_%2B78_kg"),
 5: (C, "Nac. 20-oct-1994 (igual); golf; categoria Paris 2024", W+"Hsu_Wei-ling"),
 6: (C, "Nac. 15-feb-1997 (igual); florete; categoria Paris 2024", W+"Chen_Qingyuan"),
 7: (C, "Nac. 9-jul-1992 (igual); maraton en Paris 2024 (55)", W+"Yang_Shaohui"),
 8: (C, "Nac. 25-sep-2000 (igual); piraguismo; categoria Paris 2024", W+"Wang_Nan_(canoeist)"),
 9: (N, "Nac. 12-sep-1997 (igual) pero la pagina no menciona Paris 2024 y la pagina de la prueba no se pudo leer", W+"Wang_Zifeng"),
 10: (C, "Nac. 15-mar-1996 (igual); tiro; rifle 10 m mixto por equipos en Paris 2024", W+"Seonaid_McIntosh"),
 11: (C, "Nac. 5-feb-1990 (igual); boxeo; categoria Paris 2024; Al-Hlimi / Hlimi", W+"Khouloud_Hlimi"),
 12: (C, "Nac. 5-mar-2000 (igual); gimnasia; Paris 2024 clasificacion por equipos", W+"M%C3%A9lanie_de_Jesus_dos_Santos"),
 13: (N, "Nac. 12-abr-1992 (igual) pero el texto leido de la pagina no cubre Paris 2024 (pagina truncada)", W+"Chad_le_Clos"),
 14: (C, "Nac. 22-oct-1994 (igual); judo 63 kg; categoria Paris 2024", W+"Mayl%C3%ADn_del_Toro"),
 15: (C, "Nac. 3-ene-1996 (igual); 400 m vallas en Paris 2024", W+"Naomi_Van_den_Broeck"),
 16: (C, "Nac. 23-ago-1987 (igual); relevo 4x100 en Paris 2024", W+"Murielle_Ahour%C3%A9"),
 17: (I, "Wikipedia lista dos personas: Julio Cesar Enciso (n. 1974) y Julio Enciso (n. 2004), ambos futbolistas paraguayos. El registro historico es el de 1974 (50 anios en 2024)", W+"Julio_Enciso"),
 18: (C, "Nac. 14-nov-1997 (igual); atletismo; categoria Paris 2024", W+"Mazoon_Al-Alawi"),
 19: (C, "Nac. 12-abr-1994 (igual); lanzamiento de bala; Paris 2024", W+"Dimitriana_Surdu"),
 20: (C, "Nac. 1-ene-1993 (igual); taekwondo 57 kg; categoria Paris 2024", W+"Hatice_K%C3%BCbra_%C4%B0lg%C3%BCn"),
 21: (C, "Nac. 2-jun-1992 (igual); maraton; categoria Paris 2024", W+"Matea_Parlov_Ko%C5%A1tro"),
 22: (C, "Nac. 3-mar-1996 (igual); lucha grecorromana 87 kg en Paris 2024", W+"Bachir_Sid_Azara"),
 23: (C, "Nac. 11-ene-1999 (igual); rifle 10 m mixto por equipos en Paris 2024", W+"Jeanette_Hegg_Duestad"),
 24: (C, "Nac. 10-sep-1996 (igual); maraton en Paris 2024", W+"Gabriel_Geay"),
 25: (C, "Nac. 25-nov-1991 (igual); atletismo; categoria Paris 2024", W+"Patience_Okon_George"),
 26: (C, "Nac. 26-oct-1998 (igual); voleibol femenino de Kenia en Paris 2024", W+"Sharon_Chepchumba"),
 27: (C, "Nac. 20-sep-1991 (igual); jabalina en Paris 2024", W+"Kelsey-Lee_Barber"),
 28: (C, "Nac. 15-dic-1992 (igual); triatlon, 22 en Paris 2024", W+"Marten_Van_Riel"),
 29: (C, "Nac. 26-nov-1995 (igual); keirin en Paris 2024", W+"Shah_Firdaus_Sahrom"),
 30: (C, "Nac. 1-ene-1997 (igual); abanderado de Yibuti en Paris 2024", W+"Mohamed_Ismail_Ibrahim"),
 31: (C, "Nac. 18-nov-1988 (igual); 100 m y relevo 4x100 en Paris 2024", W+"Marie-Jos%C3%A9e_Ta_Lou"),
 32: (C, "Nac. 4-dic-1992 (igual); jabalina en Paris 2024", W+"L%C4%ABna_M%C5%ABze"),
 33: (C, "Nac. 5-feb-1988 (igual); martillo en Paris 2024", W+"Zalina_Marghieva"),
 34: (C, "Nac. 14-jun-1990 (igual); 5000 m en Paris 2024", W+"Karoline_Bjerkeli_Gr%C3%B8vdal"),
 35: (C, "Nac. 22-jul-1981 (igual); tiro; categoria Paris 2024", W+"Lee_Bo-na"),
 36: (C, "Nac. 29-mar-1996 (igual); atletismo; categoria Paris 2024", W+"Silina_Pha_Aphay"),
 37: (N, "La pagina 'Juan Celaya' es de desambiguacion (futbolista y clavadista); no se confirmo cual es", W+"Juan_Celaya"),
 38: (C, "Luis Orta (Cuba) figura en lucha grecorromana 67 kg de Paris 2024; unico luchador cubano con ese nombre", W+"Wrestling_at_the_2024_Summer_Olympics_%E2%80%93_Men%27s_Greco-Roman_67_kg"),
 39: (C, "Nac. 26-nov-1985 (igual); tiro; Paris 2024 (30 de 56)", W+"Yasameen_Al-Raimi"),
 40: (N, "Nac. 27-oct-1996 (igual) pero no figura en la plantilla alemana del relevo 4x400 de Paris 2024 (posible reserva)", W+"Lisa-Marie_Kwayie"),
}
aqui = Path(__file__).resolve().parent
filas = list(csv.DictReader(open(aqui / "b2_auditoria_muestra.csv", encoding="utf-8")))
assert len(filas) == len(V) == 40
with open(aqui / "b2_auditoria_alta.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["par", "tipo", "veredicto", "evidencia", "url", "id_f3", "id_otro"])
    for i, r in enumerate(filas, 1):
        v = V[i]
        w.writerow([f'{r["nombre_f3"]} ({r["id_f3"]}) -> {r["nombre_otro"]} ({r["id_otro"]})', r["tipo"], v[0], v[1], v[2], r["id_f3"], r["id_otro"]])
import collections
c = collections.Counter((r["tipo"], V[i][0]) for i, r in enumerate(filas, 1))
for k, n in sorted(c.items()): print(k, n)
