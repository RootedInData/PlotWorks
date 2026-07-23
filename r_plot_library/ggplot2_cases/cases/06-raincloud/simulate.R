# cases/06-raincloud/simulate.R
# Case 6 - Raincloud (advanced). Leaf-out date for four tree species in rural
# vs urban environments. Base R only.

simulate_leafout <- function(seed = 1, per = 40) {
  set.seed(seed)
  species <- c("Ginkgo", "Acer", "Fraxinus", "Platanus")
  # environment mean leaf-out day; urban leafs out earlier (warmer city)
  env_mu <- c(Rural = 123, Urban = 110)
  sp_off <- c(Ginkgo = 3, Acer = -2, Fraxinus = 1, Platanus = -3)

  grid <- expand.grid(environment = names(env_mu), species = species,
                      stringsAsFactors = FALSE)
  rows <- lapply(seq_len(nrow(grid)), function(i) {
    mu <- env_mu[grid$environment[i]] + sp_off[grid$species[i]]
    data.frame(environment = grid$environment[i], species = grid$species[i],
               leafout = rnorm(per, mu, 6), stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  out$environment <- factor(out$environment, levels = c("Rural", "Urban"))
  out$species <- factor(out$species, levels = species)
  out
}
