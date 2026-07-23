# cases/18-treemap/simulate.R
# Case 18 - Treemap. Anti-phage defence systems grouped by mechanism category,
# sized by abundance. Base R only.

simulate_defensome <- function(seed = 1) {
  set.seed(seed)
  cat_systems <- list(
    "Nucleic acid degrading" = c("CasFinder","RM","Wadjet","RloC","Lamassu",
      "Hachiman","Nhi"),
    "Diverse" = c("CBASS","Retron","AbiD","BREX","PD-T7-2","Paris","Septu",
      "SoFIC","AbiE","MazEF","Shedu","SanaTA","AbiU","DRT","Hma","Rst"),
    "Membrane displacing" = c("Gabija","CapRel","DarTG","PrrC","Avs"),
    "Nucleotide modifying" = c("pAgo","ABC","SEFIR"),
    "Effector" = c("Thoeris","Dsr","Pycsar"),
    "Unknown" = c("DUF","Uncharacterised1","Uncharacterised2"))

  rows <- do.call(rbind, lapply(names(cat_systems), function(ct) {
    sys <- cat_systems[[ct]]
    data.frame(category = ct, system = sys,
               n = round(runif(length(sys), 3, 60)^1.4), stringsAsFactors = FALSE)
  }))
  # make a couple of dominant systems, as in real defensome treemaps
  rows$n[rows$system == "CasFinder"] <- 900
  rows$n[rows$system == "RM"] <- 650
  rows
}
