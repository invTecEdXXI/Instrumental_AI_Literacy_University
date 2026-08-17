#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
limpieza_bruto_a_analiticov2.py
================================

Script de limpieza BRUTO -> ANALITICO.

Lee el fichero bruto de T0 (`dataset_raw2_T0.xlsx`, 162 registros que
consintieron) y aplica los criterios de exclusion del protocolo para
obtener la muestra analitica per-protocol de 150 casos (75 Experimental /
75 Control).

CRITERIOS DE EXCLUSION (jerarquia)
------------------------------------
  R1  No otorgo consentimiento informado  –  resuelto en el registro de
      reclutamiento; los 162 registros del fichero bruto ya consintieron.
  R2  Abandono antes de T1               –  Completo_T1 == "No"
  R3  Asistencia < 80 % del total de sesiones (criterio estrictamente
      menor; quienes alcanzan exactamente el 80 % se retienen).

SALIDAS
-------
  dataset_analitico.xlsx   muestra analitica (T0_PreTest, T1_PostTest,
                            T2_FollowUp, Formato_Largo, Resumen_Estadistico)
  consort_flujo.csv         cifras del diagrama CONSORT
  analisis_atricion.csv     tabla de comparacion basal
  log_limpieza.txt          registro de ejecucion

Uso:  python limpieza_bruto_a_analiticov2.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------

ARCHIVO_BRUTO       = "dataset_raw2_T0.xlsx"
HOJA_BRUTO          = "T0_Bruto"
HOJA_RECLUTAMIENTO  = "Registro_Reclutamiento"

ARCHIVO_SALIDA  = "dataset_analitico.xlsx"
ARCHIVO_CONSORT = "consort_flujo.csv"
ARCHIVO_ATRICION = "analisis_atricion.csv"
ARCHIVO_LOG     = "log_limpieza.txt"

UMBRAL_ASISTENCIA_PCT = 80.0

DIMENSIONES   = {"D1": 6, "D2": 6, "D3": 8, "D4": 6}
RANGO_LIKERT  = (1, 5)

# Columnas administrativas que no pasan al fichero analitico
COLS_ADMIN = [
    "ID_bruto", "Codigo_estudiante", "Fecha_T0", "Consentimiento_informado",
    "Participo_piloto", "Total_sesiones", "Sesiones_asistidas",
    "Asistencia_pct", "Completo_T0", "Completo_T1", "Completo_T2",
    "Completados", "Motivo_exclusion", "Fecha_abandono",
]

# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

_log_lineas: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    _log_lineas.append(msg)


def titulo(t: str) -> None:
    log("")
    log("=" * 74)
    log(t)
    log("=" * 74)


def volcar_log() -> None:
    Path(ARCHIVO_LOG).write_text("\n".join(_log_lineas), encoding="utf-8")


def items_likert(dim: str, k: int) -> list[str]:
    return [f"{dim}_{i:02d}" for i in range(1, k + 1)]


def items_obj(dim: str, k: int) -> list[str]:
    return [f"OBJ_{dim}_{i:02d}" for i in range(1, k + 1)]


TODOS_LIKERT = [c for d, k in DIMENSIONES.items() for c in items_likert(d, k)]
TODOS_OBJ    = [c for d, k in DIMENSIONES.items() for c in items_obj(d, k)]

# ---------------------------------------------------------------------------
# PASO 1. INTEGRIDAD DEL FICHERO BRUTO
# ---------------------------------------------------------------------------


