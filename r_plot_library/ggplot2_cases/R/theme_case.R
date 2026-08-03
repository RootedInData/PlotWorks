# R/theme_case.R
# -----------------------------------------------------------------------------
# Shared look for the 20-case gallery. Each case reproduces a specific published
# figure, so individual recipes override colours and elements freely; this file
# only supplies a clean common baseline and a few reusable palettes plus a saver.
# -----------------------------------------------------------------------------

suppressPackageStartupMessages(library(ggplot2))

# Palette-provider helpers live one level above the copied case library.
# All approved recipes source this theme file, so palette support remains
# centralized rather than duplicated across 20 cases.
plotworks_palette_helper <- file.path("..", "shared", "palettes.R")
if (!file.exists(plotworks_palette_helper)) {
  stop("Missing PlotWorks palette helper: ", plotworks_palette_helper)
}
source(plotworks_palette_helper)

# A clean journal theme: black axes, no grid by default, blank strip background.
theme_case <- function(base_size = 11, base_family = "") {
  theme_bw(base_size = base_size, base_family = base_family) +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = "grey92", linewidth = 0.3),
      panel.border     = element_rect(colour = "black", linewidth = 0.5),
      axis.text        = element_text(colour = "black"),
      axis.ticks       = element_line(colour = "black", linewidth = 0.4),
      strip.background = element_rect(fill = "grey95", colour = "black",
                                      linewidth = 0.4),
      strip.text       = element_text(colour = "black", face = "bold"),
      legend.key       = element_blank(),
      plot.title       = element_text(face = "bold", hjust = 0)
    )
}

# Classic-style variant (no panel border / grid) for dot-plots and Manhattan.
theme_case_classic <- function(base_size = 11, base_family = "") {
  theme_classic(base_size = base_size, base_family = base_family) +
    theme(
      axis.text  = element_text(colour = "black"),
      axis.ticks = element_line(colour = "black"),
      axis.line  = element_line(colour = "black", linewidth = 0.4),
      strip.background = element_blank(),
      strip.text = element_text(colour = "black", face = "bold"),
      legend.key = element_blank(),
      plot.title = element_text(face = "bold", hjust = 0)
    )
}

# Okabe-Ito colourblind-safe qualitative palette (grey instead of black).
pal_oi <- c("#E69F00", "#56B4E9", "#009E73", "#F0E442",
            "#0072B2", "#D55E00", "#CC79A7", "#999999")

# Two-tone significance palette (up / down / ns).
pal_ud <- c(up = "#C0392B", down = "#2166AC", ns = "grey80")

# Save a PNG at a given size (inches) and 300 dpi on white.
save_case <- function(plot, file, width, height, dpi = 300) {
  ggsave(file, plot, width = width, height = height, units = "in",
         dpi = dpi, bg = "white")
}
