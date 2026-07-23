# cases/12-sankey-bubble/simulate.R
# Case 12 - Combined Sankey + bubble. Metabolites map to enriched pathways
# (Sankey), and each pathway carries an enrichment bubble (-log10 P, count,
# hit ratio). Base R only.

simulate_enrichment <- function(seed = 1) {
  set.seed(seed)
  pathways <- c("Purine metabolism", "Glycerophospholipid metabolism",
    "Arginine and proline metabolism",
    "Alanine, aspartate and glutamate metabolism", "Citrate cycle (TCA cycle)",
    "Pentose phosphate pathway", "Sphingolipid metabolism",
    "beta-Alanine metabolism", "Arginine biosynthesis",
    "D-Glutamine and D-glutamate metabolism",
    "Taurine and hypotaurine metabolism",
    "Phenylalanine, tyrosine and tryptophan biosynthesis")

  metabolites <- c("L-Glutamate","Pyruvate","2-Oxoglutarate","Spermine",
    "Spermidine","GMP","Xanthosine","Deoxyinosine","AMP","ATP","GDP","Choline",
    "Phosphocholine","Phosphatidylcholine","L-Proline","Citrate","Isocitrate",
    "N-Acetyl-L-aspartate","Phosphoenolpyruvate","Sedoheptulose 7-phosphate",
    "Galactosylceramide","Sphingomyelin","Carnosine","L-Citrulline",
    "D-Glutamine","Taurine","L-Tyrosine","Acetylcholine","Deoxyguanosine",
    "GDP-ethanolamine","Adenylyl sulfate","Creatine","N-Acylsphingosine")

  # each metabolite maps to one pathway
  links <- data.frame(
    metabolite = metabolites,
    pathway = sample(pathways, length(metabolites), replace = TRUE),
    freq = 1, stringsAsFactors = FALSE)

  bubble <- data.frame(
    pathway   = pathways,
    neglogP   = runif(length(pathways), 1.2, 5.5),
    count     = sample(2:8, length(pathways), replace = TRUE),
    hit_ratio = runif(length(pathways), 0.1, 0.5),
    stringsAsFactors = FALSE)

  list(links = links, bubble = bubble, pathways = pathways)
}
