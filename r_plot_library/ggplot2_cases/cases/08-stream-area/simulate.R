# cases/08-stream-area/simulate.R
# Case 8 - Individualized area plot. Left: random-forest importance (Mean
# Decrease Accuracy) per taxon, coloured by phylum. Right: each taxon's
# abundance stream across sampling days D1..D6. Base R only.

simulate_stream <- function(seed = 1, n_time = 90) {
  set.seed(seed)
  taxa <- c("unclassified_Peptostreptococcales", "Permianibacter",
            "Xanthobacter", "Giesbergeria", "Sphingobium", "GCA_003244245",
            "Actinophytocola", "Azospira", "CAJAWW01", "UBA2250",
            "Hydrogenophaga", "FEB_7", "unclassified_Rhodocyclaceae",
            "Aquabacterium", "Paucimonas", "Alipia")
  phylum <- sample(c("Actinobacteriota", "Firmicutes", "Proteobacteria"),
                   length(taxa), replace = TRUE, prob = c(0.3, 0.25, 0.45))

  mda <- sort(runif(length(taxa), 1, 16), decreasing = TRUE)
  bars <- data.frame(taxon = taxa, phylum = phylum, mda = mda,
                     stringsAsFactors = FALSE)

  # abundance stream per taxon: a smoothed positive random walk with a few
  # peaks, distinct per taxon.
  smooth <- function(x, k = 5) stats::filter(x, rep(1 / k, k), circular = TRUE)
  series <- do.call(rbind, lapply(seq_along(taxa), function(i) {
    v <- abs(as.numeric(smooth(cumsum(rnorm(n_time)) + rnorm(n_time, 0, 2))))
    v <- v / max(v)
    data.frame(taxon = taxa[i], phylum = phylum[i],
               t = seq_len(n_time), value = v, stringsAsFactors = FALSE)
  }))

  list(bars = bars, series = series, taxa = taxa)
}
