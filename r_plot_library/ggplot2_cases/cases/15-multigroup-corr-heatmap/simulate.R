# cases/15-multigroup-corr-heatmap/simulate.R
# Case 15 - Multi-group correlation heatmap. Correlations between many taxa
# (organised in row groups) and community biomass / carbon-flux variables, drawn
# as in-cell mini bars. Base R only.

simulate_corr_grid <- function(seed = 1) {
  set.seed(seed)
  rows <- list(
    "richness" = c("Protist_richness","Fungi_richness","Bacteria_richness"),
    "Bacterial phyla" = c("Verrucomicrobia","Planctomycetes","Nitrospirae",
      "Gemmatimonadetes","Gammaproteobacteria","Firmicutes",
      "Deltaproteobacteria","Chloroflexi","Chlamydiae","Betaproteobacteria",
      "Bacteroidetes","Alphaproteobacteria","Actinobacteria","Acidobacteria"),
    "Fungal phyla" = c("Mortierellomycota","Basidiomycota","Ascomycota"),
    "Fungal guilds" = c("Saprotroph","Pathogen","AM_Fungi"),
    "Protistan lineages" = c("Ochrophyta","Lobosa","Conosa","Ciliophora",
      "Cercozoa"),
    "Protistan trophic groups" = c("Phototroph","Parasite","Consumer"))

  taxa <- data.frame(
    taxon = unlist(rows, use.names = FALSE),
    group = rep(names(rows), lengths(rows)), stringsAsFactors = FALSE)

  cols <- data.frame(
    col = c("Bacterial","F:B ratio","Fungi","Microbial",
            "ER","GPP","HR","NEE","SR"),
    super = c(rep("Biomass", 4), rep("Carbon flux", 5)),
    stringsAsFactors = FALSE)

  grid <- expand.grid(taxon = taxa$taxon, col = cols$col,
                      stringsAsFactors = FALSE)
  grid$r <- round(runif(nrow(grid), -0.25, 0.35), 2)

  list(grid = grid, taxa = taxa, cols = cols,
       row_groups = names(rows))
}