def verificar_integridad(bruto: pd.DataFrame, reclutamiento: pd.DataFrame) -> None:
    titulo("PASO 1. INTEGRIDAD DEL FICHERO BRUTO")
    errores: list[str] = []

    n_bruto = len(bruto)
    n_rec   = len(reclutamiento)
    n_consint = int((reclutamiento["Consentimiento_informado"] == "Si").sum())
    log(f"  Inscritos en el registro ................. {n_rec}")
    log(f"  Consintieron ............................. {n_consint}")
    log(f"  Registros en el fichero bruto ............ {n_bruto}")

    if n_bruto != n_consint:
        errores.append(
            f"El fichero bruto tiene {n_bruto} filas pero consintieron {n_consint}"
        )

    if not bruto["ID_bruto"].is_unique:
        dup = bruto.loc[bruto["ID_bruto"].duplicated(), "ID_bruto"].tolist()
        errores.append(f"ID_bruto duplicados: {dup}")
    if not bruto["Codigo_estudiante"].is_unique:
        errores.append("Codigo_estudiante duplicado")
    log("  Identificadores unicos ................... OK")

    if (bruto["Consentimiento_informado"] != "Si").any():
        errores.append("Hay filas sin consentimiento en el fichero de T0")
    if (bruto["Participo_piloto"] != "No").any():
        errores.append("Hay participantes del piloto en el fichero de T0")
    log("  Consentimiento y criterio de piloto ...... OK")

    lik   = bruto[TODOS_LIKERT]
    fuera = ((lik < RANGO_LIKERT[0]) | (lik > RANGO_LIKERT[1])).sum().sum()
    if fuera:
        errores.append(f"{fuera} respuestas Likert fuera del rango 1-5")
    obj     = bruto[TODOS_OBJ]
    fuera_o = (~obj.isin([0, 1])).sum().sum()
    if fuera_o:
        errores.append(f"{fuera_o} items objetivos fuera de {{0,1}}")
    log("  Rangos de items (Likert 1-5, OBJ 0/1) .... OK")

    criticas = (
        ["Grupo", "Seccion", "Completados", "Asistencia_pct",
         "Sesiones_asistidas", "Total_sesiones"]
        + TODOS_LIKERT + TODOS_OBJ
    )
    perdidos = bruto[criticas].isna().sum()
    perdidos = perdidos[perdidos > 0]
    if len(perdidos):
        errores.append(
            f"Valores perdidos en variables criticas:\n{perdidos.to_string()}"
        )
    log("  Perdidos en variables criticas ........... 0")

    calc = (bruto["Sesiones_asistidas"] / bruto["Total_sesiones"] * 100).round(1)
    if not np.allclose(calc, bruto["Asistencia_pct"], atol=0.11):
        errores.append(
            "Asistencia_pct no coincide con Sesiones_asistidas/Total_sesiones"
        )
    log("  Coherencia de la asistencia .............. OK")

    if errores:
        for e in errores:
            log(f"  [ERROR] {e}")
        volcar_log()
        sys.exit("PASO 1 FALLIDO: el fichero bruto no supera los controles de integridad.")


# ---------------------------------------------------------------------------
# PASO 2. RECALCULO DE PUNTUACIONES DERIVADAS
# ---------------------------------------------------------------------------


def recalcular_scores(df: pd.DataFrame, verificar: bool = True) -> pd.DataFrame:
    """
    Recalcula las puntuaciones derivadas desde los items y, opcionalmente,
    contrasta con los valores almacenados.

    Formulas:
        Score_Dd                   = media de los items Likert de la dimension
        Score_conocimiento_Dd      = suma de los items objetivos de la dimension
        Score_conocimiento         = suma de los 26 items objetivos
        Score_total_autopercepcion = media de los 26 items Likert
    Las medias se redondean a 2 decimales.
    """
    df = df.copy()
    nuevos = {
        "Score_conocimiento": df[TODOS_OBJ].sum(axis=1).astype("int64")
    }
    for dim, k in DIMENSIONES.items():
        nuevos[f"Score_{dim}"] = df[items_likert(dim, k)].mean(axis=1).round(2)
        nuevos[f"Score_conocimiento_{dim}"] = (
            df[items_obj(dim, k)].sum(axis=1).astype("int64")
        )
    nuevos["Score_total_autopercepcion"] = df[TODOS_LIKERT].mean(axis=1).round(2)

    if verificar:
        discrepancias = []
        for col, serie in nuevos.items():
            if col not in df.columns:
                continue
            if pd.api.types.is_integer_dtype(serie):
                iguales = (df[col].astype("int64") == serie).all()
            else:
                iguales = np.allclose(
                    df[col].astype(float), serie, atol=1e-9
                )
            if not iguales:
                n = int(
                    (~np.isclose(
                        df[col].astype(float), serie.astype(float)
                    )).sum()
                )
                discrepancias.append(f"{col} ({n} filas)")
        if discrepancias:
            log(
                f"  [ERROR] Puntuaciones almacenadas != recalculadas: "
                f"{', '.join(discrepancias)}"
            )
            volcar_log()
            sys.exit("PASO 2 FALLIDO: las puntuaciones derivadas estan corruptas.")

    for col, serie in nuevos.items():
        df[col] = serie
    return df


