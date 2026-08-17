#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paquete_inferencia_clusterizada.py
==================================

Paquete de inferencia clusterizada por seccion (tareas 2 y 3 del plan E1).
Responde R2.16, R2.17, R2.18, R2.45-46, R3.2, R3.5 y R3.11.

Entrada : ../work/dataset_analitico.xlsx  (hojas T0_PreTest, T1_PostTest,
          T2_FollowUp; N=150, variable Seccion 1-8)

Metodos sobre el modelo primario  Post ~ Grupo + Pre  (ANCOVA):
  M1  OLS individual, SE clasico (analisis original, referencia)
  M2  OLS con SE cluster-robustos CR2 (Bell-McCaffrey) y gl de Satterthwaite
  M3  LMM  Post ~ Pre + Grupo + (1|Seccion), REML; inferencia conservadora
      con gl = m - 2 = 6 (a falta de Kenward-Roger en Python; cota inferior)
  M4  Agregacion por seccion: ANCOVA sobre las 8 medias de seccion (gl = 5)
  M5  Wild cluster bootstrap restringido (H0 impuesta), pesos Webb de 6
      puntos, B = 9999, estadistico t con SE CR1
  M6  Test de permutacion exacto a nivel de seccion (C(8,4) = 70
      asignaciones; p minimo bilateral = 2/70 = .0286)

Salidas (en esta carpeta):
  T_C_ICC_por_seccion.csv       ICC por outcome y ola (ANOVA de un factor,
                                IC 95% exacto basado en F) + design effect
  T_D_robustez_primarios.csv    Tabla estrella: 6 metodos x 2 outcomes primarios
  T_D2_CR2_secundarios.csv      CR2+Satterthwaite para 8 subescalas en T1
                                (Holm por familia) y totales en T2
  T_B_estructura_secciones.csv  Tabla seccion x condicion x facultad x n
  paquete_clusterizado.xlsx     Todo lo anterior en un libro
  log_inferencia.txt            Registro de ejecucion

