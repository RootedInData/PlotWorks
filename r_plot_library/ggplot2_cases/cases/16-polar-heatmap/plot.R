# cases/16-polar-heatmap/plot.R
# Case 16 - Polar-coordinate heatmap. Run from gallery root.

suppressPackageStartupMessages({ library(ggplot2); library(dplyr) })
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/16-polar-heatmap/simulate.R")

sim <- simulate_polar(seed = 1)
vars <- sim$vars

# angular order: keep variables grouped; radial order inner->outer
vars$var <- factor(vars$var, levels = vars$var)
grid <- sim$grid |>
  mutate(var = factor(var, levels = levels(vars$var)),
         ring = factor(ring, levels = sim$rings),
          y = as.integer(ring) + 1)             # leave a hole in the centre

# labels around the outside
lab <- vars |> mutate(x = as.integer(var), y = length(sim$rings) + 2.4)

p <- ggplot(grid, aes(x = as.integer(var), y = y, fill = r)) +
  geom_tile(aes(colour = sig), width = 0.95, height = 0.95, linewidth = 0.5) +
  geom_text(aes(label = sprintf("%.2f", r)), size = 1.7) +
  geom_text(data = lab, aes(x = x, y = y, label = var), inherit.aes = FALSE,
            size = 2, angle = 0) +
  scale_fill_gradient2(low = "#2166AC", mid = "white", high = "#B2182B",
                       midpoint = 0, limits = c(-0.8, 0.8),
                       name = "Partial correlation coefficient r") +
  scale_colour_manual(values = c(`TRUE` = "black", `FALSE` = "grey85"),
                      guide = "none") +
  scale_x_continuous(limits = c(0.5, nrow(vars) + 0.5)) +
  scale_y_continuous(limits = c(0, length(sim$rings) + 3)) +
  coord_polar(theta = "x") +
  annotate("text", x = nrow(vars) / 2, y = 0, label = "C poor soils\nPOC",
           size = 2.6) +
  labs(x = NULL, y = NULL) +
  theme_void(base_size = 9) +
  theme(legend.position = "bottom")

save_case(p, adk_output_path("cases/16-polar-heatmap/figures/polar_heatmap.png"),
          width = 8, height = 8.5)
message("Case 16 rendered: ", nrow(vars), " variables x ", length(sim$rings),
        " rings")
