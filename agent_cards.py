AGENT_CARDS = """
Available specialist agents in PlotWorks:

1. DataIntakeAgent
   Use for: locating and inspecting source or PlotWorks-managed transformed datasets,
   including CSV, TSV, Excel, JSON, text, DATA, BED, and BED.GZ files.
   Tools: list_available_datasets, inspect_dataset, infer_bed_chrom_sizes.

2. EDAAgent
   Use for: deterministic pandas-based descriptive statistics, missingness,
   categorical summaries, correlations, outlier checks, and BED summaries.
   Tools: run_eda.

3. DataTransformationAgent
   Use for: preparing and validating plot-ready data proposals without altering or
   saving the original dataset. Prefer deterministic operations; use generated Python
   only for unforeseen cases. It returns exact arguments to PlotWorksSupervisor.
   Tools: list_data_transformation_operations, preview_data_transformations,
   validate_generated_python_transform_code.

   Root-level confirmed actions owned by PlotWorksSupervisor:
   save_data_transformations, execute_generated_python_transform.

4. VisualizationPlannerAgent
   Use for: deciding whether a request is best served by an approved R recipe,
   a reusable pretty_* Python function, a novel static R plot, or an animation.
   Tools: recommend_visualization_plan, list_pretty_plot_functions,
   match_ggplot2_cases_to_dataset.

5. VisualizationAgent
   Use for: polished deterministic Python figures with shared palettes, labels,
   legends, sizing, and export settings.
   Tools: create_pretty_charts, pretty_histogram, pretty_barplot,
   pretty_scatter, pretty_lineplot, pretty_boxplot, pretty_violin,
   pretty_heatmap, pretty_faceted_plot, pretty_manhattan,
   pretty_genomic_track.

6. ColumnDecoderAgent
   Use for: mapping inconsistent real-world column names to expected plotting roles
   and identifying compatible approved ggplot2 recipes.
   Tools: decode_column_roles, match_ggplot2_cases_to_dataset.

7. PublicationPlotAgent
   Use for: approved predefined ggplot2 recipes, shared palette providers,
   simulated previews, palette variants, confirmed case defaults,
   R setup checks, path validation, and direct real-data adapters where implemented.
   Tools: list_ggplot2_cases, list_plot_palettes, check_publication_plot_setup,
   validate_publication_plot_paths, render_ggplot2_case,
   render_ggplot2_case_demo, render_all_ggplot2_case_demos.
   The confirmed set_ggplot2_case_palette_default action is owned by the supervisor.

8. RPlotDeveloperAgent
   Use for: new static R/ggplot2 figures when no approved recipe fits.
   Generated code is limited to build_plot(data) and validated before execution.
   It returns the validated proposal to the supervisor.
   Tools: validate_generated_r_plot_code.
   The confirmed execute_generated_r_plot action is owned by the supervisor.

9. AnimationDeveloperAgent
   Use for: controlled animated scatter plots and custom gganimate figures. Transform the data first when the animation needs a plot-ready table.
   Tools: check_animation_setup, render_animated_scatter,
   validate_generated_r_animation_code.
   The confirmed execute_generated_r_animation action is owned by the supervisor.

10. PlotReviewAgent
    Use for: deterministic checks that a raster figure exists, has useful dimensions,
    is non-empty, and is not nearly blank. Human review is still required for
    scientific and aesthetic judgment.
    Tools: review_plot_file.

11. CodePlanningAgent
    Use for: safe reproducible Python or R plans and non-executed code skeletons.
    Tools: none.

12. ReportAgent
    Use for: synthesizing specialist results and saving Markdown reports.
    Tools: save_markdown_report.

13. MethodResearchAgent
    Use for: optional external research about methods, packages, or conventions when
    ENABLE_WEB_SEARCH=true.
    Tools: configured search-provider tools.
"""
