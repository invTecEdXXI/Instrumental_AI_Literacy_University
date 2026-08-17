#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
reanalisis_menores.py
=====================

Re-analisis menores pendientes del plan E1 (16-ago-2026):

  A. Rank-ANCOVA (Conover) para el contraste primario, con SE clasico y
     CR2+Satterthwaite por seccion — sensibilidad a la no-normalidad
     detectada por Shapiro-Wilk (R2.22).
  B. Sensibilidad de atricion por cotas (R2.27): los 12 excluidos solo
     tienen T0 (no existen T1/T2), de modo que un LMM MAR no aporta
     informacion adicional; se calculan cotas explicitas del efecto
     imputando escenarios extremos:
       - Peor caso: excluidos del GE sin ganancia (T1=T0); excluidos del
         GC con la ganancia media del GE.
       - Mejor caso: espejo del anterior.
  C. Moderadores (R2.26): test omnibus F de la interaccion Grupo x
     Moderador en la ANCOVA de T1 (Facultad, Genero, Experiencia previa),
     con tabla de n por celda y reglas documentadas para categorias
     pequenas (Genero: sensibilidad binaria excluyendo No binario n=7;
     Experiencia: sensibilidad colapsando Intermedia+Avanzada).
  D. Figura 1 nueva (R2.24/E3): cargas estandarizadas del CFA WLSMV
     (desde CFA_WLSMV_cargas.csv), sin titulo embebido, segura en escala
     de grises, 300 dpi, PNG+PDF.

Salidas: SensibilidadA_rank_ancova.csv, SensibilidadB_cotas_atricion.csv,
         Moderadores_omnibus.csv, Moderadores_n_celdas.csv,
         figuras_nuevas/Fig1_CFA_Loadings.(png|pdf),
         log_menores.txt
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DIR = Path(__file__).parent
RUTA_ANALITICO = DIR.parent / "work" / "dataset_analitico.xlsx"
RUTA_BRUTO = DIR.parent / "work" / "dataset_raw2_T0.xlsx"

PRIMARIOS = ["Score_total_autopercepcion", "Score_conocimiento"]
SUBESCALAS = [f"Score_D{i}" for i in range(1, 5)] + \
             [f"Score_conocimiento_D{i}" for i in range(1, 5)]

_log: list[str] = []


def log(m: str = "") -> None:
    print(m)
    _log.append(m)


def titulo(t: str) -> None:
    log("")
    log("=" * 74)
    log(t)
    log("=" * 74)


def ols(X, y):
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    return beta, resid, XtX_inv


def cr2_satt(X, y, clusters, idx):
    n, k = X.shape
    beta, resid, XtX_inv = ols(X, y)
    H = X @ XtX_inv @ X.T
    M = np.eye(n) - H
    ell = np.zeros(k)
    ell[idx] = 1.0
    q = XtX_inv @ ell
    V = 0.0
    W_cols = []
    for c in np.unique(clusters):
        sel = clusters == c
        Xg = X[sel]
        Hgg = Xg @ XtX_inv @ Xg.T
        vals, vecs = np.linalg.eigh(np.eye(sel.sum()) - Hgg)
        Ag = vecs @ np.diag(np.clip(vals, 1e-12, None) ** -0.5) @ vecs.T
        ag = Ag @ Xg @ q
        V += float(ag @ resid[sel]) ** 2
        W_cols.append(M[sel, :].T @ ag)
    G = np.column_stack(W_cols)
    S = G.T @ G
    gl = float(np.trace(S)) ** 2 / float(np.trace(S @ S))
    se = np.sqrt(V)
    t = beta[idx] / se
    p = 2 * stats.t.sf(abs(t), gl)
    return beta[idx], se, gl, t, p


# ---------------------------------------------------------------------------

