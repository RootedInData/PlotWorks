from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .data_tools import _json_safe, load_dataset_frame


@dataclass(frozen=True)
class VisualizationSpec:
    goal: str
    renderer: str
    plot_family: str
    x: str = ""
    y: str = ""
    color: str = ""
    size: str = ""
    time: str = ""
    facet: str = ""
    label: str = ""
    title: str = ""
    output_format: str = "png"
    rationale: str = ""


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def list_pretty_plot_functions() -> dict[str, Any]:
    """List reusable polished Python plotting functions and their common purposes."""

    functions = {
        "pretty_histogram": "Numeric distributions, optionally grouped.",
        "pretty_barplot": "Counts or aggregated values across categories.",
        "pretty_scatter": "Relationships between two numeric variables.",
        "pretty_lineplot": "Ordered or time-like trends.",
        "pretty_boxplot": "Distribution summaries across categories.",
        "pretty_violin": "Distribution shape across categories.",
        "pretty_heatmap": "Long-form data converted into a numeric matrix.",
        "pretty_faceted_plot": "Small-multiple scatter or line figures.",
        "pretty_manhattan": "Genome-wide p-value signals by chromosome and position.",
        "pretty_genomic_track": "BED-like genomic interval tracks.",
        "create_pretty_charts": "A small automatic set of polished EDA charts.",
    }
    return _result("success", functions=functions)


def recommend_visualization_plan(
    file_path: str,
    user_goal: str = "",
    preferred_language: str = "auto",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Recommend an initial visualization route based on data structure and user intent.

    This tool proposes a route; the supervisor or VisualizationPlannerAgent remains
    responsible for the final choice.
    """

    try:
        df = load_dataset_frame(file_path, sheet_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    numeric = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
    categorical = [str(c) for c in df.select_dtypes(include=["object", "category", "bool"]).columns]
    goal = user_goal.lower()
    preferred = preferred_language.lower().strip()

    plot_family = "barplot"
    x = categorical[0] if categorical else (numeric[0] if numeric else "")
    y = numeric[0] if numeric else ""
    color = ""
    rationale = "A category summary is the safest initial view for the available columns."

    if any(term in goal for term in ["manhattan", "gwas", "twas"]):
        plot_family = "manhattan"
        rationale = "The request explicitly describes genome-wide association signals."
    elif any(term in goal for term in ["heatmap", "matrix", "correlation"]):
        plot_family = "heatmap"
        rationale = "The request calls for a matrix-like visual summary."
    elif any(term in goal for term in ["distribution", "histogram"]):
        plot_family = "histogram"
        rationale = "The request asks to inspect a numeric distribution."
    elif any(term in goal for term in ["boxplot", "box plot"]):
        plot_family = "boxplot"
        rationale = "The request asks for distribution summaries by category."
    elif "violin" in goal:
        plot_family = "violin"
        rationale = "The request asks to compare distribution shapes."
    elif any(term in goal for term in ["animate", "animated", "animation", "motion"]):
        plot_family = "animated_scatter"
        rationale = "The request explicitly asks for an animated visualization."
    elif any(term in goal for term in ["trend", "time", "line"]):
        plot_family = "lineplot"
        rationale = "The request suggests an ordered or time-like relationship."
    elif any(term in goal for term in ["scatter", "relationship", "association"]):
        plot_family = "scatter"
        rationale = "The request asks about a relationship between numeric variables."
    elif len(numeric) >= 2:
        plot_family = "scatter"
        x, y = numeric[:2]
        color = categorical[0] if categorical and df[categorical[0]].nunique(dropna=True) <= 8 else ""
        rationale = "The dataset contains at least two numeric variables suitable for a relationship plot."
    elif numeric and categorical:
        plot_family = "boxplot"
        x, y = categorical[0], numeric[0]
        rationale = "The dataset contains one numeric and one categorical variable."
    elif numeric:
        plot_family = "histogram"
        x, y = numeric[0], ""
        rationale = "The dataset primarily supports a numeric distribution plot."

    if any(term in goal for term in ["animate", "animated", "animation", "gganimate"]):
        renderer = "animated_r"
    elif preferred in {"r", "rscript", "ggplot2"}:
        renderer = "custom_r"
    elif preferred in {"python", "matplotlib"}:
        renderer = "pretty_python"
    elif any(term in goal for term in ["existing recipe", "approved recipe", "ggplot2 case"]):
        renderer = "approved_r_recipe"
    elif any(term in goal for term in ["custom r", "write r", "ggplot2"]):
        renderer = "custom_r"
    else:
        renderer = "pretty_python"

    specification = VisualizationSpec(
        goal=user_goal,
        renderer=renderer,
        plot_family=plot_family,
        x=x,
        y=y,
        color=color,
        time=(
            next(
                (
                    str(column)
                    for column in df.columns
                    if str(column).lower() in {"time", "year", "date", "month", "frame", "state"}
                ),
                "",
            )
            if renderer == "animated_r"
            else ""
        ),
        rationale=rationale,
    )
    return _result(
        "success",
        data_shape={"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        numeric_columns=numeric,
        categorical_columns=categorical,
        recommended_spec=asdict(specification),
        routing_guidance={
            "approved_r_recipe": "Use when an existing controlled ggplot2 case fits the request.",
            "pretty_python": "Use for routine, reproducible, polished plots from one table.",
            "custom_r": "Use experimentally when no approved recipe fits and R offers meaningful layout advantages.",
            "animated_r": "Use for movement across an ordered time/state variable; transform the data first when needed.",
        },
    )
