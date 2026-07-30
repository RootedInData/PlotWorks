# PlotWorks custom-animation contract adapted from the supplied cotton-seed example.
# PlotWorks loads the approved plot-ready dataset and saves/renders the animation.
# This file should therefore define only build_animation(data).

build_animation <- function(data) {
  data <- data |>
    dplyr::mutate(
      Year = as.integer(Year),
      area_harvested = as.numeric(area_harvested),
      yield = as.numeric(yield)
    ) |>
    dplyr::filter(
      !is.na(Year),
      !is.na(area_harvested),
      !is.na(yield)
    )

  ggplot(
    data,
    aes(
      x = area_harvested,
      y = yield,
      colour = Area,
      size = area_harvested
    )
  ) +
    annotate(
      "rect",
      xmin = -Inf,
      xmax = Inf,
      ymin = -Inf,
      ymax = Inf,
      fill = "grey98",
      alpha = 0.1
    ) +
    geom_point(alpha = 0.82, stroke = 0.5) +
    scale_colour_manual(values = plotworks_palette(length(unique(data$Area)))) +
    scale_size_continuous(
      range = c(2.5, 9),
      guide = guide_legend(override.aes = list(alpha = 1))
    ) +
    labs(
      title = "Cotton Seed (Unginned) Production Analysis",
      subtitle = "Year: {as.integer(frame_time)}",
      x = "Area harvested",
      y = "Yield",
      colour = "Country or area",
      size = "Area harvested"
    ) +
    theme_plotworks() +
    theme(legend.position = "right") +
    transition_time(Year) +
    ease_aes("linear") +
    shadow_wake(wake_length = 0.15, alpha = 0.25) +
    enter_fade() +
    exit_fade()
}
