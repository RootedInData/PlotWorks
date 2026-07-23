# cases/14-mantel-heatmap/simulate.R
# Case 14 - Mantel composite heatmap. A Spearman correlation matrix among soil
# variables, plus Mantel statistics linking each variable set to three species
# communities. Base R only.

simulate_mantel <- function(seed = 1) {
  set.seed(seed)
  vars <- c("N","P","K","Ca","Mg","S","Al","Fe","Mn","Zn","Mo",
            "Baresoil","Humdepth","pH")
  n <- length(vars)

  # a correlation matrix from random correlated data
  X <- matrix(rnorm(n * 80), ncol = n)
  X <- X + rnorm(80) * 0.6                     # shared component -> correlations
  M <- cor(X, method = "spearman")
  dimnames(M) <- list(vars, vars)
  # p-values (rough): from |r| and n
  P <- 2 * pnorm(-abs(atanh(pmin(pmax(M, -0.999), 0.999)) * sqrt(80 - 3)))

  specs <- c("Spec01", "Spec02", "Spec03")
  mantel <- expand.grid(spec = specs, var = vars, stringsAsFactors = FALSE)
  mantel$mr <- runif(nrow(mantel), 0.02, 0.55)
  mantel$mp <- runif(nrow(mantel))
  mantel$sign <- sample(c("Positive","Negative"), nrow(mantel), replace = TRUE,
                        prob = c(0.7, 0.3))
  mantel$r_cls <- cut(mantel$mr, c(-Inf, 0.2, 0.4, Inf),
                      labels = c("< 0.2","0.2 - 0.4",">= 0.4"))
  mantel$p_cls <- cut(mantel$mp, c(-Inf, 0.01, 0.05, Inf),
                      labels = c("< 0.01","0.01 - 0.05",">= 0.05"))

  list(M = M, P = P, vars = vars, mantel = mantel, specs = specs)
}
