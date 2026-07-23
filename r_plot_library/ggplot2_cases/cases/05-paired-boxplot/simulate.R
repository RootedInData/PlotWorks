# cases/05-paired-boxplot/simulate.R
# Case 5 - Paired boxplot. Minimum inhibitory concentration (MIC) of paired
# isolates, control vs a recent antibiotic, faceted by drug and coloured by
# antibiotic class. Base R only.

simulate_mic <- function(seed = 1, n_iso = 30) {
  set.seed(seed)

  # drug, class, direction of the shift, and significance label.
  spec <- rbind(
    data.frame(drug="APR", class="AMIN", dir="ns",   sig="ns",   shift= 0.0),
    data.frame(drug="SUO", class="CARB", dir="ns",   sig="ns",   shift= 0.2),
    data.frame(drug="CID", class="CEPH", dir="down", sig="****",  shift=-2.2),
    data.frame(drug="CTO", class="CEPH", dir="ns",   sig="ns",   shift=-0.3),
    data.frame(drug="POL", class="MEMB", dir="up",   sig="****",  shift= 2.0),
    data.frame(drug="SCH", class="MEMB", dir="up",   sig="****",  shift= 2.3),
    data.frame(drug="SPR", class="MEMB", dir="up",   sig="**",    shift= 1.4),
    data.frame(drug="TRD", class="MEMB", dir="up",   sig="****",  shift= 2.1),
    data.frame(drug="ERA", class="TETR", dir="down", sig="****",  shift=-1.8),
    data.frame(drug="OMA", class="TETR", dir="down", sig="***",   shift=-1.5),
    data.frame(drug="DEL", class="TOPO", dir="up",   sig="*",     shift= 1.0),
    data.frame(drug="GEP", class="TOPO", dir="ns",   sig="ns",   shift= 0.1),
    data.frame(drug="ZOL", class="TOPO", dir="up",   sig="****",  shift= 2.4),
    stringsAsFactors = FALSE
  )

  rows <- lapply(seq_len(nrow(spec)), function(i) {
    ctrl <- rnorm(n_iso, 0, 1)                    # log10 control MIC per isolate
    trt  <- ctrl + spec$shift[i] + rnorm(n_iso, 0, 0.5)
    updown <- ifelse(trt >= ctrl, "up", "down")   # per-isolate direction
    data.frame(
      drug = spec$drug[i], class = spec$class[i], sig = spec$sig[i],
      isolate = seq_len(n_iso),
      condition = rep(c("control", spec$drug[i]), each = n_iso),
      log10_mic = c(ctrl, trt),
      updown = rep(updown, 2), stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  out$mic <- 10^out$log10_mic
  out$class <- factor(out$class,
                      levels = c("AMIN","CARB","CEPH","MEMB","TETR","TOPO"))
  out
}
