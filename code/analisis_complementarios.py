#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analisis_complementarios.py
===========================

Tareas 4, 5, 6, 8 y parte de 9 del plan E1 (responde R2.19-R2.23, R2.25,
R3.7):

  T4  ANCOVA completa (Tabla 7 rehecha): medias marginales ajustadas +- SE,
      diferencia ajustada [IC 95%], F, eta2p [IC 90%], test de homogeneidad
      de pendientes (Grupo x Pretest).
  T5  Supuestos del ANOVA mixto (Tabla T-G): Shapiro-Wilk por celda,
      Levene por ocasion, Mauchly + epsilon de Greenhouse-Geisser.
      ANOVA mixto 2x3 con p corregidas GG y eta2p [IC 90%] (Tabla 6 rehecha).
  T6  Tamanos de efecto con IC: d de Cohen entre grupos en T1 y T2 con IC
      95% por t no central (Tabla 8 rehecha); razon de retencion
      RR = d(T2)/d(T1) con IC bootstrap por conglomerado (seccion), 10.000
      replicas (Tabla T-H; operacionaliza H2, R3.7).
  T8  Fiabilidad por ola y dimension: alfa de Cronbach (autopercepcion,
      Likert) y KR-20 (conocimiento, dicotomico) (Tabla 1 ampliada).

Entrada : ../work/dataset_analitico.xlsx
Salidas : Tabla7_ANCOVA_completa.csv, Tabla6_ANOVA_mixto_GG.csv,
          T_G_supuestos.csv, Tabla8_d_con_IC.csv, T_H_retencion_RR.csv,
          Tabla1_fiabilidad_por_ola.csv, analisis_complementarios.xlsx,
          log_complementarios.txt
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import brentq

RUTA_DATOS = Path(__file__).parent.parent / "work" / "dataset_analitico.xlsx"
DIR_SALIDA = Path(__file__).parent
SEED = 20260815
B_RR = 10_000

SCORES = {
    "Score_total_autopercepcion": "Autopercepcion total",
    "Score_D1": "Autopercepcion D1 (conceptual)",
    "Score_D2": "Autopercepcion D2 (tecnica)",
    "Score_D3": "Autopercepcion D3 (etica)",
    "Score_D4": "Autopercepcion D4 (colaborativa)",
    "Score_conocimiento": "Conocimiento total",
    "Score_conocimiento_D1": "Conocimiento D1",
    "Score_conocimiento_D2": "Conocimiento D2",
    "Score_conocimiento_D3": "Conocimiento D3",
    "Score_conocimiento_D4": "Conocimiento D4",
}
ITEMS_LIKERT = {
    "D1": [f"D1_{i:02d}" for i in range(1, 7)],
    "D2": [f"D2_{i:02d}" for i in range(1, 7)],
    "D3": [f"D3_{i:02d}" for i in range(1, 9)],
    "D4": [f"D4_{i:02d}" for i in range(1, 7)],
}
ITEMS_OBJ = {k: ["OBJ_" + c for c in v] for k, v in ITEMS_LIKERT.items()}

_log: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    _log.append(msg)


def titulo(txt: str) -> None:
    log("")
    log("=" * 74)
    log(txt)
    log("=" * 74)


# ---------------------------------------------------------------------------
# Utilidades de IC no centrales
# ---------------------------------------------------------------------------

def ci_d_noncentral(d: float, n1: int, n2: int, conf: float = 0.95):
    """IC de d de Cohen via distribucion t no central (Steiger & Fouladi)."""
    nc = d * np.sqrt(n1 * n2 / (n1 + n2))
    df = n1 + n2 - 2
    lo_a, hi_a = (1 - conf) / 2, 1 - (1 - conf) / 2

    def busca(alpha_obj):
        def f(ncp):
            v = stats.nct.cdf(nc, df, ncp)
            if not np.isfinite(v):
                # cdf subdesbordada: ncp muy por encima de nc -> cdf ~ 0
                v = 0.0 if ncp > nc else 1.0
            return v - alpha_obj
        a, b = nc - 80, nc + 80
        try:
            return brentq(f, a, b, xtol=1e-8)
        except ValueError:
            return np.nan

    ncp_hi = busca(lo_a)   # limite superior
    ncp_lo = busca(hi_a)   # limite inferior
    factor = np.sqrt((n1 + n2) / (n1 * n2))
    return ncp_lo * factor, ncp_hi * factor


