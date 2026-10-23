"""Levanta la Fase 3 de punta a punta: Docker, MongoDB, carga y validacion. Idempotente.

Uso (desde Fase 3/): python levantar_todo.py [--recargar]

Pasos:
  1. Verifica requisitos (Docker corriendo, mongosh, librerias de Python) y levanta MongoDB (docker compose up -d).
  2. Espera a que MongoDB responda al ping.
  3. Si la base esta vacia o incompleta, o se pasa --recargar: exportar_postgres.py, crear_colecciones.js, cargar.py,
     crear_indices.js y validar.py. Si ya hay datos: solo validar.py y los conteos.
  4. Imprime comandos de ejemplo.
El export necesita PostgreSQL (olimpiadas_pg, puerto 55433): si el contenedor no existe se crea y se restaura desde
00_infraestructura/fuente/olimpiadas_fase3_postgres.dump; si esta detenido se arranca. Si no se logra pero los .jsonl
ya existen, se reutilizan.
Si falta algo termina con codigo 1 y un mensaje claro. Bitacora con fecha y hora en 08_logs/levantar_todo_*.log.
"""
import argparse
import importlib
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
COMPOSE = RAIZ / "00_infraestructura" / "docker-compose.yml"
JSONL = RAIZ / "02_exportar" / "data"
COLECCIONES = ["atletas", "participaciones", "paises", "ediciones", "deportes"]
ARCHIVOS_JSONL = [f"{c}.jsonl" for c in COLECCIONES]
URI = "mongodb://localhost:57017"
DB = "olimpiadas_mongo"
PG_PUERTO = 55433
PG_CONTENEDOR = "olimpiadas_pg"
PG_IMAGEN = "postgres:16"
PG_DUMP = RAIZ / "00_infraestructura" / "fuente" / "olimpiadas_fase3_postgres.dump"
ESPERA_MONGO_S = 90
LIBRERIAS = [("pymongo", "pymongo"), ("psycopg2", "psycopg2-binary"), ("text_unidecode", "text-unidecode")]

ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "MSYS_NO_PATHCONV": "1"}
log = []
inicio = datetime.now()


class Falla(Exception):
    pass


def p(msg=""):
    print(msg, flush=True)
    log.append(msg)


def paso(n, titulo):
    p(f"\n[{n}] {titulo}")