def cargar_ancho():
    xl = pd.ExcelFile(RUTA_ANALITICO)
    t0 = xl.parse("T0_PreTest")
    t1 = xl.parse("T1_PostTest")
    scores = PRIMARIOS + SUBESCALAS
    df = t0[["ID_estudiante", "Grupo", "Seccion", "Facultad", "Genero",
             "Experiencia_previa_IA"] + scores].rename(
        columns={s: s + "_T0" for s in scores})
    df = df.merge(
        t1[["ID_estudiante"] + scores].rename(columns={s: s + "_T1" for s in scores}),
        on="ID_estudiante", validate="1:1")
    df["Trat"] = (df["Grupo"] == "Experimental").astype(float)
    return df


# ---------------------------------------------------------------------------
# A. Rank-ANCOVA
# ---------------------------------------------------------------------------

def rank_ancova(df) -> pd.DataFrame:
    filas = []
    for s in PRIMARIOS + SUBESCALAS:
        pre = stats.rankdata(df[f"{s}_T0"])
        post = stats.rankdata(df[f"{s}_T1"])
        X = np.column_stack([np.ones(len(df)), df["Trat"].to_numpy(), pre])
        n, k = X.shape
        beta, resid, XtX_inv = ols(X, post)
        s2 = resid @ resid / (n - k)
        se = np.sqrt(s2 * XtX_inv[1, 1])
        t = beta[1] / se
        p_cls = 2 * stats.t.sf(abs(t), n - k)
        b2, se2, gl2, t2, p_cr2 = cr2_satt(X, post, df["Seccion"].to_numpy(), 1)
        filas.append({
            "Outcome": s, "b_rangos": round(beta[1], 2),
            "t_clasico": round(t, 2), "p_clasico": p_cls,
            "SE_CR2": round(se2, 2), "gl_Satt": round(gl2, 2),
            "p_CR2": round(p_cr2, 4) if p_cr2 >= 1e-4 else "<.0001",
        })
    out = pd.DataFrame(filas)
    out["p_clasico"] = out["p_clasico"].map(
        lambda v: round(v, 4) if v >= 1e-4 else "<.0001")
    return out


# ---------------------------------------------------------------------------
# B. Cotas de atricion
# ---------------------------------------------------------------------------

def cotas_atricion(df) -> pd.DataFrame:
    bruto = pd.ExcelFile(RUTA_BRUTO).parse("T0_Bruto")
    exc = bruto[bruto["Motivo_exclusion"].notna() &
                (bruto["Motivo_exclusion"] != "")].copy()
    log(f"  Excluidos con T0 disponibles: {len(exc)} "
        f"(Exp {int((exc['Grupo']=='Experimental').sum())} / "
        f"Ctrl {int((exc['Grupo']=='Control').sum())})")

    filas = []
    for s in PRIMARIOS:
        pre_c = df[f"{s}_T0"].to_numpy(float)
        post_c = df[f"{s}_T1"].to_numpy(float)
        trat_c = df["Trat"].to_numpy(float)

        gan_e = (post_c - pre_c)[trat_c == 1].mean()
        gan_c = (post_c - pre_c)[trat_c == 0].mean()

        pre_x = exc[s].to_numpy(float)
        trat_x = (exc["Grupo"] == "Experimental").astype(float).to_numpy()

        def efecto(post_extra):
            pre_all = np.concatenate([pre_c, pre_x])
            post_all = np.concatenate([post_c, post_extra])
            trat_all = np.concatenate([trat_c, trat_x])
            X = np.column_stack([np.ones(len(pre_all)), trat_all, pre_all])
            beta, resid, XtX_inv = ols(X, post_all)
            n, k = X.shape
            s2 = resid @ resid / (n - k)
            se = np.sqrt(s2 * XtX_inv[1, 1])
            p = 2 * stats.t.sf(abs(beta[1] / se), n - k)
            return beta[1], se, p

        # Completadores (referencia)
        Xc = np.column_stack([np.ones(len(pre_c)), trat_c, pre_c])
        beta, resid, XtX_inv = ols(Xc, post_c)
        s2 = resid @ resid / (len(pre_c) - 3)
        se_ref = np.sqrt(s2 * XtX_inv[1, 1])
        b_ref = beta[1]

        # Peor caso: GE excluido sin ganancia; GC excluido con ganancia del GE
        post_peor = pre_x + np.where(trat_x == 1, 0.0, gan_e)
        b_p, se_p, p_p = efecto(post_peor)
        # Mejor caso: GE excluido con ganancia del GE; GC excluido sin ganancia
        post_mejor = pre_x + np.where(trat_x == 1, gan_e, gan_c * 0)
        b_m, se_m, p_m = efecto(post_mejor)
        # Escenario MAR-plausible: cada excluido recibe la ganancia media
        # de su propio brazo
        post_mar = pre_x + np.where(trat_x == 1, gan_e, gan_c)
        b_r, se_r, p_r = efecto(post_mar)

        filas.append({
            "Outcome": s,
            "b_completadores": round(b_ref, 3), "SE_comp": round(se_ref, 3),
            "b_peor_caso": round(b_p, 3), "p_peor_caso":
                round(p_p, 6) if p_p >= 1e-6 else "<1e-6",
            "b_mejor_caso": round(b_m, 3),
            "b_MAR_plausible": round(b_r, 3),
            "Cambio_rel_peor_%": round(100 * (b_p - b_ref) / b_ref, 1),
        })
        log(f"  {s}: b_comp={b_ref:.3f} | peor={b_p:.3f} (p={p_p:.2e}) | "
            f"mejor={b_m:.3f} | MAR={b_r:.3f}")
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# C. Moderadores
# ---------------------------------------------------------------------------