def ci_eta2p(F: float, df1: float, df2: float, conf: float = 0.90):
    """IC de eta2 parcial via F no central."""
    lo_a, hi_a = (1 - conf) / 2, 1 - (1 - conf) / 2

    def busca(alpha_obj):
        def f(lam):
            v = stats.ncf.cdf(F, df1, df2, lam)
            if not np.isfinite(v):
                v = 0.0          # lambda enorme -> cdf subdesbordada a 0
            return v - alpha_obj
        if f(0.0) <= 0.0:        # incluso lambda=0 deja a F por debajo
            return 0.0
        hi = 100.0
        while f(hi) > 0.0 and hi < 1e7:
            hi *= 4
        try:
            return brentq(f, 0.0, hi, xtol=1e-6)
        except ValueError:
            return np.nan

    lam_hi = busca(lo_a)
    lam_lo = busca(hi_a)
    conv = lambda lam: lam / (lam + df1 + df2 + 1)
    return conv(lam_lo), conv(lam_hi)


def cohen_d(x: np.ndarray, y: np.ndarray) -> float:
    n1, n2 = len(x), len(y)
    sp = np.sqrt(((n1 - 1) * x.var(ddof=1) + (n2 - 1) * y.var(ddof=1))
                 / (n1 + n2 - 2))
    return (x.mean() - y.mean()) / sp


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def cargar():
    xl = pd.ExcelFile(RUTA_DATOS)
    hojas = {t: xl.parse(h) for t, h in
             [("T0", "T0_PreTest"), ("T1", "T1_PostTest"), ("T2", "T2_FollowUp")]}
    base = hojas["T0"][["ID_estudiante", "Grupo", "Seccion"]].copy()
    ancho = base.copy()
    for t, df in hojas.items():
        cols = list(SCORES)
        ancho = ancho.merge(
            df[["ID_estudiante"] + cols].rename(
                columns={c: f"{c}_{t}" for c in cols}),
            on="ID_estudiante", validate="1:1")
    return hojas, ancho


# ---------------------------------------------------------------------------
# T4: ANCOVA completa
# ---------------------------------------------------------------------------

def tabla_ancova(ancho: pd.DataFrame) -> pd.DataFrame:
    filas = []
    trat = (ancho["Grupo"] == "Experimental").astype(float).to_numpy()
    for score, nombre in SCORES.items():
        for ola in ["T1", "T2"]:
            pre = ancho[f"{score}_T0"].to_numpy(float)
            post = ancho[f"{score}_{ola}"].to_numpy(float)
            n = len(post)
            X = np.column_stack([np.ones(n), trat, pre])
            XtX_inv = np.linalg.inv(X.T @ X)
            beta = XtX_inv @ X.T @ post
            resid = post - X @ beta
            gl_e = n - 3
            s2 = resid @ resid / gl_e
            covb = s2 * XtX_inv
            # medias ajustadas en la gran media del pretest
            x_e = np.array([1.0, 1.0, pre.mean()])
            x_c = np.array([1.0, 0.0, pre.mean()])
            emm_e, emm_c = x_e @ beta, x_c @ beta
            se_e = np.sqrt(x_e @ covb @ x_e)
            se_c = np.sqrt(x_c @ covb @ x_c)
            dif = beta[1]
            se_dif = np.sqrt(covb[1, 1])
            t = dif / se_dif
            p = 2 * stats.t.sf(abs(t), gl_e)
            ci = dif + np.array([-1, 1]) * stats.t.ppf(0.975, gl_e) * se_dif
            F = t**2
            eta = F / (F + gl_e)
            eta_lo, eta_hi = ci_eta2p(F, 1, gl_e)
            # homogeneidad de pendientes
            Xs = np.column_stack([X, trat * pre])
            beta_s = np.linalg.lstsq(Xs, post, rcond=None)[0]
            rss_s = ((post - Xs @ beta_s) ** 2).sum()
            rss = resid @ resid
            F_pend = (rss - rss_s) / (rss_s / (n - 4))
            p_pend = stats.f.sf(F_pend, 1, n - 4)
            filas.append({
                "Outcome": nombre, "Ola": ola,
                "EMM_Exp": round(emm_e, 3), "SE_Exp": round(se_e, 3),
                "EMM_Ctrl": round(emm_c, 3), "SE_Ctrl": round(se_c, 3),
                "Dif_ajustada": round(dif, 3),
                "IC95_inf": round(ci[0], 3), "IC95_sup": round(ci[1], 3),
                "F(1,147)": round(F, 2),
                "p": p,
                "eta2p": round(eta, 3),
                "eta2p_IC90_inf": round(eta_lo, 3),
                "eta2p_IC90_sup": round(eta_hi, 3),
                "F_pendientes": round(F_pend, 3),
                "p_pendientes": round(p_pend, 4),
            })
    out = pd.DataFrame(filas)
    out["p"] = out["p"].map(lambda v: round(v, 4) if v >= 1e-4 else "<.0001")
    return out


