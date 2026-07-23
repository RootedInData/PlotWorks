# cases/16-polar-heatmap/simulate.R
# Case 16 - Polar-coordinate heatmap. Partial correlations between four
# regulating factor groups (angular) and four soil-carbon processes (radial
# rings) for particulate organic carbon (POC). Base R only.

simulate_polar <- function(seed = 1) {
  set.seed(seed)
  groups <- list(
    "Structure (ST)"      = c("Aliphatic", "Aromatic", "TS", "SA"),
    "Origin (OR)"         = c("Plant", "Microbial", "Necromass", "Input"),
    "Transformation (TS)" = c("F:B", "Fun.Ap", "Bac.Ap", "MRD"),
    "Stability (SA)"      = c("MOC", "Occlude", "C limitation",
                             "Resource limitation"))
  vars <- data.frame(
    var = unlist(groups, use.names = FALSE),
    group = rep(names(groups), lengths(groups)), stringsAsFactors = FALSE)

  rings <- c("OR", "ST", "TS", "SA")            # radial rings (inner->outer)
  grid <- expand.grid(var = vars$var, ring = rings, stringsAsFactors = FALSE)
  grid <- merge(grid, vars, by = "var")
  grid$r <- round(runif(nrow(grid), -0.8, 0.8), 2)
  grid$sig <- abs(grid$r) > 0.45                # black border if "significant"

  list(grid = grid, vars = vars, rings = rings, groups = names(groups))
}
