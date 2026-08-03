# cases/03-multigroup-volcano/plot.R
# Case 3 - Multi-group volcano. Run from gallery root.

library(ggplot2)
library(dplyr)
library(ggrepel)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/03-multigroup-volcano/simulate.R")

dat <- adk_load_or_simulate("03-multigroup-volcano", simulate_multivolcano(seed = 1))
if (!"type" %in% names(dat)) dat$type <- ifelse(dat$avg_log2FC >= 0, "UP_Highly", "Down_Highly")

# Per-cluster grey background bar spanning that cluster's log2FC range.
bg <- dat |>
  group_by(cluster) |>
  summarise(lo = min(avg_log2FC), hi = max(avg_log2FC), .groups = "drop")

# Coloured strip of cluster tags at y = 0.
n_cl <- max(dat$cluster)
strip_cols <- grDevices::hcl(h = seq(15, 375, length.out = n_cl + 1)[-1],
                             c = 90, l = 65)
strip_cols <- plotworks_discrete_values(strip_cols)
pal_type <- plotworks_discrete_values(
  c(UP_Highly = "#D6403A", Down_Highly = "#2C6FB2")
)

# Genes to label: the single most extreme up gene and down gene per cluster,
# so up-labels sit high and down-labels sit low (less crowding than picking the
# top-2 by magnitude, which can put both labels at the same end).
labs_up <- dat |> filter(avg_log2FC > 0) |>
  group_by(cluster) |> slice_max(avg_log2FC, n = 1) |> ungroup()
labs_dn <- dat |> filter(avg_log2FC < 0) |>
  group_by(cluster) |> slice_min(avg_log2FC, n = 1) |> ungroup()

p <- ggplot(dat, aes(cluster, avg_log2FC)) +
  geom_rect(data = bg, aes(xmin = cluster - 0.45, xmax = cluster + 0.45,
            ymin = lo, ymax = hi), inherit.aes = FALSE, fill = "grey88") +
  geom_jitter(aes(colour = type), width = 0.32, size = 0.5, alpha = 0.8) +
  geom_tile(data = data.frame(cluster = seq_len(n_cl)),
            aes(x = cluster, y = 0, fill = factor(cluster)),
            width = 0.9, height = 0.55, inherit.aes = FALSE,
            show.legend = FALSE) +
  geom_text(data = data.frame(cluster = seq_len(n_cl)),
            aes(x = cluster, y = 0, label = cluster), inherit.aes = FALSE,
            size = 2.4) +
  ggrepel::geom_text_repel(data = labs_up, aes(label = gene, colour = type),
            size = 1.9, max.overlaps = Inf, seed = 1, segment.size = 0.15,
            direction = "y", ylim = c(2, NA), box.padding = 0.3,
            show.legend = FALSE) +
  ggrepel::geom_text_repel(data = labs_dn, aes(label = gene, colour = type),
            size = 1.9, max.overlaps = Inf, seed = 1, segment.size = 0.15,
            direction = "y", ylim = c(NA, -1.5), box.padding = 0.3,
            show.legend = FALSE) +
  scale_colour_manual(values = pal_type, name = NULL) +
  scale_fill_manual(values = strip_cols) +
  scale_x_continuous(breaks = seq_len(n_cl)) +
  labs(x = NULL, y = expression("average log"[2] * "FC")) +
  theme_case_classic(base_size = 11) +
  theme(legend.position = c(0.08, 0.9),
        legend.background = element_rect(fill = "white", colour = NA),
        panel.grid = element_blank(),
        axis.text.x = element_blank(), axis.ticks.x = element_blank())

save_case(p, adk_output_path("cases/03-multigroup-volcano/figures/multigroup_volcano.png"),
          width = 10, height = 5)
message("Case 03 rendered: ", nrow(dat), " genes across ", n_cl, " clusters")
