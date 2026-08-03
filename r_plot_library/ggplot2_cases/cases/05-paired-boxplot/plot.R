# cases/05-paired-boxplot/plot.R
# Case 5 - Paired boxplot. Run from gallery root.

library(ggplot2)
library(dplyr)
library(ggh4x)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/05-paired-boxplot/simulate.R")

dat <- adk_load_or_simulate("05-paired-boxplot", simulate_mic(seed = 1))

# order conditions so control is on the left within each facet
dat <- dat |>
  mutate(condition = factor(condition,
         levels = c("control", unique(dat$drug[dat$condition != "control"]))))
# a per-row x position: control = 1, treatment = 2
dat$xpos <- ifelse(dat$condition == "control", 1, 2)

# facet strip colours by antibiotic class
class_cols <- c(AMIN="#4FB3A9", CARB="#4C72B0", CEPH="#E7A6C4", MEMB="#E08214",
                TETR="#7FBF7B", TOPO="#8073AC")
class_cols <- plotworks_discrete_values(class_cols)
updown_cols <- plotworks_discrete_values(c(up = "#E08214", down = "#3A66A0"))
strip_fill <- class_cols[as.character(
  dat$class[match(levels(factor(dat$drug)), dat$drug)])]

# significance label per facet
sig_df <- dat |> distinct(drug, class, sig)

p <- ggplot(dat, aes(xpos, mic)) +
  geom_line(aes(group = isolate, colour = updown), linewidth = 0.25,
            alpha = 0.6, show.legend = FALSE) +
  geom_point(aes(colour = updown), size = 0.5, alpha = 0.7,
             show.legend = FALSE) +
  geom_boxplot(aes(group = xpos), width = 0.5, outlier.shape = NA,
               fill = NA, colour = "black", linewidth = 0.4) +
  geom_text(data = sig_df, aes(x = 1.5, y = 10^3.2, label = sig),
            inherit.aes = FALSE, size = 3) +
  facet_wrap2(~drug, nrow = 3, strip = strip_themed(
    background_x = elem_list_rect(fill = strip_fill))) +
  scale_colour_manual(values = updown_cols) +
  scale_x_continuous(breaks = c(1, 2),
                     labels = function(b) ifelse(b == 1, "control", "recent")) +
  scale_y_log10(labels = function(x) parse(text = paste0("10^", log10(x))),
                breaks = 10^seq(-3, 3, 2)) +
  labs(x = "Control or recent antibiotic",
       y = expression("Minimum inhibitory concentration (" * mu * "g ml"^-1 * ")")) +
  theme_case(base_size = 10) +
  theme(panel.grid = element_blank(),
        strip.text = element_text(face = "bold", colour = "black"))

save_case(p, adk_output_path("cases/05-paired-boxplot/figures/paired_boxplot.png"),
          width = 9, height = 6.5)
message("Case 05 rendered: ", length(unique(dat$drug)), " drugs")
