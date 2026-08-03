# cases/15-multigroup-corr-heatmap/plot.R
# Case 15 - Multi-group correlation heatmap with in-cell mini bars.
# Run from gallery root.

suppressPackageStartupMessages({ library(ggplot2); library(dplyr) })
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/15-multigroup-corr-heatmap/simulate.R")

sim <- simulate_corr_grid(seed = 1)
taxa <- sim$taxa; cols <- sim$cols

# integer positions: rows top->bottom, cols left->right
taxa$y <- seq_len(nrow(taxa))
cols$x <- seq_len(nrow(cols))
grid <- sim$grid |>
  left_join(taxa, by = "taxon") |>
  left_join(cols, by = "col")

# mini bar per cell: height proportional to |r|, fill by signed r
grid <- grid |>
  mutate(xmin = x - 0.32, xmax = x + 0.32,
         ymin = y - 0.38, ymax = y - 0.38 + abs(r) / 0.35 * 0.76)

# group colour strip on the far left
grp_cols <- setNames(
  c("#F2C14E","#E4884D","#5AA9E6","#3D7C6B","#B5739D","#8C6BB1"),
  sim$row_groups)
grp_cols <- plotworks_discrete_values(grp_cols)
corr_cols <- plotworks_diverging_values(c("#B2182B", "white", "#2166AC"), n = 11)
taxa$group <- factor(taxa$group, levels = sim$row_groups)

# top super-group brackets
sup <- cols |> group_by(super) |>
  summarise(x1 = min(x), x2 = max(x), xc = mean(x), .groups = "drop")

p <- ggplot() +
  # cell frames
  geom_tile(data = grid, aes(x, y), fill = NA, colour = "grey85",
            linewidth = 0.2, width = 0.9, height = 0.9) +
  # in-cell bars
  geom_rect(data = grid, aes(xmin = xmin, xmax = xmax, ymin = ymin,
            ymax = ymax, fill = r)) +
  # left group colour strip
  geom_tile(data = taxa, aes(x = 0.2, y = y, fill = NULL),
            fill = grp_cols[as.character(taxa$group)], width = 0.25,
            height = 1) +
  # taxon labels
  geom_text(data = taxa, aes(x = 0.45, y = y, label = taxon), hjust = 0,
            size = 2) +
  # column labels (top)
  geom_text(data = cols, aes(x = x, y = nrow(taxa) + 0.8, label = col),
            angle = 45, hjust = 0, size = 2.4) +
  # super-group brackets
  geom_segment(data = sup, aes(x = x1 - 0.4, xend = x2 + 0.4,
            y = nrow(taxa) + 3.2, yend = nrow(taxa) + 3.2), linewidth = 0.4) +
  geom_text(data = sup, aes(x = xc, y = nrow(taxa) + 3.8, label = super),
            size = 2.8, fontface = "bold") +
  scale_fill_gradientn(colours = corr_cols, name = "r") +
  scale_y_reverse(expand = expansion(add = c(1, 5))) +
  scale_x_continuous(expand = expansion(add = c(2.5, 0.5))) +
  coord_cartesian(clip = "off") +
  labs(x = NULL, y = NULL) +
  theme_void(base_size = 9) +
  theme(legend.position = "right")

save_case(p, adk_output_path("cases/15-multigroup-corr-heatmap/figures/multigroup_corr_heatmap.png"),
          width = 8, height = 9)
message("Case 15 rendered: ", nrow(taxa), " taxa x ", nrow(cols), " variables")
