from __future__ import annotations

from google.adk import Agent

from ..config import settings
from ..llm_factory import build_model
from ..prompts import (
    ANIMATION_DEVELOPER_PROMPT,
    CODE_PLANNING_PROMPT,
    COLUMN_DECODER_PROMPT,
    DATA_INTAKE_PROMPT,
    DATA_TRANSFORMATION_PROMPT,
    EDA_PROMPT,
    METHOD_RESEARCH_PROMPT,
    PLOT_REVIEW_PROMPT,
    PUBLICATION_PLOT_PROMPT,
    PYTHON_TRANSFORM_DEVELOPER_PROMPT,
    R_PLOT_DEVELOPER_PROMPT,
    REASONING_PROMPT,
    REPORT_PROMPT,
    VISUALIZATION_PLANNER_PROMPT,
    VISUALIZATION_PROMPT,
)
from ..search_provider import build_search_tools
from ..tools import (
    check_animation_setup,
    check_publication_plot_setup,
    create_pretty_charts,
    decode_column_roles,
    discover_dataset_inputs,
    infer_bed_chrom_sizes,
    inspect_dataset,
    inspect_dataset_bundle,
    list_available_datasets,
    list_data_transformation_operations,
    list_ggplot2_cases,
    list_plot_palettes,
    list_pretty_plot_functions,
    list_workbook_sheets,
    match_ggplot2_cases_to_dataset,
    pretty_barplot,
    pretty_boxplot,
    pretty_faceted_plot,
    pretty_genomic_track,
    pretty_heatmap,
    pretty_histogram,
    pretty_lineplot,
    pretty_manhattan,
    pretty_scatter,
    pretty_violin,
    preview_bundle_transformations,
    preview_data_transformations,
    preview_generated_bundle_transform,
    recommend_visualization_plan,
    register_dataset_bundle,
    render_all_ggplot2_case_demos,
    render_animated_scatter,
    render_ggplot2_case,
    render_ggplot2_case_demo,
    review_plot_file,
    run_eda,
    save_markdown_report,
    validate_generated_python_transform_code,
    validate_generated_r_animation_code,
    validate_generated_r_plot_code,
    validate_publication_plot_paths,
)


def build_data_intake_agent() -> Agent:
    return Agent(
        name="DataIntakeAgent",
        model=build_model(
            task="data_intake", profile="fast", agent_name="DataIntakeAgent"
        ),
        description=(
            "Finds and structurally inspects source and PlotWorks-managed transformed "
            "datasets, including BED genomic interval files and common tabular formats."
        ),
        instruction=DATA_INTAKE_PROMPT,
        tools=[
            list_available_datasets,
            inspect_dataset,
            infer_bed_chrom_sizes,
            discover_dataset_inputs,
            list_workbook_sheets,
            register_dataset_bundle,
            inspect_dataset_bundle,
        ],
    )


def build_eda_agent() -> Agent:
    return Agent(
        name="EDAAgent",
        model=build_model(task="eda", profile="fast", agent_name="EDAAgent"),
        description="Runs deterministic pandas-based exploratory data analysis.",
        instruction=EDA_PROMPT,
        tools=[run_eda],
    )


def build_data_transformation_agent() -> Agent:
    return Agent(
        name="DataTransformationAgent",
        model=build_model(
            task="transformation_planning",
            profile="standard",
            agent_name="DataTransformationAgent",
        ),
        description=(
            "Previews deterministic plot-preparation transformations and validates "
            "generated Python proposals without modifying or saving source data."
        ),
        instruction=DATA_TRANSFORMATION_PROMPT,
        tools=[
            list_data_transformation_operations,
            preview_data_transformations,
            preview_bundle_transformations,
            inspect_dataset_bundle,
            validate_generated_python_transform_code,
        ],
    )


def build_visualization_planner_agent() -> Agent:
    return Agent(
        name="VisualizationPlannerAgent",
        model=build_model(
            task="visualization_planning",
            profile="standard",
            agent_name="VisualizationPlannerAgent",
        ),
        description=(
            "Plans figures and chooses among approved R recipes, polished pretty_* "
            "Python functions, custom static R, and animated R plotting."
        ),
        instruction=VISUALIZATION_PLANNER_PROMPT,
        tools=[
            recommend_visualization_plan,
            list_pretty_plot_functions,
            match_ggplot2_cases_to_dataset,
        ],
    )


def build_visualization_agent() -> Agent:
    return Agent(
        name="VisualizationAgent",
        model=build_model(
            task="deterministic_plotting",
            profile="standard",
            agent_name="VisualizationAgent",
        ),
        description=(
            "Creates polished deterministic Python figures using reusable pretty_* "
            "functions with shared palettes, labels, legends, and export presets."
        ),
        instruction=VISUALIZATION_PROMPT,
        tools=[
            create_pretty_charts,
            pretty_histogram,
            pretty_barplot,
            pretty_scatter,
            pretty_lineplot,
            pretty_boxplot,
            pretty_violin,
            pretty_heatmap,
            pretty_faceted_plot,
            pretty_manhattan,
            pretty_genomic_track,
        ],
    )


