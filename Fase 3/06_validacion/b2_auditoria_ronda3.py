"""B2: ultima ronda de verificacion (Zhang y Liu), 2026-10-19. Agrega filas a b2_auditoria_alta.csv sin sobrescribir.
Verificacion: Wikipedia (fecha de nacimiento y participacion en Paris 2024), URL por fila.
"""
import csv
from pathlib import Path

W = "https://en.wikipedia.org/wiki/"
C, N = "CORRECTO", "NO_VERIFICABLE"
FILAS = [  # id_f3, id_otro, nombre_f3, nombre_otro, veredicto, evidencia, pagina
    (149487, 138239, "Deshun Zhang", "Zhang Deshun", C, "Nac. 21-feb-1996 (igual); maraton femenino, 59 en Paris 2024", "Zhang_Deshun"),
    (148389, 138259, "Zhiting Zhang", "Zhang Zhiting", C, "Nac. 21-dic-1995 (igual); baloncesto 3x3; categoria Paris 2024", "Zhang_Zhiting"),
    (149209, 138472, "Bowen Zhang", "Zhang Bowen", C, "Nac. 28-abr-1996 (igual); tiro; categoria Paris 2024", "Zhang_Bowen"),
    (149229, 138317, "Mingyu Zhang", "Zhang Mingyu", C, "Nac. 3-oct-2001 (igual); pentatlon moderno; categoria Paris 2024", "Zhang_Mingyu"),
    (151082, 127244, "Yufei Zhang", "Zhang Yufei", C, "Nac. 19-abr-1998 (igual); natacion; 6 medallas en Paris 2024", "Zhang_Yufei_(swimmer)"),
    (149436, 130495, "Yang Liu", "Liu Yang", C, "Nac. 11-ago-1994 (igual); gimnasia; oro en anillas y plata por equipos en Paris 2024", "Liu_Yang_(gymnast,_born_1994)"),
    (150022, 138431, "Hao Liu", "Liu Hao", C, "Nac. 6-sep-1993 (igual); piraguismo; oro C-2 500 m en Paris 2024", "Liu_Hao_(canoeist)"),
    (149390, 138460, "Zhiyu Liu", "Liu Zhiyu", C, "Nac. 5-ene-1993 (igual); remo; categoria Paris 2024", "Liu_Zhiyu"),
    (149599, 138273, "Jiali Liu", "Liu Jiali", C, "Nac. 6-abr-1994 (igual); ciclismo; categoria Paris 2024", "Liu_Jiali"),
    (151110, 127241, "Yaxin Liu", "Liu Yaxin", C, "Nac. 16-jun-1999 (igual); espalda; bronce relevo 4x200 libre en Paris 2024", "Liu_Yaxin"),
    (149463, 115599, "Hong Liu", "Liu Hong", N, "Nac. 12-may-1987 (igual) pero Liu Hong no figura en el relevo mixto de marcha de Paris 2024 (China: He Xianghong, Qieyang Shijie, Zhang Jun, Yang Jiayu); posible reserva", "Athletics_at_the_2024_Summer_Olympics_%E2%80%93_Mixed_marathon_walk_relay"),
    (149402, 138341, "Xiaoxin Liu", "Liu Xiaoxin", N, "Nac. 24-jul-1997 (igual) pero la pagina solo registra Tokio 2020, sin categoria de Paris 2024", "Liu_Xiaoxin"),
]
ruta = Path(__file__).resolve().parent / "b2_auditoria_alta.csv"
existentes = {r["id_f3"] for r in csv.DictReader(open(ruta, encoding="utf-8"))}
n = 0
with open(ruta, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for a, b, na, nb, v, ev, pag in FILAS:
        if str(a) in existentes:
            continue
        w.writerow([f"{na} ({a}) -> {nb} ({b})", "orden_invertido", v, ev, W + pag, a, b])
        n += 1
print("filas agregadas:", n)
