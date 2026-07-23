# cases/02-grouped-error-dotplot/simulate.R
# Case 2 - Grouped error dot plot (mTOR/LAMP2 colocalization).
# Four amino-acid conditions, each measured under siCtrl and siGNPTAB knockdown.
# Base R only.

simulate_coloc <- function(seed = 1, n = 42) {
  set.seed(seed)

  spec <- rbind(
    data.frame(cond = "-AA", siRNA = "siCtrl",    mu = 0.29, sd = 0.11),
    data.frame(cond = "-AA", siRNA = "siGNPTAB",  mu = 0.31, sd = 0.11),
    data.frame(cond = "+AA", siRNA = "siCtrl",    mu = 0.53, sd = 0.12),
    data.frame(cond = "+AA", siRNA = "siGNPTAB",  mu = 0.47, sd = 0.12),
    data.frame(cond = "10'", siRNA = "siCtrl",    mu = 0.44, sd = 0.12),
    data.frame(cond = "10'", siRNA = "siGNPTAB",  mu = 0.30, sd = 0.12),
    data.frame(cond = "30'", siRNA = "siCtrl",    mu = 0.50, sd = 0.12),
    data.frame(cond = "30'", siRNA = "siGNPTAB",  mu = 0.40, sd = 0.13),
    stringsAsFactors = FALSE
  )

  rows <- lapply(seq_len(nrow(spec)), function(i) {
    v <- rnorm(n, spec$mu[i], spec$sd[i])
    v[v < 0] <- abs(v[v < 0]) * 0.3
    v[v > 1] <- 1
    data.frame(cond = spec$cond[i], siRNA = spec$siRNA[i], value = v,
               stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  out$cond  <- factor(out$cond, levels = c("-AA", "+AA", "10'", "30'"))
  out$siRNA <- factor(out$siRNA, levels = c("siCtrl", "siGNPTAB"))
  out
}