# ---------------------------------------------------------------------------
# T5: supuestos + ANOVA mixto 2x3 con GG
# ---------------------------------------------------------------------------

def mauchly_gg(Y: np.ndarray, grupos: np.ndarray):
    """Mauchly y epsilons sobre la covarianza intra-grupo agrupada.

    Y: n x k (medidas repetidas). Devuelve (W, chi2, df, p, eps_gg, eps_hf).
    """
    n, k = Y.shape
    # covarianza agrupada dentro de grupos
    S = np.zeros((k, k))
    gl = 0
    for g in np.unique(grupos):
        Yg = Y[grupos == g]
        S += (len(Yg) - 1) * np.cov(Yg, rowvar=False)
        gl += len(Yg) - 1
    S /= gl
    # contrastes ortonormales (k-1)
    C = np.linalg.qr(np.vstack([np.ones(k), np.eye(k)[:-1]]).T)[0][:, 1:]
    T = C.T @ S @ C
    lam = np.linalg.eigvalsh(T)
    lam = np.clip(lam, 1e-12, None)
    k1 = k - 1
    W = np.prod(lam) / (lam.mean() ** k1)
    d_corr = 1 - (2 * k1**2 + k1 + 2) / (6 * k1 * gl)
    chi2 = -gl * d_corr * np.log(W)
    df_chi = k1 * (k1 + 1) / 2 - 1
    p = stats.chi2.sf(chi2, df_chi)
    eps_gg = lam.sum() ** 2 / (k1 * (lam**2).sum())
    eps_hf = min(1.0, (gl * k1 * eps_gg - 2)
                 / (k1 * (gl - k1 * eps_gg)))
    return W, chi2, df_chi, p, eps_gg, eps_hf


def anova_mixto_2x3(Y: np.ndarray, grupo: np.ndarray):
    """ANOVA split-plot balanceado: 2 grupos x 3 ocasiones."""
    n, k = Y.shape
    niveles = np.unique(grupo)
    gm = Y.mean()
    ss_total = ((Y - gm) ** 2).sum()
    medias_suj = Y.mean(axis=1)
    ss_entre_suj = k * ((medias_suj - gm) ** 2).sum()
    ss_grupo = sum(k * (grupo == g).sum() * (medias_suj[grupo == g].mean() - gm) ** 2
                   for g in niveles)
    ss_suj_g = ss_entre_suj - ss_grupo
    medias_t = Y.mean(axis=0)
    ss_tiempo = n * ((medias_t - gm) ** 2).sum()
    ss_celda = sum((grupo == g).sum()
                   * ((Y[grupo == g].mean(axis=0) - gm) ** 2).sum()
                   for g in niveles)
    ss_gxt = ss_celda - ss_grupo - ss_tiempo
    ss_error_w = ss_total - ss_entre_suj - ss_tiempo - ss_gxt
    df_g, df_sg = 1, n - 2
    df_t, df_gxt, df_ew = k - 1, k - 1, (n - 2) * (k - 1)
    res = {}
    for ef, ss, df1, ss_err, df2 in [
        ("Grupo", ss_grupo, df_g, ss_suj_g, df_sg),
        ("Tiempo", ss_tiempo, df_t, ss_error_w, df_ew),
        ("Grupo x Tiempo", ss_gxt, df_gxt, ss_error_w, df_ew),
    ]:
        F = (ss / df1) / (ss_err / df2)
        res[ef] = (F, df1, df2, ss, ss_err)
    return res


