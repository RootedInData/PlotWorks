#!/usr/bin/env Rscript
# scripts/run_all.R
# Render every case in its own R process and report a pass/fail table.
# Run from the gallery root: Rscript scripts/run_all.R

scripts <- sort(Sys.glob(file.path("cases", "*", "plot.R")))
if (length(scripts) == 0) stop("Run from the gallery root.")

cat("Rendering", length(scripts), "cases...\n\n")
results <- lapply(scripts, function(s) {
  figdir <- file.path(dirname(s), "figures")
  t0 <- Sys.time()
  out <- suppressWarnings(system2("Rscript",
    c("-e", shQuote(sprintf('source("%s")', s))),
    stdout = TRUE, stderr = TRUE))
  status <- attr(out, "status"); status <- if (is.null(status)) 0L else status
  pngs <- Sys.glob(file.path(figdir, "*.png"))
  fresh <- pngs[file.info(pngs)$mtime >= t0]
  big <- fresh[file.info(fresh)$size >= 20 * 1024]
  pass <- status == 0L && length(big) >= 1
  cat(sprintf("[%s] %-32s %s\n", if (pass) "OK  " else "FAIL",
              basename(dirname(s)),
              if (pass) sprintf("%d fig", length(big)) else
                paste(utils::tail(out, 1), collapse = " ")))
  pass
})

n_fail <- sum(!unlist(results))
cat(sprintf("\n%d ok, %d failed\n", sum(unlist(results)), n_fail))
if (n_fail > 0) quit(status = 1)
