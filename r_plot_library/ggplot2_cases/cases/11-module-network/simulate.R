# cases/11-module-network/simulate.R
# Case 11 - Module interaction network. A correlation network with two modules,
# nodes typed as metabolite / mRNA / phospho-protein / protein and edges
# weighted by correlation. Uses igraph to build the graph.

suppressPackageStartupMessages(library(igraph))

simulate_network <- function(seed = 1, sizes = c(38, 22),
                             p_in = 0.16, n_between = 12) {
  set.seed(seed)
  g <- sample_islands(length(sizes), sizes[1], p_in, n_between)
  # sample_islands needs equal island sizes; rebuild with a blockmodel instead
  # to allow unequal modules.
  N <- sum(sizes)
  membership <- rep(seq_along(sizes), times = sizes)
  pref <- matrix(0.015, length(sizes), length(sizes))
  diag(pref) <- p_in
  g <- sample_sbm(N, pref.matrix = pref, block.sizes = sizes)

  types <- c("metabolite", "mRNA", "phospho-protein", "protein")
  V(g)$type <- sample(types, N, replace = TRUE, prob = c(.28,.24,.20,.28))
  V(g)$name <- paste0(
    sample(c("PC","PE","TG","AGK","MAO","DSP","GALE","AKR","STAT3","CAPG",
             "IDH2","MDH","LCN1","UBE4A","CLU","AMY1","VPS13C","PPL","EVPL",
             "TG1","LGALS","HSP","GGCT","AGXT","MYO","PON2","DPP4"),
           N, replace = TRUE), seq_len(N))
  E(g)$correlation <- runif(ecount(g), 0.5, 0.9)
  g
}