def correr(cmd, descripcion, stdin_archivo=None):
    """Ejecuta cmd mostrando su salida en vivo y copiandola a la bitacora; Falla si el codigo no es 0."""
    p(f"  $ {' '.join(str(c) for c in cmd)}")
    try:
        entrada = open(stdin_archivo, "rb") if stdin_archivo else None
        proc = subprocess.Popen(cmd, cwd=RAIZ, env=ENV, stdin=entrada, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
    except FileNotFoundError:
        raise Falla(f"no se encontro el programa '{cmd[0]}' ({descripcion})")
    for linea in proc.stdout:
        p("    " + linea.decode("utf-8", errors="replace").rstrip())
    if proc.wait() != 0:
        raise Falla(f"fallo: {descripcion} (codigo {proc.returncode}). Ver la salida de arriba")


def verificar_requisitos():
    paso(1, "Verificando requisitos y levantando MongoDB")
    if not COMPOSE.exists():
        raise Falla(f"falta {COMPOSE.relative_to(RAIZ)}")
    if shutil.which("docker") is None:
        raise Falla("Docker no esta instalado o no esta en el PATH")
    r = subprocess.run(["docker", "info"], capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        raise Falla("Docker no esta corriendo. Abrir Docker Desktop, esperar a que diga 'Engine running' y repetir")
    p("  Docker: corriendo")
    faltan = []
    for modulo, paquete in LIBRERIAS:
        try:
            importlib.import_module(modulo)
        except ImportError:
            faltan.append(paquete)
    if faltan:
        raise Falla(f"faltan librerias de Python: {', '.join(faltan)}. Ejecutar: pip install -r requirements.txt")
    p("  Librerias de Python: ok")
    correr(["docker", "compose", "-f", str(COMPOSE), "up", "-d"], "docker compose up -d")


def conectar():
    from pymongo import MongoClient
    return MongoClient(URI, serverSelectionTimeoutMS=2000)


def esperar_mongo():
    paso(2, f"Esperando a que MongoDB responda en {URI}")
    t0 = time.monotonic()
    ultimo = ""
    while time.monotonic() - t0 < ESPERA_MONGO_S:
        try:
            if conectar().admin.command("ping").get("ok") == 1:
                p(f"  ping ok ({time.monotonic() - t0:.0f} s)")
                return
        except Exception as e:
            ultimo = str(e).splitlines()[0][:150]
        time.sleep(2)
    raise Falla(f"MongoDB no respondio en {ESPERA_MONGO_S} s ({ultimo}). Revisar: docker logs olimpiadas_mongo")


def conteos():
    db = conectar()[DB]
    return {c: db[c].estimated_document_count() if c in db.list_collection_names() else 0 for c in COLECCIONES}


def mostrar_conteos(cuentas):
    for c, n in cuentas.items():
        p(f"  {c:<16}{n:>10,}")


def postgres_disponible():
    try:
        with socket.create_connection(("localhost", PG_PUERTO), timeout=2):
            return True
    except OSError:
        return False


def docker_salida(*args):
    r = subprocess.run(["docker", *args], capture_output=True, text=True, env=ENV)
    return r.returncode, (r.stdout + r.stderr).strip()


def esperar_postgres():
    for _ in range(60):
        if docker_salida("exec", PG_CONTENEDOR, "pg_isready", "-U", "postgres", "-d", "olimpiadas")[0] == 0:
            return
        time.sleep(2)
    raise Falla(f"PostgreSQL no acepto conexiones en 120 s. Revisar: docker logs {PG_CONTENEDOR}")


def asegurar_postgres():
    """Deja olimpiadas_pg corriendo: lo arranca si esta detenido; si no existe, lo crea y restaura el dump versionado."""
    codigo, estado = docker_salida("inspect", "-f", "{{.State.Running}}", PG_CONTENEDOR)
    if codigo == 0 and estado == "true":
        if not postgres_disponible():
            raise Falla(f"{PG_CONTENEDOR} corre pero el puerto {PG_PUERTO} no responde (otro mapeo de puertos?)")
        p(f"  PostgreSQL: {PG_CONTENEDOR} ya corre")
        return
    if codigo == 0:
        p(f"  PostgreSQL: {PG_CONTENEDOR} esta detenido; se arranca")
        correr(["docker", "start", PG_CONTENEDOR], "docker start " + PG_CONTENEDOR)
        esperar_postgres()
        return
    if not PG_DUMP.exists():
        raise Falla(f"no existe el contenedor {PG_CONTENEDOR} ni el dump {PG_DUMP.relative_to(RAIZ)}")
    if postgres_disponible():
        raise Falla(f"el puerto {PG_PUERTO} esta ocupado por otro servicio; liberarlo para crear {PG_CONTENEDOR}")
    p(f"  PostgreSQL: se crea {PG_CONTENEDOR} y se restaura el dump versionado")
    # Credencial de desarrollo local, no reutilizar.
    correr(["docker", "run", "-d", "--name", PG_CONTENEDOR, "-e", "POSTGRES_PASSWORD=olimpiadas",
            "-e", "POSTGRES_DB=olimpiadas", "-p", f"{PG_PUERTO}:5432", PG_IMAGEN], "docker run " + PG_CONTENEDOR)
    esperar_postgres()
    time.sleep(3)  # la imagen reinicia el servidor una vez tras la inicializacion
    esperar_postgres()
    correr(["docker", "cp", str(PG_DUMP), f"{PG_CONTENEDOR}:/tmp/fase3.dump"], "docker cp del dump")
    correr(["docker", "exec", PG_CONTENEDOR, "pg_restore", "-U", "postgres", "-d", "olimpiadas", "--no-owner",
            "/tmp/fase3.dump"], "pg_restore del dump")


def mongosh(archivo):
    ruta = RAIZ / archivo
    if not ruta.exists():
        raise Falla(f"falta {archivo}")
    if shutil.which("mongosh"):
        correr(["mongosh", f"{URI}/{DB}", "--quiet", "--file", archivo], f"mongosh {archivo}")
    else:  # sin mongosh local: se usa el del contenedor leyendo el script por stdin
        p("  mongosh local no encontrado; se usa el del contenedor olimpiadas_mongo")
        correr(["docker", "exec", "-i", "olimpiadas_mongo", "mongosh", DB, "--quiet"], f"mongosh {archivo}",
               stdin_archivo=ruta)


def cargar_completo():
    paso(3, "Base vacia o incompleta (o --recargar): exportar, colecciones, carga, indices y validacion")
    p("  3a. Exportar de PostgreSQL a .jsonl")
    try:
        asegurar_postgres()
        correr([sys.executable, "02_exportar/exportar_postgres.py"], "exportar_postgres.py")
    except Falla as e:
        faltan = [a for a in ARCHIVOS_JSONL if not (JSONL / a).exists()]
        if faltan:
            raise Falla(f"{e}. Ademas faltan {', '.join(faltan)} en 02_exportar/data/")
        p(f"  AVISO: {e}. Se reutilizan los .jsonl existentes en 02_exportar/data/")
    p("  3b. Crear colecciones")
    mongosh("03_colecciones/crear_colecciones.js")
    p("  3c. Cargar")
    correr([sys.executable, "04_carga/cargar.py"], "cargar.py")
    p("  3d. Crear indices")
    mongosh("05_indices/crear_indices.js")
    validar()


def validar():
    p("  Validar")
    correr([sys.executable, "06_validacion/validar.py"], "validar.py (la base no coincide con la linea base)")


def ejemplos():
    paso(4, "Comandos de ejemplo (desde Fase 3/)")
    p('  python 07_consultas/atleta.py "Summer McIntosh"')
    p('  python 07_consultas/pais.py "Germany"')
    p(f'  mongosh "{URI}/{DB}" --eval "db.atletas.findOne({{nombre_key: \'usain bolt\'}})"')


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--recargar", action="store_true", help="rehace exportacion, carga e indices aunque ya haya datos")
    a = ap.parse_args()
    p(f"levantar_todo - inicio {inicio:%Y-%m-%d %H:%M:%S} | recargar={a.recargar}")
    codigo = 0
    try:
        verificar_requisitos()
        esperar_mongo()
        cuentas = conteos()
        p("  Conteos actuales:")
        mostrar_conteos(cuentas)
        if a.recargar or any(n == 0 for n in cuentas.values()):
            cargar_completo()
        else:
            paso(3, "La base ya tiene datos: solo se valida")
            validar()
        p("\n  Conteos finales:")
        mostrar_conteos(conteos())
        ejemplos()
        p(f"\nLISTO en {(datetime.now() - inicio).total_seconds():.0f} s")
    except Falla as e:
        p(f"\nERROR: {e}")
        codigo = 1
    except Exception as e:  # cualquier otra cosa: mensaje claro, sin traza larga
        p(f"\nERROR inesperado: {type(e).__name__}: {e}")
        codigo = 1
    finally:
        fin = datetime.now()
        p(f"fin {fin:%Y-%m-%d %H:%M:%S} | resultado {'OK' if codigo == 0 else 'FALLO'}")
        (RAIZ / "08_logs").mkdir(exist_ok=True)
        (RAIZ / "08_logs" / f"levantar_todo_{inicio:%Y-%m-%d_%H%M%S}.log").write_text(
            "\n".join(log) + "\n", encoding="utf-8")
    sys.exit(codigo)


if __name__ == "__main__":
    main()
