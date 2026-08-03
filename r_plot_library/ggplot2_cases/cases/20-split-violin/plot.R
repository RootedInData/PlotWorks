# cases/20-split-violin/plot.R
# Case 20 - Split violin. Run from gallery root.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(gghalves)
})
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/20-split-violin/simulate.R")

dat <- adk_load_or_simulate("20-split-violin", simulate_immune(seed = 1))
dat$xn <- as.integer(dat$cell)
pal <- plotworks_discrete_values(c("low-risk" = "#9AA6D4", "high-risk" = "#D98AA0"))

lo <- filter(dat, risk == "low-risk")
hi <- filter(dat, risk == "high-risk")

# per-cell Welch p-value, annotated on top
pv <- dat |>
  group_by(cell, xn) |>
  summarise(p = t.test(value ~ risk)$p.value, .groups = "drop") |>
  mutate(lab = sprintf("p = %.5f", p))

ytop <- max(dat$value) + 1

p <- ggplot() +
  gghalves::geom_half_violin(data = lo, aes(xn, value, group = xn,
     fill = "low-risk"), side = "l", colour = NA, alpha = 0.7, width = 0.9) +
  gghalves::geom_half_violin(data = hi, aes(xn, value, group = xn,
     fill = "high-risk"), side = "r", colour = NA, alpha = 0.7, width = 0.9) +
  stat_summary(data = lo, aes(xn - 0.12, value), fun = mean, geom = "point",
     size = 0.9) +
  stat_summary(data = lo, aes(xn - 0.12, value), fun.data = mean_sdl,
     fun.args = list(mult = 1), geom = "errorbar", width = 0.06,
     linewidth = 0.3) +
  stat_summary(data = hi, aes(xn + 0.12, value), fun = mean, geom = "point",
     size = 0.9) +
  stat_summary(data = hi, aes(xn + 0.12, value), fun.data = mean_sdl,
     fun.args = list(mult = 1), geom = "errorbar", width = 0.06,
     linewidth = 0.3) +
  geom_text(data = pv, aes(xn, ytop, label = lab), size = 2.2) +
  scale_x_continuous(breaks = seq_along(levels(dat$cell)),
                     labels = levels(dat$cell)) +
  scale_fill_manual(values = pal, breaks = c("high-risk", "low-risk"),
                    name = NULL) +
  labs(x = NULL, y = "Immune infiltration score") +
  guides(fill = guide_legend(override.aes = list(alpha = 0.9))) +
  theme_case(base_size = 10) +
  theme(axis.text.x = element_text(angle = 30, hjust = 1),
        legend.position = "right", panel.grid.major.x = element_blank())

save_case(p, adk_output_path("cases/20-split-violin/figures/split_violin.png"),
          width = 10, height = 5.5)
message("Case 20 rendered: ", nlevels(dat$cell), " cell types")
