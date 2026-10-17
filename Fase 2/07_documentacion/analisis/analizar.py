"""Análisis comparativo de tiempos de respaldo y restauración (sección 4.10).

Uso, desde cualquier carpeta:
    python "Fase 2/07_documentacion/analisis/analizar.py"

Lee (solo lectura) 05_logs/tiempos_*.csv y los logs de restauración de
05_logs/<tipo>_<persona>/. Escribe:
    07_documentacion/analisis/ESTADO_CSV.md
    07_documentacion/analisis/tabla_*.csv y tabla_*.md
    07_documentacion/analisis/RESUMEN_ANALISIS.md
    07_documentacion/graficos/grafico*.png

Un CSV entra al análisis solo si valida: encabezado de 14 columnas de la 4.10,
53 líneas (encabezado y 52 filas), 14 campos en todas las líneas, 0 ALERTA y
`paso` de dos dígitos leído como texto.
"""

from pathlib import Path
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
COLUMNAS = ENCABEZADO.split(",")
LINEAS_ESPERADAS = 53
ETAPAS = ["combinar", "arranque", "validacion"]
PASOS_VALIDOS = {"02", "04", "06", "08", "12", "13", "14", "15"}
PENDIENTE = "[PENDIENTE]"


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


def guardar_tabla(df: pd.DataFrame, nombre: str, titulo: str, nota: str = "") -> str:
    df.to_csv(SALIDA / f"{nombre}.csv", index=False, lineterminator="\n")
    md = f"# {titulo}\n\n" + (nota + "\n\n" if nota else "") + tabla_md(df)
    escribir(SALIDA / f"{nombre}.md", md)
    return md


def mb(b) -> float:
    return round(float(b) / 1_000_000, 2)


# ------------------------------------------------------------------ validación

def validar(ruta: Path) -> list[str]:
    """Devuelve la lista de motivos de exclusión (vacía si el CSV es válido)."""
    motivos = []
    crudo = ruta.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        motivos.append("tiene BOM (la 4.10 pide UTF-8 sin BOM)")
    if b"\r\n" in crudo:
        motivos.append("tiene fin de línea CRLF (la 4.10 pide LF)")
    lineas = crudo.decode("utf-8", errors="replace").replace("\r\n", "\n").rstrip("\n").split("\n")
    if lineas[0].lstrip("﻿") != ENCABEZADO:
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
    return motivos


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
    med = t.groupby(["corrida", "maquina", "n_cadena"])["segundos"].median().reset_index()
    base = med[med["n_cadena"] == 0].set_index("corrida")["segundos"]
    med["razon_vs_n0"] = med.apply(lambda x: x["segundos"] / base[x["corrida"]], axis=1).round(3)
    med["segundos"] = med["segundos"].round(3)
    return med.rename(columns={"n_cadena": "n", "segundos": "total_mediana_s"})


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


def tabla_e(df):
    """Segundos de pg_verifybackup leídos de los logs de restauración."""
    filas = []
    t = df[(df["operacion"] == "restore") & (df["etapa"] == "total")]
    for x in t.itertuples():
        log = LOGS / x.corrida / f"{x.corrida}_{x.paso}_restore_cadena{x.n_cadena}_rep{x.repeticion}.log"
        seg = None
        if log.exists():
            m = re.search(r"^pg_verifybackup: ([0-9.]+) s$",
                          log.read_text(encoding="utf-8", errors="replace"), re.M)
            if m:
                seg = float(m.group(1))
        filas.append({"corrida": x.corrida, "n": x.n_cadena, "repeticion": x.repeticion,
                      "verify_s": seg, "total_s": x.segundos})
    e = pd.DataFrame(filas)
    if e.empty or e["verify_s"].isna().any():
        return None
    e["pct"] = e["verify_s"] / e["total_s"] * 100
    res = e.groupby(["corrida", "n"]).agg(verify_mediana_s=("verify_s", "median"),
                                           total_mediana_s=("total_s", "median"),
                                           pct_mediana=("pct", "median")).reset_index()
    return res.round({"verify_mediana_s": 3, "total_mediana_s": 3, "pct_mediana": 1})


