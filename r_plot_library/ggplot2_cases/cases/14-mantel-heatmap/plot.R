# cases/14-mantel-heatmap/plot.R
# Case 14 - Mantel composite heatmap (hand-built). Run from gallery root.

suppressPackageStartupMessages({ library(ggplot2); library(dplyr) })
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/14-mantel-heatmap/simulate.R")

sim <- simulate_mantel(seed = 1)
vars <- sim$vars; n <- length(vars)

# lower-triangle tiles (row i below column j)
tiles <- do.call(rbind, lapply(2:n, function(i) do.call(rbind, lapply(1:(i-1),
  function(j) data.frame(i = i, j = j, r = sim$M[i, j], p = sim$P[i, j])))))
tiles$star <- ifelse(tiles$p < 0.001, "***",
               ifelse(tiles$p < 0.01, "**",
               ifelse(tiles$p < 0.05, "*", "")))
diagdf <- data.frame(i = seq_len(n), var = vars)

# spec nodes to the right; curves start from each variable's diagonal cell
spec_y <- c(Spec01 = 3, Spec02 = 7, Spec03 = 11)
spec_x <- n + 3.5
mant <- sim$mantel |>
  mutate(vi = match(var, vars),
         xend = spec_x, yend = spec_y[spec],
         x = vi, y = vi)
# thin to reduce clutter: keep the stronger / significant links
mant <- mant |> filter(mr > 0.28 | mp < 0.05)
corr_cols <- plotworks_diverging_values(c("#2166AC", "white", "#B2182B"), n = 11)
mantel_p_cols <- plotworks_discrete_values(c(
  "< 0.01" = "#D6604D", "0.01 - 0.05" = "#1B9E77", ">= 0.05" = "grey75"
))

p <- ggplot() +
  geom_tile(data = tiles, aes(j, i, fill = r), colour = "white",
            linewidth = 0.3) +
  geom_text(data = tiles, aes(j, i, label = star), size = 2.4,
            vjust = 0.75) +
  # Mantel curves (drawn before the diagonal labels so labels stay legible)
  geom_curve(data = mant, aes(x = x, y = y, xend = xend, yend = yend,
             colour = p_cls, linewidth = r_cls, linetype = sign),
             curvature = -0.25, alpha = 0.8) +
  # diagonal variable labels on top, with a white halo
  geom_label(data = diagdf, aes(i, i, label = var), fontface = "bold",
             size = 2.6, fill = "white", label.size = 0, alpha = 0.85,
             label.padding = unit(0.6, "pt")) +
  geom_point(data = data.frame(x = spec_x, y = spec_y, spec = names(spec_y)),
             aes(x, y), size = 3, colour = "#8B3A2F") +
  geom_text(data = data.frame(x = spec_x, y = spec_y, spec = names(spec_y)),
            aes(x + 0.3, y, label = spec), hjust = 0, fontface = "bold",
            size = 3) +
  scale_fill_gradientn(colours = corr_cols, limits = c(-1, 1),
                       name = "Spearman's r") +
  scale_colour_manual(values = mantel_p_cols,
                       name = "Mantel's p", drop = FALSE) +
  scale_linewidth_manual(values = c("< 0.2" = 0.3, "0.2 - 0.4" = 0.8,
                       ">= 0.4" = 1.6), name = "Mantel's r", drop = FALSE) +
  scale_linetype_manual(values = c(Positive = "solid", Negative = "dashed"),
                        name = "Mantel's r sign") +
  scale_y_reverse() +
  coord_equal(clip = "off") +
  labs(x = NULL, y = NULL) +
  theme_void(base_size = 10) +
  theme(legend.position = "left",
        plot.margin = margin(10, 60, 10, 10))

save_case(p, adk_output_path("cases/14-mantel-heatmap/figures/mantel_heatmap.png"),
          width = 10, height = 7)
message("Case 14 rendered: ", n, " variables, ", nrow(mant), " Mantel links")
