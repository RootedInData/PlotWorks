plotworks_export_presets <- list(
  single = c(width = 7.2, height = 5.0),
  wide = c(width = 10.0, height = 5.5),
  tall = c(width = 6.5, height = 8.0),
  square = c(width = 6.5, height = 6.5),
  heatmap = c(width = 8.5, height = 7.0),
  manhattan = c(width = 11.0, height = 5.5)
)

save_plotworks_plot <- function(plot, file, preset = "single", width = NULL,
                             height = NULL, dpi = 300) {
  dims <- plotworks_export_presets[[preset]]
  if (is.null(dims)) dims <- plotworks_export_presets$single
  if (is.null(width)) width <- unname(dims[["width"]])
  if (is.null(height)) height <- unname(dims[["height"]])
  ggplot2::ggsave(
    filename = file,
    plot = plot,
    width = width,
    height = height,
    units = "in",
    dpi = dpi,
    bg = "white"
  )
}