def moderadores(df):
    import statsmodels.formula.api as smf
    from statsmodels.stats.anova import anova_lm

    d = df.copy()
    d["Genero_bin"] = d["Genero"].where(d["Genero"] != "No binario")
    d["Exp_colapsada"] = d["Experiencia_previa_IA"].replace(
        {"Avanzada": "Intermedia/Avanzada", "Intermedia": "Intermedia/Avanzada"})

    especificaciones = [
        ("Facultad", "Facultad", None),
        ("Genero (3 categorias)", "Genero", None),
        ("Genero (binario, sens.)", "Genero_bin", "Genero_bin == Genero_bin"),
        ("Experiencia previa (4 cat.)", "Experiencia_previa_IA", None),
        ("Experiencia (colapsada, sens.)", "Exp_colapsada", None),
    ]
    filas = []
    for s in PRIMARIOS:
        for nombre, var, filtro in especificaciones:
            dd = d.dropna(subset=[var]).copy()
            dd = dd.rename(columns={f"{s}_T0": "Pre", f"{s}_T1": "Post"})
            m0 = smf.ols(f"Post ~ Pre + Trat + C({var})", data=dd).fit()
            m1 = smf.ols(f"Post ~ Pre + Trat * C({var})", data=dd).fit()
            cmp = anova_lm(m0, m1)
            F = float(cmp["F"].iloc[1])
            p = float(cmp["Pr(>F)"].iloc[1])
            df1 = int(cmp["df_diff"].iloc[1])
            df2 = int(m1.df_resid)
            filas.append({
                "Outcome": s, "Moderador": nombre, "n": len(dd),
                "F_interaccion": round(F, 3), "df1": df1, "df2": df2,
                "p": round(p, 4),
            })
    omnibus = pd.DataFrame(filas)

    celdas = []
    for var in ["Facultad", "Genero", "Experiencia_previa_IA"]:
        t = d.groupby([var, "Grupo"]).size().reset_index(name="n")
        t.insert(0, "Moderador", var)
        t = t.rename(columns={var: "Categoria"})
        celdas.append(t)
    n_celdas = pd.concat(celdas, ignore_index=True)
    return omnibus, n_celdas


# ---------------------------------------------------------------------------
# D. Figura 1 nueva
# ---------------------------------------------------------------------------