Uso:  python paquete_inferencia_clusterizada.py
"""

from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RUTA_DATOS = Path(__file__).parent.parent / "work" / "dataset_analitico.xlsx"
DIR_SALIDA = Path(__file__).parent

SEED = 20260815
B_BOOT = 9999

PRIMARIOS = {
    "Score_total_autopercepcion": "Autopercepcion total (primario)",
    "Score_conocimiento": "Conocimiento objetivo total (primario)",
}
FAMILIA_A = [f"Score_D{i}" for i in range(1, 5)]                 # autopercepcion
FAMILIA_B = [f"Score_conocimiento_D{i}" for i in range(1, 5)]    # conocimiento

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
# Carga y preparacion
# ---------------------------------------------------------------------------

def cargar() -> pd.DataFrame:
    xl = pd.ExcelFile(RUTA_DATOS)
    t0 = xl.parse("T0_PreTest")
    t1 = xl.parse("T1_PostTest")
    t2 = xl.parse("T2_FollowUp")
    llaves = ["ID_estudiante", "Grupo", "Seccion", "Facultad"]
    scores = list(PRIMARIOS) + FAMILIA_A + FAMILIA_B
    df = t0[llaves + scores].rename(columns={s: s + "_T0" for s in scores})
    for t, suf in [(t1, "_T1"), (t2, "_T2")]:
        df = df.merge(
            t[["ID_estudiante"] + scores].rename(
                columns={s: s + suf for s in scores}
            ),
            on="ID_estudiante",
            validate="1:1",
        )
    df["Trat"] = (df["Grupo"] == "Experimental").astype(float)
    return df


# ---------------------------------------------------------------------------
# ICC por seccion (ANOVA de un factor, IC exacto basado en F)
# ---------------------------------------------------------------------------

def icc_anova(y: np.ndarray, g: np.ndarray, alpha: float = 0.05):
    """ICC(1) de Fisher via ANOVA de un factor con IC exacto (Searle 1971)."""
    grupos = [y[g == k] for k in np.unique(g)]
    m = len(grupos)
    n = len(y)
    n_g = np.array([len(x) for x in grupos])
    m_barra = (n - (n_g**2).sum() / n) / (m - 1)  # tamano medio ajustado
    gran_media = y.mean()
    ssb = sum(len(x) * (x.mean() - gran_media) ** 2 for x in grupos)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in grupos)
    df1, df2 = m - 1, n - m
    msb, msw = ssb / df1, ssw / df2
    icc = (msb - msw) / (msb + (m_barra - 1) * msw)
    F = msb / msw
    fl = F / stats.f.ppf(1 - alpha / 2, df1, df2)
    fu = F * stats.f.ppf(1 - alpha / 2, df2, df1)
    lo = (fl - 1) / (fl + m_barra - 1)
    hi = (fu - 1) / (fu + m_barra - 1)
    return icc, lo, hi, m_barra


def tabla_icc(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    outcomes = list(PRIMARIOS) + FAMILIA_A + FAMILIA_B
    for s in outcomes:
        for ola in ["T0", "T1", "T2"]:
            y = df[f"{s}_{ola}"].to_numpy(float)
            g = df["Seccion"].to_numpy()
            icc, lo, hi, m_barra = icc_anova(y, g)
            deff = 1 + (m_barra - 1) * max(icc, 0.0)
            filas.append(
                {
                    "Outcome": s,
                    "Ola": ola,
                    "ICC_seccion": round(icc, 4),
                    "IC95_inf": round(lo, 4),
                    "IC95_sup": round(hi, 4),
                    "Design_effect": round(deff, 3),
                }
            )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# CR2 (Bell-McCaffrey) + gl de Satterthwaite
# ---------------------------------------------------------------------------

def ols_basico(X: np.ndarray, y: np.ndarray):
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    return beta, resid, XtX_inv


def cr2_satterthwaite(X, y, clusters, idx_coef):
    """Devuelve beta_j, SE CR2, gl Satterthwaite (Bell-McCaffrey), t, p."""
    n, k = X.shape
    beta, resid, XtX_inv = ols_basico(X, y)
    H = X @ XtX_inv @ X.T
    M = np.eye(n) - H
    ell = np.zeros(k)
    ell[idx_coef] = 1.0
    q = XtX_inv @ ell

    ids = np.unique(clusters)
    V = 0.0
    W_cols = []
    for c in ids:
        sel = clusters == c
        Xg = X[sel]
        Hgg = Xg @ XtX_inv @ Xg.T
        # A_g = (I - H_gg)^(-1/2) simetrica
        vals, vecs = np.linalg.eigh(np.eye(sel.sum()) - Hgg)
        vals = np.clip(vals, 1e-12, None)
        Ag = vecs @ np.diag(vals**-0.5) @ vecs.T
        ag = Ag @ Xg @ q                      # n_g
        ug = resid[sel]
        V += float(ag @ ug) ** 2
        w = M[sel, :].T @ ag                  # N-vector: M_{g.}' a_g
        W_cols.append(w)
    G = np.column_stack(W_cols)               # N x m
    S = G.T @ G                                # m x m
    gl = float(np.trace(S)) ** 2 / float(np.trace(S @ S))
    se = np.sqrt(V)
    t = beta[idx_coef] / se
    p = 2 * stats.t.sf(abs(t), gl)
    ci = beta[idx_coef] + np.array([-1, 1]) * stats.t.ppf(0.975, gl) * se
    return beta[idx_coef], se, gl, t, p, ci


def cr1_se(X, y, clusters, idx_coef):
    """SE CR1 (correccion tipo Stata) para el wild bootstrap."""
    n, k = X.shape
    beta, resid, XtX_inv = ols_basico(X, y)
    ids = np.unique(clusters)
    m = len(ids)
    meat = np.zeros((k, k))
    for c in ids:
        sel = clusters == c
        sc = X[sel].T @ resid[sel]
        meat += np.outer(sc, sc)
    factor = (m / (m - 1)) * ((n - 1) / (n - k))
    V = factor * XtX_inv @ meat @ XtX_inv
    return beta[idx_coef], np.sqrt(V[idx_coef, idx_coef])


# ---------------------------------------------------------------------------
# Metodos de la Tabla T-D
# ---------------------------------------------------------------------------

def m1_ols_clasico(X, y, idx):
    n, k = X.shape
    beta, resid, XtX_inv = ols_basico(X, y)
    s2 = resid @ resid / (n - k)
    se = np.sqrt(s2 * XtX_inv[idx, idx])
    t = beta[idx] / se
    gl = n - k
    p = 2 * stats.t.sf(abs(t), gl)
    ci = beta[idx] + np.array([-1, 1]) * stats.t.ppf(0.975, gl) * se
    return beta[idx], se, gl, t, p, ci


def m3_lmm(df, pre, post):
    import statsmodels.formula.api as smf

    d = df.rename(columns={pre: "Pre", post: "Post"}).copy()
    # Centrar el pretest estabiliza la optimizacion
    d["Pre"] = d["Pre"] - d["Pre"].mean()
    modelo = smf.mixedlm("Post ~ Pre + Trat", d, groups=d["Seccion"])
    mod = None
    for metodo in ["powell", "bfgs", "lbfgs", "cg"]:
        try:
            cand = modelo.fit(reml=True, method=metodo, maxiter=2000)
            if cand.converged and np.isfinite(cand.bse["Trat"]) and \
               cand.bse["Trat"] < 1e3:
                mod = cand
                break
        except Exception:
            continue
    if mod is None:
        raise RuntimeError("LMM no convergio con ningun optimizador")
    b = mod.params["Trat"]
    se = mod.bse["Trat"]
    gl = len(df["Seccion"].unique()) - 2  # conservador (cota inferior a KR)
    t = b / se
    p = 2 * stats.t.sf(abs(t), gl)
    ci = b + np.array([-1, 1]) * stats.t.ppf(0.975, gl) * se
    var_sec = float(mod.cov_re.iloc[0, 0])
    var_res = float(mod.scale)
    icc_cond = var_sec / (var_sec + var_res)
    return b, se, gl, t, p, ci, icc_cond


def m4_agregacion(df, pre, post):
    agg = df.groupby("Seccion").agg(
        Pre=(pre, "mean"), Post=(post, "mean"), Trat=("Trat", "first")
    )
    X = np.column_stack([np.ones(8), agg["Trat"], agg["Pre"]])
    y = agg["Post"].to_numpy(float)
    beta, resid, XtX_inv = ols_basico(X, y)
    gl = 8 - 3
    s2 = resid @ resid / gl
    se = np.sqrt(s2 * XtX_inv[1, 1])
    t = beta[1] / se
    p = 2 * stats.t.sf(abs(t), gl)
    ci = beta[1] + np.array([-1, 1]) * stats.t.ppf(0.975, gl) * se
    # Hedges g sobre medias de seccion (post), descriptivo
    e = agg.loc[agg["Trat"] == 1, "Post"]
    c = agg.loc[agg["Trat"] == 0, "Post"]
    sp = np.sqrt(((e.var(ddof=1) * 3) + (c.var(ddof=1) * 3)) / 6)
    g_hedges = (e.mean() - c.mean()) / sp * (1 - 3 / (4 * 6 - 1))
    return beta[1], se, gl, t, p, ci, g_hedges


def m5_wild_bootstrap(X, y, clusters, idx, rng):
    """WCB restringido (H0: beta_trat = 0), pesos Webb, t con CR1."""
    b_obs, se_obs = cr1_se(X, y, clusters, idx)
    t_obs = b_obs / se_obs
    # Modelo restringido: sin la columna de tratamiento
    Xr = np.delete(X, idx, axis=1)
    beta_r, resid_r, _ = ols_basico(Xr, y)
    y_hat_r = Xr @ beta_r
    ids = np.unique(clusters)
    webb = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5),
                     np.sqrt(0.5), 1.0, np.sqrt(1.5)])
    idx_cluster = [clusters == c for c in ids]
    excede = 0
    for _ in range(B_BOOT):
        w = rng.choice(webb, size=len(ids))
        u = resid_r.copy()
        for j, sel in enumerate(idx_cluster):
            u[sel] *= w[j]
        y_star = y_hat_r + u
        b_s, se_s = cr1_se(X, y_star, clusters, idx)
        if abs(b_s / se_s) >= abs(t_obs):
            excede += 1
    p = (excede + 1) / (B_BOOT + 1)
    return b_obs, t_obs, p


def m6_permutacion(df, pre, post):
    """Permutacion exacta: C(8,4)=70 asignaciones de secciones a tratamiento."""
    secciones = np.sort(df["Seccion"].unique())
    y = df[post].to_numpy(float)
    pre_v = df[pre].to_numpy(float)
    sec = df["Seccion"].to_numpy()
    obs_trat = set(df.loc[df["Trat"] == 1, "Seccion"].unique())

    def coef(trat_set):
        tr = np.isin(sec, list(trat_set)).astype(float)
        X = np.column_stack([np.ones(len(y)), tr, pre_v])
        beta, _, _ = ols_basico(X, y)
        return beta[1]

    b_obs = coef(obs_trat)
    dist = [coef(set(c)) for c in itertools.combinations(secciones, 4)]
    dist = np.array(dist)
    p = float((np.abs(dist) >= abs(b_obs) - 1e-12).mean())
    return b_obs, p, len(dist)


# ---------------------------------------------------------------------------
# Orquestacion
# ---------------------------------------------------------------------------

def tabla_td(df: pd.DataFrame, rng) -> pd.DataFrame:
    filas = []
    for score, etiqueta in PRIMARIOS.items():
        pre, post = f"{score}_T0", f"{score}_T1"
        X = np.column_stack(
            [np.ones(len(df)), df["Trat"].to_numpy(float), df[pre].to_numpy(float)]
        )
        y = df[post].to_numpy(float)
        cl = df["Seccion"].to_numpy()
        sd_post = df.groupby("Grupo")[post].std(ddof=1)
        sd_pool = np.sqrt((sd_post**2).mean())

        def fila(metodo, b, se, gl, t, p, ci, extra=""):
            filas.append(
                {
                    "Outcome": etiqueta,
                    "Metodo": metodo,
                    "Dif_ajustada": round(b, 3),
                    "d_aprox": round(b / sd_pool, 3),
                    "SE": None if se is None else round(se, 3),
                    "gl": None if gl is None else round(gl, 2),
                    "t": None if t is None else round(t, 3),
                    "IC95_inf": None if ci is None else round(ci[0], 3),
                    "IC95_sup": None if ci is None else round(ci[1], 3),
                    "p": round(p, 4) if p >= 1e-4 else "<.0001",
                    "Nota": extra,
                }
            )

        log(f"\n--- {etiqueta} ---")
        b, se, gl, t, p, ci = m1_ols_clasico(X, y, 1)
        fila("M1 OLS individual (SE clasico)", b, se, gl, t, p, ci,
             "analisis original; ignora clustering")
        log(f"  M1 OLS clasico        b={b:7.3f}  SE={se:.3f}  gl={gl:>6.1f}  p={p:.2e}")

        b, se, gl, t, p, ci = cr2_satterthwaite(X, y, cl, 1)
        fila("M2 ANCOVA CR2 + Satterthwaite", b, se, gl, t, p, ci,
             "inferencia primaria propuesta")
        log(f"  M2 CR2+Satterthwaite  b={b:7.3f}  SE={se:.3f}  gl={gl:>6.2f}  p={p:.4f}")

        b, se, gl, t, p, ci, icc_c = m3_lmm(df, pre, post)
        fila("M3 LMM (1|Seccion) REML, gl=m-2", b, se, gl, t, p, ci,
             f"ICC condicional={icc_c:.4f}; gl conservador")
        log(f"  M3 LMM (1|Seccion)    b={b:7.3f}  SE={se:.3f}  gl={gl}      p={p:.4f}  ICC_cond={icc_c:.4f}")

        b, se, gl, t, p, ci, g_h = m4_agregacion(df, pre, post)
        fila("M4 Agregacion por seccion (n=8)", b, se, gl, t, p, ci,
             f"Hedges g (medias de seccion)={g_h:.2f}")
        log(f"  M4 Agregacion (df=5)  b={b:7.3f}  SE={se:.3f}  gl={gl}      p={p:.4f}  g={g_h:.2f}")

        b, t_o, p = m5_wild_bootstrap(X, y, cl, 1, rng)
        fila("M5 Wild cluster bootstrap (Webb, B=9999)", b, None, None, t_o, p,
             None, "restringido, H0 impuesta; t con CR1")
        log(f"  M5 Wild boot Webb     b={b:7.3f}  t={t_o:.3f}            p={p:.4f}")

        b, p, n_perm = m6_permutacion(df, pre, post)
        fila("M6 Permutacion exacta por seccion", b, None, None, None, p, None,
             f"{n_perm} asignaciones; p minimo=2/70=.0286")
        log(f"  M6 Permutacion (70)   b={b:7.3f}                       p={p:.4f}")
    return pd.DataFrame(filas)


def tabla_secundarios(df: pd.DataFrame) -> pd.DataFrame:
    """CR2+Satterthwaite para subescalas T1 (Holm por familia) y totales T2."""
    filas = []

    def corre(score, ola, familia):
        pre, post = f"{score}_T0", f"{score}_{ola}"
        X = np.column_stack(
            [np.ones(len(df)), df["Trat"].to_numpy(float), df[pre].to_numpy(float)]
        )
        y = df[post].to_numpy(float)
        b, se, gl, t, p, ci = cr2_satterthwaite(X, y, df["Seccion"].to_numpy(), 1)
        filas.append(
            {
                "Outcome": score, "Ola": ola, "Familia": familia,
                "Dif_ajustada": round(b, 3), "SE_CR2": round(se, 3),
                "gl_Satt": round(gl, 2), "t": round(t, 3),
                "IC95_inf": round(ci[0], 3), "IC95_sup": round(ci[1], 3),
                "p": p,
            }
        )

    for s in FAMILIA_A:
        corre(s, "T1", "A: autopercepcion")
    for s in FAMILIA_B:
        corre(s, "T1", "B: conocimiento")
    for s in PRIMARIOS:
        corre(s, "T2", "Primarios en T2 (mantenimiento)")

    out = pd.DataFrame(filas)
    # Holm dentro de cada familia de 4 subescalas
    out["p_Holm"] = np.nan
    for fam in ["A: autopercepcion", "B: conocimiento"]:
        sel = out["Familia"] == fam
        p = out.loc[sel, "p"].to_numpy()
        orden = np.argsort(p)
        ajust = np.empty_like(p)
        prev = 0.0
        for rango, i in enumerate(orden):
            val = min(1.0, (4 - rango) * p[i])
            prev = max(prev, val)
            ajust[i] = prev
        out.loc[sel, "p_Holm"] = ajust
    out["p"] = out["p"].map(lambda v: round(v, 4) if v >= 1e-4 else v)
    return out


def tabla_estructura(df: pd.DataFrame) -> pd.DataFrame:
    t = (
        df.groupby(["Seccion", "Grupo"])
        .agg(
            n_analitico=("ID_estudiante", "count"),
            Facultades=("Facultad", lambda x: " / ".join(sorted(x.unique()))),
        )
        .reset_index()
    )
    return t


def main() -> None:
    rng = np.random.default_rng(SEED)
    titulo("PAQUETE DE INFERENCIA CLUSTERIZADA POR SECCION")
    log(f"Entrada: {RUTA_DATOS}")
    log(f"Semilla: {SEED} · Bootstrap B={B_BOOT} · Permutacion exacta C(8,4)=70")

    df = cargar()
    log(f"N={len(df)}; secciones={sorted(df['Seccion'].unique())}")
    log(str(df.groupby(['Seccion', 'Grupo']).size()))

    titulo("TABLA T-B: ESTRUCTURA POR SECCION")
    tb = tabla_estructura(df)
    log(tb.to_string(index=False))

    titulo("TABLA T-C: ICC POR SECCION (ANOVA, IC 95% exacto F)")
    tc = tabla_icc(df)
    log(tc.to_string(index=False))

    titulo("TABLA T-D: ROBUSTEZ DEL EFECTO PRIMARIO (6 METODOS)")
    td = tabla_td(df, rng)

    titulo("TABLA T-D2: CR2 SUBESCALAS T1 (HOLM) Y TOTALES T2")
    td2 = tabla_secundarios(df)
    log(td2.to_string(index=False))

    titulo("ESCRITURA DE RESULTADOS")
    tb.to_csv(DIR_SALIDA / "T_B_estructura_secciones.csv", index=False,
              encoding="utf-8-sig")
    tc.to_csv(DIR_SALIDA / "T_C_ICC_por_seccion.csv", index=False,
              encoding="utf-8-sig")
    td.to_csv(DIR_SALIDA / "T_D_robustez_primarios.csv", index=False,
              encoding="utf-8-sig")
    td2.to_csv(DIR_SALIDA / "T_D2_CR2_secundarios.csv", index=False,
               encoding="utf-8-sig")
    with pd.ExcelWriter(DIR_SALIDA / "paquete_clusterizado.xlsx",
                        engine="openpyxl") as w:
        tb.to_excel(w, sheet_name="T_B_Estructura", index=False)
        tc.to_excel(w, sheet_name="T_C_ICC", index=False)
        td.to_excel(w, sheet_name="T_D_Robustez_Primarios", index=False)
        td2.to_excel(w, sheet_name="T_D2_CR2_Secundarios", index=False)
    for f in ["T_B_estructura_secciones.csv", "T_C_ICC_por_seccion.csv",
              "T_D_robustez_primarios.csv", "T_D2_CR2_secundarios.csv",
              "paquete_clusterizado.xlsx"]:
        log(f"  {f}")

    log("")
    log("PAQUETE COMPLETADO")
    (DIR_SALIDA / "log_inferencia.txt").write_text(
        "\n".join(_log), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