def tabla_supuestos_y_anova(ancho: pd.DataFrame):
    filas_sup, filas_anova = [], []
    grupo = ancho["Grupo"].to_numpy()
    for score, nombre in SCORES.items():
        Y = ancho[[f"{score}_T0", f"{score}_T1", f"{score}_T2"]].to_numpy(float)
        # Shapiro por celda y Levene por ocasion
        shapiro_p, levene_p = {}, {}
        for j, ola in enumerate(["T0", "T1", "T2"]):
            e = Y[grupo == "Experimental", j]
            c = Y[grupo == "Control", j]
            shapiro_p[ola] = (stats.shapiro(e).pvalue, stats.shapiro(c).pvalue)
            levene_p[ola] = stats.levene(e, c, center="median").pvalue
        W, chi2, dfc, p_mau, eps_gg, eps_hf = mauchly_gg(
            Y, (grupo == "Experimental").astype(int))
        filas_sup.append({
            "Outcome": nombre,
            "Shapiro_pmin_Exp": round(min(shapiro_p[o][0] for o in shapiro_p), 4),
            "Shapiro_pmin_Ctrl": round(min(shapiro_p[o][1] for o in shapiro_p), 4),
            "Levene_p_T0": round(levene_p["T0"], 4),
            "Levene_p_T1": round(levene_p["T1"], 4),
            "Levene_p_T2": round(levene_p["T2"], 4),
            "Mauchly_W": round(W, 4), "Mauchly_p": round(p_mau, 4),
            "eps_GG": round(eps_gg, 4), "eps_HF": round(eps_hf, 4),
        })
        res = anova_mixto_2x3(Y, grupo)
        for ef, (F, df1, df2, ss, ss_err) in res.items():
            usa_gg = ef != "Grupo"
            df1c = df1 * eps_gg if usa_gg else df1
            df2c = df2 * eps_gg if usa_gg else df2
            p_gg = stats.f.sf(F, df1c, df2c)
            eta = ss / (ss + ss_err)
            eta_lo, eta_hi = ci_eta2p(F, df1, df2)
            filas_anova.append({
                "Outcome": nombre, "Efecto": ef,
                "F": round(F, 2), "df1": df1, "df2": df2,
                "p_GG": p_gg,
                "eps_aplicado": round(eps_gg, 3) if usa_gg else 1.0,
                "eta2p": round(eta, 3),
                "eta2p_IC90_inf": round(eta_lo, 3),
                "eta2p_IC90_sup": round(eta_hi, 3),
            })
    sup = pd.DataFrame(filas_sup)
    anova = pd.DataFrame(filas_anova)
    anova["p_GG"] = anova["p_GG"].map(
        lambda v: round(v, 4) if v >= 1e-4 else "<.0001")
    return sup, anova


# ---------------------------------------------------------------------------
# T6: d con IC no central + retencion RR bootstrap por seccion
# ---------------------------------------------------------------------------

def tabla_d(ancho: pd.DataFrame) -> pd.DataFrame:
    filas = []
    exp = ancho["Grupo"] == "Experimental"
    for score, nombre in SCORES.items():
        for ola in ["T0", "T1", "T2"]:
            x = ancho.loc[exp, f"{score}_{ola}"].to_numpy(float)
            y = ancho.loc[~exp, f"{score}_{ola}"].to_numpy(float)
            d = cohen_d(x, y)
            lo, hi = ci_d_noncentral(d, len(x), len(y))
            filas.append({
                "Outcome": nombre, "Ola": ola, "d": round(d, 3),
                "IC95_inf": round(lo, 3), "IC95_sup": round(hi, 3),
            })
    return pd.DataFrame(filas)


