# cases/04-manhattan-twas/plot.R
# Case 4 - Manhattan (TWAS). Run from gallery root.

library(ggplot2)
library(dplyr)
library(ggrepel)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/04-manhattan-twas/simulate.R")

twas <- adk_load_or_simulate("04-manhattan-twas", simulate_twas(seed = 1))

# Cumulative genome coordinate.
span <- twas |>
  group_by(CHR) |>
  summarise(chr_len = max(BP), .groups = "drop") |>
  mutate(chr_start = lag(cumsum(chr_len), default = 0))

twas <- twas |>
  left_join(span, by = "CHR") |>
  mutate(bp_cum = BP + chr_start, neglogp = -log10(P),
         band = factor(as.integer(factor(CHR)) %% 2))

axis_chr <- twas |>
  group_by(CHR) |>
  summarise(centre = mean(range(bp_cum)), .groups = "drop")

# Thin the null cloud below 1 for file size (seeded).
set.seed(4)
keep <- twas$neglogp >= 1 | runif(nrow(twas)) < 0.35
pd <- twas[keep, ]

thr_bonf <- -log10(0.05 / nrow(twas))
labs <- pd |> filter(!is.na(gene), neglogp > 8)
band_cols <- plotworks_discrete_values(c("#D6604D", "#4A6FA5"))
threshold_cols <- plotworks_discrete_values(
  c(bonferroni = "#2C6FB2", suggestive = "#C0392B")
)

p <- ggplot(pd, aes(bp_cum, neglogp)) +
  geom_point(aes(colour = band), size = 0.5, show.legend = FALSE) +
  geom_hline(yintercept = thr_bonf, colour = threshold_cols[["bonferroni"]], linewidth = 0.4) +
  geom_hline(yintercept = -log10(1e-5), colour = threshold_cols[["suggestive"]], linewidth = 0.4,
             linetype = "dashed") +
  ggrepel::geom_text_repel(data = labs, aes(label = gene), size = 1.9,
            max.overlaps = Inf, seed = 1, segment.size = 0.15,
            min.segment.length = 0) +
  scale_colour_manual(values = band_cols) +
  scale_x_continuous(breaks = axis_chr$centre, labels = axis_chr$CHR,
                     expand = expansion(mult = 0.01)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.08))) +
  labs(x = "Chromosome", y = expression(-log[10](italic(P)))) +
  theme_case_classic(base_size = 10) +
  theme(axis.text.x = element_text(size = 6))

save_case(p, adk_output_path("cases/04-manhattan-twas/figures/manhattan_twas.png"),
          width = 11, height = 4.5)
message("Case 04 rendered: ", nrow(twas), " genes, Bonferroni -log10 = ",
        round(thr_bonf, 2))
