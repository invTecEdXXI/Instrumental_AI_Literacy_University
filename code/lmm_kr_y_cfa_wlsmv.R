# lmm_kr_y_cfa_wlsmv.R
# =====================
# Parte A (tarea 3 E1): LMM Post ~ Pre + Grupo + (1|Seccion) con REML y
#   gl de Kenward-Roger exactos para los dos outcomes primarios
#   (actualiza el metodo M3 de la Tabla T-D, hasta ahora con gl=m-2).
# Parte B (tarea 7 E1, responde R2.24): CFA de 4 factores sobre los 26
#   items de autopercepcion en T0, estimador WLSMV sobre correlaciones
#   policoricas. Solucion completamente estandarizada, correlaciones
#   factoriales, ajuste robusto, AVE/CR de Fornell-Larcker.
#
# Entrada : ../work/dataset_analitico.xlsx
# Salidas : LMM_KenwardRoger.csv, CFA_WLSMV_ajuste.csv,
#           CFA_WLSMV_cargas.csv, CFA_WLSMV_corr_factores.csv,
#           CFA_WLSMV_AVE_CR.csv, log_R.txt

suppressMessages({
  library(lme4)
  library(lmerTest)
  library(pbkrtest)
  library(lavaan)
  library(openxlsx)
})

setwd(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))))
log_lineas <- character(0)
logg <- function(...) {
  msg <- paste0(...)
  cat(msg, "\n")
  log_lineas <<- c(log_lineas, msg)
}

ruta <- file.path("..", "work", "dataset_analitico.xlsx")
t0 <- read.xlsx(ruta, sheet = "T0_PreTest")
t1 <- read.xlsx(ruta, sheet = "T1_PostTest")

# ---------------------------------------------------------------------------
# PARTE A: LMM con Kenward-Roger
# ---------------------------------------------------------------------------
logg("=== PARTE A: LMM (1|Seccion) REML con Kenward-Roger ===")

primarios <- c("Score_total_autopercepcion", "Score_conocimiento")
res_kr <- data.frame()

for (sc in primarios) {
  d <- data.frame(
    Post = t1[[sc]],
    Pre  = scale(t0[[sc]], scale = FALSE)[, 1],
    Trat = as.numeric(t0$Grupo == "Experimental"),
    Seccion = factor(t0$Seccion)
  )
  m <- lmer(Post ~ Pre + Trat + (1 | Seccion), data = d, REML = TRUE)
  cf <- coef(summary(m))["Trat", ]
  # gl de Kenward-Roger via lmerTest (ddf = "Kenward-Roger")
  cf_kr <- coef(summary(m, ddf = "Kenward-Roger"))["Trat", ]
  vc <- as.data.frame(VarCorr(m))
  icc <- vc$vcov[1] / sum(vc$vcov)
  ci <- cf_kr["Estimate"] + c(-1, 1) * qt(.975, cf_kr["df"]) * cf_kr["Std. Error"]
  res_kr <- rbind(res_kr, data.frame(
    Outcome = sc,
    b_Trat = round(cf_kr["Estimate"], 3),
    SE = round(cf_kr["Std. Error"], 3),
    gl_KR = round(cf_kr["df"], 2),
    t = round(cf_kr["t value"], 3),
    p_KR = signif(cf_kr["Pr(>|t|)"], 4),
    IC95_inf = round(ci[1], 3),
    IC95_sup = round(ci[2], 3),
    ICC_condicional = round(icc, 4),
    singular = isSingular(m)
  ))
  logg(sprintf("  %s: b=%.3f  SE=%.3f  gl_KR=%.2f  p=%.2e  ICC_cond=%.4f%s",
               sc, cf_kr["Estimate"], cf_kr["Std. Error"], cf_kr["df"],
               cf_kr["Pr(>|t|)"], icc,
               ifelse(isSingular(m), "  [ajuste singular: var(Seccion)~0]", "")))
}
write.csv(res_kr, "LMM_KenwardRoger.csv", row.names = FALSE)

