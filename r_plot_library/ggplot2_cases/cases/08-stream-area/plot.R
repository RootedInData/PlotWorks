# cases/08-stream-area/plot.R
# Case 8 - Individualized area plot. Run from gallery root.

library(ggplot2)
library(dplyr)
library(patchwork)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/08-stream-area/simulate.R")

sim <- simulate_stream(seed = 1)
ord <- sim$bars$taxon[order(sim$bars$mda)]           # ascending for y order
pal_ph <- c(Actinobacteriota = "#9ECAE1", Firmicutes = "#2C6FB2",
            Proteobacteria = "#9E80C0")
pal_ph <- plotworks_discrete_values(pal_ph)

bars <- sim$bars |> mutate(taxon = factor(taxon, levels = ord))
series <- sim$series |> mutate(taxon = factor(taxon, levels = ord))

# Left: Mean Decrease Accuracy bars (axis runs high -> 0 toward the centre).
p_left <- ggplot(bars, aes(mda, taxon, fill = phylum)) +
  geom_col(width = 0.7, show.legend = FALSE) +
  scale_x_reverse(expand = expansion(mult = c(0.02, 0))) +
  scale_fill_manual(values = pal_ph) +
  labs(x = "Mean Decrease Accuracy", y = NULL) +
  theme_case_classic(base_size = 9) +
  theme(axis.text.y = element_blank(), axis.ticks.y = element_blank())

# Right: per-taxon abundance streams, one row each, aligned to the bar order.
day_lab <- data.frame(t = c(15, 45, 75), lab = c("D1", "D3", "D6"))
p_right <- ggplot(series, aes(t, value, fill = phylum)) +
  geom_area(alpha = 0.85, colour = NA) +
  geom_vline(xintercept = c(30, 60), colour = "black", linewidth = 0.3) +
  facet_grid(taxon ~ ., switch = "y") +
  scale_fill_manual(values = pal_ph, name = "Phylum") +
  scale_x_continuous(breaks = day_lab$t, labels = day_lab$lab,
                     position = "top", expand = c(0, 0)) +
  labs(x = NULL, y = NULL) +
  theme_case_classic(base_size = 9) +
  theme(axis.text.y = element_blank(), axis.ticks.y = element_blank(),
        strip.text.y.left = element_text(angle = 0, hjust = 1, size = 6),
        panel.spacing = unit(1, "pt"), legend.position = "right")

fig <- p_left + p_right + plot_layout(widths = c(1, 1.4))
save_case(fig, adk_output_path("cases/08-stream-area/figures/stream_area.png"),
          width = 10, height = 6)
message("Case 08 rendered: ", nrow(bars), " taxa")
