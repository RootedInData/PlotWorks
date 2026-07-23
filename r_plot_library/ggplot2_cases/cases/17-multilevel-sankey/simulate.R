# cases/17-multilevel-sankey/simulate.R
# Case 17 - Multi-level Sankey. Sample records flowing Global -> Continent ->
# Land cover -> Habitat. Base R only.

simulate_biogeo <- function(seed = 1, n = 700) {
  set.seed(seed)
  continent <- c("North America","Europe","Asia","Australia","South America",
    "Antarctica","Africa","Pacific Ocean","Atlantic Ocean","Arctic Ocean",
    "Indian Ocean")
  land <- c("forest","grassland","cropland","aquatic","desert","woodland",
    "shrubland","tundra","wetland","urban","mangrove")
  habitat <- c("soil","shoot","root","rhizosphere","deadwood","air","sediment",
    "litter","lichen","water","topsoil","dust")

  rec <- data.frame(
    Global = "Global",
    Continent = sample(continent, n, replace = TRUE,
                       prob = c(18,16,16,8,10,3,9,5,5,3,4)),
    LandCoverType = sample(land, n, replace = TRUE,
                       prob = c(20,14,12,8,7,6,6,5,6,4,4)),
    Habitat = sample(habitat, n, replace = TRUE,
                       prob = c(22,10,9,8,5,4,6,6,4,7,6,3)),
    stringsAsFactors = FALSE)

  agg <- aggregate(list(freq = rep(1, nrow(rec))),
                   rec[c("Global","Continent","LandCoverType","Habitat")],
                   FUN = length)
  agg$Continent <- factor(agg$Continent, levels = continent)
  agg$LandCoverType <- factor(agg$LandCoverType, levels = land)
  agg$Habitat <- factor(agg$Habitat, levels = habitat)
  agg
}
