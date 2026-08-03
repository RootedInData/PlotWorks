# cases/18-treemap/plot.R
# Case 18 - Treemap. Run from gallery root.

suppressPackageStartupMessages({ library(ggplot2); library(treemapify) })
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/18-treemap/simulate.R")

dat <- adk_load_or_simulate("18-treemap", simulate_defensome(seed = 1))
pal_cat <- c(
  "Effector"               = "#C0392B",
  "Diverse"                = "#8A8D8F",
  "Membrane displacing"    = "#4C72B0",
  "Nucleic acid degrading" = "#C8B560",
  "Nucleotide modifying"   = "#4FB0A5",
  "Unknown"                = "#BDBDBD")
pal_cat <- plotworks_discrete_values(pal_cat)
dat$category <- factor(dat$category, levels = names(pal_cat))

p <- ggplot(dat, aes(area = n, fill = category, subgroup = category,
                     label = system)) +
  geom_treemap(colour = "white", size = 1) +
  geom_treemap_subgroup_border(colour = "white", size = 3) +
  # big faded category label pinned to the bottom-right corner, so it does not
  # sit on top of the individual system labels (top-left)
  geom_treemap_subgroup_text(place = "bottomright", grow = FALSE, alpha = 0.30,
                    colour = "white", fontface = "bold", min.size = 6) +
  geom_treemap_text(colour = "white", place = "topleft", reflow = TRUE,
                    size = 8, min.size = 4.5) +
  scale_fill_manual(values = pal_cat, name = NULL) +
  theme_void(base_size = 10) +
  theme(legend.position = "bottom")

save_case(p, adk_output_path("cases/18-treemap/figures/treemap.png"), width = 9, height = 6.5)
message("Case 18 rendered: ", nrow(dat), " systems in ",
        nlevels(dat$category), " categories")
