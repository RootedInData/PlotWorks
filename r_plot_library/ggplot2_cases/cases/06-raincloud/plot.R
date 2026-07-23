# cases/06-raincloud/plot.R
# Case 6 - Raincloud (advanced). Run from gallery root.

library(ggplot2)
library(dplyr)
library(gghalves)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/06-raincloud/simulate.R")

dat <- adk_load_or_simulate("06-raincloud", simulate_leafout(seed = 1))
dat$xn <- as.numeric(dat$environment)             # numeric x throughout

pal_sp <- c(Ginkgo = "#E64B35", Acer = "#59A14F",
            Fraxinus = "#00A0B0", Platanus = "#8674A1")
bg <- data.frame(xmin = c(0.4, 1.4), xmax = c(1.4, 2.4),
                 fill = c("#CFE0EC", "#F3D6D2"))

p <- ggplot(dat, aes(xn, leafout)) +
  geom_rect(data = bg, aes(xmin = xmin, xmax = xmax, ymin = 88, ymax = 152,
            fill = fill), inherit.aes = FALSE, alpha = 0.5,
            show.legend = FALSE) +
  scale_fill_identity() +
  gghalves::geom_half_violin(aes(x = xn - 0.03, group = xn), side = "l",
     width = 0.9, colour = NA, fill = "grey55", alpha = 0.35) +
  geom_boxplot(aes(group = interaction(xn, species), colour = species),
     width = 0.5, outlier.shape = NA, fill = NA, linewidth = 0.4,
     position = position_dodge(width = 0.55)) +
  geom_point(aes(colour = species),
     position = position_jitterdodge(jitter.width = 0.1, dodge.width = 0.55,
     seed = 1), size = 0.7, alpha = 0.7) +
  geom_hline(yintercept = 150, linetype = "dashed", linewidth = 0.4) +
  scale_colour_manual(values = pal_sp, name = NULL) +
  scale_x_continuous(breaks = c(1, 2), labels = c("Rural", "Urban"),
                     limits = c(0.4, 2.4)) +
  scale_y_continuous(limits = c(88, 152), breaks = seq(90, 150, 10)) +
  labs(x = NULL, y = "Leaf-out date (d)") +
  theme_case_classic(base_size = 12) +
  theme(legend.position = "top")

save_case(p, adk_output_path("cases/06-raincloud/figures/raincloud.png"),
          width = 7, height = 5.5)
message("Case 06 rendered: ", nrow(dat), " trees")
