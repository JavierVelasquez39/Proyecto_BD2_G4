"""Análisis comparativo de tiempos de respaldo y restauración (sección 4.10).

Uso, desde cualquier carpeta:
    python "Fase 2/07_documentacion/analisis/analizar.py"

Lee (solo lectura) 05_logs/tiempos_*.csv y los logs de 05_logs/<tipo>_<persona>/.
Escribe (y reemplaza en cada ejecución):
    07_documentacion/analisis/ESTADO_CSV.md
    07_documentacion/analisis/tabla_*.csv y tabla_*.md
    07_documentacion/analisis/RESUMEN_ANALISIS.md
    07_documentacion/graficos/grafico*.png

Un CSV entra al análisis solo si pasa dos validaciones:
1. Formato de la 4.10: encabezado de 14 columnas, 53 líneas (encabezado y 52
   filas), 14 campos en todas las líneas, UTF-8 sin BOM, LF, 0 ALERTA y `paso`
   de dos dígitos leído como texto.
2. Cruce con los logs actuales de la corrida (no los rotados): cada respaldo
   coincide en `segundos` y `bytes` con su log, y cada fila `total` de
   restauración coincide con la línea `Total:` de su log y empieza a lo sumo
   8 s después de la hora de inicio del log.
"""

from pathlib import Path
import datetime as dt
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

FASE2 = Path(__file__).resolve().parents[2]
LOGS = FASE2 / "05_logs"
SALIDA = FASE2 / "07_documentacion" / "analisis"
GRAFICOS = FASE2 / "07_documentacion" / "graficos"

ENCABEZADO = ("persona,tipo_carga,maquina,paso,operacion,n_cadena,etapa,inicio_iso,"
              "fin_iso,segundos,bytes,validacion,repeticion,observacion")
LINEAS_ESPERADAS = 53
ETAPAS = ["combinar", "arranque", "validacion"]
PASOS_VALIDOS = {"02", "04", "06", "08", "12", "13", "14", "15"}
# El enunciado pide los tres tipos de carga
TIPOS = ["anio", "deporte", "deportista"]
VENTANA_INICIO_S = 8
SEGMENTO_WAL = 16 * 1024 * 1024
PG_WAL_MEDIDO = Path(__file__).resolve().parent / "pg_wal_respaldos.csv"
PENDIENTE = "[PENDIENTE]"
ROTADO = re.compile(r"\.\d{8}_\d{6}\.log$")


# ------------------------------------------------------------------ utilidades

