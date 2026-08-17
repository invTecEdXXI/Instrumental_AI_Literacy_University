# From Instrumental to Integral AI Learning — Reproducibility Repository

Anonymized repository accompanying the manuscript *From Instrumental to Integral
AI Learning: A Quasi-Experimental Evaluation of a Connectivist Framework for
Multidimensional AI Literacy Among University Students*
(**Social Sciences & Humanities Open**, Ms. No. SSHO-D-26-02688, revision 1).

It contains the complete chain of evidence behind the reported results: the raw
pretest file, the cleaning script that derives the analytic sample from it, the
analytic dataset, every analysis script, and every table and figure the scripts
produce. Seeds are fixed, so running the pipeline from a clean checkout
regenerates the contents of `results/` — see
[Reproduction pipeline](#reproduction-pipeline) for the one path convention the
scripts assume.

---

## Study at a glance

| | |
|---|---|
| Design | Quasi-experiment, non-equivalent control group, three waves (T0 pretest / T1 posttest / T2 follow-up) |
| Assignment | At the level of **intact sections** (8 sections: 1–4 experimental, 5–8 control) — sections are the primary clustering unit |
| Analytic sample | N = 150 per wave (75 experimental / 75 control), per-protocol; 450 rows in long format |
| Enrolled → analyzed | 174 eligible → 162 consented and completed T0 → 150 analyzed (attrition 13.8 %) |
| Constructs | Four dimensions (D1 conceptual, D2 technical, D3 ethical, D4 collaborative), each measured twice: 26 Likert self-perception items (1–5) and 26 dichotomous objective-knowledge items (0/1) |
| Primary outcomes | `Score_total_autopercepcion` (mean of 26 Likert items, 1–5) and `Score_conocimiento` (sum of 26 objective items, 0–26) |
| Primary inference | ANCOVA `Post ~ Group + Pre` with **CR2 cluster-robust SE (Bell–McCaffrey) and Satterthwaite df** at the section level |

Exclusion criteria applied by the cleaning script, in hierarchical order: no
informed consent (resolved at recruitment), dropout before T1, and attendance
below 80 % of sessions (strictly below; exactly 80 % is retained).

---

## Repository structure

```
.
├── code/                              Analysis pipeline (Python 3 + R 4.5)
│   ├── limpieza_bruto_a_analiticov2.py    raw → analytic cleaning, CONSORT, attrition
│   ├── paquete_inferencia_clusterizada.py  cluster-robust inference (6 methods), ICCs
│   ├── lmm_kr_y_cfa_wlsmv.R                LMM with Kenward–Roger df; WLSMV CFA
│   ├── analisis_complementarios.py         ANCOVA, mixed ANOVA + GG, effect sizes, reliability
│   ├── art_invarianza_sem.R                ART ANOVAs, longitudinal invariance, SEM
│   ├── reanalisis_menores.py               rank-ANCOVA, attrition bounds, moderators, Fig. 1
│   └── figuras_resultados.py               main-text Figures 2 and 3
├── data/
│   ├── dataset_raw2_T0.xlsx           Raw pretest file (162 consenting records, 86 columns,
│   │                                  5 sheets incl. recruitment log and variable dictionary)
│   ├── dataset_analitico.xlsx         Analytic dataset — 5 sheets, 72 columns per wave sheet
│   ├── T0_PreTest.csv                 UTF-8 exports of each sheet of the analytic dataset
│   ├── T1_PostTest.csv
│   ├── T2_FollowUp.csv
│   ├── Formato_Largo.csv              Long format, 450 rows, adds the `Tiempo` column
│   ├── Resumen_Estadistico.csv        Descriptives by wave × group × dimension × scale
│   ├── consort_flujo.csv              CONSORT participant flow
│   ├── analisis_atricion.csv          Baseline comparison completers vs. excluded (n = 12)
│   └── DATA_DICTIONARY_v2.md          Variable-by-variable dictionary of the analytic file
├── results/                           All tables (CSV) and main-text figures (PNG + PDF)
│   └── figures/                       Fig1_CFA_Loadings, Fig2_Trajectories_Totals,
│                                      Fig3_Forest_d_CI — 300 dpi, greyscale-safe
├── supplementary/                     Supplementary Materials A–F + statistical supplement
├── CHECKSUMS.md                       SHA-256 of the data files
└── requirements.txt                   Python dependencies
```

---

## Requirements

**Python 3** — install with `pip install -r requirements.txt`:
`numpy ≥ 2.4`, `scipy ≥ 1.17`, `pandas ≥ 3.0`, `statsmodels ≥ 0.14.6`,
`openpyxl ≥ 3.1`, `matplotlib ≥ 3.10`.

**R 4.5** — `lme4`, `lmerTest`, `pbkrtest`, `lavaan`, `semTools`, `ARTool`,
`openxlsx`:

```r
install.packages(c("lme4", "lmerTest", "pbkrtest", "lavaan",
                   "semTools", "ARTool", "openxlsx"))
```

All random seeds are fixed in code (`SEED = 20260815`); bootstrap replications
are B = 9,999 (wild cluster) and B = 10,000 (retention ratio). Reruns are
therefore deterministic.

---

## Reproduction pipeline

**Path convention.** The analysis scripts read the analytic dataset from
`../work/dataset_analitico.xlsx` relative to `code/`, and write their outputs
next to themselves in `code/` (figures into `code/figuras_nuevas/`). The
`data/` and `results/` folders of this repository are the curated, published
copies of those inputs and outputs. To run the pipeline unmodified, stage a
`work/` directory at the repository root first:

```bash
mkdir -p work
cp data/dataset_analitico.xlsx data/dataset_raw2_T0.xlsx work/
cd code
```

Then run, in this order:

| # | Script | Produces |
|---|---|---|
| 1 | `python limpieza_bruto_a_analiticov2.py` | `dataset_analitico.xlsx`, `consort_flujo.csv`, `analisis_atricion.csv`, `log_limpieza.txt` |
| 2 | `python paquete_inferencia_clusterizada.py` | `T_B_estructura_secciones.csv`, `T_C_ICC_por_seccion.csv`, `T_D_robustez_primarios.csv`, `T_D2_CR2_secundarios.csv` |
| 3 | `Rscript lmm_kr_y_cfa_wlsmv.R` | `LMM_KenwardRoger.csv`, `CFA_WLSMV_{ajuste,cargas,corr_factores,AVE_CR}.csv` |
| 4 | `python analisis_complementarios.py` | `Tabla1_fiabilidad_por_ola.csv`, `Tabla6_ANOVA_mixto_GG.csv`, `Tabla7_ANCOVA_completa.csv`, `Tabla8_d_con_IC.csv`, `T_G_supuestos.csv`, `T_H_retencion_RR.csv` |
| 5 | `Rscript art_invarianza_sem.R` | `ART_interacciones.csv`, `Invarianza_longitudinal.csv`, `SEM_WLSMV_ajuste_Nq.csv`, `SEM_WLSMV_paths.csv` |
| 6 | `python reanalisis_menores.py` | `SensibilidadA_rank_ancova.csv`, `SensibilidadB_cotas_atricion.csv`, `Moderadores_{omnibus,n_celdas}.csv`, `Fig1_CFA_Loadings.{png,pdf}` |
| 7 | `python figuras_resultados.py` | `Fig2_Trajectories_Totals.{png,pdf}`, `Fig3_Forest_d_CI.{png,pdf}` |

Step 1 is the only step that consumes the raw file; the published
`dataset_analitico.xlsx` is its verified output, so steps 2–7 can be run
directly on the shipped analytic dataset. Step 6 requires
`CFA_WLSMV_cargas.csv` from step 3. Each script also writes a `log_*.txt`
execution log.

### What each analysis does

- **`paquete_inferencia_clusterizada.py`** — the robustness core. Estimates the
  primary contrast under six inferential regimes: M1 individual-level OLS with
  classical SE (the naïve reference), M2 CR2 + Satterthwaite (the primary
  analysis), M3 LMM `(1|Seccion)` with conservative df, M4 ANCOVA on the eight
  section means, M5 restricted wild cluster bootstrap with 6-point Webb weights,
  and M6 the exact permutation test over all C(8,4) = 70 section assignments
  (minimum attainable two-sided *p* = 2/70 = .0286). Also computes section-level
  ICCs with exact F-based CIs and design effects.
- **`lmm_kr_y_cfa_wlsmv.R`** — replaces the conservative df of M3 with exact
  Kenward–Roger df, and fits the four-factor CFA on the 26 T0 self-perception
  items via WLSMV on polychoric correlations (fully standardized solution,
  factor correlations, robust fit, Fornell–Larcker AVE/CR).
- **`analisis_complementarios.py`** — full ANCOVA with adjusted marginal means
  and a homogeneity-of-slopes test; 2 × 3 mixed ANOVA with Mauchly and
  Greenhouse–Geisser correction plus per-cell Shapiro–Wilk and per-occasion
  Levene checks; Cohen's *d* with noncentral-*t* CIs; retention ratio
  RR = d(T2)/d(T1) with cluster bootstrap CIs; Cronbach's α (Likert) and KR-20
  (dichotomous) per wave and dimension.
- **`art_invarianza_sem.R`** — aligned-rank-transform ANOVA for the Group ×
  Time interaction; longitudinal measurement invariance per dimension over
  ordinal items following the Wu–Estabrook sequence (configural → thresholds →
  thresholds + loadings, ΔCFI ≤ .01); the structural model re-estimated in
  lavaan WLSMV with the N:q ratio reported.
- **`reanalisis_menores.py`** — sensitivity analyses: Conover rank-ANCOVA
  against the non-normality flagged by Shapiro–Wilk; explicit worst- and
  best-case attrition bounds (the 12 excluded cases have T0 only, so an MAR
  model adds no information); omnibus Group × Moderator interaction tests for
  faculty, gender and prior AI experience, with documented rules for small
  categories.

---

## Results inventory

| File in `results/` | Manuscript element |
|---|---|
| `Tabla1_fiabilidad_por_ola.csv` | Table 1 — α and KR-20 by wave and dimension |
| `Tabla6_ANOVA_mixto_GG.csv` | Table 6 — mixed ANOVA, GG-corrected *p*, η²ₚ [90 % CI] |
| `Tabla7_ANCOVA_completa.csv` | Table 7 — adjusted means ± SE, adjusted difference [95 % CI], F, η²ₚ |
| `Tabla8_d_con_IC.csv` | Table 8 — Cohen's *d* with noncentral 95 % CIs at T1 and T2 |
| `T_B_estructura_secciones.csv` | Section × condition × faculty × n |
| `T_C_ICC_por_seccion.csv` | ICCs and design effects by outcome and wave |
| `T_D_robustez_primarios.csv` | Six inferential methods × two primary outcomes |
| `T_D2_CR2_secundarios.csv` | CR2 + Satterthwaite for the 8 subscales at T1 (Holm within family) and totals at T2 |
| `T_G_supuestos.csv` | Assumption checks (Shapiro–Wilk, Levene, Mauchly, ε) |
| `T_H_retencion_RR.csv` | Retention ratios with bootstrap CIs (operationalizes H2) |
| `CFA_WLSMV_*.csv` | Measurement model: fit, standardized loadings, factor correlations, AVE/CR |
| `Invarianza_longitudinal.csv` | Longitudinal invariance, Wu–Estabrook sequence |
| `SEM_WLSMV_*.csv` | Structural model fit, N:q ratio, and paths with 95 % CIs |
| `ART_interacciones.csv` | Aligned-rank-transform Group × Time tests |
| `SensibilidadA_rank_ancova.csv` | Rank-ANCOVA sensitivity |
| `SensibilidadB_cotas_atricion.csv` | Attrition bounds (worst/best case) |
| `Moderadores_omnibus.csv`, `Moderadores_n_celdas.csv` | Moderation tests and cell sizes |
| `figures/Fig1_CFA_Loadings.*` | Figure 1 — standardized CFA loadings |
| `figures/Fig2_Trajectories_Totals.*` | Figure 2 — group trajectories with 95 % CIs |
| `figures/Fig3_Forest_d_CI.*` | Figure 3 — forest plot of *d* with CIs |

### Headline numbers reproduced by the pipeline

- **Measurement.** Four-factor CFA (WLSMV): CFI = .986, TLI = .984,
  RMSEA = .049 [.036, .061], SRMR = .053; AVE .628–.737 and CR .919–.944 across
  the four dimensions. Longitudinal invariance holds up to thresholds and
  loadings for all four dimensions (ΔCFI ≈ .000).
- **Clustering.** Section-level ICCs are negligible for self-perception
  (≤ .048) but non-trivial for objective knowledge at T1 (ICC = .211,
  design effect 4.73) — which is why cluster-robust inference is the primary
  analysis rather than a robustness check.
- **Primary effects.** Adjusted difference of 0.390 points on self-perception
  and 4.99 points on objective knowledge. The conclusion is invariant across
  all six inferential regimes: the most conservative, the exact permutation
  test, returns *p* = .0286 — its minimum attainable value.
- **Effect sizes and persistence.** *d* = 0.49 [0.16, 0.81] at T1 and 0.39
  [0.06, 0.71] at T2 for self-perception; *d* = 0.96 [0.62, 1.29] at T1 and
  0.69 [0.36, 1.02] at T2 for knowledge. Retention ratios show partial decay:
  the 80 % criterion is met by five of the eight subscales but by neither
  primary total (RR = .795 self-perception, .722 knowledge).
- **Robustness.** Rank-ANCOVA reaches the same conclusions under
  non-normality; the worst-case attrition bound reduces the effect by 16–18 %
  and remains significant; no moderator reaches significance (all *p* > .28),
  so the effect does not differ by faculty, gender or prior AI experience.

---

## Data availability and ethics

Both the raw pretest file and the analytic dataset are published here. Direct
identifiers were never recorded in the research files: participants appear
under sequential pseudonymous codes (`EST-0001` …) assigned at recruitment, and
the key linking codes to identities is held separately by the principal
investigator and is not part of this repository.

`dataset_raw2_T0.xlsx` retains the administrative variables needed to audit the
raw-to-analytic flow (consent, pilot participation, attendance counts and
percentage, wave-completion flags, exclusion reason, dropout date, T0 date).
`dataset_analitico.xlsx` drops all of them; the exact list of dropped variables
is documented at the end of `data/DATA_DICTIONARY_v2.md`. Anyone can therefore
verify the CONSORT flow (174 → 162 → 150) and the attrition comparison
independently, by rerunning step 1 of the pipeline.

Participants gave written informed consent; 12 of the 174 eligible students
declined and are represented only as an aggregate count in the recruitment
log.

---

## Integrity

SHA-256 checksums for the data files are listed in `CHECKSUMS.md`. Verify with:

```bash
sha256sum data/dataset_analitico.xlsx     # Linux/macOS
Get-FileHash data\dataset_analitico.xlsx -Algorithm SHA256   # Windows PowerShell
```

CSV files are UTF-8; those written by pandas carry a BOM (`utf-8-sig`) for
Excel compatibility.

---

## License

Data and materials: **CC BY-NC 4.0**. Code: **MIT**. (To be confirmed on
acceptance.)

## Citation

Until the article is published, please cite this repository as the
reproducibility package of Ms. No. SSHO-D-26-02688 (Social Sciences &
Humanities Open, under review). Author and affiliation details are withheld
during anonymous peer review.
