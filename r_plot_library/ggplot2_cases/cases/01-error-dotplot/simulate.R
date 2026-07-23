# cases/01-error-dotplot/simulate.R
# Case 1 - Individualized error dot plot (Filopodia generation capacity).
# Reproduces the structure of a per-treatment jittered dot plot where each
# treatment belongs to a signalling pathway (colour) and carries a mean +/- SD.
# Base R only.

simulate_filopodia <- function(seed = 1, n = 28) {
  set.seed(seed)

  # Treatment, pathway group, and the "true" mean filopodia length. Inhibitors
  # that block the response (PKI 14-22, H-89) sit near zero; the rest stay high.
  spec <- rbind(
    data.frame(treatment = "ctrl",            pathway = "Control",         mu = 3.0, sd = 1.6),
    data.frame(treatment = "HD5",             pathway = "cAMP-PKA",        mu = 16,  sd = 4),
    data.frame(treatment = "Hep",             pathway = "cAMP-PKA",        mu = 13,  sd = 4),
    data.frame(treatment = "PKI 14-22",       pathway = "cAMP-PKA",        mu = 2.2, sd = 1.4),
    data.frame(treatment = "IBMX",            pathway = "cAMP-PKA",        mu = 18,  sd = 4),
    data.frame(treatment = "RO 20-1724",      pathway = "cAMP-PKA",        mu = 15,  sd = 4),
    data.frame(treatment = "H-89",            pathway = "cAMP-PKA",        mu = 2.0, sd = 1.3),
    data.frame(treatment = "AZD6244",         pathway = "RAS-MAPK",        mu = 24,  sd = 5),
    data.frame(treatment = "AZD0364",         pathway = "RAS-MAPK",        mu = 21,  sd = 5),
    data.frame(treatment = "SP600125",        pathway = "RAS-MAPK",        mu = 20,  sd = 5),
    data.frame(treatment = "SB203580",        pathway = "EGFR-PKC",        mu = 18,  sd = 5),
    data.frame(treatment = "Gefitinib",       pathway = "EGFR-PKC",        mu = 14,  sd = 5),
    data.frame(treatment = "Lapatinib",       pathway = "EGFR-PKC",        mu = 19,  sd = 5),
    data.frame(treatment = "Bosutinib",       pathway = "PI3K-Akt-mTOR",   mu = 17,  sd = 5),
    data.frame(treatment = "Rapamycin",       pathway = "PI3K-Akt-mTOR",   mu = 20,  sd = 5),
    data.frame(treatment = "PI-103",          pathway = "PI3K-Akt-mTOR",   mu = 17,  sd = 5),
    data.frame(treatment = "U73122",          pathway = "Ca2+ signaling",  mu = 15,  sd = 4),
    data.frame(treatment = "Bapta-AM (5 uM)", pathway = "Ca2+ signaling",  mu = 15,  sd = 4),
    data.frame(treatment = "Bapta-AM (10 uM)",pathway = "Ca2+ signaling",  mu = 14,  sd = 4),
    stringsAsFactors = FALSE
  )

  rows <- lapply(seq_len(nrow(spec)), function(i) {
    v <- rnorm(n, spec$mu[i], spec$sd[i])
    v[v < 0] <- abs(v[v < 0]) * 0.2          # keep lengths non-negative
    data.frame(treatment = spec$treatment[i],
               pathway   = spec$pathway[i],
               value     = v, stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)

  # Preserve the on-figure ordering of treatments and pathways.
  out$treatment <- factor(out$treatment, levels = spec$treatment)
  out$pathway   <- factor(out$pathway,
                          levels = c("Control", "cAMP-PKA", "RAS-MAPK",
                                     "EGFR-PKC", "PI3K-Akt-mTOR",
                                     "Ca2+ signaling"))
  out
}
