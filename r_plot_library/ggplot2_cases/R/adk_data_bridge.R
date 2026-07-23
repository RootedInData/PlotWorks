# R/adk_data_bridge.R
# Small ADK bridge for approved ggplot2 case recipes.
# This file allows a case to use user-supplied standardized CSV/TSV input when
# ADK_INPUT_PATH is set, or fall back to the case's existing simulated data.

adk_read_table <- function(path) {
  if (!nzchar(path) || !file.exists(path)) {
    stop(paste0("ADK input file does not exist: ", path))
  }
  lower <- tolower(path)
  if (grepl("\\.(tsv|tab|bed)(\\.gz)?$", lower)) {
    read.delim(path, stringsAsFactors = FALSE, check.names = FALSE)
  } else {
    read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  }
}

adk_load_or_simulate <- function(case_id, default) {
  input_path <- Sys.getenv("ADK_INPUT_PATH", "")
  if (nzchar(input_path)) {
    message("ADK input detected for ", case_id, ": ", input_path)
    return(adk_read_table(input_path))
  }
  default
}

adk_output_path <- function(default_path) {
  output_path <- Sys.getenv("ADK_OUTPUT_PATH", "")
  output_dir <- Sys.getenv("ADK_OUTPUT_DIR", "")

  if (!nzchar(output_path) && !nzchar(output_dir)) {
    return(default_path)
  }

  if (nzchar(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  }

  # Multi-output cases should keep their distinct default basenames while using
  # ADK_OUTPUT_DIR. Single-output cases can use ADK_OUTPUT_PATH directly.
  if (nzchar(output_path)) {
    default_base <- basename(default_path)
    output_base <- basename(output_path)
    if (!identical(default_base, output_base) && nzchar(output_dir)) {
      return(file.path(output_dir, default_base))
    }
    return(output_path)
  }

  file.path(output_dir, basename(default_path))
}
