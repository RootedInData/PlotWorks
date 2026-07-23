# cases/03-multigroup-volcano/simulate.R
# Case 3 - Multi-group volcano. Differential expression (average log2FC) for many
# genes across several cell clusters, coloured up / down. Base R only.

simulate_multivolcano <- function(seed = 1, n_cluster = 18, per = 160) {
  set.seed(seed)
  syms <- c("GZMK","CCL5","IFNG","CRTAM","NMB","CXCL13","FOS","HSP1AB","GNLY",
            "XCL1","CD74","AREG","KLRB1","LTB","IL7R","NKG7","ANXA1","CCL4",
            "IGLC2","IGKC","IGHA1","JCHAIN","MS4A1","HLA-DRA","IGHG1","IGHG3",
            "CCL4L2","ITM2A","ATP5ME","MT2A","SELL","GAPDH","B2M","TXNIP")

  rows <- lapply(seq_len(n_cluster), function(k) {
    fc <- rnorm(per, 0, 0.7)
    # inject a handful of strong up / down genes whose magnitude grows toward
    # the higher-numbered clusters (mimics the fanned envelope in the figure)
    n_up <- sample(3:7, 1); n_dn <- sample(3:7, 1)
    up_mag <- 2 + (k / n_cluster) * 4
    fc[sample(per, n_up)] <- runif(n_up, 1.5, up_mag)
    fc[sample(per, n_dn)] <- -runif(n_dn, 1.5, 0.7 * up_mag)
    data.frame(cluster = k, gene = sample(syms, per, replace = TRUE),
               avg_log2FC = fc, stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  out$type <- ifelse(out$avg_log2FC > 0, "UP_Highly", "Down_Highly")
  out
}