def build_column_decoder_agent() -> Agent:
    return Agent(
        name="ColumnDecoderAgent",
        model=build_model(
            task="column_mapping", profile="fast", agent_name="ColumnDecoderAgent"
        ),
        description=(
            "Maps real dataset columns to expected roles and identifies compatible "
            "approved ggplot2 cases while surfacing uncertainty."
        ),
        instruction=COLUMN_DECODER_PROMPT,
        tools=[decode_column_roles, match_ggplot2_cases_to_dataset],
    )


def build_publication_plot_agent() -> Agent:
    return Agent(
        name="PublicationPlotAgent",
        model=build_model(
            task="r_recipe_rendering",
            profile="standard",
            agent_name="PublicationPlotAgent",
        ),
        description=(
            "Runs approved ggplot2 recipes, palette variants, simulated previews, setup "
            "checks, and direct real-data adapters through controlled Rscript calls."
        ),
        instruction=PUBLICATION_PLOT_PROMPT,
        tools=[
            list_ggplot2_cases,
            list_plot_palettes,
            check_publication_plot_setup,
            validate_publication_plot_paths,
            render_ggplot2_case,
            render_ggplot2_case_demo,
            render_all_ggplot2_case_demos,
        ],
    )


def build_r_plot_developer_agent() -> Agent:
    return Agent(
        name="RPlotDeveloperAgent",
        model=build_model(
            task="r_code", profile="coding", agent_name="RPlotDeveloperAgent"
        ),
        description=(
            "Writes and validates guarded plotting-only R code for novel static figures "
            "when no approved recipe fits, then returns the proposal to the supervisor."
        ),
        instruction=R_PLOT_DEVELOPER_PROMPT,
        tools=[validate_generated_r_plot_code],
    )


def build_animation_developer_agent() -> Agent:
    return Agent(
        name="AnimationDeveloperAgent",
        model=build_model(
            task="animation_code",
            profile="coding",
            agent_name="AnimationDeveloperAgent",
        ),
        description=(
            "Creates controlled animated scatter plots and validates custom R/gganimate "
            "proposals for root-level confirmed GIF or MP4 execution."
        ),
        instruction=ANIMATION_DEVELOPER_PROMPT,
        tools=[
            check_animation_setup,
            render_animated_scatter,
            validate_generated_r_animation_code,
        ],
    )


def build_plot_review_agent() -> Agent:
    return Agent(
        name="PlotReviewAgent",
        model=build_model(
            task="technical_review", profile="fast", agent_name="PlotReviewAgent"
        ),
        description=(
            "Runs deterministic technical checks on saved raster plots for validity, "
            "dimensions, file size, and likely blankness."
        ),
        instruction=PLOT_REVIEW_PROMPT,
        tools=[review_plot_file],
    )


def build_code_planning_agent() -> Agent:
    return Agent(
        name="CodePlanningAgent",
        model=build_model(
            task="code_planning", profile="coding", agent_name="CodePlanningAgent"
        ),
        description="Writes safe Python or R analysis plans and non-executed code skeletons.",
        instruction=CODE_PLANNING_PROMPT,
    )


def build_report_agent() -> Agent:
    return Agent(
        name="ReportAgent",
        model=build_model(task="reporting", profile="fast", agent_name="ReportAgent"),
        description="Synthesizes specialist outputs and can save Markdown reports.",
        instruction=REPORT_PROMPT,
        tools=[save_markdown_report],
    )


def build_method_research_agent() -> Agent:
    return Agent(
        name="MethodResearchAgent",
        model=build_model(
            task="method_research",
            profile="standard",
            agent_name="MethodResearchAgent",
            required_backend="gemini" if settings.enable_web_search else "",
        ),
        description="Optionally researches current statistical and plotting method guidance.",
        instruction=METHOD_RESEARCH_PROMPT,
        tools=build_search_tools(),
    )


def build_python_transform_developer_agent() -> Agent:
    return Agent(
        name="PythonTransformDeveloperAgent",
        model=build_model(
            task="python_transformation_code",
            profile="coding",
            agent_name="PythonTransformDeveloperAgent",
        ),
        description="Writes and previews Python transformations over named input datasets when a deterministic plan is insufficient.",
        instruction=PYTHON_TRANSFORM_DEVELOPER_PROMPT,
        tools=[
            inspect_dataset_bundle,
            validate_generated_python_transform_code,
            preview_generated_bundle_transform,
        ],
    )


def build_reasoning_agent() -> Agent:
    return Agent(
        name="ReasoningAgent",
        model=build_model(
            task="complex_planning", profile="reasoning", agent_name="ReasoningAgent"
        ),
        description="Resolves complex analytical plans, ambiguous multi-dataset relationships and difficult debugging without executing writes.",
        instruction=REASONING_PROMPT,
        tools=[inspect_dataset_bundle],
    )
