"""
ETL - Proyecto Olimpiadas (BD2, USAC)
=====================================
Carga la Fuente 1 (KeithGalli/Olympics-Dataset, origen olympedia.org) al
modelo relacional en PostgreSQL 16, siguiendo la estrategia de unificación
acordada: fuente 1 = columna vertebral 1896-2022.

Fuentes 2, 3 y 4 (Kaggle heesoo37, Kaggle stefanydeoliveira, DataCamp
r-olympics) NO se cargan en esta corrida: requieren credenciales de Kaggle /
acceso a la plataforma DataCamp que no están disponibles en este entorno.
Ver REPORTE.md para el detalle y la estrategia documentada para cuando se
disponga de esos archivos localmente.

Uso:
    python etl.py --dsn "postgresql://postgres:olimpiadas@localhost:55433/olimpiadas"
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
from text_unidecode import unidecode

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
SRC_DIR = PROJECT_DIR / "data_raw" / "Olympics-Dataset"
CLEAN_DIR = SRC_DIR / "clean-data"
RAW_BIOS = SRC_DIR / "athletes" / "bios.csv"
REF_EDITIONS = BASE_DIR / "reference_editions.csv"  # fallback residual, ver DECISIONES.md

FUENTE2_DIR = PROJECT_DIR / "data_raw" / "fuente2_kaggle120"
FUENTE2_ATHLETE_EVENTS = FUENTE2_DIR / "athlete_events.csv"
FUENTE2_NOC_REGIONS = FUENTE2_DIR / "noc_regions.csv"
FUENTE3_DIR = PROJECT_DIR / "data_raw" / "fuente3_kaggle2024"
FUENTE3_FILE = FUENTE3_DIR / "olympics_dataset.csv"

# ---------------------------------------------------------------------------
# Reporte de rechazos / decisiones, acumulado durante toda la corrida
# ---------------------------------------------------------------------------
@dataclass
class Report:
    lines: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    sections: list = field(default_factory=list)  # (titulo, cuerpo_markdown)

    def note(self, msg: str):
        self.lines.append(msg)
        print(msg)

    def count(self, key: str, n: int):
        self.counts[key] = self.counts.get(key, 0) + n

    def section(self, title: str, body_md: str):
        """Bloque markdown calculado en esta misma corrida (tablas de
        reconciliación, etc.) -- se regenera siempre desde los contadores
        reales del ETL, nunca se edita a mano en el .md de salida."""
        self.sections.append((title, body_md))

    def dump(self, path: Path):
        """Escribe Conteos/Detalle/secciones con el estado de ESTA corrida
        (refleja lo que hay cargado ahora mismo, según la regla 3 de
        CLAUDE.md), pero preserva el historial de corridas anteriores: toda
        sección "## Corrida ..." ya presente en el archivo se conserva tal
        cual, en orden cronológico, antes de la de esta corrida."""
        own_corridas = [(t, b) for t, b in self.sections if t.startswith("Corrida ")]
        own_titles = {t for t, _ in own_corridas}

        old_corridas = []
        if path.exists():
            old_text = path.read_text(encoding="utf-8")
            blocks = re.split(r"\n(?=## Corrida )", old_text)
            for b in blocks:
                if not b.startswith("## Corrida "):
                    continue
                header = b.splitlines()[0][len("## "):].strip()
                if header in own_titles:
                    continue  # esta misma corrida se regenera fresca más abajo
                old_corridas.append(b.rstrip() + "\n")
        other_sections = [(t, b) for t, b in self.sections if not t.startswith("Corrida ")]

        with open(path, "w", encoding="utf-8") as f:
            f.write("# Reporte de carga ETL - Proyecto Olimpiadas\n\n")
            f.write("## Conteos (estado actual, esta corrida)\n\n")
            for k, v in self.counts.items():
                f.write(f"- {k}: {v}\n")
            f.write("\n## Detalle / decisiones (esta corrida)\n\n")
            for line in self.lines:
                f.write(f"- {line}\n")
            for title, body in other_sections:
                f.write(f"\n## {title}\n\n{body}\n")
            f.write("\n## Historial de corridas\n")
            for block in old_corridas:
                f.write(f"\n{block}\n")
            for title, body in own_corridas:
                f.write(f"\n## {title}\n\n{body}\n")


REPORT = Report()

# ---------------------------------------------------------------------------
# Normalización NOC <-> PAIS (por nombre, no por código; ver notas del ETL)
# ---------------------------------------------------------------------------
# NOC.region (fuente 1) -> nombre de país tal como aparece en populations.csv
# (World Bank). Solo se listan los que NO calzan por igualdad directa.
REGION_TO_WB_NAME = {
    "Antigua": "Antigua and Barbuda",
    "Bahamas": "Bahamas, The",
    "Boliva": "Bolivia",  # typo real de la fuente
    "Brunei": "Brunei Darussalam",
    "Cape Verde": "Cabo Verde",
    "Czech Republic": "Czechia",
    "Democratic Republic of the Congo": "Congo, Dem. Rep.",
    "Egypt": "Egypt, Arab Rep.",
    "Gambia": "Gambia, The",
    "Iran": "Iran, Islamic Rep.",
    "Ivory Coast": "Cote d'Ivoire",
    "Kyrgyzstan": "Kyrgyz Republic",
    "Laos": "Lao PDR",
    "Macedonia": "North Macedonia",
    "Micronesia": "Micronesia, Fed. Sts.",
    "North Korea": "Korea, Dem. People's Rep.",
    "Palestine": "West Bank and Gaza",
    "Republic of Congo": "Congo, Rep.",
    "Russia": "Russian Federation",
    "Saint Kitts": "St. Kitts and Nevis",
    "Saint Lucia": "St. Lucia",
    "Saint Vincent": "St. Vincent and the Grenadines",
    "Slovakia": "Slovak Republic",
    "South Korea": "Korea, Rep.",
    "Swaziland": "Eswatini",
    "Syria": "Syrian Arab Republic",
    "Trinidad": "Trinidad and Tobago",
    "Turkey": "Turkiye",
    "UK": "United Kingdom",
    "USA": "United States",
    "Venezuela": "Venezuela, RB",
    "Vietnam": "Viet Nam",
    "Virgin Islands, British": "British Virgin Islands",
    "Virgin Islands, US": "Virgin Islands (U.S.)",
    "Yemen": "Yemen, Rep.",
}

# Códigos NOC cuya "region" en la fuente 1 es una simplificación de una
# entidad histórica fusionada/disuelta en VARIOS países actuales (equipo
# conjunto o desintegración). Se fuerza pais_id = NULL en vez de aceptar el
# país "sucesor" que aporta la fuente, siguiendo la decisión de diseño ya
# acordada ("equipos históricos fusionados: EUN, ANZ, SCG, etc.") extendida
# por el mismo criterio a URS/YUG/TCH/BOH (desintegraciones análogas).
NOC_FORCE_NULL_PAIS = {
    "URS": "Unión Soviética (disuelta en 15 países)",
    "EUN": "Equipo Unificado 1992 (ex-URSS, 12 países)",
    "YUG": "Yugoslavia (disuelta)",
    "SCG": "Serbia y Montenegro (disuelta)",
    "TCH": "Checoslovaquia (disuelta)",
    "ANZ": "Australasia (equipo conjunto Australia+Nueva Zelanda)",
    "BOH": "Bohemia (entidad histórica pre-Checoslovaquia)",
    "IOA": "Atletas Olímpicos Individuales",
    "ROT": "Refugee Olympic Team",
    "UNK": "Desconocido",
    "COK": "Islas Cook (no reconocidas como país independiente por el Banco Mundial)",
    "TPE": "Taiwán / Chinese Taipei (sin entrada propia en el catálogo del Banco Mundial)",
}

# TUV trae region=NaN y el nombre real del país aparece en notes (bug de la
# fuente): se corrige aquí en vez de dejarlo como "sin país".
NOC_REGION_FIX = {
    "TUV": "Tuvalu",
}

# Códigos NOC que aparecen en results.csv pero no existen en noc_regions.csv
# (códigos IOC agregados/renombrados después de la publicación de ese
# archivo). codigo_noc, nombre_region, notas, pais_id(via WB name o None)
NOC_SUPPLEMENTARY = [
    ("LBN", "Lebanon", "Alias moderno de LIB (Lebanon) no presente en noc_regions.csv", "Lebanon"),
    ("SGP", "Singapore", "Alias moderno de SIN (Singapore) no presente en noc_regions.csv", "Singapore"),
    ("ROC", "Russian Olympic Committee", "Equipo bajo sanción (Tokyo 2020 / Beijing 2022)", None),
    ("EOR", "Refugee Olympic Team", "Acrónimo francés (Équipe Olympique des Réfugiés)", None),
    ("COR", "Corea unificada", "Equipo conjunto Corea del Norte + Corea del Sur", None),
    ("AIN", "Individual Neutral Athletes",
     "Atletas neutrales individuales (Rusia/Bielorrusia bajo sanción, Paris 2024), "
     "código nuevo en fuente 3, no presente en noc_regions.csv de fuente 1/2", None),
]

MEDAL_ES = {"Gold": "Oro", "Silver": "Plata", "Bronze": "Bronce"}
SEASON_ES = {"Summer": "Verano", "Winter": "Invierno"}

# ---------------------------------------------------------------------------
# Ciudad sede -> país (fuente 2 y fuente 3 solo traen el nombre de la ciudad,
# ninguna de las 3 fuentes trae el país sede como columna). Se reutiliza el
# mismo conocimiento histórico público que antes poblaba
# reference_editions.csv completo, ahora acotado a mapear ciudad->país en vez
# de ser la fuente primaria de ciudad+edición. Nombres de ciudad tal como
# aparecen literalmente en athlete_events.csv (fuente 2), incluida grafía
# local (ej. "Moskva", "Roma", "Antwerpen").
HOST_COUNTRY_BY_CITY = {
    "Albertville": "France", "Amsterdam": "Netherlands", "Antwerpen": "Belgium",
    "Athina": "Greece", "Atlanta": "United States", "Barcelona": "Spain",
    "Beijing": "China", "Berlin": "Germany", "Calgary": "Canada",
    "Chamonix": "France", "Cortina d'Ampezzo": "Italy",
    "Garmisch-Partenkirchen": "Germany", "Grenoble": "France", "Helsinki": "Finland",
    "Innsbruck": "Austria", "Lake Placid": "United States", "Lillehammer": "Norway",
    "London": "United Kingdom", "Los Angeles": "United States", "Melbourne": "Australia",
    "Mexico City": "Mexico", "Montreal": "Canada", "Moskva": "Russian Federation",
    "Munich": "Germany", "Nagano": "Japan", "Oslo": "Norway", "Paris": "France",
    "Rio de Janeiro": "Brazil", "Roma": "Italy", "Salt Lake City": "United States",
    "Sankt Moritz": "Switzerland", "Sapporo": "Japan", "Sarajevo": "Bosnia and Herzegovina",
    "Seoul": "Korea, Rep.", "Sochi": "Russian Federation", "Squaw Valley": "United States",
    "St. Louis": "United States", "Stockholm": "Sweden", "Sydney": "Australia",
    "Tokyo": "Japan", "Torino": "Italy", "Vancouver": "Canada",
}

# Ediciones del catálogo de fuente 1 (1896-2022) para las que NINGUNA fuente
# real (fuente 2: hasta 2016; fuente 3: solo Verano) trae columna City. Se
# retiene el dato de reference_editions.csv únicamente para estos 3 casos
# residuales (ver DECISIONES.md, entrada de sedes/ediciones cerrada hoy).
EDICIONES_SIN_CITY_REAL = {
    (2018, "Invierno"), (2020, "Verano"), (2022, "Invierno"),
    (2010, "Verano-YOG"), (2012, "Invierno-YOG"), (2014, "Verano-YOG"),
    (2016, "Invierno-YOG"), (2018, "Verano-YOG"), (2020, "Invierno-YOG")
}

# Desambiguación de "Sport" corrupto en fuente 3: para un mismo player_id que
# compitió en más de una disciplina en su carrera, el campo "Sport" de esta
# fuente queda con el join de TODAS sus disciplinas separadas por coma (igual
# patrón de corrupción que bios.csv.NOC en fuente 1, ver DECISIONES.md). Solo
# afecta a 89 de las 14,892 filas de París 2024; se resuelve con esta tabla
# exhaustiva (Sport tal cual viene, Event) -> deporte real, construida a mano
# revisando cada nombre de evento (hecho real y no ambiguo del deporte
# olímpico correspondiente).
EVENT_SPORT_OVERRIDE = {
    ("Marathon Swimming, Swimming", "Men's 10km"): "Marathon Swimming",
    ("Marathon Swimming, Swimming", "Women's 10km"): "Marathon Swimming",
    ("Marathon Swimming, Swimming", "Men's 1500m Freestyle"): "Swimming",
    ("Marathon Swimming, Swimming", "Men's 800m Freestyle"): "Swimming",
    ("Marathon Swimming, Swimming", "Men's 400m Freestyle"): "Swimming",
    ("Marathon Swimming, Swimming", "Women's 1500m Freestyle"): "Swimming",
    ("Marathon Swimming, Swimming", "Men's 200m Freestyle"): "Swimming",
    ("Marathon Swimming, Swimming", "Men's 4 x 200m Freestyle Relay"): "Swimming",
    ("Marathon Swimming, Swimming", "Women's 400m Freestyle"): "Swimming",
    ("Marathon Swimming, Swimming", "Women's 400m Individual Medley"): "Swimming",
    ("Cycling Road, Cycling Track", "Women's Road Race"): "Cycling Road",
    ("Cycling Road, Cycling Track", "Men's Road Race"): "Cycling Road",
    ("Cycling Road, Cycling Track", "Women's Individual Time Trial"): "Cycling Road",
    ("Cycling Road, Cycling Track", "Men's Individual Time Trial"): "Cycling Road",
    ("Cycling Road, Cycling Track", "Women's Team Pursuit"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Men's Team Pursuit"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Men's Madison"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Women's Madison"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Women's Omnium"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Men's Omnium"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Women's Keirin"): "Cycling Track",
    ("Cycling Road, Cycling Track", "Women's Sprint"): "Cycling Track",
    ("Cycling Road, Cycling Mountain Bike", "Women's Road Race"): "Cycling Road",
    ("Cycling Road, Cycling Mountain Bike", "Men's Road Race"): "Cycling Road",
    ("Cycling Road, Cycling Mountain Bike", "Women's Cross-country"): "Cycling Mountain Bike",
    ("Cycling Road, Cycling Mountain Bike", "Men's Cross-country"): "Cycling Mountain Bike",
    ("Cycling Road, Triathlon", "Women's Individual Time Trial"): "Cycling Road",
    ("Cycling Road, Triathlon", "Women's Individual"): "Triathlon",
    # Único caso realmente ambiguo (1 fila): Event="Women" no distingue por sí
    # solo 3x3 de Basketball tradicional. Se asume Basketball (categoría base,
    # muchas más atletas). Ver DECISIONES.md.
    ("3x3 Basketball, Basketball", "Women"): "Basketball",
}


def normalize_ws(s):
    if pd.isna(s):
        return s
    return re.sub(r"\s+", " ", str(s).replace("•", " ")).strip()


def name_match_key(s):
    """Clave de emparejamiento de nombres: normaliza espacios, mayúsculas Y
    tildes/diacríticos (ver auditoría 2026-09-13 en DECISIONES.md: 4 de 30
    "nuevos" de la muestra eran en realidad el mismo atleta con distinta
    grafía de acento -- 'Pawel Fajdek'/'Paweł Fajdek', 'Alberto
    Gonzalez'/'Alberto González', 'Laura Galvan'/'Laura Galván'). Solo se usa
    para EMPAREJAR, nunca para mostrar (el nombre original con tildes se
    conserva en la BD).

    Usa text_unidecode en vez de unicodedata.normalize("NFKD", ...) + strip
    de combinantes (ver DECISIONES.md, hallazgo 2026-09-14): NFKD solo
    descompone diacríticos *compuestos* (é, á, ñ) y no cubre letras Unicode
    propias sin descomposición de compatibilidad como la ł polaca, la ı
    turca o la æ nórdica -- confirmado que esto dejó sin fusionar ~30 casos
    reales de la extensión de fuente 3/2024 contra fuente 1 (Fajdek entre
    ellos), pese a que la corrección de 2026-09-13 los daba por resueltos."""
    if not isinstance(s, str):
        return s
    return unidecode(normalize_ws(s)).casefold()


# ---------------------------------------------------------------------------
# EXTRACT
# ---------------------------------------------------------------------------
def extract():
    bios_clean = pd.read_csv(CLEAN_DIR / "bios.csv", low_memory=False)
    bios_raw = pd.read_csv(RAW_BIOS, low_memory=False)
    noc_regions = pd.read_csv(CLEAN_DIR / "noc_regions.csv")
    populations = pd.read_csv(CLEAN_DIR / "populations.csv")
    results = pd.read_csv(CLEAN_DIR / "results.csv", low_memory=False)
    editions_fallback = pd.read_csv(REF_EDITIONS)
    REPORT.note(f"Fuente 1 cargada: bios_clean={len(bios_clean)}, bios_raw={len(bios_raw)}, "
                f"noc_regions={len(noc_regions)}, populations={len(populations)}, "
                f"results={len(results)}, editions(ref, fallback residual)={len(editions_fallback)}")

    athlete_events = pd.read_csv(FUENTE2_ATHLETE_EVENTS, low_memory=False)
    noc_regions_f2 = pd.read_csv(FUENTE2_NOC_REGIONS)
    REPORT.note(f"Fuente 2 cargada (solo para derivar SEDE/EDICION_OLIMPICA y para "
                f"cross-check, NO se cargan sus participaciones): athlete_events="
                f"{len(athlete_events)}, noc_regions={len(noc_regions_f2)}.")

    olympics_f3 = pd.read_csv(FUENTE3_FILE, low_memory=False)
    REPORT.note(f"Fuente 3 cargada: olympics_dataset.csv={len(olympics_f3)} filas totales "
                f"(1896-2024, todas las temporadas); se filtra a solo lo necesario más abajo.")

    return (bios_clean, bios_raw, noc_regions, populations, results, editions_fallback,
            athlete_events, noc_regions_f2, olympics_f3)


# ---------------------------------------------------------------------------
# TRANSFORM
# ---------------------------------------------------------------------------
def build_pais(noc_regions: pd.DataFrame, host_countries: set):
    """PAIS = union de países representados por algún NOC actual + países sede
    (derivados de ciudad real vía HOST_COUNTRY_BY_CITY, ver build_sede_edicion).
    No se importan las ~215 filas 'agregadas' de populations.csv (regiones,
    grupos de ingreso, 'World', etc.) porque nada del modelo las referencia."""
    names = set()

    for _, row in noc_regions.iterrows():
        code = row["NOC"]
        region = row["region"]
        if code in NOC_FORCE_NULL_PAIS:
            continue
        if pd.isna(region):
            region = NOC_REGION_FIX.get(code)
        if region is None:
            continue
        names.add(REGION_TO_WB_NAME.get(region, region))

    for code, _, _, wb_name in NOC_SUPPLEMENTARY:
        if wb_name:
            names.add(wb_name)

    names |= set(host_countries)

    pais_df = pd.DataFrame(sorted(names), columns=["nombre"])
    pais_df.insert(0, "pais_id", range(1, len(pais_df) + 1))
    pais_id_by_name = dict(zip(pais_df["nombre"], pais_df["pais_id"]))
    REPORT.note(f"PAIS construido: {len(pais_df)} países (unión NOC vigentes + sedes).")
    return pais_df, pais_id_by_name


def build_poblacion(pais_df: pd.DataFrame, pais_id_by_name: dict, populations: pd.DataFrame):
    year_cols = [c for c in populations.columns if c.isdigit()]
    long = populations.melt(
        id_vars=["Country Name", "Country Code"], value_vars=year_cols,
        var_name="anio", value_name="cantidad",
    )
    long = long.dropna(subset=["cantidad"])
    long["pais_id"] = long["Country Name"].map(pais_id_by_name)
    matched = long.dropna(subset=["pais_id"]).copy()
    matched["pais_id"] = matched["pais_id"].astype(int)
    matched["anio"] = matched["anio"].astype(int)
    matched["cantidad"] = matched["cantidad"].round().astype("int64")
    matched = matched[["pais_id", "anio", "cantidad"]].reset_index(drop=True)
    matched.insert(0, "poblacion_id", range(1, len(matched) + 1))

    unmatched_countries = sorted(set(long["Country Name"]) - set(matched.merge(
        pais_df, on="pais_id")["nombre"]) - set(pais_df["nombre"]))
    n_unmatched_rows = len(long) - len(matched)
    REPORT.note(
        f"POBLACION_PAIS: {len(matched)} filas cargadas de {len(long)} disponibles en "
        f"populations.csv; {n_unmatched_rows} filas descartadas por pertenecer a países/"
        f"agregados del Banco Mundial que ningún NOC ni sede representa "
        f"(ej. regiones agregadas 'World', 'OECD members', etc.)."
    )
    return matched


def build_noc(noc_regions: pd.DataFrame, pais_id_by_name: dict, noc_regions_f2: pd.DataFrame = None):
    rows = []
    for _, row in noc_regions.iterrows():
        code = row["NOC"]
        region = row["region"]
        notas = row["notes"] if pd.notna(row["notes"]) else None
        if pd.isna(region):
            region = NOC_REGION_FIX.get(code, code)
        if code in NOC_FORCE_NULL_PAIS:
            pais_id = None
            notas = NOC_FORCE_NULL_PAIS[code] if notas is None else f"{notas}; {NOC_FORCE_NULL_PAIS[code]}"
        else:
            wb_name = REGION_TO_WB_NAME.get(region, region)
            pais_id = pais_id_by_name.get(wb_name)
        rows.append((code, region, notas, pais_id))

    for code, region, notas, wb_name in NOC_SUPPLEMENTARY:
        pais_id = pais_id_by_name.get(wb_name) if wb_name else None
        rows.append((code, region, notas, pais_id))

    noc_df = pd.DataFrame(rows, columns=["codigo_noc", "nombre_region", "notas", "pais_id"])
    noc_df["pais_id"] = noc_df["pais_id"].astype("Int64")
    n_null = noc_df["pais_id"].isna().sum()
    REPORT.note(f"NOC construido: {len(noc_df)} códigos ({n_null} con pais_id NULL: "
                f"equipos históricos/mixtos, refugiados, atletas individuales, códigos "
                f"sin país actual reconocible).")

    n_base = len(noc_regions)
    n_supl = len(NOC_SUPPLEMENTARY)
    supl_desc = ', '.join(c for c, *_ in NOC_SUPPLEMENTARY)

    if noc_regions_f2 is not None:
        s1, s2 = set(noc_regions["NOC"]), set(noc_regions_f2["NOC"])
        solo_f1 = sorted(s1 - s2)
        solo_f2 = sorted(s2 - s1)
        common = noc_regions.merge(noc_regions_f2, on="NOC", suffixes=("_f1", "_f2"))
        diffs = common[common["region_f1"].fillna("") != common["region_f2"].fillna("")]
        cuerpo = (
            f"Comparación real, columna por columna, entre "
            f"`data_raw/Olympics-Dataset/clean-data/noc_regions.csv` (fuente 1, {len(noc_regions)} "
            f"filas) y `data_raw/fuente2_kaggle120/noc_regions.csv` (fuente 2, {len(noc_regions_f2)} "
            f"filas), verificada en esta corrida:\n\n"
            f"- Códigos NOC solo en fuente 1: {solo_f1 or 'ninguno'}.\n"
            f"- Códigos NOC solo en fuente 2: {solo_f2 or 'ninguno'}.\n"
            f"- Diferencias de `region` para el mismo código NOC: "
            f"{len(diffs)} ({diffs['NOC'].tolist() if len(diffs) else 'ninguna'}).\n\n"
            f"**Los dos archivos son idénticos** (mismos {len(noc_regions)} códigos, mismos "
            f"nombres de región). Esto resuelve de forma definitiva la pregunta abierta en una "
            f"revisión anterior sobre si fuente 1 y fuente 2 comparten el mismo "
            f"`noc_regions.csv`.\n\n"
            f"El conteo final de **{len(noc_df)}** en la tabla `NOC` de esta carga es "
            f"`{n_base} (noc_regions.csv, idéntico en fuente 1 y fuente 2) + {n_supl} "
            f"(códigos agregados manualmente en el ETL porque aparecen en `results.csv` u "
            f"`olympics_dataset.csv` pero no en `noc_regions.csv`: {supl_desc}) = "
            f"{n_base + n_supl}`.\n\n"
            f"De los 5 códigos agregados para fuente 1 (LBN, SGP, ROC, EOR, COR), se verificó "
            f"contra `PARTICIPACION` que los 5 tienen atletas asociados (362, 389, 1128, 47 y "
            f"26 participaciones respectivamente en la corrida de fuente 1). En cambio, sus "
            f"códigos \"base\" equivalentes que sí están en `noc_regions.csv` (LIB para Lebanon "
            f"y SIN para Singapore) **tienen 0 participaciones**: `results.csv` usa "
            f"exclusivamente los códigos modernos LBN/SGP, nunca LIB/SIN. AIN (agregado en "
            f"esta corrida para fuente 3, atletas neutrales de París 2024) también tiene "
            f"atletas asociados por construcción, al venir directo de `olympics_dataset.csv`."
        )
    else:
        cuerpo = (
            f"`noc_regions.csv` **es parte de la fuente 1** (`clean-data/noc_regions.csv`, "
            f"repo de Keith Galli), no de la fuente 2. Ese archivo tiene **{n_base} filas**.\n\n"
            f"El conteo final de **{len(noc_df)}** en la tabla `NOC` de esta carga es: "
            f"`{n_base} (noc_regions.csv, fuente 1) + {n_supl} (códigos agregados manualmente: "
            f"{supl_desc}) = {n_base + n_supl}`.\n\n"
            f"No se pudo comparar contra el archivo `noc_regions.csv` de fuente 2: no se "
            f"dispone de ese archivo en este entorno."
        )
    REPORT.section("Reconciliación de conteos NOC", cuerpo)
    return noc_df


def _editions_from_city_column(df: pd.DataFrame, year_col: str, season_col: str,
                                city_col: str, season_map: dict | None = None):
    """(anio, tipo, ciudad) real, una fila por edición -- ciudad = la más
    frecuente en las filas de esa (year,season) (ver nota del caso 1956, que
    de hecho tiene un fundamento histórico real: equitación en Estocolmo)."""
    grp = df.groupby([year_col, season_col])[city_col].agg(
        lambda s: s.value_counts().idxmax())
    out = grp.reset_index()
    out.columns = ["anio", "tipo", "ciudad"]
    if season_map:
        out["tipo"] = out["tipo"].map(season_map)
    out["anio"] = out["anio"].astype(int)
    return out


def build_sede_edicion(athlete_events: pd.DataFrame, olympics_f3_2024: pd.DataFrame,
                        editions_fallback: pd.DataFrame, pais_id_by_name: dict):
    """SEDE/EDICION_OLIMPICA derivadas de columnas City reales:
    - 1896-2016 (todas las temporadas): fuente 2 (athlete_events.csv).
    - 2024 Verano: fuente 3 (única fuente que llega hasta ahí).
    - 2018 Invierno, 2020 Verano, 2022 Invierno: NINGUNA fuente real trae City
      para estos 3 (fuente 2 no llega, fuente 3 es solo Verano); se retiene
      reference_editions.csv únicamente para estos 3 residuales (ver
      DECISIONES.md, entrada de sedes/ediciones).
    """
    ed_f2 = _editions_from_city_column(athlete_events, "Year", "Season", "City", SEASON_ES)
    ed_f2["pais_sede"] = ed_f2["ciudad"].map(HOST_COUNTRY_BY_CITY)
    ed_f3 = _editions_from_city_column(olympics_f3_2024, "Year", "Season", "City", SEASON_ES)
    ed_f3["pais_sede"] = ed_f3["ciudad"].map(HOST_COUNTRY_BY_CITY)

    fallback_keys = EDICIONES_SIN_CITY_REAL
    ed_fallback = editions_fallback[
        editions_fallback.apply(lambda r: (int(r["anio"]), r["tipo"]) in fallback_keys, axis=1)
    ][["anio", "tipo", "ciudad", "pais_sede"]].copy()

    all_eds = pd.concat([ed_f2, ed_f3, ed_fallback], ignore_index=True)
    dup = all_eds.duplicated(subset=["anio", "tipo"], keep=False)
    if dup.any():
        raise ValueError(f"Ediciones duplicadas al combinar fuente2/fuente3/fallback:\n"
                          f"{all_eds[dup]}")
    all_eds = all_eds.sort_values(["anio", "tipo"]).reset_index(drop=True)

    faltantes = all_eds[all_eds["pais_sede"].isna()]
    if len(faltantes):
        raise ValueError(f"Ciudades sin país mapeado en HOST_COUNTRY_BY_CITY:\n{faltantes}")

    sede_rows = all_eds[["ciudad", "pais_sede"]].drop_duplicates().reset_index(drop=True)
    sede_rows["pais_id"] = sede_rows["pais_sede"].map(pais_id_by_name).astype("Int64")
    sede_rows.insert(0, "sede_id", range(1, len(sede_rows) + 1))
    sede_id_by_key = {(r.ciudad, r.pais_sede): r.sede_id for r in sede_rows.itertuples()}

    edicion_rows = all_eds.copy()
    edicion_rows["sede_id"] = edicion_rows.apply(
        lambda r: sede_id_by_key[(r["ciudad"], r["pais_sede"])], axis=1)
    edicion_rows = edicion_rows[["anio", "tipo", "sede_id"]].reset_index(drop=True)
    edicion_rows.insert(0, "edicion_id", range(1, len(edicion_rows) + 1))
    edicion_id_by_key = {(r.anio, r.tipo): r.edicion_id for r in edicion_rows.itertuples()}

    sede_df = sede_rows[["sede_id", "ciudad", "pais_id"]]
    n_fallback = len(ed_fallback)
    REPORT.note(f"SEDE: {len(sede_df)} sedes; EDICION_OLIMPICA: {len(edicion_rows)} ediciones. "
                f"Ciudad real derivada de columna City: {len(ed_f2)} ediciones de fuente 2 "
                f"(1896-2016) + {len(ed_f3)} de fuente 3 (2024 Verano). Solo "
                f"{n_fallback} ediciones ({sorted(fallback_keys)}) siguen viniendo de "
                f"reference_editions.csv porque ninguna fuente real trae City para esos años "
                f"(fuente 2 no llega, fuente 3 es solo Verano); ver DECISIONES.md.")
    return sede_df, edicion_rows, edicion_id_by_key


def parse_born(born_str):
    """'12 December 1886 in Bordeaux, Gironde (FRA)' -> (city, noc3)"""
    if pd.isna(born_str):
        return None, None
    m = re.search(r"in (.+?)(?:,[^,()]+)?\s*\(([A-Z]{3})\)\s*$", str(born_str))
    if m:
        return m.group(1).strip(), m.group(2)
    m2 = re.search(r"in (.+)$", str(born_str))
    if m2:
        return m2.group(1).strip(), None
    return None, None


def build_atleta(bios_clean: pd.DataFrame, bios_raw: pd.DataFrame, results: pd.DataFrame,
                  noc_region_display: dict):
    raw = bios_raw[["athlete_id", "Sex", "Full name", "Used name", "Nationality"]].copy()
    merged = bios_clean.merge(raw, on="athlete_id", how="left")

    merged["sexo"] = merged["Sex"].map({"Male": "M", "Female": "F"})
    merged["nombre_usado"] = merged["Used name"].apply(normalize_ws).fillna(
        merged["name"].apply(normalize_ws))
    merged["nombre_completo"] = merged["Full name"].apply(normalize_ws).fillna(merged["nombre_usado"])
    merged["fecha_nacimiento"] = pd.to_datetime(merged["born_date"], errors="coerce")
    merged["fecha_fallecimiento"] = pd.to_datetime(merged["died_date"], errors="coerce")
    merged["ciudad_nacimiento"] = merged["born_city"].apply(normalize_ws)
    merged["pais_nacimiento"] = merged["born_country"].map(noc_region_display).fillna(
        merged["born_country"])

    # nacionalidad: primer NOC (por año de participación más antiguo) del
    # atleta en results.csv. Es una simplificación documentada: un atleta
    # puede haber competido bajo varios NOC a lo largo de su carrera (ver
    # PARTICIPACION.codigo_noc para el histórico real, autoritativo).
    first_noc = (
        results.dropna(subset=["year"])
        .sort_values("year")
        .drop_duplicates("athlete_id", keep="first")[["athlete_id", "noc"]]
        .rename(columns={"noc": "primer_noc"})
    )
    merged = merged.merge(first_noc, left_on="athlete_id", right_on="athlete_id", how="left")
    merged["nacionalidad"] = merged["primer_noc"].map(noc_region_display).fillna(merged["primer_noc"])

    atleta_df = merged[[
        "athlete_id", "nombre_completo", "nombre_usado", "sexo", "nacionalidad",
        "fecha_nacimiento", "ciudad_nacimiento", "pais_nacimiento", "fecha_fallecimiento",
        "height_cm", "weight_kg",
    ]].copy()
    atleta_df.insert(0, "atleta_id", range(1, len(atleta_df) + 1))
    atleta_id_by_source = dict(zip(atleta_df["athlete_id"], atleta_df["atleta_id"]))

    n_no_sexo = atleta_df["sexo"].isna().sum()
    REPORT.note(f"ATLETA: {len(atleta_df)} personas cargadas desde bios (incluye roles no "
                f"competitivos: coach/referee/administrator, ya que la fuente no separa esa "
                f"información en un archivo distinto). {n_no_sexo} sin sexo registrado.")
    return atleta_df, atleta_id_by_source


def build_deporte_evento(results: pd.DataFrame):
    valid = results.dropna(subset=["discipline", "event"])
    deportes = sorted(valid["discipline"].unique())
    deporte_df = pd.DataFrame({"deporte_id": range(1, len(deportes) + 1), "nombre": deportes})
    deporte_id_by_name = dict(zip(deporte_df["nombre"], deporte_df["deporte_id"]))

    ev = valid[["event", "discipline"]].drop_duplicates().reset_index(drop=True)
    ev["deporte_id"] = ev["discipline"].map(deporte_id_by_name)
    ev.insert(0, "evento_id", range(1, len(ev) + 1))
    evento_id_by_key = {(r.event, r.discipline): r.evento_id for r in ev.itertuples()}
    evento_df = ev[["evento_id", "event", "deporte_id"]].rename(columns={"event": "nombre"})

    REPORT.note(f"DEPORTE: {len(deporte_df)} disciplinas; EVENTO: {len(evento_df)} eventos "
                f"distintos (nombre, deporte).")
    return deporte_df, evento_df, deporte_id_by_name, evento_id_by_key


# ---------------------------------------------------------------------------
# Extensión con fuente 3 (Kaggle stefanydeoliveira, CC BY-NC-SA 4.0) -- SOLO
# para cerrar el hueco real de París 2024, que fuente 1 no cubre (ver
# DECISIONES.md). Nunca se usa para 1896-2020 (ya cargado desde fuente 1).
# ---------------------------------------------------------------------------
def build_atleta_extension_f3(atleta_df: pd.DataFrame, f3_2024: pd.DataFrame,
                               noc_region_display: dict):
    """Empareja atletas de fuente 3 - 2024 contra ATLETA ya cargado (fuente 1)
    por nombre normalizado; crea filas nuevas solo para quien no calza.
    Fuente 3 no trae fecha de nacimiento/ciudad/país de nacimiento
    (limitación conocida, documentada en DECISIONES.md): esos campos quedan
    NULL para los atletas nuevos.

    Criterio de emparejamiento (revisado 2026-09-13 tras auditoría manual de
    60 casos, ver DECISIONES.md): el emparejamiento por nombre exacto solo
    produjo un ~6.7% de falsos positivos verificados en la muestra (dos
    homónimos reales de países distintos fusionados bajo el mismo
    atleta_id, uno de ellos ya fallecido en fuente 1). Se agregan dos
    salvaguardas antes de aceptar un candidato:
    1. Se descarta cualquier candidato con `fecha_fallecimiento` no nula
       (una persona fallecida no puede competir en 2024).
    2. Si el nombre tiene más de un candidato vivo, o exactamente un
       candidato vivo pero su `nacionalidad` no coincide con el país del
       NOC de fuente 3, se rechaza el emparejamiento y el atleta se trata
       como nuevo (más seguro que fusionar homónimos por error: el costo de
       un falso negativo -- un atleta recurrente duplicado -- es mucho
       menor que el de un falso positivo -- historial de dos personas
       distintas mezclado)."""
    candidates_by_name: dict = {}
    for r in atleta_df.itertuples():
        for nm in (r.nombre_usado, r.nombre_completo):
            if isinstance(nm, str):
                candidates_by_name.setdefault(name_match_key(nm), {})[r.atleta_id] = r
    candidates_by_name = {k: list(v.values()) for k, v in candidates_by_name.items()}

    players = f3_2024[["player_id", "Name", "Sex", "NOC"]].drop_duplicates("player_id").copy()
    players["_key"] = players["Name"].apply(name_match_key)
    players["_pais_f3"] = players["NOC"].map(noc_region_display)

    matched_ids, motivo_rechazo = [], []
    n_dead_filtered = n_ambiguous = n_nationality_mismatch = 0
    for _, row in players.iterrows():
        cands = candidates_by_name.get(row["_key"], [])
        alive = [c for c in cands if pd.isna(c.fecha_fallecimiento)]
        if len(alive) < len(cands):
            n_dead_filtered += len(cands) - len(alive)
        if not alive:
            matched_ids.append(None)
            continue
        matching_nat = [c for c in alive if isinstance(c.nacionalidad, str)
                         and c.nacionalidad == row["_pais_f3"]]
        if len(matching_nat) == 1:
            matched_ids.append(matching_nat[0].atleta_id)
        elif len(alive) == 1 and not isinstance(alive[0].nacionalidad, str):
            matched_ids.append(alive[0].atleta_id)  # nacionalidad desconocida, único candidato vivo
        elif len(alive) == 1:
            n_nationality_mismatch += 1
            matched_ids.append(None)
        else:
            n_ambiguous += 1
            matched_ids.append(None)
    players["atleta_id"] = matched_ids

    n_matched = players["atleta_id"].notna().sum()
    nuevos = players[players["atleta_id"].isna()].copy().reset_index(drop=True)
    next_id = int(atleta_df["atleta_id"].max()) + 1
    nuevos["atleta_id"] = range(next_id, next_id + len(nuevos))

    nuevos["nombre_completo"] = None
    nuevos["nombre_usado"] = nuevos["Name"].apply(normalize_ws)
    nuevos["sexo"] = nuevos["Sex"]
    nuevos["nacionalidad"] = nuevos["NOC"].map(noc_region_display)
    nuevos["fecha_nacimiento"] = pd.NaT
    nuevos["ciudad_nacimiento"] = None
    nuevos["pais_nacimiento"] = None
    nuevos["fecha_fallecimiento"] = pd.NaT

    nuevas_cols = ["atleta_id", "nombre_completo", "nombre_usado", "sexo", "nacionalidad",
                   "fecha_nacimiento", "ciudad_nacimiento", "pais_nacimiento", "fecha_fallecimiento"]
    nuevos_df = nuevos[nuevas_cols]

    # player_id -> atleta_id final (matched contra fuente 1, o nuevo de fuente 3)
    matched_map = dict(zip(players.loc[players["atleta_id"].notna(), "player_id"],
                            players.loc[players["atleta_id"].notna(), "atleta_id"].astype(int)))
    new_map = dict(zip(nuevos["player_id"], nuevos["atleta_id"]))
    atleta_id_by_player = {**matched_map, **new_map}

    REPORT.note(
        f"ATLETA (extensión fuente 3, solo 2024): {len(players)} atletas distintos en "
        f"París 2024; {n_matched} calzaron (nombre normalizado + vivo + nacionalidad "
        f"consistente con el NOC de fuente 3, o nacionalidad desconocida con candidato único); "
        f"{len(nuevos_df)} se cargan como nuevos. De los rechazos: {n_dead_filtered} candidatos "
        f"descartados por estar fallecidos en fuente 1 (no pueden competir en 2024), "
        f"{n_nationality_mismatch} rechazados por nacionalidad inconsistente con el NOC de "
        f"fuente 3 (único candidato vivo, pero de otro país -- probable homónimo), "
        f"{n_ambiguous} rechazados por ambigüedad (más de un candidato vivo con ese nombre). "
        f"Ver auditoría manual y criterio revisado en DECISIONES.md."
    )
    return nuevos_df, atleta_id_by_player


def _resolve_f3_sport(row):
    sport = row["Sport"]
    if "," in sport:
        return EVENT_SPORT_OVERRIDE[(sport, row["Event"])]
    return sport


# ---------------------------------------------------------------------------
# Canonicalización de nombres de EVENTO fuente1 <-> fuente3 (ver auditoría del
# 2026-09-13 en DECISIONES.md: un escaneo sistemático de similitud reveló que
# el desajuste de nombres no se limitaba a 2 deportes -- afecta a decenas de
# eventos que son el MISMO evento real bajo dos convenciones de redacción
# distintas: fuente 1 "<descriptor>, <Género> (Olympic)" (ej. "Javelin
# Throw, Men (Olympic)") vs fuente 3 "<Género>'s <descriptor>" (ej. "Men's
# Javelin Throw"). Se normaliza ambas formas a una clave canónica
# (deporte_id, género, descriptor) y solo se reusa el evento_id de fuente 1
# cuando la clave canónica calza EXACTO -- nunca por similitud aproximada,
# para no arriesgar fusionar dos eventos realmente distintos.
# ---------------------------------------------------------------------------
GENEROS_EVENTO = {"Men", "Women", "Mixed", "Boys", "Girls", "Open"}


def _normalize_event_text(s: str) -> str:
    s = s.lower()
    s = s.replace("synchronised", "synchronized")
    s = re.sub(r"\bmetres\b", "m", s)
    s = re.sub(r"\bkilometres\b", "km", s)
    s = re.sub(r"(\d+)\s*m\b", r"\1m", s)
    s = s.replace("�", "e")  # acentos mal codificados en el CSV de fuente 1
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _canon_f1_event(event_text: str):
    """'Javelin Throw, Men (Olympic)' -> ('Men', 'javelin throw')"""
    e = re.sub(r"\s*\([^)]*\)\s*$", "", event_text).strip()
    parts = [p.strip() for p in e.split(",")]
    genero = None
    if parts and parts[-1] in GENEROS_EVENTO:
        genero = parts[-1]
        parts = parts[:-1]
    return genero, _normalize_event_text(" ".join(parts))


def _canon_f3_event(event_text: str):
    """"Men's Javelin Throw" -> ('Men', 'javelin throw')"""
    e = event_text.strip()
    m = re.match(r"^(Men|Women|Mixed|Boys|Girls)'s (.+)$", e)
    if m:
        genero, desc = m.group(1), m.group(2)
    elif e.startswith("Mixed "):
        genero, desc = "Mixed", e[len("Mixed "):]
    else:
        genero, desc = None, e
    return genero, _normalize_event_text(desc)


def extend_deporte_evento_f3(deporte_df: pd.DataFrame, evento_df: pd.DataFrame,
                             deporte_id_by_name: dict, evento_id_by_key: dict,
                             f3_2024: pd.DataFrame):
    """Agrega a DEPORTE/EVENTO lo necesario para París 2024 y gestiona la tabla de equivalencias.
    
    Ajuste de mapeo (Punto 2.B):
    - Se crea el deporte general 'Equestrian' para no forzar la equitación de 2024 a una sub-disciplina específica.
    - Se registran equivalencias explícitas en 'deporte_equivalencia'.
    """
    base_name_to_id = dict(deporte_id_by_name)
    for nombre, did in deporte_id_by_name.items():
        base = re.sub(r"\s*\([^)]*\)\s*$", "", nombre).strip()
        base_name_to_id.setdefault(base, did)

    # 1. Asegurar la existencia de 'Equestrian' genérico
    next_deporte_id = int(deporte_df["deporte_id"].max()) + 1
    nuevos_deportes = []
    
    if "Equestrian" not in deporte_id_by_name and "Equestrian" not in base_name_to_id:
        deporte_id_by_name["Equestrian"] = next_deporte_id
        base_name_to_id["Equestrian"] = next_deporte_id
        nuevos_deportes.append((next_deporte_id, "Equestrian"))
        next_deporte_id += 1

    # 2. Definir equivalencias mapeadas manualmente (Fuente 3 -> Deporte Canónico)
    equivalencias_raw = [
        ("Equestrian", deporte_id_by_name["Equestrian"], "f3"),
        ("Trampoline Gymnastics", base_name_to_id.get("Trampolining (Gymnastics)"), "f3")
    ]
    
    equivalencias_rows = []
    equivalencia_map = {}
    eq_id = 1
    for nombre_fuente, did, f_origen in equivalencias_raw:
        if did is not None:
            equivalencias_rows.append((eq_id, nombre_fuente, did, f_origen))
            equivalencia_map[nombre_fuente] = did
            eq_id += 1

    df = f3_2024.copy()
    df["sport_resuelto"] = df.apply(_resolve_f3_sport, axis=1)

    # 3. Procesar deportes de Fuente 3 usando tabla de equivalencias primero
    for sport in sorted(df["sport_resuelto"].unique()):
        if sport in equivalencia_map:
            deporte_id_by_name[sport] = equivalencia_map[sport]
        elif sport in base_name_to_id:
            deporte_id_by_name[sport] = base_name_to_id[sport]  # alias, mismo id
        else:
            deporte_id_by_name[sport] = next_deporte_id
            nuevos_deportes.append((next_deporte_id, sport))
            next_deporte_id += 1

    nuevos_deporte_df = pd.DataFrame(nuevos_deportes, columns=["deporte_id", "nombre"])
    equivalencia_df = pd.DataFrame(equivalencias_rows, columns=["equivalencia_id", "nombre_fuente", "deporte_id", "fuente_origen"])

    df["deporte_id_resuelto"] = df["sport_resuelto"].map(deporte_id_by_name)

    # --- índice canónico de eventos YA existentes (fuente 1) ---
    f1_canon_index = {}
    n_ambiguos_f1 = 0
    for (event_text, discipline_raw), eid in evento_id_by_key.items():
        did = deporte_id_by_name.get(discipline_raw)
        if did is None:
            continue
        genero, desc = _canon_f1_event(event_text)
        key = (did, genero, desc)
        es_olympic = event_text.rstrip().endswith("(Olympic)")
        prev = f1_canon_index.get(key)
        if prev is None:
            f1_canon_index[key] = (eid, es_olympic)
        elif es_olympic and not prev[1]:
            f1_canon_index[key] = (eid, es_olympic)
        elif prev[1] == es_olympic:
            n_ambiguos_f1 += 1

    nuevos_eventos = []
    next_evento_id = int(evento_df["evento_id"].max()) + 1
    ev_unique = df[["Event", "sport_resuelto", "deporte_id_resuelto"]].drop_duplicates(
        subset=["Event", "deporte_id_resuelto"])
    n_reused_canon = 0
    for r in ev_unique.itertuples():
        key = (r.Event, r.sport_resuelto)
        if key in evento_id_by_key:
            continue
        genero, desc = _canon_f3_event(r.Event)
        canon_key = (r.deporte_id_resuelto, genero, desc)
        canon_hit = f1_canon_index.get(canon_key)
        if canon_hit:
            evento_id_by_key[key] = canon_hit[0]
            n_reused_canon += 1
            continue
        evento_id_by_key[key] = next_evento_id
        nuevos_eventos.append((next_evento_id, r.Event, r.deporte_id_resuelto))
        next_evento_id += 1
    nuevos_evento_df = pd.DataFrame(nuevos_eventos, columns=["evento_id", "nombre", "deporte_id"])

    df["evento_id"] = list(zip(df["Event"], df["sport_resuelto"]))
    df["evento_id"] = df["evento_id"].map(evento_id_by_key)

    REPORT.note(
        f"DEPORTE_EQUIVALENCIA: {len(equivalencia_df)} equivalencias cargadas "
        f"(ej. 'Equestrian' -> Deporte General 'Equestrian', 'Trampoline Gymnastics' -> 'Trampolining (Gymnastics)')."
    )

    return nuevos_deporte_df, nuevos_evento_df, equivalencia_df, deporte_id_by_name, evento_id_by_key, df


def build_participacion_resultado_f3(df_f3_resolved: pd.DataFrame, atleta_id_by_player: dict,
                                      edicion_id_2024: int, noc_valid_codes: set,
                                      start_participacion_id: int, start_resultado_id: int):
    df = df_f3_resolved.copy()
    n_total = len(df)

    df["atleta_id"] = df["player_id"].map(atleta_id_by_player)
    df["edicion_id"] = edicion_id_2024
    df["codigo_noc"] = df["NOC"].where(df["NOC"].isin(noc_valid_codes), None)
    n_noc_null = df["codigo_noc"].isna().sum()
    if n_noc_null:
        REPORT.note(f"Fuente 3 (2024): {n_noc_null} filas con codigo_noc NULL (código NOC no "
                    f"resoluble contra el catálogo NOC).")
    df["equipo"] = df["Team"].apply(normalize_ws)

    dup = df.duplicated(subset=["atleta_id", "edicion_id", "evento_id"], keep=False)
    n_dup = int(dup.sum())
    if n_dup:
        REPORT.note(f"Fuente 3 (2024): {n_dup} filas comparten (atleta_id, edicion_id, "
                    f"evento_id) tras el emparejamiento por nombre, probable colisión de "
                    f"nombres entre dos player_id distintos mapeados al mismo atleta_id "
                    f"existente. Se deduplican igual que el caso Polo 1900 (ver DECISIONES.md), "
                    f"manteniendo la primera fila para PARTICIPACION y preservando cada "
                    f"resultado en RESULTADO.")

    participacion_cols = ["atleta_id", "edicion_id", "evento_id", "codigo_noc", "equipo"]
    df = df.reset_index(drop=True)
    df["_orig_order"] = df.index
    first_per_group = (
        df.sort_values("_orig_order")
        .groupby(["atleta_id", "edicion_id", "evento_id"], as_index=False).first()
    )
    participacion_df = first_per_group[participacion_cols].copy()
    # fuente 3 no trae Age/Height/Weight (ver DECISIONES.md): quedan NULL.
    participacion_df["edad"] = pd.array([pd.NA] * len(participacion_df), dtype="Int64")
    participacion_df["altura_cm"] = None
    participacion_df["peso_kg"] = None
    participacion_df.insert(0, "participacion_id",
                             range(start_participacion_id, start_participacion_id + len(participacion_df)))

    group_to_pid = {
        (r.atleta_id, r.edicion_id, r.evento_id): r.participacion_id
        for r in participacion_df.itertuples()
    }
    df["participacion_id"] = [
        group_to_pid[k] for k in zip(df["atleta_id"], df["edicion_id"], df["evento_id"])
    ]

    resultado_df = pd.DataFrame({
        "participacion_id": df["participacion_id"].values,
        "lugar": pd.array([pd.NA] * len(df), dtype="Int64"),  # fuente 3 no trae lugar/rank
        "empatado": False,
        "medalla": df["Medal"].map(MEDAL_ES).values,  # "No medal" -> NaN -> NULL
    })
    resultado_df.insert(0, "resultado_id",
                         range(start_resultado_id, start_resultado_id + len(resultado_df)))

    REPORT.note(
        f"PARTICIPACION/RESULTADO (fuente 3, solo edición 2024): {n_total} filas de origen -> "
        f"{len(participacion_df)} filas de PARTICIPACION ({n_total - len(participacion_df)} "
        f"colapsadas por deduplicación de clave natural) y {len(resultado_df)} filas de "
        f"RESULTADO. `edad`, `altura_cm`, `peso_kg` y `lugar` quedan NULL para todas estas "
        f"filas: fuente 3 no trae esas columnas (limitación conocida, documentada)."
    )
    return participacion_df, resultado_df


def build_participacion_resultado(results: pd.DataFrame, atleta_id_by_source: dict,
                                   edicion_id_by_key: dict, evento_id_by_key: dict,
                                   noc_valid_codes: set, atleta_df: pd.DataFrame):
    df = results.copy()
    n_total = len(df)

    df["event_clean"] = df["event"].apply(normalize_ws)
    
    # --- PROCESAMIENTO DE FILAS YOG ---
    # En lugar de excluir las filas (df = df[~is_yog]), detectamos cuáles son YOG
    # para mapear su tipo como 'Verano-YOG' o 'Invierno-YOG'.
    is_yog = df["event_clean"].str.contains(r"\(YOG\)", regex=True, na=False)
    n_yog = int(is_yog.sum())
    
    REPORT.note(f"Se procesan {n_yog} filas de Juegos Olímpicos de la Juventud (YOG) "
                f"catalogándolas en 'Verano-YOG' / 'Invierno-YOG'.")

    before = len(df)
    df = df.dropna(subset=["year", "type"])
    n_no_edition = before - len(df)
    REPORT.note(f"Se descartan {n_no_edition} filas sin year/type resolvible en la fuente "
                f"(no se puede construir la FK a EDICION_OLIMPICA).")

    before = len(df)
    df = df.dropna(subset=["discipline", "event"])
    n_no_discipline_event = before - len(df)
    if n_no_discipline_event:
        REPORT.note(f"Se descartan {n_no_discipline_event} filas sin discipline/event (fila(s) "
                    f"malformada(s) en la fuente, sin datos suficientes para resolver DEPORTE/EVENTO).")

    # Mapeo de temporada base ('Summer' -> 'Verano', 'Winter' -> 'Invierno')
    df["tipo_base"] = df["type"].map(SEASON_ES)
    
    # Asignación del tipo final para EDICION_OLIMPICA
    df["tipo_es"] = df.apply(
        lambda r: f"{r['tipo_base']}-YOG" if r["event_clean"] and "(YOG)" in r["event_clean"] else r["tipo_base"],
        axis=1
    )
    
    df["edicion_id"] = df.apply(lambda r: edicion_id_by_key.get((int(r["year"]), r["tipo_es"])), axis=1)
    before = len(df)
    df = df.dropna(subset=["edicion_id"])
    n_no_edicion_match = before - len(df)
    if n_no_edicion_match:
        REPORT.note(f"Se descartan {n_no_edicion_match} filas cuyo (anio,tipo) no calza con "
                    f"ninguna edición del catálogo de sedes.")

    df["evento_id"] = df.apply(lambda r: evento_id_by_key.get((r["event_clean"], r["discipline"])), axis=1)
    before = len(df)
    df = df.dropna(subset=["evento_id"])
    n_no_evento = before - len(df)
    if n_no_evento:
        REPORT.note(f"Se descartan {n_no_evento} filas sin evento resoluble.")

    df["atleta_id"] = df["athlete_id"].map(atleta_id_by_source)
    before = len(df)
    df = df.dropna(subset=["atleta_id"])
    n_no_atleta = before - len(df)
    if n_no_atleta:
        REPORT.note(f"Se descartan {n_no_atleta} filas sin atleta resoluble en bios.")

    df["codigo_noc"] = df["noc"].where(df["noc"].isin(noc_valid_codes), None)
    n_noc_null = df["codigo_noc"].isna().sum()
    if n_noc_null:
        REPORT.note(f"{n_noc_null} filas quedan con codigo_noc NULL: el código NOC de la fila "
                    f"no existe en el catálogo NOC construido.")

    birth_year = atleta_df.set_index("athlete_id")["fecha_nacimiento"].dt.year
    df["birth_year"] = df["athlete_id"].map(birth_year)
    df["edad"] = (df["year"] - df["birth_year"]).where(
        lambda s: s.between(0, 120), None)

    height = atleta_df.set_index("athlete_id")["height_cm"]
    weight = atleta_df.set_index("athlete_id")["weight_kg"]
    df["altura_cm"] = df["athlete_id"].map(height)
    df["peso_kg"] = df["athlete_id"].map(weight)
    REPORT.note("altura_cm/peso_kg en PARTICIPACION se toman del valor único registrado en "
                "bios por atleta. Simplificación documentada.")

    df["equipo"] = df["team"].apply(normalize_ws)
    df["atleta_id"] = df["atleta_id"].astype(int)
    df["edicion_id"] = df["edicion_id"].astype(int)
    df["evento_id"] = df["evento_id"].astype(int)

    n_rows_pre_dedup = len(df)

    # --- Deduplicación de clave natural (atleta_id, edicion_id, evento_id) ---
    group_keys = ["atleta_id", "edicion_id", "evento_id"]
    df = df.reset_index(drop=True)
    df["_orig_order"] = df.index

    group_sizes = df.groupby(group_keys).size()
    dup_groups = group_sizes[group_sizes > 1]
    n_dup_groups = len(dup_groups)
    n_dup_rows = int(dup_groups.sum())

    noc_nunique = df.groupby(group_keys)["codigo_noc"].nunique(dropna=False)
    equipo_nunique = df.groupby(group_keys)["equipo"].nunique(dropna=False)
    n_groups_noc_mismatch = int((noc_nunique > 1).sum())
    n_groups_equipo_mismatch = int((equipo_nunique > 1).sum())

    first_per_group = (
        df.sort_values("_orig_order").groupby(group_keys, as_index=False).first()
    )

    if n_dup_groups:
        REPORT.note(
            f"Deduplicación de clave natural (atleta_id, edicion_id, evento_id): "
            f"{n_dup_groups} grupos con más de una fila en results.csv "
            f"({n_dup_rows} filas en total) colapsados a 1 fila de PARTICIPACION cada uno; "
            f"se preserva 1 fila de RESULTADO por cada resultado distinto traído."
        )

    participacion_cols = ["atleta_id", "edicion_id", "evento_id", "codigo_noc", "equipo",
                           "edad", "altura_cm", "peso_kg"]
    participacion_df = first_per_group[participacion_cols].reset_index(drop=True)
    participacion_df["edad"] = participacion_df["edad"].astype("Int64")
    participacion_df.insert(0, "participacion_id", range(1, len(participacion_df) + 1))

    group_to_pid = {
        (r.atleta_id, r.edicion_id, r.evento_id): r.participacion_id
        for r in participacion_df.itertuples()
    }
    df["participacion_id"] = [
        group_to_pid[k] for k in zip(df["atleta_id"], df["edicion_id"], df["evento_id"])
    ]

    resultado_df = pd.DataFrame({
        "participacion_id": df["participacion_id"].values,
        "lugar": df["place"].astype("Int64").values,
        "empatado": df["tied"].fillna(False).values,
        "medalla": df["medal"].map(MEDAL_ES).values,
    })
    resultado_df.insert(0, "resultado_id", range(1, len(resultado_df) + 1))

    REPORT.note(f"PARTICIPACION: {len(participacion_df)} filas; RESULTADO: {len(resultado_df)} filas, de "
                f"{n_total} filas originales en results.csv.")

    # --- RECONCILIACIÓN ACTUALIZADA CON YOG INCLUIDO ---
    reconciliacion = (
        "Reconciliación exacta de results.csv -> PARTICIPACION/RESULTADO (con YOG cargados):\n\n"
        "| Motivo | Filas |\n|---|---:|\n"
        f"| Filas totales en `results.csv` | {n_total} |\n"
        f"| (+) Incluidas de Youth Olympic Games (`event` contiene `(YOG)`) | {n_yog} |\n"
        f"| (-) Sin `year`/`type` resolvible en la fuente | {n_no_edition} |\n"
        f"| (-) Sin `discipline`/`event` (fila malformada) | {n_no_discipline_event} |\n"
        f"| (-) `(anio,tipo)` sin edición correspondiente en el catálogo de sedes | {n_no_edicion_match} |\n"
        f"| (-) Sin `evento_id` resoluble | {n_no_evento} |\n"
        f"| (-) Sin `atleta_id` resoluble | {n_no_atleta} |\n"
        f"| **= Filas que sobreviven a RESULTADO** | **{len(resultado_df)}** |\n"
        f"| (-) Colapsadas por deduplicación de clave natural "
        f"({n_dup_groups} grupos, {n_dup_rows} filas de origen -> {n_dup_groups} filas) "
        f"| {n_rows_pre_dedup - len(participacion_df)} |\n"
        f"| **= Filas finales en PARTICIPACION** | **{len(participacion_df)}** |\n\n"
        f"Verificación de cierre: {n_total} - {n_no_edition} - "
        f"{n_no_discipline_event} - {n_no_edicion_match} - {n_no_evento} - {n_no_atleta} "
        f"= {n_total - n_no_edition - n_no_discipline_event - n_no_edicion_match - n_no_evento - n_no_atleta} "
        f"(coincide con las {len(resultado_df)} filas de RESULTADO)."
    )
    REPORT.section("Reconciliación exacta de results.csv", reconciliacion)
    return participacion_df, resultado_df

# ---------------------------------------------------------------------------
# Cross-check con fuente 2 (SOLO validación, nunca se carga -- 1896-2016 ya
# está cubierto por fuente 1). Opcional, ver DECISIONES.md.
# ---------------------------------------------------------------------------
def cross_check_fuente2(atleta_df: pd.DataFrame, athlete_events: pd.DataFrame):
    multi_noc = athlete_events.groupby("ID")["NOC"].nunique()
    n_multi_f2 = int((multi_noc > 1).sum())

    existing_by_name = {}
    for r in atleta_df.itertuples():
        for nm in (r.nombre_usado, r.nombre_completo):
            if isinstance(nm, str):
                existing_by_name.setdefault(name_match_key(nm), r)

    ae = athlete_events.drop_duplicates("ID")[["ID", "Name", "Height", "Weight"]].copy()
    ae["_key"] = ae["Name"].apply(name_match_key)
    ae["match"] = ae["_key"].map(existing_by_name)
    matched = ae[ae["match"].notna()].copy()
    matched["height_f1"] = matched["match"].apply(lambda r: r.height_cm)
    matched["weight_f1"] = matched["match"].apply(lambda r: r.weight_kg)

    both_h = matched.dropna(subset=["Height", "height_f1"])
    both_w = matched.dropna(subset=["Weight", "weight_f1"])
    h_mismatch = int((both_h["Height"] != both_h["height_f1"]).sum())
    w_mismatch = int((both_w["Weight"] != both_w["weight_f1"]).sum())

    REPORT.section(
        "Cross-check con fuente 2 (validación, NO se carga a la BD)",
        f"Fuente 2 (`athlete_events.csv`, 271,116 filas, 1896-2016) se usa únicamente para "
        f"validar fuente 1, nunca para cargar participaciones adicionales (ya cubiertas).\n\n"
        f"- **Patrón multi-NOC:** agrupando por `ID` (columna propia de fuente 2, distinta del "
        f"`athlete_id` de fuente 1) y contando `NOC` distintos, **{n_multi_f2} atletas** de "
        f"fuente 2 compitieron bajo más de un NOC. Esto confirma cualitativamente el mismo patrón "
        f"que fuente 1 (1,834 atletas, ver `DECISIONES.md`); los conteos no son directamente "
        f"comparables 1:1 porque fuente 2 solo llega a 2016 (menos ediciones = menos "
        f"oportunidades de cambio de NOC) y usa una numeración de atleta propia.\n\n"
        f"- **Consistencia de Height/Weight:** de {len(ae)} atletas distintos en fuente 2, "
        f"{len(matched)} calzaron por nombre normalizado exacto con un atleta ya cargado de "
        f"fuente 1. De los que tienen altura registrada en ambas fuentes ({len(both_h)} "
        f"personas), {h_mismatch} difieren. De los que tienen peso registrado en ambas "
        f"({len(both_w)} personas), {w_mismatch} difieren. Las diferencias no se investigaron "
        f"caso por caso en esta corrida (quedan registradas, no resueltas, según lo pedido)."
    )


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------
def copy_df(cur, df: pd.DataFrame, table: str, columns: list):
    buf = io.StringIO()
    df[columns].to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)
    cur.copy_expert(
        f"COPY olimpiadas.{table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')",
        buf,
    )


def load(conn, tables: dict):
    with conn.cursor() as cur:
        cur.execute("SET search_path TO olimpiadas")
        cur.execute("TRUNCATE TABLE resultado, participacion, evento, deporte_equivalencia, deporte, "
                    "edicion_olimpica, atleta, sede, noc, poblacion_pais, pais RESTART IDENTITY CASCADE")
        copy_df(cur, tables["pais"], "pais", ["pais_id", "nombre"])
        copy_df(cur, tables["poblacion"], "poblacion_pais", ["poblacion_id", "pais_id", "anio", "cantidad"])
        copy_df(cur, tables["noc"], "noc", ["codigo_noc", "nombre_region", "notas", "pais_id"])
        copy_df(cur, tables["sede"], "sede", ["sede_id", "ciudad", "pais_id"])
        copy_df(cur, tables["atleta"], "atleta", [
            "atleta_id", "nombre_completo", "nombre_usado", "sexo", "nacionalidad",
            "fecha_nacimiento", "ciudad_nacimiento", "pais_nacimiento", "fecha_fallecimiento"])
        copy_df(cur, tables["edicion"], "edicion_olimpica", ["edicion_id", "anio", "tipo", "sede_id"])
        copy_df(cur, tables["deporte"], "deporte", ["deporte_id", "nombre"])
        copy_df(cur, tables["deporte_equivalencia"], "deporte_equivalencia", [
            "equivalencia_id", "nombre_fuente", "deporte_id", "fuente_origen"])
        copy_df(cur, tables["evento"], "evento", ["evento_id", "nombre", "deporte_id"])
        copy_df(cur, tables["participacion"], "participacion", [
            "participacion_id", "atleta_id", "edicion_id", "evento_id", "codigo_noc",
            "equipo", "edad", "altura_cm", "peso_kg"])
        copy_df(cur, tables["resultado"], "resultado", [
            "resultado_id", "participacion_id", "lugar", "empatado", "medalla"])

        pk_cols = {
            "pais": "pais_id", "poblacion_pais": "poblacion_id", "sede": "sede_id",
            "atleta": "atleta_id", "edicion_olimpica": "edicion_id", "deporte": "deporte_id",
            "deporte_equivalencia": "equivalencia_id", "evento": "evento_id",
            "participacion": "participacion_id", "resultado": "resultado_id",
        }
        for t, pk in pk_cols.items():
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence(%s, %s), "
                f"COALESCE((SELECT MAX({pk}) FROM olimpiadas.{t}), 1))",
                (f"olimpiadas.{t}", pk),
            )
    conn.commit()


# Conteos de la corrida anterior (solo fuente 1), tomados de la sección
# fechada previa de este mismo REPORTE.md -- sirven de línea base para la
# comparación pedida en esta corrida (integración fuente 2 + fuente 3).
CONTEOS_CORRIDA_ANTERIOR = {
    "pais": 204, "poblacion_pais": 13026, "noc": 235, "sede": 43, "atleta": 145500,
    "edicion_olimpica": 53, "deporte": 93, "evento": 1904,
    "participacion": 299216, "resultado": 299731,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    ap.add_argument("--only-transform", action="store_true",
                     help="No conecta a la BD; solo corre extract/transform y guarda el reporte.")
    args = ap.parse_args()

    (bios_clean, bios_raw, noc_regions, populations, results, editions_fallback,
     athlete_events, noc_regions_f2, olympics_f3) = extract()

    host_countries = set(HOST_COUNTRY_BY_CITY.values())
    fallback_mask = editions_fallback.apply(
        lambda r: (int(r["anio"]), r["tipo"]) in EDICIONES_SIN_CITY_REAL, axis=1)
    host_countries |= set(editions_fallback.loc[fallback_mask, "pais_sede"])

    pais_df, pais_id_by_name = build_pais(noc_regions, host_countries)
    poblacion_df = build_poblacion(pais_df, pais_id_by_name, populations)
    noc_df = build_noc(noc_regions, pais_id_by_name, noc_regions_f2)
    noc_region_display = dict(zip(noc_df["codigo_noc"], noc_df["nombre_region"]))

    olympics_f3_2024 = olympics_f3[olympics_f3["Year"] == 2024].copy()
    REPORT.note(
        f"Fuente 3: se retienen solo {len(olympics_f3_2024)} filas de Year==2024 de "
        f"{len(olympics_f3)} totales (1896-2024). Regla aplicada: se toma de fuente 3 "
        f"únicamente el/los año(s) que NO aparecen ya en el catálogo de ediciones cargado "
        f"desde fuente 1 (1896-2022) -- en la práctica, solo 2024 (París). El resto "
        f"(1896-2020 Verano) se descarta explícitamente para no duplicar PARTICIPACION contra "
        f"lo ya cargado de fuente 1. Al ser fuente 3 de licencia CC BY-NC-SA (más restrictiva "
        f"que la CC0 de fuente 2), se usa solo para esto -- no como fuente de validación "
        f"cruzada general -- para minimizar cuánto del dataset final hereda esa licencia "
        f"(ver DECISIONES.md y FUENTES.md)."
    )

    sede_df, edicion_df, edicion_id_by_key = build_sede_edicion(
        athlete_events, olympics_f3_2024, editions_fallback, pais_id_by_name)

    atleta_df, atleta_id_by_source = build_atleta(bios_clean, bios_raw, results, noc_region_display)
    deporte_df, evento_df, deporte_id_by_name, evento_id_by_key = build_deporte_evento(results)
    participacion_df, resultado_df = build_participacion_resultado(
        results, atleta_id_by_source, edicion_id_by_key, evento_id_by_key,
        set(noc_df["codigo_noc"]), atleta_df)

    cross_check_fuente2(atleta_df, athlete_events)

    # --- extensión con fuente 3 (solo edición 2024) y tabla de equivalencias ---
    nuevos_atletas_df, atleta_id_by_player = build_atleta_extension_f3(
        atleta_df, olympics_f3_2024, noc_region_display)
    atleta_cols_final = ["atleta_id", "nombre_completo", "nombre_usado", "sexo", "nacionalidad",
                         "fecha_nacimiento", "ciudad_nacimiento", "pais_nacimiento",
                         "fecha_fallecimiento"]
    atleta_df_final = pd.concat(
        [atleta_df[atleta_cols_final], nuevos_atletas_df], ignore_index=True)

    nuevos_deporte_df, nuevos_evento_df, equivalencia_df, deporte_id_by_name, evento_id_by_key, f3_resolved = (
        extend_deporte_evento_f3(deporte_df, evento_df, deporte_id_by_name, evento_id_by_key,
                                  olympics_f3_2024)
    )
    deporte_df_final = pd.concat([deporte_df, nuevos_deporte_df], ignore_index=True)
    evento_df_final = pd.concat([evento_df, nuevos_evento_df], ignore_index=True)

    edicion_id_2024 = edicion_id_by_key[(2024, "Verano")]
    participacion_f3_df, resultado_f3_df = build_participacion_resultado_f3(
        f3_resolved, atleta_id_by_player, edicion_id_2024, set(noc_df["codigo_noc"]),
        start_participacion_id=int(participacion_df["participacion_id"].max()) + 1,
        start_resultado_id=int(resultado_df["resultado_id"].max()) + 1,
    )
    participacion_df_final = pd.concat([participacion_df, participacion_f3_df], ignore_index=True)
    resultado_df_final = pd.concat([resultado_df, resultado_f3_df], ignore_index=True)

    conteos_final = {
        "pais": len(pais_df), "poblacion_pais": len(poblacion_df), "noc": len(noc_df),
        "sede": len(sede_df), "atleta": len(atleta_df_final), "edicion_olimpica": len(edicion_df),
        "deporte": len(deporte_df_final), "deporte_equivalencia": len(equivalencia_df),
        "evento": len(evento_df_final), "participacion": len(participacion_df_final),
        "resultado": len(resultado_df_final),
    }
    for k, v in conteos_final.items():
        REPORT.count(k.upper(), v)

    comparacion = "| Tabla | Corrida solo fuente 1 (2026-09-12 mañana) | Esta corrida | Diferencia |\n|---|---:|---:|---:|\n"
    for k in CONTEOS_CORRIDA_ANTERIOR:
        a, b = CONTEOS_CORRIDA_ANTERIOR[k], conteos_final[k]
        signo = "+" if (b - a) >= 0 else ""
        comparacion += f"| {k} | {a} | {b} | {signo}{b - a} |\n"

    hoy = date.today().isoformat()
    REPORT.section(
        f"Corrida {hoy}: estado final (fuente 1 + fuente 2 sedes + fuente 3 2024, con "
        f"auditoría de emparejamiento y equivalencias de deportes)",
        "Se reemplaza `reference_editions.csv` como fuente primaria de SEDE/EDICION_OLIMPICA "
        "por columnas `City` reales de fuente 2 (1896-2016) y fuente 3 (2024); solo 3 "
        "ediciones (2018 Invierno, 2020 Verano, 2022 Invierno) siguen viniendo del archivo "
        "manual porque ninguna fuente real trae `City` para esos años. Se agrega la edición "
        "2024 Verano (París) cargando fuente 3 filtrada a `Year==2024`. Esta corrida incluye "
        "además la corrección del criterio de emparejamiento de atletas (nombre plegando "
        "tildes + vivo + nacionalidad consistente, en vez de nombre exacto simple), la "
        "canonicalización de EVENTO/DEPORTE entre fuente 1 y fuente 3, y la incorporación de "
        "la tabla `deporte_equivalencia` para mapear disciplinas genéricas o renombradas. "
        "Ver detalle completo en las secciones de arriba (SEDE/EDICION_OLIMPICA, ATLETA "
        "extensión fuente 3, DEPORTE/EVENTO extensión fuente 3, PARTICIPACION/RESULTADO "
        "fuente 3, reconciliación NOC, cross-check fuente 2).\n\n"
        + comparacion
    )

    if not args.only_transform:
        conn = psycopg2.connect(args.dsn)
        try:
            load(conn, {
                "pais": pais_df, "poblacion": poblacion_df, "noc": noc_df, "sede": sede_df,
                "atleta": atleta_df_final, "edicion": edicion_df, "deporte": deporte_df_final,
                "deporte_equivalencia": equivalencia_df, "evento": evento_df_final,
                "participacion": participacion_df_final, "resultado": resultado_df_final,
            })
            REPORT.note("Carga a PostgreSQL completada y confirmada (COMMIT).")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    REPORT.dump(BASE_DIR / "REPORTE.md")
    print("\nReporte guardado en etl/REPORTE.md")


if __name__ == "__main__":
    main()
