# cases/07-swimmer/plot.R
# Case 7 - Swimmer plot. Run from gallery root.

library(ggplot2)
library(dplyr)
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/07-swimmer/simulate.R")

dat <- adk_load_or_simulate("07-swimmer", simulate_swimmer(seed = 1)) |>
  arrange(weeks) |>
  mutate(patient = factor(patient, levels = patient),
         yn = as.integer(patient))
n_pat <- nrow(dat)

pal_resp <- c(CR = "#4E9A51", PR = "#A6D96A", SD = "#9ECAE1",
              `Tumour shrinkage` = "#4292C6", PD = "#BDBDBD")

# event-marker layers
ong <- filter(dat, ongoing)
prog <- filter(dat, progression)
rtd <- filter(dat, rt)

# month gridlines (4-week months): 6, 12, 18 months
months <- data.frame(wk = c(24, 48, 72), lab = c("6 months", "12 months",
                                                 "18 months"))

p <- ggplot(dat, aes(weeks, yn, fill = response)) +
  geom_vline(data = months, aes(xintercept = wk), colour = "grey80",
             linewidth = 1.2) +
  geom_col(width = 0.65, orientation = "y") +
  geom_point(data = ong, aes(x = weeks + 2, y = yn), shape = 23,
             fill = "black", size = 1.8, inherit.aes = FALSE) +
  geom_point(data = prog, aes(x = weeks + 2, y = yn), shape = 4,
             size = 1.8, stroke = 0.7, inherit.aes = FALSE) +
  geom_point(data = rtd, aes(x = rt_week, y = yn), shape = 2, size = 1.8,
             stroke = 0.7, inherit.aes = FALSE) +
  geom_text(data = months, aes(x = wk, y = n_pat + 0.8, label = lab),
            inherit.aes = FALSE, size = 3, vjust = 0) +
  scale_fill_manual(values = pal_resp, name = NULL) +
  scale_x_continuous(breaks = seq(0, 96, 8), limits = c(0, 98),
                     expand = expansion(mult = c(0, 0.02))) +
  scale_y_continuous(breaks = NULL) +
  coord_cartesian(clip = "off") +
  labs(x = "Time on study (weeks)", y = "NSCLC") +
  theme_case_classic(base_size = 11) +
  theme(axis.text.y = element_blank(), axis.ticks.y = element_blank(),
        legend.position = "right",
        plot.margin = margin(20, 10, 6, 6))

save_case(p, adk_output_path("cases/07-swimmer/figures/swimmer.png"), width = 8, height = 6)
message("Case 07 rendered: ", nrow(dat), " patients")
