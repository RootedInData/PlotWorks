# cases/01-error-dotplot/plot.R
# Case 1 - Individualized error dot plot.
# Run: Rscript -e 'source("cases/01-error-dotplot/plot.R")'  (from gallery root)

library(ggplot2)
library(dplyr)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/01-error-dotplot/simulate.R")

dat <- adk_load_or_simulate("01-error-dotplot", simulate_filopodia(seed = 1))

pal_path <- c(
  "Control"        = "grey55",
  "cAMP-PKA"       = "#4C72B0",
  "RAS-MAPK"       = "#DD8452",
  "EGFR-PKC"       = "#8172B2",
  "PI3K-Akt-mTOR"  = "#C79A6B",
  "Ca2+ signaling" = "#55A868"
)
pal_path <- plotworks_discrete_values(pal_path)

# Significance brackets (a few illustrative comparisons vs control), placed by
# treatment index on the x-axis.
lvl <- levels(dat$treatment)
xi  <- function(t) match(t, lvl)
brk <- data.frame(
  x1 = xi("ctrl"), x2 = c(xi("HD5"), xi("IBMX"), xi("AZD6244")),
  y  = c(30, 33, 37),
  lab = c("P = 0.0083", "p < 0.0001", "p < 0.0001")
)

p <- ggplot(dat, aes(treatment, value)) +
  geom_jitter(aes(colour = pathway), width = 0.18, size = 0.9,
              alpha = 0.7, show.legend = TRUE) +
  stat_summary(fun = mean, geom = "crossbar", width = 0.5,
               linewidth = 0.4, colour = "black") +
  stat_summary(fun.data = mean_sdl, fun.args = list(mult = 1),
               geom = "errorbar", width = 0.25, linewidth = 0.4,
               colour = "black") +
  # brackets
  geom_segment(data = brk, aes(x = x1, xend = x2, y = y, yend = y),
               inherit.aes = FALSE, linewidth = 0.3) +
  geom_text(data = brk, aes(x = (x1 + x2) / 2, y = y + 1, label = lab),
            inherit.aes = FALSE, size = 2.8) +
  scale_colour_manual(values = pal_path, name = NULL) +
  scale_y_continuous(limits = c(0, 40), expand = expansion(mult = c(0, 0.02))) +
  labs(title = "Filopodia generation capacity",
       x = NULL, y = expression("Filopodia length per " * mu * "m peri")) +
  theme_case_classic(base_size = 11) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        legend.position = "right",
        plot.title = element_text(hjust = 0.5))

save_case(p, adk_output_path("cases/01-error-dotplot/figures/error_dotplot.png"),
          width = 9, height = 5)
message("Case 01 rendered: ", nrow(dat), " points, ",
        nlevels(dat$treatment), " treatments")
