# art_invarianza_sem.R
# =====================
# Re-analisis menores en R (16-ago-2026):
#   Parte A (R2.22): ANOVA de rangos alineados (ART, ARTool) para la
#     interaccion Grupo x Tiempo de los dos outcomes primarios.
#   Parte B (A-8 / plan maestro): invarianza de medida longitudinal por
#     dimension (autopercepcion), items ordinales, secuencia Wu-Estabrook:
#     configural -> +umbrales -> +umbrales+cargas; criterio dCFI <= .01.
#   Parte C (R3.8): SEM original re-estimado en lavaan WLSMV (items T1
#     ordinales): ajuste robusto, paths estructurales con IC 95%, numero
#     de parametros libres y razon N:q.
#
# Entrada : ../work/dataset_analitico.xlsx
# Salidas : ART_interacciones.csv, Invarianza_longitudinal.csv,
#           SEM_WLSMV_ajuste_Nq.csv, SEM_WLSMV_paths.csv, log_R2.txt

suppressMessages({
  library(ARTool)
  library(lavaan)
  library(semTools)
  library(openxlsx)
})

setwd(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))))
log_lineas <- character(0)
logg <- function(...) { msg <- paste0(...); cat(msg, "\n"); log_lineas <<- c(log_lineas, msg) }

ruta <- file.path("..", "work", "dataset_analitico.xlsx")
t0 <- read.xlsx(ruta, sheet = "T0_PreTest")
t1 <- read.xlsx(ruta, sheet = "T1_PostTest")
t2 <- read.xlsx(ruta, sheet = "T2_FollowUp")

items <- list(
  D1 = sprintf("D1_%02d", 1:6),
  D2 = sprintf("D2_%02d", 1:6),
  D3 = sprintf("D3_%02d", 1:8),
  D4 = sprintf("D4_%02d", 1:6)
)

# ===========================================================================
# PARTE A: ART Grupo x Tiempo (primarios)
# ===========================================================================
logg("=== PARTE A: ANOVA de rangos alineados (ART), Grupo x Tiempo ===")
res_art <- data.frame()
for (sc in c("Score_total_autopercepcion", "Score_conocimiento")) {
  largo <- rbind(
    data.frame(ID = t0$ID_estudiante, Grupo = t0$Grupo, Tiempo = "T0", y = t0[[sc]]),
    data.frame(ID = t1$ID_estudiante, Grupo = t1$Grupo, Tiempo = "T1", y = t1[[sc]]),
    data.frame(ID = t2$ID_estudiante, Grupo = t2$Grupo, Tiempo = "T2", y = t2[[sc]])
  )
  largo$ID <- factor(largo$ID); largo$Grupo <- factor(largo$Grupo)
  largo$Tiempo <- factor(largo$Tiempo)
  m <- art(y ~ Grupo * Tiempo + (1 | ID), data = largo)
  a <- anova(m)
  for (i in seq_len(nrow(a))) {
    res_art <- rbind(res_art, data.frame(
      Outcome = sc, Efecto = a$Term[i], F = round(a$F[i], 2),
      df1 = a$Df[i], df2 = round(a$Df.res[i], 1),
      p = signif(a$`Pr(>F)`[i], 4)))
    logg(sprintf("  %s | %-14s F=%9.2f  df=(%s, %.0f)  p=%.2e",
                 sc, a$Term[i], a$F[i], a$Df[i], a$Df.res[i], a$`Pr(>F)`[i]))
  }
}
write.csv(res_art, "ART_interacciones.csv", row.names = FALSE)

# ===========================================================================
# PARTE B: invarianza longitudinal por dimension (Wu-Estabrook, WLSMV)
# ===========================================================================
logg("")
logg("=== PARTE B: invarianza longitudinal por dimension (dCFI <= .01) ===")

