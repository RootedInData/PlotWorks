# cases/10-circos-fusion/plot.R
# Case 10 - Circos fusion-gene plot (circlize). Run from gallery root.

library(circlize)
source("R/adk_data_bridge.R")
source("cases/10-circos-fusion/simulate.R")

sim  <- simulate_fusions(seed = 1)
lens <- hg19_lengths()
loci <- sim$loci
pairs <- sim$pairs

chr_df <- data.frame(chr = names(lens), start = 0, end = as.numeric(lens),
                     stringsAsFactors = FALSE)

# gene-label bed (outside labels)
gene_bed <- data.frame(chr = loci$chr, start = loci$pos, end = loci$pos + 1e5,
                       gene = loci$gene, stringsAsFactors = FALSE)

pal <- c(TFE3 = "#C0392B", TFEB = "#2E8B57")

png(adk_output_path("cases/10-circos-fusion/figures/circos_fusion.png"),
    width = 2200, height = 2200, res = 300)

circos.clear()
circos.par(gap.degree = 1, start.degree = 90, cell.padding = c(0, 0, 0, 0))
circos.genomicInitialize(chr_df, plotType = NULL)

# outside gene labels with connector lines
circos.genomicLabels(gene_bed, labels.column = 4, side = "outside",
                     cex = 0.55, connection_height = mm_h(4),
                     line_lwd = 0.6)

# chromosome ideogram band track
circos.track(ylim = c(0, 1), track.height = 0.06, bg.border = NA,
  panel.fun = function(x, y) {
    circos.rect(CELL_META$xlim[1], 0, CELL_META$xlim[2], 1,
                col = "grey85", border = "grey40", lwd = 0.5)
    circos.text(CELL_META$xcenter, 1.9,
                gsub("chr", "", CELL_META$sector.index),
                cex = 0.5, facing = "clockwise", niceFacing = TRUE)
  })

# fusion links
xy <- function(g) loci[loci$gene == g, c("chr", "pos")]
for (i in seq_len(nrow(pairs))) {
  a <- xy(pairs$a[i]); b <- xy(pairs$b[i])
  circos.link(a$chr, a$pos, b$chr, b$pos,
              col = pal[[pairs$grp[i]]], lwd = 1.6, h.ratio = 0.6)
}

legend("center", legend = names(pal), col = pal, lwd = 2, bty = "n",
       title = "Fusion partner", cex = 0.8)
title("Fusion-gene Circos", cex.main = 1)
dev.off()
circos.clear()
cat("Case 10 rendered:", nrow(pairs), "fusions\n")
