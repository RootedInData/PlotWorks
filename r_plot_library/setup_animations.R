# Install/check packages used by PlotWorks animated plotting.
# Run from anywhere with:
#   Rscript r_plot_library/setup_animations.R

repo <- "https://cloud.r-project.org"
required <- c(
  "ggplot2", "gganimate", "gifski", "transformr",
  "dplyr", "tidyr", "ggrepel", "scales"
)
optional <- c("av")  # Needed only for MP4 output.

installed <- rownames(installed.packages())
to_get <- setdiff(required, installed)
if (length(to_get)) {
  install.packages(to_get, repos = repo, dependencies = TRUE)
}

missing_required <- setdiff(required, rownames(installed.packages()))
if (length(missing_required)) {
  cat("Still missing required animation packages:",
      paste(missing_required, collapse = ", "), "\n")
  quit(status = 1)
}

missing_optional <- setdiff(optional, rownames(installed.packages()))
if (length(missing_optional)) {
  cat("GIF animation is ready. Optional MP4 package missing:",
      paste(missing_optional, collapse = ", "), "\n")
} else {
  cat("GIF and MP4 animation packages are ready.\n")
}
