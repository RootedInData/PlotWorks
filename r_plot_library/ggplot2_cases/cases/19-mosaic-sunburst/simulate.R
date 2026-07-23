# cases/19-mosaic-sunburst/simulate.R
# Case 19 - Mosaic plot (+ sunburst). Composition of four gene classes across
# three gene-set groups. Base R only.

simulate_geneset <- function(seed = 1) {
  set.seed(seed)
  classes <- c("Core", "Softcore", "Dispensable", "Private")

  # group totals (bar widths) and within-group class proportions (bar heights)
  spec <- list(
    Double   = list(total = 5300, p = c(0.90, 0.05, 0.03, 0.02)),
    Variable = list(total = 8600, p = c(0.35, 0.15, 0.25, 0.25)),
    Single   = list(total = 4100, p = c(0.05, 0.05, 0.05, 0.85)))

  mosaic <- do.call(rbind, lapply(names(spec), function(g) {
    data.frame(group = g, total = spec[[g]]$total, class = classes,
               prop = spec[[g]]$p, stringsAsFactors = FALSE)
  }))
  mosaic$group <- factor(mosaic$group, levels = c("Double","Variable","Single"))
  mosaic$class <- factor(mosaic$class, levels = classes)

  # sunburst hierarchy: inner ring class, outer ring subdivision
  sun <- rbind(
    data.frame(inner="Core",        outer="Core_double",         n=2372),
    data.frame(inner="Core",        outer="Core_variable",       n=2981),
    data.frame(inner="Core",        outer="Core_single",         n=535),
    data.frame(inner="Softcore",    outer="Softcore_variable",   n=1970),
    data.frame(inner="Softcore",    outer="Softcore_double",     n=104),
    data.frame(inner="Dispensable", outer="Dispensable_variable",n=1234),
    data.frame(inner="Dispensable", outer="Dispensable",         n=1263),
    stringsAsFactors = FALSE)

  list(mosaic = mosaic, sun = sun, classes = classes)
}
