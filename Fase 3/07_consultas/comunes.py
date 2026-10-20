"""Utilidades compartidas por atleta.py y pais.py (Fase D)."""
import re
import sys
import time
from datetime import datetime

from pymongo import MongoClient
from text_unidecode import unidecode

URI = "mongodb://localhost:57017"
BASE = "olimpiadas_mongo"
ETIQ_ATLETA = "por atleta (una medalla por atleta y resultado, criterio de la Fase 1)"
ETIQ_EVENTO = "por evento (conteo oficial: una medalla por evento y NOC)"


def fold(s):
    """name_match_key() de la Fase 1: espacios normalizados, sin acentos, minusculas."""
    return unidecode(re.sub(r"\s+", " ", str(s).replace("•", " ")).strip()).casefold()


def conectar(uri=URI, base=BASE):
    cli = MongoClient(uri, serverSelectionTimeoutMS=3000)
    cli.admin.command("ping")  # la conexion no cuenta para el tiempo de respuesta
    return cli[base]


def configurar_salida():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def etapas(nodo, acc=None):
    """Recorre un plan de MongoDB y devuelve [(etapa, indice), ...]."""
    acc = [] if acc is None else acc
    if isinstance(nodo, dict):
        if "stage" in nodo:
            acc.append((nodo["stage"], nodo.get("indexName")))
        for v in nodo.values():
            etapas(v, acc)
    elif isinstance(nodo, list):
        for v in nodo:
            etapas(v, acc)
    return acc


def explicar(db, coleccion, filtro, sort=None, proyeccion=None, limit=None, etiqueta=""):
    """Imprime el plan (executionStats) de un find. Devuelve False si hay COLLSCAN."""
    cmd = {"find": coleccion, "filter": filtro}
    if sort:
        cmd["sort"] = dict(sort)
    if proyeccion:
        cmd["projection"] = proyeccion
    if limit:
        cmd["limit"] = limit
    ex = db.command({"explain": cmd, "verbosity": "executionStats"})
    est = ex["executionStats"]
    lista = etapas(ex["queryPlanner"]["winningPlan"])
    vistos, partes = set(), []
    for e, i in lista:
        txt = f"{e}({i})" if i else e
        if txt not in vistos:
            vistos.add(txt)
            partes.append(txt)
    colscan = any(e == "COLLSCAN" for e, _ in lista)
    print(f"  [explain {etiqueta or coleccion}] plan: {' > '.join(partes)} | "
          f"indices examinados {est['totalKeysExamined']}, documentos examinados {est['totalDocsExamined']}, "
          f"devueltos {est['nReturned']}, {est['executionTimeMillis']} ms en el servidor"
          + ("  <<< COLLSCAN" if colscan else ""))
    return not colscan


def encabezado(titulo, parametros):
    ahora = datetime.now()
    print("=" * 100)
    print(f"{titulo} | ejecutado el {ahora:%Y-%m-%d %H:%M:%S}")
    if parametros:
        print("Parametros: " + ", ".join(f"{k}={v}" for k, v in parametros.items() if v not in (None, False)))
    print("=" * 100)


class Cronometro:
    def __init__(self):
        self.t0 = time.perf_counter()
        self.consulta = 0.0

    def medir(self, f):
        t = time.perf_counter()
        r = f()
        self.consulta += time.perf_counter() - t
        return r

    def pie(self):
        total = (time.perf_counter() - self.t0) * 1000
        print("-" * 100)
        print(f"Tiempo de respuesta: consultas a MongoDB {self.consulta * 1000:.1f} ms | total con formato {total:.1f} ms")


def trunca(s, n):
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[: n - 1] + "~"


def med_txt(m):
    return f"oro {m['oro']} / plata {m['plata']} / bronce {m['bronce']}"
