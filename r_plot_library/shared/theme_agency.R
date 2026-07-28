suppressPackageStartupMessages(library(ggplot2))

theme_agency <- function(base_size = 11, base_family = "") {
  theme_bw(base_size = base_size, base_family = base_family) +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = "grey92", linewidth = 0.3),
      panel.border = element_rect(colour = "black", linewidth = 0.5),
      axis.text = element_text(colour = "black"),
      axis.ticks = element_line(colour = "black", linewidth = 0.4),
      axis.title = element_text(face = "bold"),
      strip.background = element_rect(fill = "grey95", colour = "black", linewidth = 0.4),
      strip.text = element_text(colour = "black", face = "bold"),
      legend.key = element_blank(),
      legend.title = element_text(face = "bold"),
      plot.title = element_text(face = "bold", hjust = 0, size = rel(1.25)),
      plot.subtitle = element_text(colour = "grey35", hjust = 0),
      plot.caption = element_text(colour = "grey40", hjust = 1)
    )
}

theme_agency_classic <- function(base_size = 11, base_family = "") {
  theme_classic(base_size = base_size, base_family = base_family) +
    theme(
      axis.text = element_text(colour = "black"),
      axis.title = element_text(face = "bold"),
      axis.ticks = element_line(colour = "black"),
      axis.line = element_line(colour = "black", linewidth = 0.4),
      strip.background = element_blank(),
      strip.text = element_text(colour = "black", face = "bold"),
      legend.key = element_blank(),
      legend.title = element_text(face = "bold"),
      plot.title = element_text(face = "bold", hjust = 0, size = rel(1.25)),
      plot.subtitle = element_text(colour = "grey35", hjust = 0)
    )
}
