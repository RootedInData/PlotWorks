# cases/09-variance-bars/plot.R
# Case 9 - Multi-group variance-analysis bars. Run from gallery root.

library(ggplot2)
library(dplyr)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/09-variance-bars/simulate.R")

dat <- adk_load_or_simulate("09-variance-bars", simulate_qpcr(seed = 1))
pal_time <- c(Mock = "#9ECAE1", `06h` = "#4292C6",
              `12h` = "#F4D03F", `24h` = "#08519C")
dw <- 0.8

p <- ggplot(dat, aes(stress, mean, fill = time)) +
  geom_col(position = position_dodge(width = dw), width = 0.75,
           colour = "black", linewidth = 0.2) +
  geom_errorbar(aes(ymin = mean - se, ymax = mean + se),
                position = position_dodge(width = dw), width = 0.25,
                linewidth = 0.3) +
  geom_text(aes(y = mean + se + 0.15, label = letter),
            position = position_dodge(width = dw), size = 2.3) +
  facet_wrap(~gene, nrow = 3, scales = "free_y") +
  scale_fill_manual(values = pal_time, name = NULL) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.12))) +
  labs(x = NULL, y = "Relative abundance") +
  theme_case(base_size = 9) +
  theme(legend.position = "top", panel.grid.major.x = element_blank())

save_case(p, adk_output_path("cases/09-variance-bars/figures/variance_bars.png"),
          width = 9, height = 7)
message("Case 09 rendered: ", nlevels(dat$gene), " genes")