def verify_respaldos(df):
    filas = []
    r = df[df["operacion"].isin(["backup_full", "backup_incr"])]
    for x in r.itertuples():
        nombre = "backup_full" if x.operacion == "backup_full" else f"backup_incr{x.n_cadena}"
        log = LOGS / x.corrida / f"{x.corrida}_{x.paso}_{nombre}.log"
        seg = None
        if log.exists():
            m = re.search(r"^pg_verifybackup: ([0-9.]+) s$",
                          log.read_text(encoding="utf-8", errors="replace"), re.M)
            if m:
                seg = float(m.group(1))
        filas.append({"corrida": x.corrida, "respaldo": "FULL" if x.n_cadena == 0 else f"INCR {x.n_cadena}",
                      "verify_s": seg, "basebackup_s": x.segundos})
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

    estado, validos = [], []
    for ruta in sorted(LOGS.glob("tiempos_*.csv")):
        motivos = validar(ruta)
        estado.append((ruta.name, motivos))
        if not motivos:
            validos.append(cargar(ruta))
    esperados = ["tiempos_anio_pa.csv", "tiempos_deporte_pb.csv", "tiempos_deportista_pc.csv"]
    presentes = {n for n, _ in estado}

    md = ["# Estado de los CSV de tiempos", "",
          "Generado por `analizar.py`. Criterios: encabezado de 14 columnas de la sección 4.10, "
          f"{LINEAS_ESPERADAS} líneas, 14 campos por línea, UTF-8 sin BOM, LF, 0 filas con ALERTA "
          "y `paso` de dos dígitos leído como texto.", "",
          "| Archivo | Estado | Motivo |", "|---|---|---|"]
    for nombre, motivos in estado:
        md.append(f"| `{nombre}` | {'válido' if not motivos else 'excluido'} | "
                  f"{'; '.join(motivos) if motivos else ''} |")
    for nombre in esperados:
        if nombre not in presentes:
            md.append(f"| `{nombre}` | no existe | {PENDIENTE} |")
    escribir(SALIDA / "ESTADO_CSV.md", "\n".join(md) + "\n")
    print("\n".join(md))

    if not validos:
        print("Ningún CSV válido: no se generan tablas ni gráficos.")
        return
    df = pd.concat(validos, ignore_index=True)

    a = tabla_a(df)
    b = tabla_b(df)
    c = tabla_c_restore(df)
    cb = tabla_c_bytes(df)
    e = tabla_e(df)
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
    guardar_tabla(c, "tabla_c1_razon_restauracion",
                  "Tabla (c1): restore(n) / restore(0)",
                  "Solo `etapa == total`, mediana de las repeticiones.")
    guardar_tabla(cb, "tabla_c2_razon_bytes", "Tabla (c2): incr(n).bytes / full.bytes")
    if len(maquinas) > 1:
        d = c[c["corrida"].str.startswith("deportista_")].pivot_table(
            index="n", columns="maquina", values="razon_vs_n0").reset_index()
        guardar_tabla(d, "tabla_d_maquinas", "Tabla (d): razones de Bolt por máquina")
    else:
        escribir(SALIDA / "tabla_d_maquinas.md",
                 "# Tabla (d): razones de Bolt por máquina\n\n"
                 f"{PENDIENTE} Solo hay una máquina con CSV válido de deportista "
                 f"({', '.join(maquinas) or 'ninguna'}). Falta `tiempos_deportista_pa.csv` "
                 "y `tiempos_deportista_pb.csv`.\n")
    if e is not None:
        guardar_tabla(e, "tabla_e_pg_verifybackup",
                      "Tabla (e): peso de pg_verifybackup dentro de total",
                      "Segundos leídos de la línea `pg_verifybackup: X s` de cada log de "
                      "restauración. `pct_mediana` es la mediana de verify/total por repetición.")
    else:
        escribir(SALIDA / "tabla_e_pg_verifybackup.md",
                 f"# Tabla (e): peso de pg_verifybackup\n\n{PENDIENTE} Faltan logs de restauración "
                 "con la línea `pg_verifybackup: X s`.\n")

    g1 = grafico1(b)
    g2 = grafico2(a)
    g3 = grafico3(c)
    g4 = grafico4(c, maquinas) if len(maquinas) > 1 else None

    escribir(SALIDA / "RESUMEN_ANALISIS.md",
             resumen(estado, esperados, presentes, a, b, c, cb, e, vr, maquinas, g1, g2, g3, g4))
    print("\nTablas en", SALIDA)
    print("Gráficos:", ", ".join(p.name for p in g1 + [g2, g3] + ([g4] if g4 else [])))


