# cases/04-manhattan-twas/simulate.R
# Case 4 - Manhattan plot for a TWAS across 29 chromosomes. Columns SNP/gene,
# CHR, BP, P. Base R only. Dense null cloud plus injected gene-level peaks.

simulate_twas <- function(seed = 1, n_chr = 29, per_min = 300, per_max = 1200,
                          n_peaks = 30) {
  set.seed(seed)
  syms <- c("RBMBA","LOC102039","PET100","ATP5ME","LUZP6","CIART","SEC61B",
            "ZUP1","NFXN3","LOC101902301","LOC112441655","EIF6B","CHCHD7",
            "FAM161A","ZNF706","DEGS1","CQ7O6","CQYBB1","SNURF","NOVA1","PBX2",
            "FUS","FAU","CSNK2B","MARVELD1","CRL1","TAF15","ACADVL","CAPN15",
            "COMMD9")

  per <- sample(per_min:per_max, n_chr, replace = TRUE)
  chr <- rep(seq_len(n_chr), times = per)
  bp  <- unlist(lapply(per, function(m) sort(runif(m, 1, 1e8))))
  n   <- length(chr)

  # Null association p-values, then lift a random set of genes into peaks.
  neglogp <- -log10(runif(n))
  gene <- rep(NA_character_, n)
  peak_idx <- sort(sample(n, n_peaks))
  neglogp[peak_idx] <- runif(n_peaks, 8, 30)
  # add a few flanking points around each peak so hits are not lone spikes
  for (i in peak_idx) {
    nb <- intersect((i - 3):(i + 3), seq_len(n))
    nb <- nb[chr[nb] == chr[i]]
    neglogp[nb] <- pmax(neglogp[nb], neglogp[i] * runif(length(nb), 0.4, 0.8))
  }
  gene[peak_idx] <- sample(syms, n_peaks, replace = TRUE)

  data.frame(gene = gene, CHR = chr, BP = bp, P = 10^(-neglogp),
             stringsAsFactors = FALSE)
}