def tabla_rr(ancho: pd.DataFrame, rng) -> pd.DataFrame:
    """RR = d(T2)/d(T1) con bootstrap por seccion (remuestreo de secciones
    con reemplazo dentro de cada brazo), B=10.000."""
    filas = []
    sec_e = sorted(ancho.loc[ancho["Grupo"] == "Experimental", "Seccion"].unique())
    sec_c = sorted(ancho.loc[ancho["Grupo"] == "Control", "Seccion"].unique())
    por_seccion = {s: ancho[ancho["Seccion"] == s] for s in sec_e + sec_c}

    def rr_de(df, score):
        e = df.loc[df["Grupo"] == "Experimental"]
        c = df.loc[df["Grupo"] == "Control"]
        d1 = cohen_d(e[f"{score}_T1"].to_numpy(float),
                     c[f"{score}_T1"].to_numpy(float))
        d2 = cohen_d(e[f"{score}_T2"].to_numpy(float),
                     c[f"{score}_T2"].to_numpy(float))
        return d1, d2, (d2 / d1 if abs(d1) > 1e-9 else np.nan)

    for score, nombre in SCORES.items():
        d1_obs, d2_obs, rr_obs = rr_de(ancho, score)
        boots = np.empty(B_RR)
        for b in range(B_RR):
            se = rng.choice(sec_e, size=len(sec_e), replace=True)
            sc = rng.choice(sec_c, size=len(sec_c), replace=True)
            df_b = pd.concat([por_seccion[s] for s in list(se) + list(sc)],
                             ignore_index=True)
            boots[b] = rr_de(df_b, score)[2]
        boots = boots[np.isfinite(boots)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        filas.append({
            "Outcome": nombre,
            "d_T1": round(d1_obs, 3), "d_T2": round(d2_obs, 3),
            "RR": round(rr_obs, 3),
            "RR_IC95_inf": round(lo, 3), "RR_IC95_sup": round(hi, 3),
            "Cumple_80pct": "Si" if rr_obs >= 0.80 else "NO",
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# T8: fiabilidad por ola y dimension
# ---------------------------------------------------------------------------

def alfa(items: pd.DataFrame) -> float:
    k = items.shape[1]
    var_items = items.var(axis=0, ddof=1).sum()
    var_total = items.sum(axis=1).var(ddof=1)
    return k / (k - 1) * (1 - var_items / var_total)


def tabla_fiabilidad(hojas: dict) -> pd.DataFrame:
    filas = []
    for ola, df in hojas.items():
        for dim, cols in ITEMS_LIKERT.items():
            filas.append({"Instrumento": "Autopercepcion (alfa)", "Dimension": dim,
                          "Ola": ola, "Coef": round(alfa(df[cols]), 3),
                          "k_items": len(cols)})
        todos_l = [c for v in ITEMS_LIKERT.values() for c in v]
        filas.append({"Instrumento": "Autopercepcion (alfa)", "Dimension": "Total",
                      "Ola": ola, "Coef": round(alfa(df[todos_l]), 3),
                      "k_items": len(todos_l)})
        for dim, cols in ITEMS_OBJ.items():
            filas.append({"Instrumento": "Conocimiento (KR-20)", "Dimension": dim,
                          "Ola": ola, "Coef": round(alfa(df[cols]), 3),
                          "k_items": len(cols)})
        todos_o = [c for v in ITEMS_OBJ.values() for c in v]
        filas.append({"Instrumento": "Conocimiento (KR-20)", "Dimension": "Total",
                      "Ola": ola, "Coef": round(alfa(df[todos_o]), 3),
                      "k_items": len(todos_o)})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(SEED)
    titulo("ANALISIS COMPLEMENTARIOS (TAREAS 4, 5, 6, 8)")
    log(f"Entrada: {RUTA_DATOS} · Semilla {SEED} · Bootstrap RR B={B_RR}")
    hojas, ancho = cargar()
    log(f"N={len(ancho)}")

    titulo("TABLA 7 REHECHA: ANCOVA COMPLETA")
    t7 = tabla_ancova(ancho)
    log(t7.to_string(index=False))

    titulo("TABLA T-G: SUPUESTOS · TABLA 6 REHECHA: ANOVA MIXTO GG")
    tg, t6 = tabla_supuestos_y_anova(ancho)
    log(tg.to_string(index=False))
    log("")
    log(t6.to_string(index=False))

    titulo("TABLA 8 REHECHA: d DE COHEN CON IC 95% (t NO CENTRAL)")
    t8 = tabla_d(ancho)
    log(t8.to_string(index=False))

    titulo("TABLA T-H: RETENCION RR = d(T2)/d(T1), BOOTSTRAP POR SECCION")
    th = tabla_rr(ancho, rng)
    log(th.to_string(index=False))

    titulo("TABLA 1 AMPLIADA: FIABILIDAD POR OLA Y DIMENSION")
    t1 = tabla_fiabilidad(hojas)
    log(t1.to_string(index=False))

    titulo("ESCRITURA DE RESULTADOS")
    salidas = {
        "Tabla7_ANCOVA_completa.csv": t7,
        "T_G_supuestos.csv": tg,
        "Tabla6_ANOVA_mixto_GG.csv": t6,
        "Tabla8_d_con_IC.csv": t8,
        "T_H_retencion_RR.csv": th,
        "Tabla1_fiabilidad_por_ola.csv": t1,
    }
    for nombre, df in salidas.items():
        df.to_csv(DIR_SALIDA / nombre, index=False, encoding="utf-8-sig")
        log(f"  {nombre}")
    with pd.ExcelWriter(DIR_SALIDA / "analisis_complementarios.xlsx",
                        engine="openpyxl") as w:
        for nombre, df in salidas.items():
            df.to_excel(w, sheet_name=nombre.replace(".csv", "")[:31], index=False)
    log("  analisis_complementarios.xlsx")
    log("")
    log("ANALISIS COMPLEMENTARIOS COMPLETADOS")
    (DIR_SALIDA / "log_complementarios.txt").write_text(
        "\n".join(_log), encoding="utf-8")


if __name__ == "__main__":
    main()
