plotworks_humanize_label <- function(x) {
  x <- gsub("([a-z0-9])([A-Z])", "\\1 \\2", x)
  x <- gsub("[_\\.-]+", " ", x)
  x <- trimws(gsub("\\s+", " ", x))
  paste0(toupper(substr(x, 1, 1)), substr(x, 2, nchar(x)))
}

plotworks_significance_label <- function(p) {
  ifelse(
    is.na(p), "",
    ifelse(p < 0.001, "***", ifelse(p < 0.01, "**", ifelse(p < 0.05, "*", "ns")))
  )
}
