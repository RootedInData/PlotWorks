# cases/13-discrete-heatmap/simulate.R
# Case 13 - Discrete heatmap. Resistance ratio RR(AUC) of Candida strains to
# antifungals, binned into fold-change categories, plus a strain annotation
# table (clade, strain, variant, ERG gene). Base R only.

simulate_rr <- function(seed = 1) {
  set.seed(seed)
  drugs <- c("AMB", "POS", "FLU", "MCF", "CAS", "ANF", "5FC", "GEL")

  ann <- rbind(
    data.frame(clade="I",  strain=1,  variant="M504I",       erg="ERG11"),
    data.frame(clade="I",  strain=2,  variant="E165*(T308M)",erg="ERG11(+ERG3)"),
    data.frame(clade="I",  strain=3,  variant="R318",        erg="ERG6"),
    data.frame(clade="I",  strain=4,  variant="Y177*",       erg="ERG6"),
    data.frame(clade="I",  strain=5,  variant="Q587*",       erg="NCP1"),
    data.frame(clade="I",  strain=6,  variant="T451fs",      erg="NCP1"),
    data.frame(clade="III",strain=7,  variant="T369M(G108*)",erg="ERG11(+ERG3)"),
    data.frame(clade="III",strain=8,  variant="M306I",       erg="ERG11"),
    data.frame(clade="III",strain=9,  variant="Transl.",     erg="NCP1"),
    data.frame(clade="III",strain=10, variant="K234_D236del",erg="ERG6"),
    data.frame(clade="III",strain=11, variant="Q368*",       erg="NCP1"),
    data.frame(clade="III",strain=12, variant="E86fs",       erg="ERG6"),
    data.frame(clade="IV", strain=13, variant="E311fs",      erg="ERG6"),
    data.frame(clade="IV", strain=14, variant="E329*",       erg="ERG6"),
    data.frame(clade="IV", strain=15, variant="R100fs",      erg="ERG6"),
    data.frame(clade="IV", strain=16, variant="E18Q",        erg="ERG12"),
    data.frame(clade="IV", strain=17, variant="R983S",       erg="HMG1"),
    data.frame(clade="IV", strain=18, variant="T244N",       erg="ERG10"),
    data.frame(clade="II", strain=19, variant="E429*(W182*)",erg="ERG11(+ERG3)"),
    stringsAsFactors = FALSE)

  # RR(AUC): mostly modest, a few strongly resistant (>8) or hypersensitive.
  vals <- expand.grid(strain = ann$strain, drug = drugs,
                      stringsAsFactors = FALSE)
  vals$rr <- round(10^rnorm(nrow(vals), mean = 0, sd = 0.55), 2)
  # inject some strong resistances and a few sensitivities
  vals$rr[sample(nrow(vals), 12)] <- round(runif(12, 8, 20), 2)
  vals$rr[sample(nrow(vals), 20)] <- round(runif(20, 0.03, 0.12), 2)

  brk <- c(0, 0.06, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16, Inf)
  lab <- c("<0.06","0.06-0.125","0.125-0.25","0.25-0.5","0.5-1","1-2","2-4",
           "4-8","8-16",">16")
  vals$cat <- cut(vals$rr, breaks = brk, labels = lab, right = FALSE)

  list(vals = vals, ann = ann, drugs = drugs,
       cat_levels = rev(lab))            # high -> low for the legend
}