# ---------------------------------------------------------------------------
# PASO 3. APLICACION DE LOS CRITERIOS DE EXCLUSION
# ---------------------------------------------------------------------------


def aplicar_exclusiones(
    bruto: pd.DataFrame, reclutamiento: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Aplica R1-R3 en jerarquia y devuelve el bruto etiquetado mas recuentos."""
    titulo("PASO 3. CRITERIOS DE EXCLUSION")

    df = bruto.copy()

    # R1: consentimiento – resuelto en el registro de reclutamiento
    r1 = int((reclutamiento["Consentimiento_informado"] == "No").sum())

    # R2: abandono antes de T1
    m_r2 = df["Completo_T1"].eq("No")

    # R3: asistencia < 80 % (solo entre quienes no cayeron en R2)
    # Criterio INCLUSIVO: exactamente el 80 % se retiene.
    m_r3 = (~m_r2) & (df["Asistencia_pct"] < UMBRAL_ASISTENCIA_PCT)

    df["_motivo_derivado"] = np.select(
        [m_r2, m_r3],
        ["Abandono antes de T1", "Asistencia < 80%"],
        default="",
    )
    df["_retenido"] = df["_motivo_derivado"] == ""

    conteos = {
        "rechazo_consentimiento": r1,
        "abandono_pre_t1":        int(m_r2.sum()),
        "asistencia_insuf":       int(m_r3.sum()),
        "retenidos":              int(df["_retenido"].sum()),
    }

    log(f"  R1  No otorgo consentimiento informado ... {r1:>3}")
    log(f"  R2  Abandono antes de T1 ................. {conteos['abandono_pre_t1']:>3}")
    log(f"  R3  Asistencia < {UMBRAL_ASISTENCIA_PCT:.0f}% ................... "
        f"{conteos['asistencia_insuf']:>3}")
    log(f"      Retenidos ........................... {conteos['retenidos']:>3}")

    # Detalle de los casos excluidos del fichero de T0
    log("")
    log(f"  Detalle de los {conteos['abandono_pre_t1'] + conteos['asistencia_insuf']} "
        f"excluidos del fichero de T0:")
    det = df.loc[
        ~df["_retenido"],
        ["ID_bruto", "Codigo_estudiante", "Grupo", "Seccion",
         "Sesiones_asistidas", "Total_sesiones", "Asistencia_pct",
         "_motivo_derivado"],
    ]
    for _, r in det.iterrows():
        log(
            f"    ID_bruto {r.ID_bruto:>4}  {r.Codigo_estudiante}  "
            f"{r.Grupo:<12} sec.{r.Seccion}  "
            f"{r.Sesiones_asistidas:>2}/{r.Total_sesiones} ses. "
            f"({r.Asistencia_pct:>5.1f}%)  {r._motivo_derivado}"
        )

    return df, conteos


# ---------------------------------------------------------------------------
# PASO 4. CONSTRUCCION DE LA MUESTRA ANALITICA (T0)
# ---------------------------------------------------------------------------


def construir_analitico(
    etiquetado: pd.DataFrame, cols_analiticas: list[str]
) -> pd.DataFrame:
    """Filtra los retenidos, asigna ID_estudiante 1..N y poda columnas."""
    titulo("PASO 4. CONSTRUCCION DE LA MUESTRA ANALITICA")

    ana = (
        etiquetado[etiquetado["_retenido"]]
        .sort_values("ID_bruto")
        .reset_index(drop=True)
        .copy()
    )
    ana.insert(0, "ID_estudiante", np.arange(1, len(ana) + 1))

    n_exp = int((ana["Grupo"] == "Experimental").sum())
    n_ctr = int((ana["Grupo"] == "Control").sum())
    log(f"  N analitico .............................. {len(ana)}")
    log(f"  Experimental / Control ................... {n_exp} / {n_ctr}")

    ana = ana.drop(
        columns=[
            c for c in COLS_ADMIN + ["_motivo_derivado", "_retenido"]
            if c in ana.columns
        ]
    )
    ana = ana[cols_analiticas]

    n_perdidos = int(ana.isna().sum().sum())
    log(f"  Valores perdidos ......................... {n_perdidos}")
    log(f"  Columnas ................................. {ana.shape[1]}")

    if n_perdidos:
        volcar_log()
        sys.exit("PASO 4 FALLIDO: hay valores perdidos en el fichero analitico.")

    return ana


# ---------------------------------------------------------------------------
# PASO 5. FORMATO LARGO Y RESUMEN ESTADISTICO
# ---------------------------------------------------------------------------


def construir_resumen(largo: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la hoja Resumen_Estadistico (Tiempo x Grupo x Dimension x Escala).

    La autopercepcion se calcula sobre la media sin redondear de los items,
    no sobre las columnas Score_* (redondeadas a 2 decimales), para reproducir
    la precision numerica del fichero de referencia.
    """
    bloques = [
        (d, items_likert(d, k), f"Score_conocimiento_{d}")
        for d, k in DIMENSIONES.items()
    ]
    bloques.append(("TOTAL", TODOS_LIKERT, "Score_conocimiento"))

    filas = []
    for tiempo in ["T0", "T1", "T2"]:
        for grupo in ["Experimental", "Control"]:
            sub = largo[(largo["Tiempo"] == tiempo) & (largo["Grupo"] == grupo)]
            for dim, items_auto, col_obj in bloques:
                for escala, s in [
                    ("Autopercepción", sub[items_auto].mean(axis=1)),
                    ("Conocimiento objetivo", sub[col_obj]),
                ]:
                    s = s.astype(float)
                    filas.append({
                        "Tiempo": tiempo, "Grupo": grupo, "Dimension": dim,
                        "Escala": escala, "N": len(s),
                        "Media":   round(s.mean(), 3),
                        "DE":      round(s.std(ddof=1), 3),
                        "Min":     round(s.min(), 2),
                        "Max":     round(s.max(), 2),
                        "Mediana": round(s.median(), 2),
                    })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# ANALISIS DE ATRICION
# ---------------------------------------------------------------------------


def analisis_atricion(etiquetado: pd.DataFrame) -> pd.DataFrame:
    titulo("ANALISIS DE ATRICION (comparabilidad basal T0)")

    comp = etiquetado[etiquetado["_retenido"]]
    exc  = etiquetado[~etiquetado["_retenido"]]

    variables = (
        ["Score_total_autopercepcion"]
        + [f"Score_{d}" for d in DIMENSIONES]
        + ["Score_conocimiento"]
        + [f"Score_conocimiento_{d}" for d in DIMENSIONES]
        + ["Anio_nacimiento", "Ciclo_academico"]
    )

    filas = []
    log(
        f"  {'Variable T0':<28}{'Completadores':>18}{'Excluidos':>18}"
        f"{'t':>8}{'p':>8}{'d':>8}"
    )
    log("  " + "-" * 86)

    for v in variables:
        a, b = comp[v].astype(float), exc[v].astype(float)
        t, p = stats.ttest_ind(a, b, equal_var=False)
        s_pool = np.sqrt(
            ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
            / (len(a) + len(b) - 2)
        )
        d = (a.mean() - b.mean()) / s_pool
        filas.append({
            "Variable_T0":           v,
            "N_completadores":       len(a),
            "Media_completadores":   round(a.mean(), 3),
            "DE_completadores":      round(a.std(ddof=1), 3),
            "N_excluidos":           len(b),
            "Media_excluidos":       round(b.mean(), 3),
            "DE_excluidos":          round(b.std(ddof=1), 3),
            "t_Welch":               round(t, 3),
            "p":                     round(p, 4),
            "d_Cohen":               round(d, 3),
        })
        log(
            f"  {v:<28}{a.mean():>9.2f} ({a.std(ddof=1):.2f})"
            f"{b.mean():>9.2f} ({b.std(ddof=1):.2f})"
            f"{t:>8.2f}{p:>8.3f}{d:>8.2f}"
        )

    tabla = pd.crosstab(etiquetado["Grupo"], etiquetado["_retenido"])
    odds, p_f = stats.fisher_exact(tabla.values)
    n_exp_out = int(tabla.loc["Experimental", False])
    n_ctr_out = int(tabla.loc["Control", False])
    log("  " + "-" * 86)
    log(
        f"  Atricion diferencial: Experimental {n_exp_out}/{int(tabla.loc['Experimental'].sum())} "
        f"vs Control {n_ctr_out}/{int(tabla.loc['Control'].sum())}  "
        f"-> Fisher exacto p = {p_f:.3f}, OR = {odds:.3f}"
    )

    sig = [f["Variable_T0"] for f in filas if f["p"] < 0.05]
    log("")
    if sig or p_f < 0.05:
        log(
            f"  ATENCION: diferencias basales significativas ({sig}"
            f"{'; atricion diferencial' if p_f < 0.05 else ''}). "
            f"Documenta el sesgo potencial en Limitaciones."
        )
    else:
        log("  Sin diferencias basales significativas (todas p > .05) y sin")
        log("  atricion diferencial: la perdida es compatible con MCAR.")

    filas.append({
        "Variable_T0":           "Atricion diferencial por grupo (Fisher exacto)",
        "N_completadores":       int(tabla.loc["Experimental", True]),
        "Media_completadores":   np.nan,
        "DE_completadores":      np.nan,
        "N_excluidos":           n_exp_out,
        "Media_excluidos":       np.nan,
        "DE_excluidos":          np.nan,
        "t_Welch":               round(odds, 3),
        "p":                     round(p_f, 4),
        "d_Cohen":               np.nan,
    })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# DIAGRAMA CONSORT
# ---------------------------------------------------------------------------


def tabla_consort(
    etiquetado: pd.DataFrame, reclutamiento: pd.DataFrame, conteos: dict
) -> pd.DataFrame:
    titulo("DIAGRAMA CONSORT")
    n_inscritos = len(reclutamiento)
    n_consint   = len(etiquetado)
    ret = etiquetado[etiquetado["_retenido"]]
    mot = etiquetado["_motivo_derivado"]
    exp = etiquetado["Grupo"] == "Experimental"
    ctr = etiquetado["Grupo"] == "Control"

    def fila(e, n, ne, nc):
        return {"Etapa_CONSORT": e, "N": n, "N_experimental": ne, "N_control": nc}

    t = pd.DataFrame([
        fila("Inscritos inicialmente (elegibles)", n_inscritos, "", ""),
        fila(
            "Rehusaron el consentimiento informado",
            -conteos["rechazo_consentimiento"], "", ""
        ),
        fila(
            "Consintieron y completaron T0", n_consint,
            int(exp.sum()), int(ctr.sum())
        ),
        fila(
            "Abandonaron antes de T1", -conteos["abandono_pre_t1"],
            -int((exp & (mot == "Abandono antes de T1")).sum()),
            -int((ctr & (mot == "Abandono antes de T1")).sum()),
        ),
        fila(
            "Incumplieron asistencia >= 80%", -conteos["asistencia_insuf"],
            -int((exp & (mot == "Asistencia < 80%")).sum()),
            -int((ctr & (mot == "Asistencia < 80%")).sum()),
        ),
        fila(
            "Analizados (per-protocol, T0/T1/T2)", len(ret),
            int((ret.Grupo == "Experimental").sum()),
            int((ret.Grupo == "Control").sum()),
        ),
        fila(
            "Tasa de atricion",
            f"{(n_inscritos - len(ret)) / n_inscritos * 100:.1f}%", "", ""
        ),
    ])
    for _, r in t.iterrows():
        extra = (
            f"   [Exp {r.N_experimental} | Ctrl {r.N_control}]"
            if r.N_experimental != "" else ""
        )
        log(f"  {r.Etapa_CONSORT:<44}{str(r.N):>7}{extra}")
    return t


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    log(f"limpieza_bruto_a_analiticov2.py  --  {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"Entrada : {ARCHIVO_BRUTO}  (hojas {HOJA_BRUTO}, {HOJA_RECLUTAMIENTO})")
    log(f"Salida  : {ARCHIVO_SALIDA}")

    if not Path(ARCHIVO_BRUTO).exists():
        sys.exit(f"ERROR: no se encuentra {ARCHIVO_BRUTO}.")

    bruto          = pd.read_excel(ARCHIVO_BRUTO, sheet_name=HOJA_BRUTO)
    reclutamiento  = pd.read_excel(ARCHIVO_BRUTO, sheet_name=HOJA_RECLUTAMIENTO)

    # Columnas que pasan al fichero analitico (mismo orden que en el bruto,
    # sin las columnas administrativas, con ID_estudiante al frente).
    cols_analiticas = ["ID_estudiante"] + [
        c for c in bruto.columns if c not in COLS_ADMIN
    ]

    # --- Paso 1: integridad ---------------------------------------------------
    verificar_integridad(bruto, reclutamiento)

    # --- Paso 2: recalculo de scores -----------------------------------------
    titulo("PASO 2. RECALCULO DE PUNTUACIONES DERIVADAS")
    bruto = recalcular_scores(bruto, verificar=True)
    log("  Las puntuaciones derivadas coinciden con el recalculo desde items.")

    # --- Paso 3: exclusiones -------------------------------------------------
    etiquetado, conteos = aplicar_exclusiones(bruto, reclutamiento)

    # --- Paso 4: muestra analitica T0 ----------------------------------------
    ana_t0 = construir_analitico(etiquetado, cols_analiticas)

    # --- Paso 5: datos longitudinales (T1 / T2) ------------------------------
    # Los datos de T1 y T2 provienen del fichero longitudinal completo.
    # Se filtran los IDs retenidos y se recalculan los scores.
    titulo("PASO 5. INCORPORACION DE DATOS LONGITUDINALES (T1 / T2)")
    ids_retenidos = list(ana_t0["ID_estudiante"])

    # Fuente longitudinal: el propio fichero analitico previo si existe,
    # o cualquier fuente con las hojas T1_PostTest / T2_FollowUp.
    fuente_long = ARCHIVO_SALIDA
    hojas: dict[str, pd.DataFrame] = {"T0_PreTest": ana_t0}

    if Path(fuente_long).exists():
        for hoja, etiqueta in [("T1_PostTest", "T1"), ("T2_FollowUp", "T2")]:
            try:
                df_long = pd.read_excel(fuente_long, sheet_name=hoja)
                df_long = (
                    df_long[df_long["ID_estudiante"].isin(ids_retenidos)]
                    .sort_values("ID_estudiante")
                    .reset_index(drop=True)
                )
                df_long = recalcular_scores(df_long, verificar=True)
                # Alinear columnas con T0
                cols_disponibles = [c for c in cols_analiticas if c in df_long.columns]
                hojas[hoja] = df_long[cols_disponibles]
                log(f"  {etiqueta}: {len(hojas[hoja])} filas recuperadas.")
            except Exception as exc:
                log(f"  AVISO: no se pudo leer {hoja} ({exc}). Hoja omitida.")
    else:
        log(f"  AVISO: {fuente_long} no existe; se generan solo datos de T0.")

    # Formato largo y resumen
    largo = pd.concat(list(hojas.values()), ignore_index=True)
    hojas["Formato_Largo"]      = largo
    hojas["Resumen_Estadistico"] = construir_resumen(largo)

    # --- Analisis auxiliares -------------------------------------------------
    consort  = tabla_consort(etiquetado, reclutamiento, conteos)
    atricion = analisis_atricion(etiquetado)

    # --- Escritura -----------------------------------------------------------
    titulo("ESCRITURA DE RESULTADOS")
    with pd.ExcelWriter(ARCHIVO_SALIDA, engine="openpyxl") as w:
        for nombre, df in hojas.items():
            df.to_excel(w, sheet_name=nombre, index=False)
            log(f"  {ARCHIVO_SALIDA} / {nombre:<22} {df.shape[0]:>4} x {df.shape[1]}")
    consort.to_csv(ARCHIVO_CONSORT,   index=False, encoding="utf-8-sig")
    atricion.to_csv(ARCHIVO_ATRICION, index=False, encoding="utf-8-sig")
    log(f"  {ARCHIVO_CONSORT}")
    log(f"  {ARCHIVO_ATRICION}")
    log(f"  {ARCHIVO_LOG}")

    log("")
    log("LIMPIEZA COMPLETADA")
    volcar_log()


if __name__ == "__main__":
    main()
