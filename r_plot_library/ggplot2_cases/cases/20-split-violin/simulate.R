# cases/20-split-violin/simulate.R
# Case 20 - Split violin. Immune-cell abundance scores in low-risk vs high-risk
# patients across cell types. Base R only.

simulate_immune <- function(seed = 1, per = 60) {
  set.seed(seed)
  cells <- c("B cells","T cells","CD8 T cells","Cytotoxic lymphocytes",
             "Endothelial cells","Fibroblasts","Monocytic lineage",
             "Myeloid dendritic cells","Neutrophils","NK cells")
  # per-cell mean and the low->high shift (some strongly different, some not)
  base  <- c(8.0, 7.6, 7.4, 6.8, 6.7, 8.4, 7.5, 8.7, 7.8, 7.9)
  shift <- c(-0.9,-0.8,-0.6, 0.7, 0.05,-0.2, 0.2,-0.25, 0.03,-0.05)

  rows <- lapply(seq_along(cells), function(i) {
    lo <- rnorm(per, base[i], 0.6)
    hi <- rnorm(per, base[i] + shift[i], 0.6)
    data.frame(cell = cells[i],
               risk = rep(c("low-risk","high-risk"), each = per),
               value = c(lo, hi), stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  out$cell <- factor(out$cell, levels = cells)
  out$risk <- factor(out$risk, levels = c("low-risk","high-risk"))
  out
}
