# setup.R
# Install every package the gallery needs. Run once from the gallery root:
#   Rscript setup.R
# Then render everything with:
#   Rscript scripts/run_all.R

repo <- "https://cloud.r-project.org"

pkgs <- c(
  "ggplot2", "dplyr", "tidyr", "ggrepel", "patchwork",   # core
  "ggalluvial",   # Sankey (cases 12, 17)
  "treemapify",   # treemap (case 18)
  "circlize",     # Circos (case 10)
  "ggh4x",        # per-panel strips (case 5)
  "ggridges",     # ridgelines
  "igraph", "ggraph"  # network (case 11)
)

to_get <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_get)) install.packages(to_get, repos = repo)

# gghalves (raincloud, split violin) is archived on CRAN, so install it from
# the archive if a plain install is not available for this R version.
if (!requireNamespace("gghalves", quietly = TRUE)) {
  ok <- tryCatch({
    install.packages("gghalves", repos = repo); TRUE
  }, warning = function(w) FALSE, error = function(e) FALSE)
  if (!requireNamespace("gghalves", quietly = TRUE)) {
    install.packages(
      "https://cran.r-project.org/src/contrib/Archive/gghalves/gghalves_0.1.4.tar.gz",
      repos = NULL, type = "source")
  }
}

need <- c(pkgs, "gghalves")
miss <- setdiff(need, rownames(installed.packages()))
if (length(miss)) {
  cat("Still missing:", paste(miss, collapse = ", "), "\n")
} else {
  cat("All", length(need), "packages installed. Now run: Rscript scripts/run_all.R\n")
}