def escribir(ruta: Path, texto: str) -> None:
    """UTF-8 sin BOM, fin de línea LF."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def tabla_md(df: pd.DataFrame) -> str:
    """Tabla Markdown sin depender de tabulate."""
    cab = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if pd.api.types.is_numeric_dtype(df[c]) else "---"
                         for c in df.columns) + "|"
    filas = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in fila) + " |"
             for fila in df.itertuples(index=False)]
    return "\n".join([cab, sep] + filas) + "\n"


def guardar_tabla(df: pd.DataFrame, nombre: str, titulo: str, nota: str = "") -> None:
    df.to_csv(SALIDA / f"{nombre}.csv", index=False, lineterminator="\n")
    escribir(SALIDA / f"{nombre}.md", f"# {titulo}\n\n" + (nota + "\n\n" if nota else "") + tabla_md(df))


def mb(b) -> float:
    return round(float(b) / 1_000_000, 2)


def leer_log(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8", errors="replace") if ruta.exists() else None


def buscar(rx: str, texto: str):
    m = re.search(rx, texto, re.M)
    return m.group(1) if m else None


def limpiar_salidas() -> None:
    """Borra solo lo que genera este script, para no dejar resultados viejos."""
    for patron in ("tabla_*.csv", "tabla_*.md", "ESTADO_CSV.md", "RESUMEN_ANALISIS.md"):
        for p in SALIDA.glob(patron):
            p.unlink()
    for p in GRAFICOS.glob("grafico*.png"):
        p.unlink()


# ------------------------------------------------------------------ validación

def validar_formato(ruta: Path) -> list[str]:
    """Motivos de exclusión por formato (lista vacía si cumple la 4.10)."""
    motivos = []
    crudo = ruta.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        motivos.append("tiene BOM (la 4.10 pide UTF-8 sin BOM)")
    if b"\r\n" in crudo:
        motivos.append("tiene fin de línea CRLF (la 4.10 pide LF)")
    lineas = crudo.decode("utf-8", errors="replace").replace("\r\n", "\n").rstrip("\n").split("\n")
    if lineas[0].lstrip("\ufeff") != ENCABEZADO:
        motivos.append("el encabezado no es el de 14 columnas de la 4.10")
    if len(lineas) != LINEAS_ESPERADAS:
        motivos.append(f"tiene {len(lineas)} líneas y se esperan {LINEAS_ESPERADAS}")
    malas = [i + 1 for i, l in enumerate(lineas) if len(l.split(",")) != 14]
    if malas:
        muestra = ", ".join(str(i) for i in malas[:5]) + (" ..." if len(malas) > 5 else "")
        motivos.append(f"{len(malas)} líneas no tienen 14 campos (líneas {muestra})")
    if motivos:
        return motivos
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    alertas = int((df["validacion"] == "ALERTA").sum())
    if alertas:
        motivos.append(f"tiene {alertas} filas con ALERTA")
    pasos = set(df["paso"])
    if not pasos <= PASOS_VALIDOS:
        motivos.append(f"pasos fuera de la 4.10: {sorted(pasos - PASOS_VALIDOS)}")
    if df[["persona", "tipo_carga", "maquina"]].drop_duplicates().shape[0] != 1:
        motivos.append("mezcla más de una persona, tipo de carga o máquina")
    conteo = df.groupby(["operacion", "etapa"]).size().to_dict()
    esperado = {("backup_full", "basebackup"): 1, ("backup_incr", "basebackup"): 3,
                **{("restore", e): 12 for e in ETAPAS + ["total"]}}
    if conteo != esperado:
        motivos.append(f"la distribución por operación y etapa no es 1/3/12: {conteo}")
    return motivos


def cruzar_logs(df: pd.DataFrame, corrida: str) -> tuple[list[str], int]:
    """Compara las filas del CSV con los logs actuales de la corrida.

    Devuelve (motivos, logs_rotados). Los logs rotados no se usan para validar,
    solo se cuentan y se nombran cuando son los únicos que coinciden con una fila.
    """
    carpeta = LOGS / corrida
    if not carpeta.is_dir():
        return [f"no existe `05_logs/{corrida}/`: no hay logs para verificar las filas"], 0
    rotados = sorted(p for p in carpeta.glob("*.log") if ROTADO.search(p.name))
    motivos = []
    for i, x in enumerate(df.itertuples(), start=2):
        if x.operacion in ("backup_full", "backup_incr"):
            nombre = "backup_full" if x.operacion == "backup_full" else f"backup_incr{x.n_cadena}"
            log = carpeta / f"{corrida}_{x.paso}_{nombre}.log"
            txt = leer_log(log)
            if txt is None:
                motivos.append(f"fila {i}: falta `{log.name}`")
                continue
            seg, byt = buscar(r"segundos=([0-9.]+)", txt), buscar(r"bytes=(\d+)", txt)
            if seg != x.segundos or byt != x.bytes:
                motivos.append(f"fila {i} ({x.operacion} n={x.n_cadena}): CSV {x.segundos} s y {x.bytes} "
                               f"bytes; `{log.name}` dice {seg} s y {byt} bytes")
        elif x.etapa == "total":
            base = f"{corrida}_{x.paso}_restore_cadena{x.n_cadena}_rep{x.repeticion}"
            log = carpeta / f"{base}.log"
            txt = leer_log(log)
            if txt is None:
                motivos.append(f"fila {i}: falta `{log.name}`")
                continue
            if not coincide_total(txt, x):
                otros = [p.name for p in rotados if p.name.startswith(base + ".")
                         and coincide_total(leer_log(p), x)]
                extra = f"; solo coincide con el log rotado `{otros[0]}`" if otros else ""
                motivos.append(f"fila {i} (restore n={x.n_cadena} rep {x.repeticion}, total "
                               f"{x.segundos} s, inicio {x.inicio_iso[11:23]}): no coincide con "
                               f"`{log.name}` (Total {buscar(r'Total: ([0-9.]+) s', txt)} s, "
                               f"inicio {inicio_log(txt)}){extra}")
    return motivos, len(rotados)


def inicio_log(txt: str):
    return buscar(r"=== Inicio de .*?: (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", txt)


def coincide_total(txt: str, x) -> bool:
    if buscar(r"Total: ([0-9.]+) s\)", txt) != x.segundos:
        return False
    ini = inicio_log(txt)
    if ini is None:
        return False
    csv_ini = dt.datetime.fromisoformat(x.inicio_iso).replace(tzinfo=None)
    return 0 <= (csv_ini - dt.datetime.fromisoformat(ini)).total_seconds() <= VENTANA_INICIO_S


def cargar(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    df["segundos"] = df["segundos"].astype(float)
    df["bytes"] = pd.to_numeric(df["bytes"].replace("", pd.NA), errors="coerce")
    df["n_cadena"] = df["n_cadena"].astype(int)
    df["repeticion"] = df["repeticion"].astype(int)
    df["corrida"] = df["tipo_carga"] + "_" + df["persona"]
    return df


# ------------------------------------------------------------------ tablas

def tabla_a(df):
    r = df[df["operacion"].isin(["backup_full", "backup_incr"])].copy()
    r["respaldo"] = r.apply(lambda x: "FULL" if x["operacion"] == "backup_full"
                            else f"INCR {x['n_cadena']}", axis=1)
    r = r.sort_values(["corrida", "n_cadena"])
    return pd.DataFrame({
        "corrida": r["corrida"], "maquina": r["maquina"], "paso": r["paso"],
        "respaldo": r["respaldo"], "segundos": r["segundos"].round(3),
        "bytes": r["bytes"].astype("int64"), "MB": r["bytes"].map(mb),
    })


def tabla_b(df):
    r = df[(df["operacion"] == "restore") & df["etapa"].isin(ETAPAS)]
    med = (r.groupby(["corrida", "maquina", "n_cadena", "etapa"])["segundos"]
           .agg(["median", "count"]).reset_index())
    piv = med.pivot_table(index=["corrida", "maquina", "n_cadena"], columns="etapa",
                          values="median").reset_index()
    reps = med.groupby(["corrida", "n_cadena"])["count"].min().reset_index()
    piv = piv.merge(reps, on=["corrida", "n_cadena"]).rename(columns={"count": "repeticiones"})
    piv = piv[["corrida", "maquina", "n_cadena", "repeticiones"] + ETAPAS]
    for e in ETAPAS:
        piv[e] = piv[e].round(3)
    return piv.rename(columns={"n_cadena": "n", "combinar": "combinar_s",
                               "arranque": "arranque_s", "validacion": "validacion_s"})


def tabla_c_restore(df):
    t = df[(df["operacion"] == "restore") & (df["etapa"] == "total")]
    med = (t.groupby(["corrida", "maquina", "n_cadena"])["segundos"]
           .agg(segundos="median", total_min_s="min", total_max_s="max").reset_index())
    base = med[med["n_cadena"] == 0].set_index("corrida")["segundos"]
    med["razon_vs_n0"] = med.apply(lambda x: x["segundos"] / base[x["corrida"]], axis=1).round(3)
    med = med.round({"segundos": 3, "total_min_s": 3, "total_max_s": 3})
    med = med.rename(columns={"n_cadena": "n", "segundos": "total_mediana_s"})
    return med[["corrida", "maquina", "n", "total_mediana_s", "total_min_s", "total_max_s", "razon_vs_n0"]]


def tabla_c_bytes(df):
    r = df[df["operacion"].isin(["backup_full", "backup_incr"])]
    full = r[r["operacion"] == "backup_full"].set_index("corrida")["bytes"]
    inc = r[r["operacion"] == "backup_incr"].sort_values(["corrida", "n_cadena"]).copy()
    inc["full_bytes"] = inc["corrida"].map(full).astype("int64")
    inc["razon_incr_vs_full"] = (inc["bytes"] / inc["full_bytes"]).round(3)
    return pd.DataFrame({
        "corrida": inc["corrida"], "maquina": inc["maquina"], "n": inc["n_cadena"],
        "incr_bytes": inc["bytes"].astype("int64"), "full_bytes": inc["full_bytes"],
        "razon_incr_vs_full": inc["razon_incr_vs_full"],
    })


def verify_de(log: Path):
    txt = leer_log(log)
    v = buscar(r"^pg_verifybackup: ([0-9.]+) s$", txt) if txt else None
    return float(v) if v else None


def tabla_e(df):
    """pg_verifybackup dentro de total, por corrida. Devuelve (tabla, corridas sin logs)."""
    partes, sin_logs = [], []
    for corrida, g in df[(df["operacion"] == "restore") & (df["etapa"] == "total")].groupby("corrida"):
        filas = []
        for x in g.itertuples():
            log = LOGS / corrida / f"{corrida}_{x.paso}_restore_cadena{x.n_cadena}_rep{x.repeticion}.log"
            filas.append({"corrida": corrida, "n": x.n_cadena, "verify_s": verify_de(log),
                          "total_s": x.segundos})
        e = pd.DataFrame(filas)
        if e["verify_s"].isna().any():
            sin_logs.append(corrida)
            continue
        e["pct"] = e["verify_s"] / e["total_s"] * 100
        partes.append(e.groupby(["corrida", "n"]).agg(
            verify_mediana_s=("verify_s", "median"), total_mediana_s=("total_s", "median"),
            pct_mediana=("pct", "median")).reset_index())
    tabla = pd.concat(partes, ignore_index=True) if partes else None
    if tabla is not None:
        tabla = tabla.round({"verify_mediana_s": 3, "total_mediana_s": 3, "pct_mediana": 1})
    return tabla, sin_logs


def lsn(texto: str) -> int:
    alto, bajo = texto.split("/")
    return (int(alto, 16) << 32) | int(bajo, 16)


def tabla_f(df):
    """WAL dentro de cada respaldo.

    De los logs: segmentos entre el punto de inicio y el de fin del WAL que
    imprime pg_basebackup -v (con -Xs el respaldo lleva esos segmentos en pg_wal).
    Medido: pg_wal_respaldos.csv (medir_pg_wal.sh), solo si el total del
    respaldo coincide con la columna bytes del CSV de tiempos.
    """
    medido = {}
    if PG_WAL_MEDIDO.exists():
        m = pd.read_csv(PG_WAL_MEDIDO, dtype=str)
        medido = {(x.corrida, x.respaldo): x for x in m.itertuples()}
    filas = []
    for x in df[df["operacion"].isin(["backup_full", "backup_incr"])].sort_values(["corrida", "n_cadena"]).itertuples():
        nombre = "backup_full" if x.operacion == "backup_full" else f"backup_incr{x.n_cadena}"
        txt = leer_log(LOGS / x.corrida / f"{x.corrida}_{x.paso}_{nombre}.log") or ""
        ini = buscar(r"write-ahead log start point: ([0-9A-F]+/[0-9A-F]+)", txt)
        fin = buscar(r"write-ahead log end point: ([0-9A-F]+/[0-9A-F]+)", txt)
        seg = (lsn(fin) // SEGMENTO_WAL - lsn(ini) // SEGMENTO_WAL + 1) if ini and fin else None
        clave = (x.corrida, "full" if x.n_cadena == 0 else f"incr{x.n_cadena}")
        med = medido.get(clave)
        wal_medido = int(med.bytes_pg_wal) if med is not None and int(med.bytes_total) == int(x.bytes) else None
        wal = seg * SEGMENTO_WAL if seg else None
        filas.append({
            "corrida": x.corrida, "respaldo": "FULL" if x.n_cadena == 0 else f"INCR {x.n_cadena}",
            "bytes": int(x.bytes), "segmentos_wal_log": seg, "wal_bytes_log": wal,
            "wal_bytes_medido": wal_medido,
            "pct_wal": round(wal / x.bytes * 100, 1) if wal else None,
            "sin_wal_MB": mb(x.bytes - wal) if wal else None,
        })
    f = pd.DataFrame(filas)
    for c in ("segmentos_wal_log", "wal_bytes_log", "wal_bytes_medido"):
        f[c] = f[c].astype("Int64")
    return f


def verify_respaldos(df):
    filas = []
    for x in df[df["operacion"].isin(["backup_full", "backup_incr"])].itertuples():
        nombre = "backup_full" if x.operacion == "backup_full" else f"backup_incr{x.n_cadena}"
        filas.append({"corrida": x.corrida, "respaldo": "FULL" if x.n_cadena == 0 else f"INCR {x.n_cadena}",
                      "verify_s": verify_de(LOGS / x.corrida / f"{x.corrida}_{x.paso}_{nombre}.log")})
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ gráficos

def grafico1(b):
    rutas = []
    for corrida, g in b.groupby("corrida"):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        abajo = [0.0] * len(g)
        etiquetas = ["FULL (n=0)" if n == 0 else f"Cadena {n}" for n in g["n"]]
        for etapa, col in zip(ETAPAS, ["combinar_s", "arranque_s", "validacion_s"]):
            ax.bar(etiquetas, g[col], bottom=abajo, label=etapa)
            abajo = [a + v for a, v in zip(abajo, g[col])]
        ax.set_title(f"Restauración por etapa, mediana de 3 repeticiones ({corrida})")
        ax.set_xlabel("Cadena restaurada")
        ax.set_ylabel("Segundos")
        ax.legend(title="Etapa")
        fig.tight_layout()
        ruta = GRAFICOS / f"grafico1_etapas_restauracion_{corrida}.png"
        fig.savefig(ruta, dpi=150)
        plt.close(fig)
        rutas.append(ruta)
    return rutas


def grafico2(a):
    corridas = list(a["corrida"].unique())
    respaldos = list(a["respaldo"].unique())
    ancho = 0.8 / len(corridas)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, c in enumerate(corridas):
        g = a[a["corrida"] == c].set_index("respaldo").reindex(respaldos)
        xs = [j + i * ancho for j in range(len(respaldos))]
        barras = ax.bar(xs, g["MB"], width=ancho, label=c)
        ax.bar_label(barras, fmt="%.1f", fontsize=8)
    ax.set_xticks([j + ancho * (len(corridas) - 1) / 2 for j in range(len(respaldos))], respaldos)
    ax.set_title("Tamaño de cada respaldo (no acumulado)")
    ax.set_xlabel("Respaldo")
    ax.set_ylabel("MB (10^6 bytes)")
    ax.legend(title="Corrida")
    fig.tight_layout()
    ruta = GRAFICOS / "grafico2_tamano_respaldos.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def grafico3(c):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for corrida, g in c.groupby("corrida"):
        ax.plot(g["n"], g["razon_vs_n0"], marker="o", label=corrida)
        for n, r in zip(g["n"], g["razon_vs_n0"]):
            ax.annotate(f"{r:.2f}", (n, r), textcoords="offset points", xytext=(0, 6),
                        ha="center", fontsize=8)
    ax.axhline(1.0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xticks([0, 1, 2, 3])
    ax.set_title("Razón restore(n) / restore(0), etapa total, mediana")
    ax.set_xlabel("n (INCR combinados)")
    ax.set_ylabel("Razón respecto al FULL")
    ax.legend(title="Corrida")
    fig.tight_layout()
    ruta = GRAFICOS / "grafico3_razon_restauracion.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def grafico4(c, maquinas):
    d = c[c["corrida"].str.startswith("deportista_")]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ancho = 0.8 / len(maquinas)
    for i, m in enumerate(maquinas):
        g = d[d["maquina"] == m]
        ax.bar([n + i * ancho for n in g["n"]], g["razon_vs_n0"], width=ancho, label=m)
    ax.set_xticks([n + ancho * (len(maquinas) - 1) / 2 for n in range(4)], [str(n) for n in range(4)])
    ax.set_title("Bolt en cada máquina: razón restore(n) / restore(0)")
    ax.set_xlabel("n (INCR combinados)")
    ax.set_ylabel("Razón respecto al FULL")
    ax.legend(title="Máquina")
    fig.tight_layout()
    ruta = GRAFICOS / "grafico4_comparacion_maquinas.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


# ------------------------------------------------------------------ principal

def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    limpiar_salidas()

    estado, validos = [], []
    for ruta in sorted(LOGS.glob("tiempos_*.csv")):
        corrida = ruta.stem.removeprefix("tiempos_")
        motivos, rotados = validar_formato(ruta), None
        if not motivos:
            motivos, rotados = cruzar_logs(pd.read_csv(ruta, dtype=str, keep_default_na=False), corrida)
        estado.append({"archivo": ruta.name, "corrida": corrida, "tipo": corrida.split("_")[0],
                       "motivos": motivos, "rotados": rotados})
        if not motivos:
            validos.append(cargar(ruta))
    cubre = {}
    for x in estado:
        if not x["motivos"]:
            cubre.setdefault(x["tipo"], []).append(x["corrida"])
    sin_tipo = [t for t in TIPOS if t not in cubre]

    texto_estado = estado_md(estado, cubre, sin_tipo)
    escribir(SALIDA / "ESTADO_CSV.md", texto_estado)
    print(texto_estado)
    if not validos:
        print("Ningún CSV válido: no se generan tablas ni gráficos.")
        return
    df = pd.concat(validos, ignore_index=True)

    a, b, c, cb = tabla_a(df), tabla_b(df), tabla_c_restore(df), tabla_c_bytes(df)
    e, e_sin_logs = tabla_e(df)
    f = tabla_f(df)
    vr = verify_respaldos(df)
    maquinas = sorted(df.loc[df["tipo_carga"] == "deportista", "maquina"].unique())

    guardar_tabla(a, "tabla_a_respaldos", "Tabla (a): tamaño y tiempo de cada respaldo",
                  "`segundos` es la etapa `basebackup`; `pg_verifybackup` queda fuera. MB = 10^6 bytes.")
    guardar_tabla(b, "tabla_b_restauracion_etapas",
                  "Tabla (b): restauración por etapa, mediana de las repeticiones",
                  "Sin la etapa `total`. Cada columna es la mediana de esa etapa por separado. "
                  "La suma de las tres no es igual al `total`: el `total` incluye además "
                  "`pg_verifybackup` y el tiempo entre etapas, y la mediana de una suma no es la "
                  "suma de las medianas.")
    guardar_tabla(c, "tabla_c1_razon_restauracion", "Tabla (c1): restore(n) / restore(0)",
                  "Solo `etapa == total`: mediana, mínimo y máximo de las repeticiones.")
    guardar_tabla(cb, "tabla_c2_razon_bytes", "Tabla (c2): incr(n).bytes / full.bytes")
    if len(maquinas) > 1:
        d = c[c["corrida"].str.startswith("deportista_")].pivot_table(
            index="n", columns="maquina", values="razon_vs_n0").reset_index()
        guardar_tabla(d, "tabla_d_maquinas", "Tabla (d): razones de Bolt por máquina")
    nota_e = ("Segundos leídos de la línea `pg_verifybackup: X s` de cada log de restauración. "
              "`pct_mediana` es la mediana de verify/total por repetición.")
    if e is not None:
        guardar_tabla(e, "tabla_e_pg_verifybackup", "Tabla (e): peso de pg_verifybackup dentro de total", nota_e)
    guardar_tabla(f, "tabla_f_wal_respaldos", "Tabla (f): WAL dentro de cada respaldo",
                  "`segmentos_wal_log`: segmentos de 16 MiB entre el punto de inicio y el de fin del WAL "
                  "que imprime `pg_basebackup -v` en el log del respaldo. `wal_bytes_medido`: tamaño real "
                  "de `pg_wal` dentro del respaldo (`medir_pg_wal.sh`, volumen montado de solo lectura), "
                  "solo en las corridas cuyos volúmenes están en la máquina donde se midió. "
                  "`sin_wal_MB`: tamaño del respaldo sin su WAL.")

    g1, g2, g3 = grafico1(b), grafico2(a), grafico3(c)
    g4 = grafico4(c, maquinas) if len(maquinas) > 1 else None

    escribir(SALIDA / "RESUMEN_ANALISIS.md",
             resumen(estado, cubre, sin_tipo, a, b, c, cb, e, e_sin_logs, f, vr, g1, g2, g3, g4))
    print("\nTablas en", SALIDA)
    print("Gráficos:", ", ".join(p.name for p in g1 + [g2, g3] + ([g4] if g4 else [])))


def estado_md(estado, cubre, sin_tipo):
    L = ["# Estado de los CSV de tiempos", "",
         "Generado por `analizar.py`. Un CSV entra al análisis si cumple el formato de la "
         f"sección 4.10 ({LINEAS_ESPERADAS} líneas, 14 campos por línea, UTF-8 sin BOM, LF, "
         "0 ALERTA, 1 FULL, 3 INCR y 12 filas por etapa de restauración, `paso` como texto) "
         "y si sus filas coinciden con los logs actuales de la corrida: `segundos` y `bytes` "
         "de cada respaldo, y `Total:` y hora de inicio de cada restauración. Los logs rotados "
         "(`.AAAAMMDD_HHMMSS.log`) no cuentan como respaldo de una fila.", "",
         "| Archivo | Estado | Logs rotados | Motivo |", "|---|---|---:|---|"]
    for x in estado:
        rot = "" if x["rotados"] is None else str(x["rotados"])
        L.append(f"| `{x['archivo']}` | {'válido' if not x['motivos'] else 'excluido'} | {rot} | "
                 f"{'<br>'.join(x['motivos'])} |")
    L += ["", "Cobertura de los tres tipos de carga del enunciado:", ""]
    for t in TIPOS:
        L.append(f"- `{t}`: " + (", ".join(f"`{c}`" for c in cubre[t]) if t in cubre
                                 else f"sin corrida válida {PENDIENTE}"))
    return "\n".join(L) + "\n"


def resumen(estado, cubre, sin_tipo, a, b, c, cb, e, e_sin_logs, f, vr, g1, g2, g3, g4):
    corridas = list(a["corrida"].unique())
    maq_por_corrida = a.drop_duplicates("corrida").set_index("corrida")["maquina"]
    L = ["# Resumen del análisis comparativo (sección 4.10)", "",
         "Generado por `07_documentacion/analisis/analizar.py` a partir de `05_logs/tiempos_*.csv`, "
         "de los logs de cada corrida y de `pg_wal_respaldos.csv`. Todos los números salen de esos "
         "archivos; no hay valores escritos a mano.", "",
         "## Datos usados", ""]
    for x in estado:
        if not x["motivos"]:
            L.append(f"- `{x['archivo']}`: válido (formato y cruce con logs), máquina "
                     f"`{maq_por_corrida[x['corrida']]}`.")
        else:
            otro = [c for c in cubre.get(x["tipo"], []) if c != x["corrida"]]
            L.append(f"- `{x['archivo']}`: **excluido** ({len(x['motivos'])} motivos, todos en "
                     f"`ESTADO_CSV.md`). Primero: {x['motivos'][0]}."
                     + (f" La carga `{x['tipo']}` queda cubierta por `{otro[0]}`." if otro else ""))
    for t in sin_tipo:
        L.append(f"- Carga `{t}`: sin corrida válida. {PENDIENTE}")
    L += ["", "**Advertencia:** las máquinas del equipo son distintas. Entre máquinas se comparan "
          "razones (por ejemplo restore(n)/restore(0)), no segundos. Los tamaños en bytes sí se "
          "comparan entre corridas: dependen de los datos y de PostgreSQL, no de la máquina.", ""]
    for maq, grupo in maq_por_corrida.groupby(maq_por_corrida):
        if len(grupo) > 1:
            L += [f"En `{maq}` hay {len(grupo)} corridas ({', '.join(grupo.index)}): entre ellas la máquina "
                  "es la misma, así que la diferencia de tiempos se atribuye al tipo de carga y sí se pueden "
                  "comparar segundos, con la salvedad de la caché del sistema operativo.", ""]
    if maq_por_corrida.nunique() > 1:
        L += [f"Las corridas en máquinas distintas ({', '.join(f'{c} en {maq_por_corrida[c]}' for c in corridas)}) "
              "solo se comparan por razones; entre ellas no se puede separar el efecto de la carga del de la máquina.", ""]

    L += ["## Medido", ""]
    for corrida in corridas:
        aa, bb = a[a["corrida"] == corrida], b[b["corrida"] == corrida]
        cc, cbb = c[c["corrida"] == corrida], cb[cb["corrida"] == corrida]
        ff = f[f["corrida"] == corrida]
        L += [f"### Corrida `{corrida}` (máquina `{aa['maquina'].iloc[0]}`)", "",
              "Respaldos (etapa `basebackup`):", ""]
        for x in aa.itertuples():
            L.append(f"- {x.respaldo}: {x.segundos:.3f} s, {x.bytes} bytes ({x.MB:.2f} MB).")
        L += ["", "Razón de tamaño incr(n).bytes / full.bytes:", ""]
        for x in cbb.itertuples():
            L.append(f"- INCR {x.n}: {x.incr_bytes} / {x.full_bytes} = {x.razon_incr_vs_full:.3f}.")
        L += ["", "WAL dentro de cada respaldo:", ""]
        for x in ff.itertuples():
            med = ("; medido en el volumen: " + (f"{x.wal_bytes_medido} bytes, coincide" if x.wal_bytes_medido == x.wal_bytes_log
                                                 else f"{x.wal_bytes_medido} bytes, NO coincide")) if pd.notna(x.wal_bytes_medido) else ""
            L.append(f"- {x.respaldo}: {x.segmentos_wal_log} segmento(s) según el log ({x.wal_bytes_log} bytes, "
                     f"{x.pct_wal:.1f} % del respaldo){med}.")
        L += ["", f"Restauración, mediana de {int(bb['repeticiones'].min())} repeticiones por etapa (sin `total`):", ""]
        for x in bb.itertuples():
            L.append(f"- n={x.n}: combinar {x.combinar_s:.3f} s, arranque {x.arranque_s:.3f} s, "
                     f"validacion {x.validacion_s:.3f} s.")
        L += ["", "Restauración, `total` (mediana, mínimo y máximo) y razón restore(n) / restore(0):", ""]
        for x in cc.itertuples():
            L.append(f"- n={x.n}: {x.total_mediana_s:.3f} s ({x.total_min_s:.3f} a {x.total_max_s:.3f}), "
                     f"razón {x.razon_vs_n0:.3f}.")
        ee = e[e["corrida"] == corrida] if e is not None else pd.DataFrame()
        if len(ee):
            L += ["", "`pg_verifybackup` dentro de `total` (de los logs de restauración):", ""]
            for x in ee.itertuples():
                L.append(f"- n={x.n}: mediana {x.verify_mediana_s:.3f} s, {x.pct_mediana:.1f} % del total.")
        vv = vr[vr["corrida"] == corrida]
        if len(vv) and vv["verify_s"].notna().all():
            L += ["", "`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): "
                  + ", ".join(f"{x.respaldo} {x.verify_s:.3f} s" for x in vv.itertuples()) + "."]
        L.append("")

    L += ["### Gráficos", ""]
    L += [f"- `graficos/{g.name}`" for g in g1 + [g2, g3] + ([g4] if g4 else [])]

    # ---------------------------------------------------------------- interpretación
    L += ["", "## Interpretación", "",
          "Esta sección interpreta los números de arriba. No son mediciones nuevas.", ""]
    for corrida in corridas:
        aa, cbb = a[a["corrida"] == corrida], cb[cb["corrida"] == corrida]
        cc = c[c["corrida"] == corrida].set_index("n")
        bb = b[b["corrida"] == corrida].set_index("n")
        ff = f[f["corrida"] == corrida]
        inc = ff[ff["respaldo"] != "FULL"]
        resto = bb[bb.index > 0]
        L += [f"### `{corrida}`", ""]
        rmin, rmax = cbb["razon_incr_vs_full"].min(), cbb["razon_incr_vs_full"].max()
        razon_txt = f"{rmin:.3f}" if rmin == rmax else f"entre {rmin:.3f} y {rmax:.3f}"
        tamano = (f"- **Tamaño de los respaldos.** Cada INCR pesa {razon_txt} veces el FULL "
                  f"({aa['MB'].iloc[1:].min():.2f} a {aa['MB'].iloc[1:].max():.2f} MB, FULL {aa['MB'].iloc[0]:.2f} MB). ")
        if inc["pct_wal"].notna().all():
            tamano += (f"El WAL ocupa entre {inc['pct_wal'].min():.1f} % y {inc['pct_wal'].max():.1f} % de cada INCR; "
                       f"sin él, cada INCR pesa {inc['sin_wal_MB'].min():.2f} a {inc['sin_wal_MB'].max():.2f} MB. ")
        if corrida.startswith("deportista_"):
            tamano += ("Bolt agrega muy pocas filas por ronda, así que el tamaño del INCR es casi todo piso "
                       "fijo: el segmento de WAL y los archivos del sistema.")
        L.append(tamano.rstrip())
        L.append(
            f"- **Restauración.** La cadena completa (n=3) tomó {cc.loc[3, 'razon_vs_n0']:.2f} veces lo que el "
            f"FULL. `combinar` pasa de {bb.loc[0, 'combinar_s']:.3f} s con n=0 a "
            f"{resto['combinar_s'].min():.3f} a {resto['combinar_s'].max():.3f} s con n=1 a 3, y `arranque` "
            f"pasa de {bb.loc[0, 'arranque_s']:.3f} s a {resto['arranque_s'].min():.3f} a "
            f"{resto['arranque_s'].max():.3f} s. Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n "
            "mayor o igual a 1 usa `pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. "
            f"Entre n=1 y n=3 el `total` va de {cc.loc[1, 'total_mediana_s']:.3f} a "
            f"{cc.loc[3, 'total_mediana_s']:.3f} s." + (
                f" Las 3 repeticiones de n=0 ({cc.loc[0, 'total_min_s']:.3f} a {cc.loc[0, 'total_max_s']:.3f} s) "
                f"y de n=3 ({cc.loc[3, 'total_min_s']:.3f} a {cc.loc[3, 'total_max_s']:.3f} s) se solapan: "
                "la diferencia entre el FULL y la cadena completa está dentro de la variación entre "
                "repeticiones y no se interpreta."
                if cc.loc[3, "total_min_s"] <= cc.loc[0, "total_max_s"] else ""))
        L.append("")

    if len(corridas) > 1:
        sw = f[f["respaldo"] != "FULL"].groupby("corrida")["sin_wal_MB"].agg(["min", "max"])
        L += ["### Entre corridas", "",
              "- **Tamaño sin WAL** (comparable entre máquinas): "
              + ", ".join(f"`{k}` {v['min']:.2f} a {v['max']:.2f} MB" for k, v in sw.iterrows())
              + " por INCR. El FULL pesa casi lo mismo en todas porque la carga base es la misma.", ""]

    # ---------------------------------------------------------------- recomendación
    razones = c[c["n"] == 3].set_index("corrida")
    solapa = {k: c[(c["corrida"] == k) & (c["n"] == 3)]["total_min_s"].iloc[0]
              <= c[(c["corrida"] == k) & (c["n"] == 0)]["total_max_s"].iloc[0] for k in corridas}
    ahorro = 1 - cb.groupby("corrida")["razon_incr_vs_full"].max()
    L += ["## Recomendación para el volumen de datos manejado", "",
          f"Base: FULL de {a[a['respaldo'] == 'FULL']['MB'].min():.2f} a {a[a['respaldo'] == 'FULL']['MB'].max():.2f} MB "
          "y rondas de unas pocas a decenas de miles de filas.", "",
          "- **En ninguna corrida restaurar la cadena fue claramente más rápido que restaurar el FULL.** Cadena completa contra FULL: "
          + ", ".join(f"`{k}` {razones.loc[k, 'razon_vs_n0']:.2f} veces"
                      + (" (dentro de la variación entre repeticiones)" if solapa[k] else "") for k in corridas)
          + ". Donde la cadena tarda más, el aumento viene de `combinar` (`pg_combinebackup`).",
          "- **Cada INCR ahorra espacio, pero menos de lo que parece.** Cada INCR ahorra entre "
          f"{ahorro.min() * 100:.0f} % y {ahorro.max() * 100:.0f} % del tamaño de un FULL, y "
          "de lo que sí ocupa, una parte grande es el segmento fijo de WAL de 16 MiB.",
          "- **Recomendación.** Con este volumen conviene el **FULL frecuente** (por ejemplo, uno después de cada "
          "carga) cuando lo prioritario es el tiempo de restauración: el FULL es pequeño, se toma en segundos y "
          "se restaura sin combinar. El **incremental** conviene cuando lo prioritario es el espacio o la "
          "ventana de respaldo, con un FULL periódico para que la cadena sea corta, porque restaurar exige "
          "combinar toda la cadena.",
          "- **Diferencial.** El enunciado pide FULL más incremental **o** diferencial; el equipo eligió "
          "incremental (`pg_basebackup --incremental`, cada INCR encadenado al anterior), así que el "
          "diferencial no se midió y la recomendación no lo compara con datos.", ""]

    L += ["## Limitaciones", "",
          "- Se reporta la mediana de 3 repeticiones; la caché del sistema operativo puede favorecer a las "
          "repeticiones 2 y 3.",
          "- Las conclusiones valen para el volumen manejado (FULL de unos 50 MB); no se extrapolan a bases "
          "más grandes."]
    medidas = sorted(f.loc[f["wal_bytes_medido"].notna(), "corrida"].unique())
    solo_log = sorted(set(f["corrida"]) - set(medidas))
    if medidas:
        L.append(f"- El WAL de cada respaldo se midió en el volumen en {', '.join(medidas)} y coincide con el "
                 "cálculo desde el log; en " + (", ".join(solo_log) if solo_log else "ninguna otra corrida")
                 + " se toma del log con el mismo método.")
    if e is not None:
        L.append(f"- `pg_verifybackup` pesó entre {e['pct_mediana'].min():.1f} % y {e['pct_mediana'].max():.1f} % "
                 f"del `total` de restauración (mediana por n).")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
