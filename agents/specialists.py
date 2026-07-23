from __future__ import annotations

from google.adk import Agent

from ..llm_factory import build_model
from ..prompts import (
    CODE_PLANNING_PROMPT,
    COLUMN_DECODER_PROMPT,
    DATA_INTAKE_PROMPT,
    EDA_PROMPT,
    METHOD_RESEARCH_PROMPT,
    PUBLICATION_PLOT_PROMPT,
    REPORT_PROMPT,
    VISUALIZATION_PROMPT,
)
from ..search_provider import build_search_tools
from ..tools import (
    check_publication_plot_setup,
    create_basic_charts,
    decode_column_roles,
    infer_bed_chrom_sizes,
    inspect_dataset,
    list_available_datasets,
    list_ggplot2_cases,
    match_ggplot2_cases_to_dataset,
    render_ggplot2_case,
    render_ggplot2_case_demo,
    run_eda,
    save_markdown_report,
    validate_publication_plot_paths,
)


def build_data_intake_agent() -> Agent:
    return Agent(
        name="DataIntakeAgent",
        model=build_model(),
        description=(
            "Finds local datasets and inspects data format, shape, columns, data types, "
            "missingness, duplicates, sample values, likely structural issues, and BED "
            "genomic interval summaries."
        ),
        instruction=DATA_INTAKE_PROMPT,
        tools=[list_available_datasets, inspect_dataset, infer_bed_chrom_sizes],
    )


def build_eda_agent() -> Agent:
    return Agent(
        name="EDAAgent",
        model=build_model(),
        description=(
            "Runs deterministic exploratory data analysis using pandas: descriptive "
            "statistics, missingness, categorical summaries, correlations, outliers, "
            "BED interval summaries, and data-quality warnings."
        ),
        instruction=EDA_PROMPT,
        tools=[run_eda],
    )


def build_visualization_agent() -> Agent:
    return Agent(
        name="VisualizationAgent",
        model=build_model(),
        description=(
            "Creates basic exploratory charts and returns saved chart paths. Use for "
            "simple plots, histograms, bar charts, or visual EDA. For publication-style "
            "figures, use PublicationPlotAgent instead."
        ),
        instruction=VISUALIZATION_PROMPT,
        tools=[create_basic_charts],
    )


def build_column_decoder_agent() -> Agent:
    return Agent(
        name="ColumnDecoderAgent",
        model=build_model(),
        description=(
            "Maps real dataset columns to expected roles for approved plotting recipes. "
            "Use when columns may have names like start, Start, chrom_start, or chromStart, "
            "or when the user asks what publication-style plots their data supports."
        ),
        instruction=COLUMN_DECODER_PROMPT,
        tools=[decode_column_roles, match_ggplot2_cases_to_dataset],
    )


def build_publication_plot_agent() -> Agent:
    return Agent(
        name="PublicationPlotAgent",
        model=build_model(),
        description=(
            "Creates approved ggplot2 publication-style plots through controlled Rscript "
            "calls. Can list plot cases, check R setup, validate paths, render demo plots "
            "from simulated data, and render real-data plots when columns match a supported recipe."
        ),
        instruction=PUBLICATION_PLOT_PROMPT,
        tools=[
            list_ggplot2_cases,
            check_publication_plot_setup,
            validate_publication_plot_paths,
            render_ggplot2_case,
            render_ggplot2_case_demo,
        ],
    )


def build_code_planning_agent() -> Agent:
    return Agent(
        name="CodePlanningAgent",
        model=build_model(),
        description=(
            "Writes safe Python/pandas/R analysis plans and code skeletons for the user "
            "to review. Does not execute arbitrary user code."
        ),
        instruction=CODE_PLANNING_PROMPT,
    )


def build_report_agent() -> Agent:
    return Agent(
        name="ReportAgent",
        model=build_model(),
        description=(
            "Synthesizes specialist outputs into a clear final data-analysis report and "
            "can save Markdown reports to the output folder."
        ),
        instruction=REPORT_PROMPT,
        tools=[save_markdown_report],
    )


def build_method_research_agent() -> Agent:
    return Agent(
        name="MethodResearchAgent",
        model=build_model(),
        description=(
            "Optionally researches statistical methods, package choices, and analysis "
            "conventions when external context is needed."
        ),
        instruction=METHOD_RESEARCH_PROMPT,
        tools=build_search_tools(),
    )
