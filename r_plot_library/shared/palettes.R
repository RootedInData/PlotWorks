pal_agency_categorical <- c(
  "#E69F00", "#56B4E9", "#009E73", "#F0E442",
  "#0072B2", "#D55E00", "#CC79A7", "#7F7F7F"
)

pal_agency_muted <- c(
  "#4C78A8", "#F58518", "#54A24B", "#E45756",
  "#72B7B2", "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC"
)

pal_agency_up_down <- c(up = "#B2182B", down = "#2166AC", ns = "grey80")

agency_palette <- function(n, palette = "categorical") {
  base <- switch(
    palette,
    muted = pal_agency_muted,
    up_down = pal_agency_up_down,
    pal_agency_categorical
  )
  rep(base, length.out = n)
}
