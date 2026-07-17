from __future__ import annotations

from google.adk import Agent

from ..llm_factory import build_model
from ..prompts import (
    CODE_PLANNING_PROMPT,
    DATA_INTAKE_PROMPT,
    EDA_PROMPT,
    METHOD_RESEARCH_PROMPT,
    REPORT_PROMPT,
    VISUALIZATION_PROMPT,
)
from ..search_provider import build_search_tools
from ..tools import (
    create_basic_charts,
    inspect_dataset,
    list_available_datasets,
    run_eda,
    save_markdown_report,
)


def build_data_intake_agent() -> Agent:
    return Agent(
        name="DataIntakeAgent",
        model=build_model(),
        description=(
            "Finds local datasets and inspects data format, shape, columns, data types, "
            "missingness, duplicates, sample values, and likely structural issues."
        ),
        instruction=DATA_INTAKE_PROMPT,
        tools=[list_available_datasets, inspect_dataset],
    )


def build_eda_agent() -> Agent:
    return Agent(
        name="EDAAgent",
        model=build_model(),
        description=(
            "Runs deterministic exploratory data analysis using pandas: descriptive "
            "statistics, missingness, categorical summaries, correlations, outliers, "
            "and data-quality warnings."
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
            "requests involving plots, graphs, histograms, bar charts, or visual EDA."
        ),
        instruction=VISUALIZATION_PROMPT,
        tools=[create_basic_charts],
    )


def build_code_planning_agent() -> Agent:
    return Agent(
        name="CodePlanningAgent",
        model=build_model(),
        description=(
            "Writes safe Python/pandas analysis plans and code skeletons for the user "
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
