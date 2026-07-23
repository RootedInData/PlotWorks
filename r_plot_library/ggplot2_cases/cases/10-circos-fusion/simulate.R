# cases/10-circos-fusion/simulate.R
# Case 10 - Circos fusion genes. Genomic loci of fusion partners plus the pairs
# that fuse. Base R only (deterministic loci; a seed is accepted for interface
# consistency).

# hg19 chromosome lengths (bp), used to lay out the ideogram offline.
hg19_lengths <- function() {
  c(chr1=249250621, chr2=243199373, chr3=198022430, chr4=191154276,
    chr5=180915260, chr6=171115067, chr7=159138663, chr8=146364022,
    chr9=141213431, chr10=135534747, chr11=135006516, chr12=133851895,
    chr13=115169878, chr14=107349540, chr15=102531392, chr16=90354753,
    chr17=81195210, chr18=78077248, chr19=59128983, chr20=63025520,
    chr21=48129895, chr22=51304566, chrX=155270560, chrY=59373566)
}

simulate_fusions <- function(seed = 1) {
  # gene loci (chr, approx bp)
  loci <- rbind(
    data.frame(gene="TFE3",    chr="chrX",  pos=48.9e6),
    data.frame(gene="TFEB",    chr="chr6",  pos=41.6e6),
    data.frame(gene="SFPQ",    chr="chr1",  pos=35.6e6),
    data.frame(gene="PRCC",    chr="chr1",  pos=156.7e6),
    data.frame(gene="NONO",    chr="chrX",  pos=70.5e6),
    data.frame(gene="ASPSCR1", chr="chr17", pos=79.7e6),
    data.frame(gene="CLTC",    chr="chr17", pos=57.7e6),
    data.frame(gene="MALAT1",  chr="chr11", pos=65.5e6),
    data.frame(gene="PARP14",  chr="chr3",  pos=122.3e6),
    data.frame(gene="EIF4A2",  chr="chr3",  pos=186.5e6),
    data.frame(gene="MATR3",   chr="chr5",  pos=138.6e6),
    data.frame(gene="ACTB",    chr="chr7",  pos=5.5e6),
    data.frame(gene="PTPN12",  chr="chr7",  pos=77.4e6),
    data.frame(gene="VCP",     chr="chr9",  pos=35.0e6),
    data.frame(gene="NR2F1",   chr="chr5",  pos=92.9e6),
    data.frame(gene="U2AF2",   chr="chr19", pos=56.2e6),
    data.frame(gene="LUC7L3",  chr="chr17", pos=50.7e6),
    data.frame(gene="ZNF687",  chr="chr1",  pos=151.3e6),
    data.frame(gene="KHSRP",   chr="chr19", pos=6.4e6),
    data.frame(gene="DVL2",    chr="chr17", pos=7.1e6),
    stringsAsFactors = FALSE)

  # fusion pairs: TFE3 partners (red), TFEB partners (green)
  pairs <- rbind(
    data.frame(a="SFPQ",   b="TFE3", grp="TFE3"),
    data.frame(a="PRCC",   b="TFE3", grp="TFE3"),
    data.frame(a="NONO",   b="TFE3", grp="TFE3"),
    data.frame(a="ASPSCR1",b="TFE3", grp="TFE3"),
    data.frame(a="CLTC",   b="TFE3", grp="TFE3"),
    data.frame(a="LUC7L3", b="TFE3", grp="TFE3"),
    data.frame(a="MALAT1", b="TFEB", grp="TFEB"),
    data.frame(a="ACTB",   b="TFEB", grp="TFEB"),
    data.frame(a="PARP14", b="TFEB", grp="TFEB"),
    data.frame(a="EIF4A2", b="TFEB", grp="TFEB"),
    data.frame(a="MATR3",  b="TFEB", grp="TFEB"),
    stringsAsFactors = FALSE)

  list(loci = loci, pairs = pairs)
}