# ---------------------------------------------------------------------------
# PARTE B: CFA WLSMV sobre policoricas (26 items autopercepcion, T0)
# ---------------------------------------------------------------------------
logg("")
logg("=== PARTE B: CFA 4 factores, WLSMV / policoricas, T0 (N=150) ===")

items <- list(
  D1 = sprintf("D1_%02d", 1:6),
  D2 = sprintf("D2_%02d", 1:6),
  D3 = sprintf("D3_%02d", 1:8),
  D4 = sprintf("D4_%02d", 1:6)
)
todos <- unlist(items)
dat <- t0[, todos]
dat[] <- lapply(dat, function(x) ordered(x, levels = 1:5))

modelo <- paste(
  sapply(names(items), function(f)
    paste0(f, " =~ ", paste(items[[f]], collapse = " + "))),
  collapse = "\n"
)

fit <- cfa(modelo, data = dat, ordered = todos, estimator = "WLSMV",
           std.lv = TRUE)

medidas <- fitMeasures(fit, c("chisq.scaled", "df.scaled", "pvalue.scaled",
                              "cfi.scaled", "tli.scaled", "rmsea.scaled",
                              "rmsea.ci.lower.scaled", "rmsea.ci.upper.scaled",
                              "srmr"))
ajuste <- data.frame(Indice = names(medidas), Valor = round(as.numeric(medidas), 4))
write.csv(ajuste, "CFA_WLSMV_ajuste.csv", row.names = FALSE)
logg("  Ajuste robusto (scaled):")
for (i in seq_len(nrow(ajuste))) logg(sprintf("    %-24s %.4f", ajuste$Indice[i], ajuste$Valor[i]))

std <- standardizedSolution(fit)
cargas <- std[std$op == "=~", c("lhs", "rhs", "est.std", "se", "pvalue")]
names(cargas) <- c("Factor", "Item", "Carga_std", "SE", "p")
cargas[, 3:5] <- round(cargas[, 3:5], 4)
write.csv(cargas, "CFA_WLSMV_cargas.csv", row.names = FALSE)
logg(sprintf("  Cargas estandarizadas: min=%.3f  max=%.3f  (todas <1: %s)",
             min(cargas$Carga_std), max(cargas$Carga_std),
             ifelse(max(cargas$Carga_std) < 1, "SI", "NO")))

corrs <- std[std$op == "~~" & std$lhs != std$rhs &
             std$lhs %in% names(items) & std$rhs %in% names(items),
             c("lhs", "rhs", "est.std", "se", "pvalue")]
names(corrs) <- c("F1", "F2", "r", "SE", "p")
corrs[, 3:5] <- round(corrs[, 3:5], 4)
write.csv(corrs, "CFA_WLSMV_corr_factores.csv", row.names = FALSE)
logg("  Correlaciones factoriales:")
for (i in seq_len(nrow(corrs)))
  logg(sprintf("    %s-%s  r=%.3f", corrs$F1[i], corrs$F2[i], corrs$r[i]))

# varianzas residuales negativas (Heywood)
resvar <- std[std$op == "~~" & std$lhs == std$rhs & std$lhs %in% todos, "est.std"]
logg(sprintf("  Varianzas residuales negativas (Heywood): %d", sum(resvar < 0)))

# AVE y CR de Fornell-Larcker desde cargas estandarizadas
ave_cr <- do.call(rbind, lapply(names(items), function(f) {
  l <- cargas$Carga_std[cargas$Factor == f]
  ave <- mean(l^2)
  cr <- sum(l)^2 / (sum(l)^2 + sum(1 - l^2))
  data.frame(Factor = f, k = length(l), AVE = round(ave, 3), CR = round(cr, 3))
}))
write.csv(ave_cr, "CFA_WLSMV_AVE_CR.csv", row.names = FALSE)
logg("  AVE / CR:")
for (i in seq_len(nrow(ave_cr)))
  logg(sprintf("    %s  AVE=%.3f  CR=%.3f", ave_cr$Factor[i], ave_cr$AVE[i], ave_cr$CR[i]))

writeLines(log_lineas, "log_R.txt")
logg("")
logg("SCRIPT R COMPLETADO")
