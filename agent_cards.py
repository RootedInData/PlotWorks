AGENT_CARDS = """
Available specialist agents in the Data Analysis Agency:

1. DataIntakeAgent
   Use for: locating datasets, checking whether a file loads, identifying file type,
   inspecting columns, data types, shape, missingness, duplicates, and sample values.
   Tools: list_available_datasets, inspect_dataset.

2. EDAAgent
   Use for: deterministic exploratory data analysis with pandas, including summary
   statistics, categorical summaries, missingness, correlations, and outlier checks.
   Tools: run_eda.

3. VisualizationAgent
   Use for: generating basic local charts from the dataset and returning saved file paths.
   Tools: create_basic_charts.

4. CodePlanningAgent
   Use for: writing a safe analysis plan or Python/pandas code skeleton for a task.
   This agent writes code as a plan of action; it does not execute arbitrary user code.
   Tools: none.

5. ReportAgent
   Use for: synthesizing specialist outputs into a clear final report for the user.
   Tools: save_markdown_report.

6. MethodResearchAgent
   Use for: optional external research about statistical methods, packages, or analysis
   conventions. Only available when ENABLE_WEB_SEARCH=true.
   Tools: configured search provider tools.
"""