def figura1():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cargas = pd.read_csv(DIR / "CFA_WLSMV_cargas.csv")
    (DIR / "figuras_nuevas").mkdir(exist_ok=True)

    nombres = {"D1": "Conceptual understanding", "D2": "Technical skills",
               "D3": "Ethics & social impact", "D4": "Collaboration & transfer"}
    grises = {"D1": "0.15", "D2": "0.40", "D3": "0.60", "D4": "0.78"}
    tramas = {"D1": "", "D2": "//", "D3": "..", "D4": "xx"}

    fig, ax = plt.subplots(figsize=(7.0, 8.5))
    ypos, etiquetas, y = [], [], 0
    for f in ["D1", "D2", "D3", "D4"]:
        sub = cargas[cargas["Factor"] == f]
        for _, r in sub.iterrows():
            ax.barh(y, r["Carga_std"], height=0.8, color=grises[f],
                    hatch=tramas[f], edgecolor="black", linewidth=0.4)
            ax.errorbar(r["Carga_std"], y, xerr=1.96 * r["SE"], fmt="none",
                        ecolor="black", elinewidth=0.9, capsize=2)
            ypos.append(y)
            etiquetas.append(r["Item"].replace("_", "-"))
            y += 1
        y += 1  # separador entre factores
    ax.set_yticks(ypos)
    ax.set_yticklabels(etiquetas, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Standardized factor loading (WLSMV, polychoric)", fontsize=10)
    ax.axvline(0.70, color="black", linestyle="--", linewidth=0.8)
    ax.text(0.705, -0.6, "0.70", fontsize=8, va="bottom")
    from matplotlib.patches import Patch
    fig.legend(handles=[
        Patch(facecolor=grises[f], hatch=tramas[f], edgecolor="black",
              label=f"{f}: {nombres[f]}") for f in nombres],
        loc="lower center", ncol=2, fontsize=8, frameon=False,
        bbox_to_anchor=(0.5, 0.0))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ["png", "pdf"]:
        fig.savefig(DIR / "figuras_nuevas" / f"Fig1_CFA_Loadings.{ext}",
                    dpi=300, bbox_inches="tight")
    plt.close(fig)
    log("  figuras_nuevas/Fig1_CFA_Loadings.png|pdf (300 dpi, sin titulo, "
        "grises + tramas)")


# ---------------------------------------------------------------------------

def main():
    titulo("RE-ANALISIS MENORES (A: rank-ANCOVA · B: cotas atricion · "
           "C: moderadores · D: Fig. 1)")
    df = cargar_ancho()
    log(f"N completadores = {len(df)}")

    titulo("A. RANK-ANCOVA (CONOVER), CLASICO Y CR2+SATTERTHWAITE")
    ta = rank_ancova(df)
    log(ta.to_string(index=False))

    titulo("B. COTAS DE ATRICION (12 EXCLUIDOS, SOLO T0 DISPONIBLE)")
    tb = cotas_atricion(df)
    log(tb.to_string(index=False))

    titulo("C. MODERADORES: OMNIBUS GRUPO x MODERADOR")
    tc, tn = moderadores(df)
    log(tc.to_string(index=False))
    log("")
    log(tn.to_string(index=False))

    titulo("D. FIGURA 1 NUEVA (CARGAS CFA WLSMV)")
    figura1()

    titulo("ESCRITURA")
    ta.to_csv(DIR / "SensibilidadA_rank_ancova.csv", index=False,
              encoding="utf-8-sig")
    tb.to_csv(DIR / "SensibilidadB_cotas_atricion.csv", index=False,
              encoding="utf-8-sig")
    tc.to_csv(DIR / "Moderadores_omnibus.csv", index=False, encoding="utf-8-sig")
    tn.to_csv(DIR / "Moderadores_n_celdas.csv", index=False, encoding="utf-8-sig")
    for f in ["SensibilidadA_rank_ancova.csv", "SensibilidadB_cotas_atricion.csv",
              "Moderadores_omnibus.csv", "Moderadores_n_celdas.csv"]:
        log(f"  {f}")
    log("")
    log("RE-ANALISIS MENORES COMPLETADOS")
    (DIR / "log_menores.txt").write_text("\n".join(_log), encoding="utf-8")


if __name__ == "__main__":
    main()
