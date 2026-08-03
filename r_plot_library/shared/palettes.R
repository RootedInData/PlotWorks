# Shared PlotWorks palette layer.
#
# Approved ggplot2 recipes call these helpers instead of importing palette
# packages directly. The selected provider/name are supplied through managed
# environment variables by tools/r_bridge.py. With no override, the original
# recipe colors are preserved.

pal_plotworks_categorical <- c(
  "#E69F00", "#56B4E9", "#009E73", "#F0E442",
  "#0072B2", "#D55E00", "#CC79A7", "#7F7F7F"
)

pal_plotworks_muted <- c(
  "#4C78A8", "#F58518", "#54A24B", "#E45756",
  "#72B7B2", "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC"
)

pal_plotworks_sequential_blue <- c(
  "#EFF3FF", "#C6DBEF", "#9ECAE1", "#6BAED6",
  "#4292C6", "#2171B5", "#084594"
)

pal_plotworks_diverging_blue_red <- c(
  "#2166AC", "#67A9CF", "#D1E5F0", "#F7F7F7",
  "#FDDBC7", "#EF8A62", "#B2182B"
)

pal_plotworks_up_down <- c(up = "#B2182B", down = "#2166AC", ns = "grey80")

.plotworks_builtin_palettes <- list(
  categorical = pal_plotworks_categorical,
  muted = pal_plotworks_muted,
  sequential_blue = pal_plotworks_sequential_blue,
  diverging_blue_red = pal_plotworks_diverging_blue_red,
  up_down = unname(pal_plotworks_up_down)
)

.plotworks_truthy <- function(value) {
  tolower(trimws(as.character(value))) %in% c("1", "true", "t", "yes", "y", "on")
}

plotworks_palette_request <- function(
    default_provider = "recipe",
    default_name = "",
    default_reverse = FALSE) {
  provider <- trimws(Sys.getenv("PLOTWORKS_PALETTE_PROVIDER", default_provider))
  name <- trimws(Sys.getenv("PLOTWORKS_PALETTE_NAME", default_name))
  reverse_raw <- Sys.getenv(
    "PLOTWORKS_PALETTE_REVERSE",
    if (isTRUE(default_reverse)) "true" else "false"
  )
  list(
    provider = tolower(ifelse(nzchar(provider), provider, default_provider)),
    name = name,
    reverse = .plotworks_truthy(reverse_raw)
  )
}

plotworks_available_palettes <- function(provider = "ggrateful") {
  provider <- tolower(trimws(provider))
  if (provider == "recipe") return(character())
  if (provider == "plotworks") return(names(.plotworks_builtin_palettes))
  if (provider == "ggrateful") {
    if (!requireNamespace("ggrateful", quietly = TRUE)) {
      stop(
        "The ggrateful R package is required for this palette request. ",
        "Run r_plot_library/ggplot2_cases/setup.R first."
      )
    }
    return(names(getExportedValue("ggrateful", "ggrateful_palettes")))
  }
  stop("Unknown PlotWorks palette provider: ", provider)
}

.plotworks_provider_colors <- function(provider, name, mode = "discrete") {
  provider <- tolower(trimws(provider))
  name <- trimws(name)

  if (provider == "plotworks") {
    colors <- .plotworks_builtin_palettes[[name]]
    if (is.null(colors)) {
      stop(
        "Unknown PlotWorks palette '", name, "'. Available: ",
        paste(names(.plotworks_builtin_palettes), collapse = ", ")
      )
    }
    return(unname(colors))
  }

  if (provider == "ggrateful") {
    if (!requireNamespace("ggrateful", quietly = TRUE)) {
      stop(
        "The ggrateful R package is required for palette '", name, "'. ",
        "Run r_plot_library/ggplot2_cases/setup.R first."
      )
    }
    palettes <- getExportedValue("ggrateful", "ggrateful_palettes")
    gradients <- getExportedValue("ggrateful", "ggrateful_gradients")
    if (!name %in% names(palettes)) {
      stop(
        "Unknown ggrateful palette '", name, "'. Available: ",
        paste(names(palettes), collapse = ", ")
      )
    }
    if (mode %in% c("continuous", "diverging") && name %in% names(gradients)) {
      return(unname(gradients[[name]]))
    }
    return(unname(palettes[[name]]))
  }

  stop("Unknown PlotWorks palette provider: ", provider)
}

.plotworks_resize_palette <- function(colors, n, mode = "discrete") {
  colors <- unname(colors)
  if (n <= 0) return(character())
  if (length(colors) == 1) return(rep(colors, n))

  if (mode == "discrete" && n <= length(colors)) {
    # Spread selections across the source palette rather than taking only its
    # first colors. This keeps small category sets representative of the palette.
    idx <- unique(round(seq(1, length(colors), length.out = n)))
    if (length(idx) < n) {
      return(grDevices::colorRampPalette(colors)(n))
    }
    return(colors[idx])
  }
  grDevices::colorRampPalette(colors)(n)
}

plotworks_palette_values <- function(
    fallback,
    n = length(fallback),
    mode = "discrete",
    provider = NULL,
    name = NULL,
    reverse = NULL) {
  request <- plotworks_palette_request()
  if (is.null(provider) || !nzchar(trimws(provider))) provider <- request$provider
  if (is.null(name) || !nzchar(trimws(name))) name <- request$name
  if (is.null(reverse)) reverse <- request$reverse
  provider <- tolower(trimws(provider))
  name <- trimws(name)

  if (provider == "recipe" || !nzchar(name)) {
    result <- fallback
    if (length(result) != n) result <- .plotworks_resize_palette(result, n, mode)
    return(result)
  }

  source_colors <- .plotworks_provider_colors(provider, name, mode)
  if (isTRUE(reverse)) source_colors <- rev(source_colors)
  result <- .plotworks_resize_palette(source_colors, n, mode)

  fallback_names <- names(fallback)
  if (!is.null(fallback_names) && length(fallback_names) == n) {
    names(result) <- fallback_names
  }
  result
}

plotworks_discrete_values <- function(
    fallback,
    n = length(fallback),
    provider = NULL,
    name = NULL,
    reverse = NULL) {
  plotworks_palette_values(
    fallback = fallback,
    n = n,
    mode = "discrete",
    provider = provider,
    name = name,
    reverse = reverse
  )
}

plotworks_continuous_values <- function(
    fallback,
    n = 11,
    provider = NULL,
    name = NULL,
    reverse = NULL) {
  plotworks_palette_values(
    fallback = fallback,
    n = n,
    mode = "continuous",
    provider = provider,
    name = name,
    reverse = reverse
  )
}

plotworks_diverging_values <- function(
    fallback,
    n = 11,
    provider = NULL,
    name = NULL,
    reverse = NULL) {
  plotworks_palette_values(
    fallback = fallback,
    n = n,
    mode = "diverging",
    provider = provider,
    name = name,
    reverse = reverse
  )
}

# Backward-compatible helper used by static and animated custom R wrappers.
plotworks_palette <- function(n, palette = "categorical") {
  fallback <- .plotworks_builtin_palettes[[palette]]
  if (is.null(fallback)) fallback <- pal_plotworks_categorical
  plotworks_discrete_values(fallback = fallback, n = n)
}