res_inv <- data.frame()
for (dim in names(items)) {
  its <- items[[dim]]
  ancho <- data.frame(ID = t0$ID_estudiante)
  for (ola in c("T0", "T1", "T2")) {
    src <- get(tolower(ola))
    for (it in its) ancho[[paste0(it, "_", ola)]] <- src[[it]]
  }
  vars_ord <- setdiff(names(ancho), "ID")
  ancho[vars_ord] <- lapply(ancho[vars_ord], function(x) ordered(x, levels = 1:5))

  fac_names <- paste0(dim, c("T0", "T1", "T2"))
  conf_model <- paste(
    sapply(c("T0", "T1", "T2"), function(ola)
      paste0(dim, ola, " =~ ", paste(paste0(its, "_", ola), collapse = " + "))),
    collapse = "\n")
  # residuos del mismo item correlacionados entre olas
  resid_cor <- unlist(lapply(its, function(it) c(
    paste0(it, "_T0 ~~ ", it, "_T1"),
    paste0(it, "_T0 ~~ ", it, "_T2"),
    paste0(it, "_T1 ~~ ", it, "_T2"))))
  conf_model <- paste(c(conf_model, resid_cor), collapse = "\n")

  longFac <- setNames(list(fac_names), dim)
  niveles <- list(configural = "", umbrales = c("thresholds"),
                  umbrales_cargas = c("thresholds", "loadings"))
  cfis <- c()
  for (nv in names(niveles)) {
    fit <- tryCatch({
      syn <- measEq.syntax(configural.model = conf_model, data = ancho,
                           ordered = vars_ord, parameterization = "delta",
                           ID.fac = "std.lv", ID.cat = "Wu.Estabrook.2016",
                           longFacNames = longFac,
                           long.equal = niveles[[nv]])
      cfa(as.character(syn), data = ancho, ordered = vars_ord,
          parameterization = "delta", estimator = "WLSMV")
    }, error = function(e) e)
    if (inherits(fit, "error")) {
      logg(sprintf("  %s %-16s ERROR: %s", dim, nv, conditionMessage(fit)))
      cfis[nv] <- NA
      res_inv <- rbind(res_inv, data.frame(Dimension = dim, Modelo = nv,
        chisq = NA, df = NA, CFI = NA, RMSEA = NA, dCFI = NA, Cumple = NA))
      next
    }
    med <- fitMeasures(fit, c("chisq.scaled", "df.scaled", "cfi.scaled",
                              "rmsea.scaled"))
    cfis[nv] <- med["cfi.scaled"]
    dcfi <- if (nv == "configural") NA else
      round(cfis[[nv]] - cfis[[which(names(niveles) == nv) - 1]], 4)
    prev <- names(niveles)[max(1, which(names(niveles) == nv) - 1)]
    dcfi <- if (nv == "configural") NA else round(cfis[[nv]] - cfis[[prev]], 4)
    res_inv <- rbind(res_inv, data.frame(
      Dimension = dim, Modelo = nv,
      chisq = round(med["chisq.scaled"], 1), df = med["df.scaled"],
      CFI = round(med["cfi.scaled"], 4), RMSEA = round(med["rmsea.scaled"], 4),
      dCFI = ifelse(is.na(dcfi), "", dcfi),
      Cumple = ifelse(is.na(dcfi), "", ifelse(abs(dcfi) <= .01, "SI", "NO"))))
    logg(sprintf("  %s %-16s chi2=%7.1f df=%3.0f CFI=%.4f RMSEA=%.4f dCFI=%s",
                 dim, nv, med["chisq.scaled"], med["df.scaled"],
                 med["cfi.scaled"], med["rmsea.scaled"],
                 ifelse(is.na(dcfi), "-", sprintf("%+.4f", dcfi))))
  }
}
write.csv(res_inv, "Invarianza_longitudinal.csv", row.names = FALSE)

# ===========================================================================
# PARTE C: SEM en lavaan WLSMV + N:q
# ===========================================================================
logg("")
logg("=== PARTE C: SEM (spec original) re-estimado WLSMV; N:q e IC ===")

todos <- unlist(items)
df_sem <- t1[, todos]
df_sem[] <- lapply(df_sem, function(x) ordered(x, levels = 1:5))
df_sem$Improvement <- t1$Score_total_autopercepcion - t0$Score_total_autopercepcion
df_sem$Knowledge <- t1$Score_conocimiento
df_sem$Group <- as.numeric(t1$Grupo == "Experimental")

modelo_sem <- paste(c(
  sapply(names(items), function(f)
    paste0(f, " =~ ", paste(items[[f]], collapse = " + "))),
  "Improvement ~ D1 + D2 + D3 + D4 + Group",
  "Knowledge ~ D1 + D2 + D3 + D4"), collapse = "\n")

fit_sem <- sem(modelo_sem, data = df_sem, ordered = todos, estimator = "WLSMV")
med <- fitMeasures(fit_sem, c("npar", "chisq.scaled", "df.scaled",
                              "cfi.scaled", "tli.scaled", "rmsea.scaled",
                              "rmsea.ci.lower.scaled", "rmsea.ci.upper.scaled",
                              "srmr"))
nq <- round(nrow(df_sem) / med["npar"], 2)
ajuste <- data.frame(Indice = c(names(med), "N", "N_q"),
                     Valor = c(round(as.numeric(med), 4), nrow(df_sem), nq))
write.csv(ajuste, "SEM_WLSMV_ajuste_Nq.csv", row.names = FALSE)
logg(sprintf("  npar=%d  ->  N:q = %d/%d = %.2f : 1  (limite habitual 5:1)",
             med["npar"], nrow(df_sem), med["npar"], nq))
logg(sprintf("  CFI=%.4f TLI=%.4f RMSEA=%.4f [%.4f-%.4f] SRMR=%.4f",
             med["cfi.scaled"], med["tli.scaled"], med["rmsea.scaled"],
             med["rmsea.ci.lower.scaled"], med["rmsea.ci.upper.scaled"],
             med["srmr"]))

std <- standardizedSolution(fit_sem, level = 0.95)
paths <- std[std$op == "~", c("lhs", "rhs", "est.std", "se", "pvalue",
                              "ci.lower", "ci.upper")]
names(paths) <- c("Endogena", "Predictor", "beta_std", "SE", "p",
                  "IC95_inf", "IC95_sup")
paths[, 3:7] <- round(paths[, 3:7], 4)
write.csv(paths, "SEM_WLSMV_paths.csv", row.names = FALSE)
logg("  Paths estructurales (estandarizados, IC 95%):")
for (i in seq_len(nrow(paths)))
  logg(sprintf("    %s <- %-6s beta=%+.3f [%+.3f, %+.3f] p=%s",
               paths$Endogena[i], paths$Predictor[i], paths$beta_std[i],
               paths$IC95_inf[i], paths$IC95_sup[i],
               format.pval(paths$p[i], digits = 3)))

writeLines(log_lineas, "log_R2.txt")
logg("")
logg("SCRIPT R2 COMPLETADO")
