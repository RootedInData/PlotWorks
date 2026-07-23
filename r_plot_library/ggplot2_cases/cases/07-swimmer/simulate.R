# cases/07-swimmer/simulate.R
# Case 7 - Swimmer plot. One row per NSCLC patient: time on study (weeks), best
# response, and event markers (ongoing treatment, progression, radiotherapy).
# Base R only.

simulate_swimmer <- function(seed = 1, n = 24) {
  set.seed(seed)
  resp_levels <- c("CR", "PR", "SD", "Tumour shrinkage", "PD")

  response <- sample(resp_levels, n, replace = TRUE,
                     prob = c(0.10, 0.18, 0.25, 0.17, 0.30))
  # responders stay on study longer
  base_wk <- c(CR = 70, PR = 55, SD = 30, `Tumour shrinkage` = 26, PD = 10)
  weeks <- pmax(4, round(base_wk[response] + rnorm(n, 0, 12)))

  ongoing <- response %in% c("CR", "PR") & runif(n) < 0.6
  progression <- response %in% c("SD", "PD", "Tumour shrinkage") & runif(n) < 0.8
  rt <- runif(n) < 0.18
  rt_week <- ifelse(rt, pmax(4, round(weeks * runif(n, 0.3, 0.8))), NA)

  data.frame(
    patient = paste0("P", sprintf("%02d", seq_len(n))),
    response = factor(response, levels = resp_levels),
    weeks = as.numeric(weeks),
    ongoing = ongoing, progression = progression,
    rt = rt, rt_week = rt_week, stringsAsFactors = FALSE)
}
