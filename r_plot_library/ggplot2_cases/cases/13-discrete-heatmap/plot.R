# cases/13-discrete-heatmap/plot.R
# Case 13 - Discrete heatmap. Run from gallery root.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(patchwork)
})
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/13-discrete-heatmap/simulate.R")

sim <- simulate_rr(seed = 1)
vals <- sim$vals; ann <- sim$ann

# strains top (1) to bottom (19)
ylev <- rev(ann$strain)
vals$strain <- factor(vals$strain, levels = ylev)
ann$strain  <- factor(ann$strain, levels = ylev)
vals$drug   <- factor(vals$drug, levels = sim$drugs)
vals$cat    <- factor(vals$cat, levels = sim$cat_levels)

# RdBu-style ramp: high fold-change red, low blue.
cat_cols <- setNames(
  colorRampPalette(c("#67001F","#B2182B","#D6604D","#F4A582","#FDDBC7",
                     "#D1E5F0","#92C5DE","#4393C3","#2166AC","#053061"))(10),
  sim$cat_levels)
cat_cols <- plotworks_continuous_values(cat_cols, n = length(cat_cols))
names(cat_cols) <- sim$cat_levels

# main heatmap
p_hm <- ggplot(vals, aes(drug, strain, fill = cat)) +
  geom_tile(colour = "white", linewidth = 0.4) +
  geom_text(aes(label = rr), size = 2) +
  scale_fill_manual(values = cat_cols, name = "RR(AUC)", drop = FALSE) +
  scale_x_discrete(position = "top") +
  labs(x = NULL, y = NULL) +
  theme_minimal(base_size = 9) +
  theme(panel.grid = element_blank(), axis.text.y = element_blank(),
        axis.ticks = element_blank())

# left annotation table
tab <- data.frame(
  strain = rep(ann$strain, 4),
  col = rep(c("Clade","Strain","Variant","Variant ERG gene"), each = nrow(ann)),
  lab = c(ann$clade, as.character(ann$strain), ann$variant, ann$erg),
  stringsAsFactors = FALSE)
tab$col <- factor(tab$col,
                  levels = c("Clade","Strain","Variant","Variant ERG gene"))

p_tab <- ggplot(tab, aes(col, strain)) +
  geom_text(aes(label = lab), size = 2, hjust = 0.5) +
  scale_x_discrete(position = "top") +
  labs(x = NULL, y = NULL) +
  theme_void(base_size = 9) +
  theme(axis.text.x.top = element_text(face = "bold", size = 7))

fig <- p_tab + p_hm + plot_layout(widths = c(1.5, 1.4))
save_case(fig, adk_output_path("cases/13-discrete-heatmap/figures/discrete_heatmap.png"),
          width = 11, height = 6)
message("Case 13 rendered: ", nrow(ann), " strains x ", length(sim$drugs),
        " drugs")
