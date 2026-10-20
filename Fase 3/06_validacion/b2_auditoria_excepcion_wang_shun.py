"""B2: re-verificacion individual del par Shun Wang (151102) / Wang Shun (120437), 2026-10-20.

Agrega una fila CORRECTO a b2_auditoria_alta.csv (sin sobrescribir la fila NO_VERIFICABLE anterior; el generador usa la ultima).
Evidencia (Wikipedia): Wang Shun, nadador chino nacido el 11-feb-1994 en Ningbo; 200 m estilos: 22 en Londres 2012,
bronce en Rio 2016, oro en Tokio 2020 y bronce en Paris 2024 (1:56.00; oro Marchand, plata Scott). El registro historico
(120437) tiene esa fecha de nacimiento y los resultados 2012, 2016 y 2020; el registro de la fuente 3 (151102) es 200 m estilos
masculino 2024, NOC CHN, bronce. Es la misma persona; no hay participacion del historico en 2024, por lo que no hay colision.
"""
import csv
from pathlib import Path

ruta = Path(__file__).resolve().parent / "b2_auditoria_alta.csv"
filas = list(csv.DictReader(open(ruta, encoding="utf-8")))
ultimas = [r for r in filas if r["id_f3"] == "151102"]
if not ultimas or ultimas[-1]["veredicto"] != "CORRECTO":
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "Shun Wang (151102) -> Wang Shun (120437)", "orden_invertido", "CORRECTO",
            "Re-verificacion 2026-10-20. Nac. 11-feb-1994 (igual); natacion, 200 m estilos: 22 en Londres 2012, bronce en Rio 2016, oro en Tokio 2020 "
            "y bronce en Paris 2024 (1:56.00, oro Marchand, plata Scott). El registro de 2024 es 200 m estilos masculino, CHN, bronce",
            "https://en.wikipedia.org/wiki/Wang_Shun", "151102", "120437"])
    print("fila agregada")
else:
    print("ya registrado")
