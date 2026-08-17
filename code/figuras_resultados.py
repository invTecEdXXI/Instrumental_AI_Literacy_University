#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
figuras_resultados.py — Figuras esenciales de la seccion de Resultados revisada.

  Fig2_Trajectories_Totals : medias con IC 95% por grupo y ola (2 paneles:
                             autopercepcion total, conocimiento total).
  Fig3_Forest_d_CI         : d de Cohen con IC 95% (t no central) en T1 y T2
                             por dimension y total, ambas escalas.

Estilo: escala de grises segura, sin titulos embebidos, 300 dpi, PNG+PDF.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

DIR = Path(__file__).parent
OUT = DIR / "figuras_nuevas"
OUT.mkdir(exist_ok=True)

xl = pd.ExcelFile(DIR.parent / "work" / "dataset_analitico.xlsx")
hojas = {t: xl.parse(h) for t, h in
         [("T0", "T0_PreTest"), ("T1", "T1_PostTest"), ("T2", "T2_FollowUp")]}

# ---------------------------------------------------------------------------
# Fig 2: trayectorias de los totales
# ---------------------------------------------------------------------------
paneles = [("Score_total_autopercepcion", "Self-perceived AI literacy (1-5)",
            "(a)"),
           ("Score_conocimiento", "Objective AI knowledge (0-26)", "(b)")]
fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
estilo = {"Experimental": dict(color="0.10", marker="o", linestyle="-"),
          "Control": dict(color="0.45", marker="s", linestyle="--")}
for ax, (score, ylab, letra) in zip(axes, paneles):
    for grupo, st in estilo.items():
        m, lo, hi = [], [], []
        for t in ["T0", "T1", "T2"]:
            v = hojas[t].loc[hojas[t]["Grupo"] == grupo, score]
            mu = v.mean()
            half = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
            m.append(mu); lo.append(mu - half); hi.append(mu + half)
        x = np.arange(3)
        ax.errorbar(x, m, yerr=[np.subtract(m, lo), np.subtract(hi, m)],
                    label=grupo, capsize=3, linewidth=1.4, markersize=5, **st)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["T0\n(pretest)", "T1\n(posttest)", "T2\n(follow-up)"],
                       fontsize=9)
    ax.set_ylabel(ylab, fontsize=10)
    ax.text(0.02, 0.97, letra, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top")
    ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=9, frameon=False, loc="lower right")
fig.tight_layout()
for ext in ["png", "pdf"]:
    fig.savefig(OUT / f"Fig2_Trajectories_Totals.{ext}", dpi=300,
                bbox_inches="tight")
plt.close(fig)
print("Fig2_Trajectories_Totals OK")

# ---------------------------------------------------------------------------
# Fig 3: forest plot de d con IC 95%
# ---------------------------------------------------------------------------
t8 = pd.read_csv(DIR / "Tabla8_d_con_IC.csv")
orden = ["Autopercepcion total", "Autopercepcion D1 (conceptual)",
         "Autopercepcion D2 (tecnica)", "Autopercepcion D3 (etica)",
         "Autopercepcion D4 (colaborativa)", "Conocimiento total",
         "Conocimiento D1", "Conocimiento D2", "Conocimiento D3",
         "Conocimiento D4"]
etiq = {"Autopercepcion total": "Self-perception: Total",
        "Autopercepcion D1 (conceptual)": "  D1 Conceptual",
        "Autopercepcion D2 (tecnica)": "  D2 Technical",
        "Autopercepcion D3 (etica)": "  D3 Ethics",
        "Autopercepcion D4 (colaborativa)": "  D4 Collaboration",
        "Conocimiento total": "Knowledge: Total",
        "Conocimiento D1": "  D1 Conceptual",
        "Conocimiento D2": "  D2 Technical",
        "Conocimiento D3": "  D3 Ethics",
        "Conocimiento D4": "  D4 Collaboration"}

fig, ax = plt.subplots(figsize=(7.2, 5.4))
y = 0
ypos, ylabels = [], []
for out in orden:
    for ola, mk, col, dy in [("T1", "o", "0.10", 0.18), ("T2", "s", "0.55", -0.18)]:
        r = t8[(t8.Outcome == out) & (t8.Ola == ola)].iloc[0]
        ax.errorbar(r["d"], y + dy,
                    xerr=[[r["d"] - r["IC95_inf"]], [r["IC95_sup"] - r["d"]]],
                    fmt=mk, color=col, capsize=2.5, markersize=5,
                    elinewidth=1.1)
    ypos.append(y)
    ylabels.append(etiq[out])
    y -= 1
    if out in ("Autopercepcion D4 (colaborativa)",):
        y -= 0.6  # separador entre escalas
ax.axvline(0, color="black", linewidth=0.8)
ax.set_yticks(ypos)
ax.set_yticklabels(ylabels, fontsize=9)
ax.set_xlabel("Cohen's d (experimental vs. control), 95% CI", fontsize=10)
from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([0], [0], marker="o", color="0.10", linestyle="", label="T1 (posttest)"),
    Line2D([0], [0], marker="s", color="0.55", linestyle="", label="T2 (follow-up)")],
    fontsize=9, frameon=False, loc="center left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
for ext in ["png", "pdf"]:
    fig.savefig(OUT / f"Fig3_Forest_d_CI.{ext}", dpi=300, bbox_inches="tight")
plt.close(fig)
print("Fig3_Forest_d_CI OK")
