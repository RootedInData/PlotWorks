# cases/11-module-network/plot.R
# Case 11 - Module interaction network. Run from gallery root.

suppressPackageStartupMessages({
  library(ggplot2); library(ggraph); library(igraph)
})
source("R/theme_case.R")
source("R/adk_data_bridge.R")
source("cases/11-module-network/simulate.R")

g <- simulate_network(seed = 1)

pal_type <- c(metabolite = "#B2182B", mRNA = "#EF8A62",
              `phospho-protein` = "#67A9CF", protein = "#1B9E77")
pal_type <- plotworks_discrete_values(pal_type)
edge_cols <- plotworks_continuous_values(c("#FCBBA1", "#67000D"), n = 11)

set.seed(11)                                   # fix the force layout
p <- ggraph(g, layout = "fr") +
  geom_edge_link(aes(colour = correlation), width = 0.3, alpha = 0.7) +
  geom_node_point(aes(fill = type), shape = 21, size = 2.6, stroke = 0.2,
                  colour = "grey30") +
  geom_node_text(aes(label = name), size = 1.5, repel = TRUE,
                 max.overlaps = Inf, seed = 11, box.padding = 0.25,
                 point.padding = 0.1, force = 3, segment.size = 0.15,
                 segment.colour = "grey70", bg.color = "white",
                 bg.r = 0.08) +
  scale_edge_colour_gradientn(colours = edge_cols,
                             name = "Correlation",
                             breaks = c(0.5, 0.6, 0.7, 0.8, 0.9)) +
  scale_fill_manual(values = pal_type, name = "Type") +
  labs(title = "Module interaction network") +
  theme_void(base_size = 11) +
  theme(plot.title = element_text(face = "bold", hjust = 0.5),
        legend.position = "right")

save_case(p, adk_output_path("cases/11-module-network/figures/module_network.png"),
          width = 9, height = 7)
message("Case 11 rendered: ", vcount(g), " nodes, ", ecount(g), " edges")
