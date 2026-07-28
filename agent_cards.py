AGENT_CARDS = """
Available specialist agents in the Data Analysis Agency:

1. DataIntakeAgent
   Use for: locating and inspecting datasets, including CSV, TSV, Excel, JSON,
   text, DATA, BED, and BED.GZ files.
   Tools: list_available_datasets, inspect_dataset, infer_bed_chrom_sizes.

2. EDAAgent
   Use for: deterministic pandas-based descriptive statistics, missingness,
   categorical summaries, correlations, outlier checks, and BED summaries.
   Tools: run_eda.

3. VisualizationPlannerAgent
   Use for: deciding whether a request is best served by an approved R recipe,
   a reusable pretty_* Python function, or experimental custom R plotting.
   Tools: recommend_visualization_plan, list_pretty_plot_functions,
   match_ggplot2_cases_to_dataset.

4. VisualizationAgent
   Use for: polished deterministic Python figures with shared palettes, labels,
   legends, sizing, and export settings.
   Tools: create_pretty_charts, pretty_histogram, pretty_barplot,
   pretty_scatter, pretty_lineplot, pretty_boxplot, pretty_violin,
   pretty_heatmap, pretty_faceted_plot, pretty_manhattan,
   pretty_genomic_track.

5. ColumnDecoderAgent
   Use for: mapping inconsistent real-world column names to expected plotting roles
   and identifying compatible approved ggplot2 recipes.
   Tools: decode_column_roles, match_ggplot2_cases_to_dataset.

6. PublicationPlotAgent
   Use for: approved predefined ggplot2 recipes, their simulated previews, R setup
   checks, path validation, and direct real-data adapters where implemented.
   Tools: list_ggplot2_cases, check_publication_plot_setup,
   validate_publication_plot_paths, render_ggplot2_case,
   render_ggplot2_case_demo, render_all_ggplot2_case_demos.

7. RPlotDeveloperAgent
   Use for: experimental new R/ggplot2 figures when no approved recipe fits and R
   offers a meaningful advantage. Generated code is limited to a build_plot(data)
   function and is validated before controlled execution.
   Tools: validate_generated_r_plot_code, execute_generated_r_plot.

8. PlotReviewAgent
   Use for: deterministic checks that a raster figure exists, has useful dimensions,
   is non-empty, and is not nearly blank. Human review is still required for
   scientific and aesthetic judgment.
   Tools: review_plot_file.

9. CodePlanningAgent
   Use for: safe reproducible Python or R analysis plans and non-executed code
   skeletons.
   Tools: none.

10. ReportAgent
    Use for: synthesizing specialist results and saving Markdown reports.
    Tools: save_markdown_report.

11. MethodResearchAgent
    Use for: optional external research about methods, packages, or conventions when
    ENABLE_WEB_SEARCH=true.
    Tools: configured search-provider tools.
"""
