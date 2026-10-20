"""Línea base de la Fase 1 contra PostgreSQL (solo lectura).

Reproduce los números de referencia de la Fase 1 usando las mismas funciones
que se entregaron (fn_pais_info) y conteos directos de tablas. Escribe
linea_base_fase1.json (junto a este script) y una bitácora en 08_logs/.
Termina con código 1 si algún número no coincide con la referencia.

Uso: python linea_base.py [--dsn DSN]
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

DSN_DEFECTO = "postgresql://postgres:olimpiadas@localhost:55433/olimpiadas"
RAIZ = Path(__file__).resolve().parent.parent

REFERENCIA = {
    "tablas": {"atleta": 153443, "participacion": 319950, "resultado": 320465},
    "medallero": {
        "Germany": {"Oro": 1354, "Plata": 1302, "Bronce": 1331},
        "Russian Federation": {"Oro": 1575, "Plata": 1135, "Bronce": 1158},
    },
    "sedes": {"United States": 8, "France": 6, "Guatemala": 0},
}

REFERENCIA_FASE3 = {
    "tablas": {"atleta": 153049, "participacion": 319961, "resultado": 320476},
    "medallero": {
        "Germany": {"Oro": 1357, "Plata": 1303, "Bronce": 1331},
        "Russian Federation": {"Oro": 1575, "Plata": 1135, "Bronce": 1158},
    },
    "sedes": {"United States": 8, "France": 6, "Guatemala": 0},
}

TABLAS = ["pais", "poblacion_pais", "noc", "sede", "atleta", "edicion_olimpica",
          "deporte", "deporte_equivalencia", "evento", "participacion", "resultado"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN_DEFECTO)
    ap.add_argument("--salida", default="linea_base_fase1.json", help="nombre del JSON (junto al script)")
    ap.add_argument("--referencia", choices=["fase1", "fase3"], default="fase1",
                    help="fase3 = linea base despues de B1 y B2 (correcciones de la Fase 3)")
    ap.add_argument("--etiqueta", default="linea_base", help="prefijo de la bitacora en 08_logs")
    args = ap.parse_args()

    global REFERENCIA
    if args.referencia == "fase3":
        REFERENCIA = REFERENCIA_FASE3
    inicio = datetime.now()
    t0 = time.perf_counter()
    log = []

    def p(msg):
        print(msg)
        log.append(msg)

    p(f"Línea base Fase 1 - inicio: {inicio:%Y-%m-%d %H:%M:%S}")
    con = psycopg2.connect(args.dsn)
    con.set_session(readonly=True)
    cur = con.cursor()

    resultado = {"generado": inicio.isoformat(timespec="seconds"),
                 "tablas": {}, "medallero": {}, "sedes": {}, "discrepancias": []}

    for t in TABLAS:
        cur.execute(f"SELECT count(*) FROM olimpiadas.{t}")
        resultado["tablas"][t] = cur.fetchone()[0]
        p(f"  {t}: {resultado['tablas'][t]:,}")

    for pais in REFERENCIA["medallero"]:
        cur.execute("SELECT medalla, cantidad FROM olimpiadas.fn_pais_info(%s) "
                    "WHERE seccion = 'RESUMEN_MEDALLAS'", (pais,))
        resultado["medallero"][pais] = {m: int(c) for m, c in cur.fetchall()}
        p(f"  medallero {pais}: {resultado['medallero'][pais]}")

    for pais in REFERENCIA["sedes"]:
        cur.execute("SELECT seccion, edicion_anio, edicion_tipo, sede_ciudad "
                    "FROM olimpiadas.fn_pais_info(%s) "
                    "WHERE seccion IN ('SEDE','NUNCA_SEDE')", (pais,))
        filas = cur.fetchall()
        n = sum(1 for f in filas if f[0] == "SEDE")
        resultado["sedes"][pais] = n
        p(f"  sedes {pais}: {n} ({', '.join(f'{f[1]} {f[2]} {f[3]}' for f in filas if f[0] == 'SEDE') or 'NUNCA_SEDE'})")
    con.close()

    for t, esperado in REFERENCIA["tablas"].items():
        if resultado["tablas"][t] != esperado:
            resultado["discrepancias"].append(f"tabla {t}: esperado {esperado}, obtenido {resultado['tablas'][t]}")
    for pais, esperado in REFERENCIA["medallero"].items():
        if resultado["medallero"][pais] != esperado:
            resultado["discrepancias"].append(f"medallero {pais}: esperado {esperado}, obtenido {resultado['medallero'][pais]}")
    for pais, esperado in REFERENCIA["sedes"].items():
        if resultado["sedes"][pais] != esperado:
            resultado["discrepancias"].append(f"sedes {pais}: esperado {esperado}, obtenido {resultado['sedes'][pais]}")

    fin = datetime.now()
    resultado["referencia"] = REFERENCIA
    resultado["coincide"] = not resultado["discrepancias"]
    resultado["duracion_s"] = round(time.perf_counter() - t0, 2)

    ruta_json = Path(__file__).resolve().parent / args.salida
    ruta_json.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    p("COINCIDE con la referencia" if resultado["coincide"]
      else "DISCREPANCIAS: " + "; ".join(resultado["discrepancias"]))
    p(f"Fin: {fin:%Y-%m-%d %H:%M:%S} | duración {resultado['duracion_s']} s")

    logs = RAIZ / "08_logs"
    logs.mkdir(exist_ok=True)
    (logs / f"{args.etiqueta}_{inicio:%Y-%m-%d_%H%M%S}.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    sys.exit(0 if resultado["coincide"] else 1)


if __name__ == "__main__":
    main()
