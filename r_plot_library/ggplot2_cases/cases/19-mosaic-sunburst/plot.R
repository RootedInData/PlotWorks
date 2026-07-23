# cases/19-mosaic-sunburst/plot.R
# Case 19 - Mosaic plot (+ sunburst). Run from gallery root.

suppressPackageStartupMessages({ library(ggplot2); library(dplyr) })
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/19-mosaic-sunburst/simulate.R")

sim <- simulate_geneset(seed = 1)
pal_cls <- c(Core = "#E8563F", Softcore = "#4FB0C6",
             Dispensable = "#3E9B6E", Private = "#3B4F8C")

# --- Mosaic: bar widths ~ group total, heights ~ class proportion ---
gt <- sim$mosaic |> distinct(group, total) |>
  mutate(w = total / sum(total),
         xmax = cumsum(w), xmin = xmax - w, xc = (xmin + xmax) / 2)

mos <- sim$mosaic |>
  left_join(gt[c("group","xmin","xmax","xc")], by = "group") |>
  group_by(group) |>
  arrange(class) |>
  mutate(ymax = cumsum(prop), ymin = ymax - prop) |>
  ungroup()

p_mosaic <- ggplot(mos) +
  geom_rect(aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax,
                fill = class), colour = "white", linewidth = 0.4) +
  scale_fill_manual(values = pal_cls, name = NULL) +
  scale_x_continuous(breaks = gt$xc, labels = gt$group,
                     expand = c(0, 0)) +
  scale_y_continuous(labels = function(y) paste0(y * 100, "%"),
                     expand = c(0, 0)) +
  labs(x = "Gene set groups", y = NULL) +
  theme_case(base_size = 11) +
  theme(panel.grid = element_blank(), legend.position = "top")

save_case(p_mosaic, adk_output_path("cases/19-mosaic-sunburst/figures/mosaic.png"),
          width = 6.5, height = 5.5)

# --- Sunburst: two stacked rings in polar coordinates ---
sun <- sim$sun
inner <- sun |> group_by(inner) |> summarise(n = sum(n), .groups = "drop")
pal_sun <- c(Core = "#E8563F", Softcore = "#3B6BA5", Dispensable = "#3E9B6E")

p_sun <- ggplot() +
  geom_col(data = inner, aes(x = 1, y = n, fill = inner), colour = "white",
           width = 1) +
  geom_col(data = sun, aes(x = 2, y = n, fill = inner), colour = "white",
           width = 1, alpha = 0.75) +
  geom_text(data = sun, aes(x = 2, y = n, label = paste0(outer, "\n", n)),
            position = position_stack(vjust = 0.5), size = 1.9) +
  scale_fill_manual(values = pal_sun, name = NULL) +
  coord_polar(theta = "y") +
  xlim(c(-0.5, 2.5)) +
  theme_void(base_size = 9) +
  theme(legend.position = "right")

save_case(p_sun, adk_output_path("cases/19-mosaic-sunburst/figures/sunburst.png"),
          width = 6.5, height = 6)
message("Case 19 rendered: mosaic + sunburst")
