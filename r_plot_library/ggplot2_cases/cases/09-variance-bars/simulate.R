# cases/09-variance-bars/simulate.R
# Case 9 - Multi-group variance-analysis bars. qPCR relative abundance of nine
# OSCA genes across four stresses and four time points, with SE and significance
# letters. Base R only.

simulate_qpcr <- function(seed = 1) {
  set.seed(seed)
  genes  <- c("HvHvOSCA1.1", "HvHvOSCA1.3_2", "HvHvOSCA1.4",
              "HvHvOSCA2.1_1", "HvHvOSCA2.1_2", "HvHvOSCA2.2",
              "HvHvOSCA2.4", "HvHvOSCA3.1", "HvHvOSCA4.1")
  stress <- c("ABA", "Cold", "PEG", "Salt")
  time   <- c("Mock", "06h", "12h", "24h")

  grid <- expand.grid(gene = genes, stress = stress, time = time,
                      stringsAsFactors = FALSE)
  grid$mean <- pmax(0.1, rgamma(nrow(grid), shape = 4, scale = 0.4))
  grid$se   <- grid$mean * runif(nrow(grid), 0.05, 0.18)

  # significance letters: rank the four time points within each gene x stress.
  ladder <- c("a", "ab", "bc", "c")
  grid$letter <- NA_character_
  key <- paste(grid$gene, grid$stress)
  for (k in unique(key)) {
    idx <- which(key == k)
    ord <- idx[order(grid$mean[idx], decreasing = TRUE)]
    grid$letter[ord] <- ladder
  }

  grid$gene   <- factor(grid$gene, levels = genes)
  grid$stress <- factor(grid$stress, levels = stress)
  grid$time   <- factor(grid$time, levels = time)
  grid
}
