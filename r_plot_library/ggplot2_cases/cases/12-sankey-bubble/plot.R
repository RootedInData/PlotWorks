# cases/12-sankey-bubble/plot.R
# Case 12 - Combined Sankey + bubble. Run from gallery root.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(ggalluvial); library(patchwork)
})
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/12-sankey-bubble/simulate.R")

sim <- simulate_enrichment(seed = 1)
links <- sim$links
bubble <- sim$bubble

# order pathways by enrichment so both panels share a vertical order
ord <- bubble$pathway[order(bubble$neglogP)]
# wrap long pathway names so the middle Sankey stratum labels do not clip
wrapf <- function(x) vapply(x, function(s)
  paste(strwrap(s, width = 22), collapse = "\n"), character(1))
links$pathway  <- factor(links$pathway, levels = ord, labels = wrapf(ord))
bubble$pathway <- factor(bubble$pathway, levels = ord)
# unnamed palette maps to factor levels by order (labels differ per panel)
pal_pw <- grDevices::hcl(seq(15, 375, length.out = length(ord) + 1)[-1], 70, 62)
pal_pw <- plotworks_discrete_values(pal_pw)
hit_ratio_cols <- plotworks_continuous_values(c("#FDD49E", "#7F0000"), n = 11)

# --- Sankey (metabolite -> pathway) ---
p_sankey <- ggplot(links, aes(axis1 = metabolite, axis2 = pathway, y = freq)) +
  geom_alluvium(aes(fill = pathway), width = 0.18, alpha = 0.6,
                show.legend = FALSE) +
  geom_stratum(width = 0.18, fill = "grey95", colour = "grey60",
               linewidth = 0.2) +
  geom_text(stat = "stratum", aes(label = after_stat(stratum)), size = 1.7) +
  scale_fill_manual(values = pal_pw) +
  scale_x_continuous(breaks = 1:2, labels = c("Metabolite", "Pathway"),
                     expand = c(0.02, 0.02)) +
  labs(x = NULL, y = NULL) +
  theme_void(base_size = 9) +
  theme(axis.text.x = element_text())

# --- Bubble (enrichment) ---
p_bubble <- ggplot(bubble, aes(neglogP, pathway)) +
  geom_point(aes(size = count, colour = hit_ratio)) +
  scale_colour_gradientn(colours = hit_ratio_cols, name = "Hit Ratio") +
  scale_size_continuous(range = c(1.5, 6), name = "count") +
  scale_y_discrete(position = "right") +
  labs(x = expression(-log[10](Pvalue)), y = NULL) +
  theme_case(base_size = 9) +
  theme(panel.grid.minor = element_blank())

fig <- p_sankey + p_bubble + plot_layout(widths = c(1.5, 1))
save_case(fig, adk_output_path("cases/12-sankey-bubble/figures/sankey_bubble.png"),
          width = 12, height = 6.5)
message("Case 12 rendered: ", nrow(links), " metabolites -> ",
        nlevels(links$pathway), " pathways")
