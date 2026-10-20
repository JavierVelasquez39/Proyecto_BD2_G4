"""Genera GUION_CALIFICACION.md ejecutando cada comando de la lista y resumiendo su salida real (solo lectura).

Uso: python generar_guion.py
Vuelve a correr todos los comandos, asi los tiempos y las salidas del guion son reales y reproducibles.
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

# (titulo, que demuestra, script, argumentos)
GUION = [
    ("Atleta conocido", "Detalle completo de un atleta: datos, medallas por atleta, participaciones y resultados desde un solo documento.", "atleta.py", ["Michael Phelps"]),
    ("Atleta con filtros de deporte y anio", "Filtros combinados; se usa el nombre completo del deporte.", "atleta.py", ["Michael Phelps", "--deporte", "Swimming (Aquatics)", "--anio", "2008"]),
    ("Atleta con filtro de pais", "El filtro de pais usa todos los NOC historicos del pais.", "atleta.py", ["Katie Ledecky", "--pais", "United States"]),
    ("Atleta con medallas de Paris 2024", "Muestra las medallas de Paris que estaban repartidas en dos registros antes de la fusion.", "atleta.py", ["Summer McIntosh"]),
    ("Atleta corregido (medalla que faltaba en la fuente)", "El oro de ruta de Paris 2024 fue una correccion (B1).", "atleta.py", ["Kristen Faulkner"]),
    ("Homonimos: modo CANDIDATO", "Dos personas con el mismo nombre: se listan, no se elige una.", "atleta.py", ["Jack Robinson"]),
    ("Homonimos: detalle por id", "Se elige uno de los candidatos con --id.", "atleta.py", ["Jack Robinson", "--id", "151209"]),
    ("Alias de un atleta fusionado", "Se busca con el nombre que traia la otra fuente y se encuentra al atleta historico.", "atleta.py", ["Shiyu Lu"]),
    ("Atleta con historia unificada (caso Fajdek)", "Cuatro ediciones, 2012 a 2024, bajo un solo atleta.", "atleta.py", ["Pawel Fajdek"]),
    ("Juegos de la Juventud: excluidos por defecto", "Sin --incluir-yog solo salen los Juegos adultos.", "atleta.py", ["Mariana Avitia"]),
    ("Juegos de la Juventud: con --incluir-yog", "Con la bandera aparecen las participaciones YOG.", "atleta.py", ["Mariana Avitia", "--incluir-yog"]),
    ("Atleta inexistente", "Modo SIN_COINCIDENCIAS.", "atleta.py", ["Nadie Inexistente"]),
    ("Pais multi-NOC y sedes", "Alemania agrega GER, FRG, GDR y SAA; lista sus sedes.", "pais.py", ["Germany"]),
    ("Pais con entidades historicas (URS y EUN)", "Rusia incluye URS y EUN como entidades historicas no atribuidas.", "pais.py", ["Russian Federation"]),
    ("Pais que nunca fue sede", "Resultado explicito NUNCA_SEDE, distinto de pais no encontrado.", "pais.py", ["Guatemala"]),
    ("Pais con historial de sedes", "Francia: seis ediciones como sede.", "pais.py", ["France"]),
    ("Pais con detalle paginado y filtros", "Participaciones y resultados, desde la coleccion participaciones con indice.", "pais.py", ["United States", "--anio", "2024", "--deporte", "Swimming (Aquatics)", "--detalle", "--tam", "8"]),
    ("Pais con Juegos de la Juventud incluidos", "Medallero total, con YOG.", "pais.py", ["Germany", "--incluir-yog"]),
    ("Entidad sin pais", "Taiwan (NOC TPE) existe como entidad aparte.", "pais.py", ["Taiwan"]),
    ("Plan de ejecucion de un atleta", "IXSCAN en la busqueda y IDHACK en el detalle; nunca COLLSCAN.", "atleta.py", ["Usain Bolt", "--explain"]),
    ("Plan de ejecucion de un pais", "IXSCAN sobre el indice compuesto de participaciones.", "pais.py", ["Japan", "--detalle", "--tam", "5", "--explain"]),
]
CLAVES_ATLETA = ("MODO:", "Alias", "Medallas", "Participaciones:", "   desglose")
CLAVES_PAIS = ("PAIS:", "ENTIDAD", "NOC asociados", "SEDE", "NUNCA_SEDE", "RESUMEN", "MEDALLAS", "EDICION ", "FILTRO", "DETALLE:", "PAIS_NO")


def correr(script, args):
    r = subprocess.run([sys.executable, str(AQUI / script), *args], capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=AQUI)
    return r.stdout


def resumir(salida, script):
    claves = CLAVES_ATLETA if script == "atleta.py" else CLAVES_PAIS
    out = []
    lineas = salida.splitlines()
    for i, l in enumerate(lineas):
        if "[explain" in l:
            out.append(l.strip())
        elif l.startswith(claves):
            out.append(l if len(l) <= 190 else l[:187] + "...")
        elif script == "atleta.py" and re.match(r"^\s*\d+\s{2}\S", l) and "CANDIDATO" in salida:
            out.append(l)
        elif re.match(r"^\d{4} ", l) and len([x for x in out if re.match(r"^\d{4} ", x)]) < 3:
            out.append(l if len(l) <= 190 else l[:187] + "...")
    t = next((l for l in lineas if l.startswith("Tiempo de respuesta")), "")
    if t:
        out.append(t)
    return out


def main():
    ahora = datetime.now()
    md = ["# Guion de calificacion", "",
          f"Comandos listos para copiar y salida esperada (resumida), ejecutados el {ahora:%Y-%m-%d %H:%M:%S}. Se corren desde la carpeta `Fase 3/` "
          "con MongoDB arriba (`docker compose -f 00_infraestructura/docker-compose.yml up -d`). Los tiempos son los de MongoDB "
          "(las consultas); el proceso completo de Python tarda cerca de 1 s en arrancar. Antes de empezar conviene correr una vez "
          "`python 07_consultas/evidencia_consultas.py` para calentar la cache.", "",
          "Reglas utiles: el nombre del pais va en ingles (convencion del Banco Mundial, \"Russian Federation\"); el deporte se escribe "
          "completo (\"Swimming (Aquatics)\"); la busqueda ignora acentos y mayusculas; los YOG solo salen con `--incluir-yog`; las "
          "medallas se muestran siempre como **por atleta** (criterio de la Fase 1) y **por evento** (oficial).", ""]
    for i, (titulo, demuestra, script, args) in enumerate(GUION, 1):
        cmd = f'python 07_consultas/{script} ' + " ".join(f'"{a}"' if (" " in a or a.startswith("(")) else a for a in args)
        salida = correr(script, args)
        md += [f"## {i}. {titulo}", "", demuestra, "", "```", cmd, "```", "", "Salida esperada (resumida):", "", "```"]
        md += resumir(salida, script) + ["```", ""]
    md += ["## Diferencias por diseno frente a las funciones de Postgres", "",
           "Las funciones de la Fase 1 (`fn_atleta_info`, `fn_pais_info`) y estos scripts dan los mismos resultados (comparacion cruzada en "
           "`06_validacion/`), salvo por cuatro diferencias deliberadas:", "",
           "- **Alias de atletas fusionados:** MongoDB encuentra a un atleta por el nombre con que aparecia en la otra fuente (\"Shiyu Lu\" lleva a Lu Shiyu); Postgres no.",
           "- **Taiwan como entidad:** los NOC sin pais (TPE, ROC, EOR y otros) existen en MongoDB como entidades consultables; la funcion de Postgres responde PAIS_NO_ENCONTRADO.",
           "- **`--anio` filtra las sedes:** `pais.py --anio N` muestra solo la sede de ese anio; la funcion de Postgres siempre lista todas.",
           "- **`--deporte` acepta prefijo:** `--deporte Swimming` equivale a `Swimming (Aquatics)`; Postgres exige el nombre completo.", "",
           "## Si algo falla", "", "- `Connection refused` en MongoDB: levantar Docker Desktop y `docker compose -f 00_infraestructura/docker-compose.yml up -d`.",
           "- Una consulta de pais responde `PAIS_NO_ENCONTRADO`: usar el nombre en ingles o el codigo NOC (`GER`, `USA`).",
           "- Un atleta famoso aparece con la historia incompleta: ver `01_correcciones/LIMITACIONES_CONOCIDAS.md` (hay pares de duplicados probables no fusionados, por ejemplo los de equipos grandes).",
           "- Validar toda la base: `python 06_validacion/validar.py`."]
    (AQUI / "GUION_CALIFICACION.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"GUION_CALIFICACION.md: {len(GUION)} comandos")


if __name__ == "__main__":
    main()
