AGENT_CARDS = """
Available specialist agents in the Data Analysis Agency:

1. DataIntakeAgent
   Use for: locating datasets, checking whether a file loads, identifying file type,
   inspecting columns, data types, shape, missingness, duplicates, sample values,
   and recognizing common data formats including CSV, TSV, Excel, JSON, TXT, DATA,
   and BED genomic interval files.
   Tools: list_available_datasets, inspect_dataset, infer_bed_chrom_sizes.

2. EDAAgent
   Use for: deterministic exploratory data analysis with pandas, including summary
   statistics, categorical summaries, missingness, correlations, outlier checks,
   and BED interval summaries when applicable.
   Tools: run_eda.

3. VisualizationAgent
   Use for: generating basic exploratory charts from the dataset and returning saved
   file paths. Use for simple histograms and top-value bar charts.
   Tools: create_basic_charts.

4. ColumnDecoderAgent
   Use for: matching real dataset columns to expected plot recipe columns. This is
   especially important when column names vary, such as start, Start, chrom_start,
   and chromStart. The agent should surface uncertain mappings instead of pretending
   that every mapping is certain.
   Tools: decode_column_roles, match_ggplot2_cases_to_dataset.

5. PublicationPlotAgent
   Use for: listing approved ggplot2 publication-style plot cases, checking R setup,
   validating R/Python path readability, and rendering approved plot recipes. It can
   render demo plots from simulated data, and it can render real-data plots only when
   the data can be mapped to a supported recipe.
   Tools: list_ggplot2_cases, check_publication_plot_setup,
   validate_publication_plot_paths, render_ggplot2_case, render_ggplot2_case_demo.

6. CodePlanningAgent
   Use for: writing a safe analysis plan or Python/pandas/R code skeleton for a task.
   This agent writes code as a plan of action; it does not execute arbitrary user code.
   Tools: none.

7. ReportAgent
   Use for: synthesizing specialist outputs into a clear final report for the user.
   Tools: save_markdown_report.

8. MethodResearchAgent
   Use for: optional external research about statistical methods, packages, or analysis
   conventions. Only available when ENABLE_WEB_SEARCH=true.
   Tools: configured search provider tools.
"""