def resumen(estado, esperados, presentes, a, b, c, cb, e, vr, maquinas, g1, g2, g3, g4):
    L = ["# Resumen del análisis comparativo (sección 4.10)", "",
         "Generado por `07_documentacion/analisis/analizar.py` a partir de `05_logs/tiempos_*.csv`. "
         "Todos los números salen de los CSV y de los logs; no hay valores escritos a mano.", "",
         "## Datos usados", ""]
    for nombre, motivos in estado:
        L.append(f"- `{nombre}`: " + ("válido." if not motivos else "excluido: " + "; ".join(motivos) + "."))
    for nombre in esperados:
        if nombre not in presentes:
            L.append(f"- `{nombre}`: no existe. {PENDIENTE}")
    L += ["", "Detalle en `ESTADO_CSV.md`.", "",
          "**Advertencia:** las máquinas del equipo son distintas. Entre máquinas se comparan "
          "razones (por ejemplo restore(n)/restore(0)), no segundos. Los segundos absolutos "
          "solo sirven dentro de una misma corrida.", "",
          "## Medido", ""]

    for corrida in a["corrida"].unique():
        aa = a[a["corrida"] == corrida]
        bb = b[b["corrida"] == corrida]
        cc = c[c["corrida"] == corrida]
        cbb = cb[cb["corrida"] == corrida]
        L += [f"### Corrida `{corrida}` (máquina `{aa['maquina'].iloc[0]}`)", "",
              "Respaldos (etapa `basebackup`):", ""]
        for x in aa.itertuples():
            L.append(f"- {x.respaldo}: {x.segundos:.3f} s, {x.bytes} bytes ({x.MB:.2f} MB).")
        L += ["", "Razón de tamaño incr(n).bytes / full.bytes:", ""]
        for x in cbb.itertuples():
            L.append(f"- INCR {x.n}: {x.incr_bytes} / {x.full_bytes} = {x.razon_incr_vs_full:.3f}.")
        L += ["", f"Restauración, mediana de {int(bb['repeticiones'].min())} repeticiones por etapa (sin `total`):", ""]
        for x in bb.itertuples():
            L.append(f"- n={x.n}: combinar {x.combinar_s:.3f} s, arranque {x.arranque_s:.3f} s, "
                     f"validacion {x.validacion_s:.3f} s.")
        L += ["", "Restauración, `total` (mediana) y razón restore(n) / restore(0):", ""]
        for x in cc.itertuples():
            L.append(f"- n={x.n}: {x.total_mediana_s:.3f} s, razón {x.razon_vs_n0:.3f}.")
        if e is not None:
            ee = e[e["corrida"] == corrida]
            L += ["", "`pg_verifybackup` dentro de `total` (de los logs de restauración):", ""]
            for x in ee.itertuples():
                L.append(f"- n={x.n}: mediana {x.verify_mediana_s:.3f} s, {x.pct_mediana:.1f} % del total.")
        else:
            L += ["", f"`pg_verifybackup` en la restauración: {PENDIENTE}"]
        vv = vr[vr["corrida"] == corrida]
        if vv["verify_s"].notna().all():
            L += ["", "`pg_verifybackup` de los respaldos (fuera del tiempo medido, solo informativo): "
                  + ", ".join(f"{x.respaldo} {x.verify_s:.3f} s" for x in vv.itertuples()) + "."]
        L.append("")

    L += ["### Comparación entre máquinas (tabla d, gráfico 4)", ""]
    if len(maquinas) > 1:
        L.append(f"Máquinas con CSV válido de deportista: {', '.join(maquinas)}. Ver `tabla_d_maquinas.md`.")
    else:
        L.append(f"{PENDIENTE} Solo hay una máquina con CSV válido de deportista "
                 f"({', '.join(maquinas)}). La tabla (d) y el gráfico 4 se generan cuando existan "
                 "`tiempos_deportista_pa.csv` y `tiempos_deportista_pb.csv` válidos.")
    L += ["", "### Gráficos", ""]
    for g in g1 + [g2, g3]:
        L.append(f"- `graficos/{g.name}`")
    L.append(f"- `graficos/{g4.name}`" if g4 else f"- Gráfico 4 (comparación entre máquinas): {PENDIENTE}")

    L += ["", "## Interpretación", "",
          "Esta sección interpreta los números de arriba. No son mediciones nuevas.", ""]
    if "deportista_pc" in set(a["corrida"]):
        aa = a[a["corrida"] == "deportista_pc"]
        cbb = cb[cb["corrida"] == "deportista_pc"]
        cc = c[c["corrida"] == "deportista_pc"].set_index("n")
        bb = b[b["corrida"] == "deportista_pc"].set_index("n")
        L += [
            f"- **Costo fijo en la carga de Bolt.** Las rondas de Bolt agregan muy pocas filas, "
            f"pero cada INCR pesa entre {cbb['razon_incr_vs_full'].min():.3f} y "
            f"{cbb['razon_incr_vs_full'].max():.3f} veces el FULL "
            f"({aa['MB'].iloc[1:].min():.2f} a {aa['MB'].iloc[1:].max():.2f} MB). La hipótesis de la "
            "4.10 es que ese tamaño lo domina un piso fijo (al menos un segmento de WAL de 16 MB y "
            "archivos del sistema) y no los datos nuevos. Falta confirmarlo midiendo `pg_wal` dentro "
            f"de cada respaldo. {PENDIENTE}",
            f"- **Restauración.** La cadena completa (n=3) tomó {cc.loc[3, 'razon_vs_n0']:.2f} veces "
            f"lo que el FULL. `combinar` sube de {bb.loc[0, 'combinar_s']:.3f} s con n=0 a "
            f"{bb[bb.index > 0]['combinar_s'].min():.3f} a {bb[bb.index > 0]['combinar_s'].max():.3f} s con n=1 a 3, "
            f"mientras `arranque` baja de {bb.loc[0, 'arranque_s']:.3f} s a "
            f"{bb[bb.index > 0]['arranque_s'].min():.3f} a {bb[bb.index > 0]['arranque_s'].max():.3f} s. "
            "Con n=0 `restaurar.sh` copia el FULL con `cp -a`; con n mayor o igual a 1 usa "
            "`pg_combinebackup`, así que n=0 y n=1 no miden la misma herramienta. Entre n=1 y n=3 el "
            f"`total` cambia de {cc.loc[1, 'total_mediana_s']:.3f} a {cc.loc[3, 'total_mediana_s']:.3f} s. "
            "Con tres repeticiones y diferencias de décimas de segundo, no se interpreta la causa de "
            "la baja de `arranque`.",
            "- **Alcance.** Con Bolt domina el costo fijo de cada respaldo y de cada restauración: "
            f"el tiempo medido más largo de la corrida es {max(aa['segundos'].max(), cc['total_mediana_s'].max()):.3f} s "
            "(respaldos y `total` mediano). Estos números **no** sirven para concluir en "
            "general si conviene el respaldo incremental o el FULL frecuente: esa comparación necesita "
            f"las corridas con más volumen (por año y por deporte). {PENDIENTE}",
            "- **Repeticiones.** Se reporta la mediana de 3 repeticiones. La caché del sistema operativo "
            "puede favorecer a las repeticiones 2 y 3.",
        ]
        if e is not None:
            ee = e[e["corrida"] == "deportista_pc"]
            L.append(f"- **pg_verifybackup** pesó entre {ee['pct_mediana'].min():.1f} % y "
                     f"{ee['pct_mediana'].max():.1f} % del `total` de restauración (mediana por n).")
    L += ["",
          "## Pendiente", "",
          f"- {PENDIENTE} CSV válidos de `anio_pa`, `deporte_pb`, `deportista_pa` y `deportista_pb`.",
          f"- {PENDIENTE} Tabla (d) y gráfico 4 (requieren más de una máquina).",
          f"- {PENDIENTE} Recomendación por escenario (FULL, incremental, diferencial): requiere las "
          "corridas con más volumen.",
          f"- {PENDIENTE} Tamaño de `pg_wal` dentro de cada respaldo, para confirmar el piso fijo.",
          ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
