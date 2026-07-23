# cases/17-multilevel-sankey/plot.R
# Case 17 - Multi-level Sankey. Run from gallery root.

suppressPackageStartupMessages({
  library(ggplot2); library(ggalluvial)
})
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/17-multilevel-sankey/simulate.R")

dat <- adk_load_or_simulate("17-multilevel-sankey", simulate_biogeo(seed = 1))
cont_cols <- setNames(grDevices::hcl(
  seq(15, 375, length.out = nlevels(dat$Continent) + 1)[-1], 75, 60),
  levels(dat$Continent))

p <- ggplot(dat, aes(axis1 = Global, axis2 = Continent, axis3 = LandCoverType,
                     axis4 = Habitat, y = freq)) +
  geom_alluvium(aes(fill = Continent), width = 0.22, alpha = 0.55,
                show.legend = FALSE) +
  geom_stratum(width = 0.22, fill = "grey93", colour = "grey55",
               linewidth = 0.2) +
  geom_text(stat = "stratum", aes(label = after_stat(stratum)), size = 2) +
  scale_fill_manual(values = cont_cols) +
  scale_x_continuous(breaks = 1:4,
    labels = c("Global","Continent","LandCoverType","Habitat"),
    expand = c(0.03, 0.03), position = "top") +
  labs(x = NULL, y = NULL) +
  theme_void(base_size = 10) +
  theme(axis.text.x = element_text(face = "bold", colour = "#2C6FB2"))

save_case(p, adk_output_path("cases/17-multilevel-sankey/figures/multilevel_sankey.png"),
          width = 10, height = 8)
message("Case 17 rendered: ", nrow(dat), " flows")
