# cases/02-grouped-error-dotplot/plot.R
# Case 2 - Grouped error dot plot. Run from gallery root.

library(ggplot2)
library(dplyr)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/02-grouped-error-dotplot/simulate.R")

dat <- adk_load_or_simulate("02-grouped-error-dotplot", simulate_coloc(seed = 1))
dw  <- 0.6                                   # dodge width
pal <- plotworks_discrete_values(c(siCtrl = "#B0A18F", siGNPTAB = "#2E86AB"))

# x positions of each dodged column, for the +/- table and significance stars.
xpos <- expand.grid(siRNA = levels(dat$siRNA), cond = levels(dat$cond))
xpos$x <- as.integer(xpos$cond) +
  ifelse(xpos$siRNA == "siCtrl", -dw / 4, dw / 4)

stars <- data.frame(cond = c("10'", "30'"),
                    x = c(3, 4), y = c(0.9, 0.9),
                    lab = c("****", "**"))

# +/- table rows drawn below the axis (clip turned off).
tab <- data.frame(
  x = rep(xpos$x, 2),
  y = rep(c(-0.11, -0.17), each = nrow(xpos)),
  lab = c(ifelse(xpos$siRNA == "siCtrl", "+", "-"),
          ifelse(xpos$siRNA == "siCtrl", "-", "+"))
)

p <- ggplot(dat, aes(cond, value, colour = siRNA)) +
  geom_point(position = position_jitterdodge(jitter.width = 0.25,
             dodge.width = dw, seed = 1), size = 0.9, alpha = 0.7) +
  stat_summary(fun = mean, geom = "crossbar", width = 0.35, linewidth = 0.4,
               colour = "black",
               position = position_dodge(width = dw)) +
  stat_summary(fun.data = mean_se, geom = "errorbar", width = 0.18,
               linewidth = 0.4, colour = "black",
               position = position_dodge(width = dw)) +
  # significance brackets over paired columns
  geom_segment(data = stars, aes(x = x - dw/4, xend = x + dw/4, y = 0.86,
               yend = 0.86), inherit.aes = FALSE, linewidth = 0.3) +
  geom_text(data = stars, aes(x = x, y = y, label = lab), inherit.aes = FALSE,
            size = 4) +
  # +/- table and row labels
  geom_text(data = tab, aes(x = x, y = y, label = lab), inherit.aes = FALSE,
            size = 3) +
  annotate("text", x = 0.35, y = c(-0.11, -0.17), hjust = 1,
           label = c("siCtrl", "siGNPTAB"), size = 3) +
  annotate("segment", x = 2.6, xend = 4.4, y = -0.23, yend = -0.23,
           linewidth = 0.3) +
  annotate("text", x = 3.5, y = -0.27, label = "-/+AA", vjust = 1, size = 3) +
  scale_colour_manual(values = pal, name = NULL) +
  scale_y_continuous(breaks = seq(0, 1, 0.2),
                     expand = expansion(mult = c(0, 0.02))) +
  coord_cartesian(ylim = c(0, 1), clip = "off") +
  labs(x = NULL, y = "mTOR/LAMP2 colocalization\n(Pearson's coefficient)") +
  theme_case_classic(base_size = 11) +
  theme(legend.position = "top",
        axis.text.x = element_text(size = 10),
        plot.margin = margin(6, 10, 55, 30))

save_case(p, adk_output_path("cases/02-grouped-error-dotplot/figures/grouped_error_dotplot.png"),
          width = 7, height = 5.6)
message("Case 02 rendered: ", nrow(dat), " points")
