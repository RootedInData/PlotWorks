from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import settings
from ..plot_styles import get_figure_preset, get_palette, humanize_label, wrap_labels
from .data_tools import _json_safe, load_dataset_frame

_ALLOWED_EXTENSIONS = {".png", ".pdf", ".svg"}


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    style_path = settings.package_dir / "plot_styles" / "agency_publication.mplstyle"
    if style_path.exists():
        plt.style.use(str(style_path))
    return plt


def _column(df: pd.DataFrame, name: str, *, required: bool = True) -> str:
    clean = str(name).strip()
    if clean in df.columns:
        return clean
    lowered = {str(col).lower(): str(col) for col in df.columns}
    if clean.lower() in lowered:
        return lowered[clean.lower()]
    if required:
        raise KeyError(f"Column {name!r} was not found. Available columns: {list(map(str, df.columns))}")
    return ""


def _safe_filename(output_name: str, default_stem: str) -> Path:
    """Resolve a filename inside the configured plot directory.

    Directory components are intentionally rejected so an agent cannot recreate nested
    ``outputs/plots/outputs/plots`` paths or escape the managed output folder.
    """

    raw = str(output_name).strip() if output_name else f"{default_stem}.png"
    candidate = Path(raw)
    if candidate.name != raw or candidate.parent != Path("."):
        raise ValueError("output_name must be a filename only, without directory components")
    suffix = candidate.suffix.lower() or ".png"
    if suffix not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported plot extension {suffix!r}; use PNG, PDF, or SVG")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate.stem).strip("._") or default_stem
    settings.plot_output_dir.mkdir(parents=True, exist_ok=True)
    return settings.plot_output_dir / f"{stem}{suffix}"


def _save(fig: Any, output_name: str, default_stem: str, preset: str) -> Path:
    destination = _safe_filename(output_name, default_stem)
    figure_preset = get_figure_preset(preset)
    fig.set_size_inches(figure_preset.width, figure_preset.height)
    fig.savefig(destination, dpi=figure_preset.dpi, bbox_inches="tight", facecolor="white")
    return destination.resolve()


def _finish_axes(ax: Any, title: str = "", subtitle: str = "") -> None:
    if title:
        ax.set_title(title, loc="left", pad=14)
    if subtitle:
        ax.text(
            0,
            1.01,
            subtitle,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=9,
            color="#555555",
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def pretty_histogram(
    file_path: str,
    column: str,
    group: str = "",
    bins: int = 30,
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished histogram, optionally overlaid by a grouping column."""

    try:
        df = load_dataset_frame(file_path, sheet_name)
        value_col = _column(df, column)
        group_col = _column(df, group, required=False) if group else ""
        values = pd.to_numeric(df[value_col], errors="coerce")
        if values.notna().sum() == 0:
            raise ValueError(f"Column {value_col!r} has no numeric values")

        plt = _matplotlib()
        fig, ax = plt.subplots()
        if group_col:
            groups = [g for g in df[group_col].dropna().unique()]
            colors = get_palette(len(groups))
            for color, group_value in zip(colors, groups):
                subset = pd.to_numeric(
                    df.loc[df[group_col] == group_value, value_col], errors="coerce"
                ).dropna()
                ax.hist(subset, bins=bins, alpha=0.58, color=color, label=str(group_value))
            ax.legend(title=humanize_label(group_col), loc="best")
        else:
            ax.hist(values.dropna(), bins=bins, color=get_palette(1)[0], alpha=0.86)

        ax.set_xlabel(humanize_label(value_col))
        ax.set_ylabel("Count")
        _finish_axes(ax, title or f"Distribution of {humanize_label(value_col)}")
        destination = _save(fig, output_name, f"pretty_{value_col}_histogram", "single")
        plt.close(fig)
        return _result("success", plot_type="histogram", saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def pretty_barplot(
    file_path: str,
    category: str,
    value: str = "",
    group: str = "",
    aggregation: str = "mean",
    top_n: int = 20,
    horizontal: bool = True,
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished count or aggregated bar plot."""

    try:
        df = load_dataset_frame(file_path, sheet_name)
        category_col = _column(df, category)
        value_col = _column(df, value, required=False) if value else ""
        group_col = _column(df, group, required=False) if group else ""
        aggregation = aggregation.lower().strip()
        allowed_aggregations = {"mean", "median", "sum", "count"}
        if aggregation not in allowed_aggregations:
            raise ValueError(f"aggregation must be one of {sorted(allowed_aggregations)}")

        if value_col:
            working = df[[category_col] + ([group_col] if group_col else []) + [value_col]].copy()
            working[value_col] = pd.to_numeric(working[value_col], errors="coerce")
            group_fields = [category_col] + ([group_col] if group_col else [])
            if aggregation == "count":
                summarized = working.groupby(group_fields, dropna=False)[value_col].count()
            else:
                summarized = working.groupby(group_fields, dropna=False)[value_col].agg(aggregation)
        else:
            group_fields = [category_col] + ([group_col] if group_col else [])
            summarized = df.groupby(group_fields, dropna=False).size()
            aggregation = "count"

        plotted = summarized.unstack(group_col) if group_col else summarized
        if group_col:
            totals = plotted.fillna(0).sum(axis=1)
            plotted = plotted.loc[totals.nlargest(max(1, top_n)).index]
        else:
            plotted = plotted.nlargest(max(1, top_n)).sort_values(ascending=True if horizontal else False)

        plt = _matplotlib()
        fig, ax = plt.subplots()
        colors = get_palette(plotted.shape[1] if isinstance(plotted, pd.DataFrame) else 1)
        plotted.plot(
            kind="barh" if horizontal else "bar",
            ax=ax,
            color=colors,
            width=0.78,
        )
        axis_label = "Count" if aggregation == "count" else f"{aggregation.title()} {humanize_label(value_col)}"
        if horizontal:
            ax.set_xlabel(axis_label)
            ax.set_ylabel(humanize_label(category_col))
            ax.set_yticklabels(wrap_labels([tick.get_text() for tick in ax.get_yticklabels()], 28))
        else:
            ax.set_ylabel(axis_label)
            ax.set_xlabel(humanize_label(category_col))
            ax.tick_params(axis="x", rotation=35)
        if group_col:
            ax.legend(title=humanize_label(group_col), frameon=False)
        elif ax.get_legend() is not None:
            ax.get_legend().remove()
        _finish_axes(ax, title or f"{axis_label} by {humanize_label(category_col)}")
        destination = _save(fig, output_name, f"pretty_{category_col}_barplot", "wide" if horizontal else "single")
        plt.close(fig)
        return _result("success", plot_type="barplot", saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def pretty_scatter(
    file_path: str,
    x: str,
    y: str,
    color: str = "",
    size: str = "",
    label: str = "",
    trendline: bool = False,
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished scatter plot with optional groups, sizes, labels, and trend lines."""

    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        x_col, y_col = _column(df, x), _column(df, y)
        color_col = _column(df, color, required=False) if color else ""
        size_col = _column(df, size, required=False) if size else ""
        label_col = _column(df, label, required=False) if label else ""
        df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        df = df.dropna(subset=[x_col, y_col])
        if df.empty:
            raise ValueError("No complete numeric x/y observations remain after conversion")

        plt = _matplotlib()
        fig, ax = plt.subplots()
        if size_col:
            sizes = pd.to_numeric(df[size_col], errors="coerce").fillna(0)
            spread = sizes.max() - sizes.min()
            marker_sizes = 35 + (sizes - sizes.min()) / (spread if spread else 1) * 130
        else:
            marker_sizes = 48

        if color_col:
            groups = list(df[color_col].astype("string").fillna("<MISSING>").unique())
            colors = get_palette(len(groups))
            for group_value, group_color in zip(groups, colors):
                mask = df[color_col].astype("string").fillna("<MISSING>") == group_value
                group_sizes = marker_sizes[mask] if isinstance(marker_sizes, pd.Series) else marker_sizes
                ax.scatter(
                    df.loc[mask, x_col],
                    df.loc[mask, y_col],
                    s=group_sizes,
                    color=group_color,
                    alpha=0.78,
                    edgecolor="white",
                    linewidth=0.6,
                    label=str(group_value),
                )
            ax.legend(title=humanize_label(color_col), frameon=False)
        else:
            ax.scatter(
                df[x_col],
                df[y_col],
                s=marker_sizes,
                color=get_palette(1)[0],
                alpha=0.78,
                edgecolor="white",
                linewidth=0.6,
            )

        if trendline and len(df) >= 3:
            coefficients = np.polyfit(df[x_col], df[y_col], 1)
            line_x = np.linspace(df[x_col].min(), df[x_col].max(), 100)
            ax.plot(line_x, coefficients[0] * line_x + coefficients[1], color="#333333", linestyle="--")

        if label_col:
            for _, row in df.head(40).iterrows():
                if pd.notna(row[label_col]):
                    ax.annotate(str(row[label_col]), (row[x_col], row[y_col]), xytext=(4, 4), textcoords="offset points", fontsize=7)

        ax.set_xlabel(humanize_label(x_col))
        ax.set_ylabel(humanize_label(y_col))
        _finish_axes(ax, title or f"{humanize_label(y_col)} versus {humanize_label(x_col)}")
        destination = _save(fig, output_name, f"pretty_{x_col}_{y_col}_scatter", "single")
        plt.close(fig)
        return _result("success", plot_type="scatter", rows_plotted=len(df), saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def pretty_lineplot(
    file_path: str,
    x: str,
    y: str,
    group: str = "",
    marker: bool = True,
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished line plot for ordered or time-like data."""

    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        x_col, y_col = _column(df, x), _column(df, y)
        group_col = _column(df, group, required=False) if group else ""
        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        df = df.dropna(subset=[x_col, y_col])
        if df.empty:
            raise ValueError("No observations remain after converting the y column to numeric")

        plt = _matplotlib()
        fig, ax = plt.subplots()
        if group_col:
            groups = list(df[group_col].astype("string").fillna("<MISSING>").unique())
            for group_value, group_color in zip(groups, get_palette(len(groups))):
                subset = df[df[group_col].astype("string").fillna("<MISSING>") == group_value].sort_values(x_col)
                ax.plot(subset[x_col], subset[y_col], marker="o" if marker else None, color=group_color, label=str(group_value))
            ax.legend(title=humanize_label(group_col), frameon=False)
        else:
            subset = df.sort_values(x_col)
            ax.plot(subset[x_col], subset[y_col], marker="o" if marker else None, color=get_palette(1)[0])

        ax.set_xlabel(humanize_label(x_col))
        ax.set_ylabel(humanize_label(y_col))
        ax.tick_params(axis="x", rotation=30)
        _finish_axes(ax, title or f"{humanize_label(y_col)} across {humanize_label(x_col)}")
        destination = _save(fig, output_name, f"pretty_{x_col}_{y_col}_lineplot", "wide")
        plt.close(fig)
        return _result("success", plot_type="lineplot", saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def _grouped_distribution_plot(
    kind: str,
    file_path: str,
    category: str,
    value: str,
    group: str,
    title: str,
    output_name: str,
    sheet_name: str,
) -> dict[str, Any]:
    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        category_col, value_col = _column(df, category), _column(df, value)
        group_col = _column(df, group, required=False) if group else ""
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=[category_col, value_col])
        categories = list(df[category_col].astype("string").unique())
        if not categories:
            raise ValueError("No categories with numeric observations were found")

        plt = _matplotlib()
        fig, ax = plt.subplots()
        groups = list(df[group_col].astype("string").unique()) if group_col else [""]
        colors = get_palette(len(groups))
        base_positions = np.arange(len(categories), dtype=float)
        width = 0.72 / max(len(groups), 1)

        for group_index, (group_value, group_color) in enumerate(zip(groups, colors)):
            datasets: list[np.ndarray] = []
            for category_value in categories:
                subset = df[df[category_col].astype("string") == category_value]
                if group_col:
                    subset = subset[subset[group_col].astype("string") == group_value]
                datasets.append(subset[value_col].dropna().to_numpy())
            offset = (group_index - (len(groups) - 1) / 2) * width
            positions = base_positions + offset
            if kind == "boxplot":
                result = ax.boxplot(
                    datasets,
                    positions=positions,
                    widths=width * 0.82,
                    patch_artist=True,
                    manage_ticks=False,
                    showfliers=False,
                    medianprops={"color": "#222222", "linewidth": 1.2},
                    whiskerprops={"color": "#555555"},
                    capprops={"color": "#555555"},
                )
                for patch in result["boxes"]:
                    patch.set_facecolor(group_color)
                    patch.set_alpha(0.75)
            else:
                nonempty = [(position, values) for position, values in zip(positions, datasets) if len(values) > 0]
                if nonempty:
                    violin = ax.violinplot(
                        [values for _, values in nonempty],
                        positions=[position for position, _ in nonempty],
                        widths=width * 0.9,
                        showmeans=False,
                        showmedians=True,
                        showextrema=False,
                    )
                    for body in violin["bodies"]:
                        body.set_facecolor(group_color)
                        body.set_edgecolor("white")
                        body.set_alpha(0.72)
                    violin["cmedians"].set_color("#222222")
            if group_col:
                ax.scatter([], [], color=group_color, label=str(group_value))

        ax.set_xticks(base_positions)
        ax.set_xticklabels(wrap_labels(categories, 18), rotation=25, ha="right")
        ax.set_xlabel(humanize_label(category_col))
        ax.set_ylabel(humanize_label(value_col))
        if group_col:
            ax.legend(title=humanize_label(group_col), frameon=False)
        _finish_axes(ax, title or f"{humanize_label(value_col)} by {humanize_label(category_col)}")
        preset = "wide" if len(categories) > 5 else "single"
        destination = _save(fig, output_name, f"pretty_{category_col}_{kind}", preset)
        plt.close(fig)
        return _result("success", plot_type=kind, saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def pretty_boxplot(
    file_path: str,
    category: str,
    value: str,
    group: str = "",
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished box plot."""

    return _grouped_distribution_plot("boxplot", file_path, category, value, group, title, output_name, sheet_name)


def pretty_violin(
    file_path: str,
    category: str,
    value: str,
    group: str = "",
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished violin plot."""

    return _grouped_distribution_plot("violin", file_path, category, value, group, title, output_name, sheet_name)


def pretty_heatmap(
    file_path: str,
    row: str,
    column: str,
    value: str,
    aggregation: str = "mean",
    annotate: bool = False,
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished matrix heatmap from long-form data."""

    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        row_col, column_col, value_col = _column(df, row), _column(df, column), _column(df, value)
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        aggregation = aggregation.lower().strip()
        if aggregation not in {"mean", "median", "sum", "count"}:
            raise ValueError("aggregation must be mean, median, sum, or count")
        matrix = pd.pivot_table(
            df,
            index=row_col,
            columns=column_col,
            values=value_col,
            aggfunc=aggregation,
        )
        if matrix.empty:
            raise ValueError("The selected columns did not produce a non-empty matrix")

        plt = _matplotlib()
        fig, ax = plt.subplots()
        image = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="Blues")
        ax.set_xticks(np.arange(matrix.shape[1]))
        ax.set_yticks(np.arange(matrix.shape[0]))
        ax.set_xticklabels(wrap_labels(matrix.columns, 14), rotation=45, ha="right")
        ax.set_yticklabels(wrap_labels(matrix.index, 20))
        ax.set_xlabel(humanize_label(column_col))
        ax.set_ylabel(humanize_label(row_col))
        colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        colorbar.set_label(f"{aggregation.title()} {humanize_label(value_col)}")
        if annotate and matrix.size <= 225:
            values = matrix.to_numpy(dtype=float)
            threshold = np.nanmean(values)
            for i in range(values.shape[0]):
                for j in range(values.shape[1]):
                    if not np.isnan(values[i, j]):
                        ax.text(j, i, f"{values[i, j]:.2g}", ha="center", va="center", fontsize=7, color="white" if values[i, j] > threshold else "#222222")
        _finish_axes(ax, title or f"{humanize_label(value_col)} heatmap")
        ax.grid(False)
        destination = _save(fig, output_name, f"pretty_{value_col}_heatmap", "heatmap")
        plt.close(fig)
        return _result("success", plot_type="heatmap", matrix_shape=list(matrix.shape), saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def pretty_faceted_plot(
    file_path: str,
    x: str,
    y: str,
    facet: str,
    kind: str = "scatter",
    color: str = "",
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a small-multiple scatter or line figure."""

    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        x_col, y_col, facet_col = _column(df, x), _column(df, y), _column(df, facet)
        color_col = _column(df, color, required=False) if color else ""
        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        facets = list(df[facet_col].dropna().astype("string").unique())[:12]
        if not facets:
            raise ValueError("No facet values were found")
        kind = kind.lower().strip()
        if kind not in {"scatter", "line"}:
            raise ValueError("kind must be 'scatter' or 'line'")

        plt = _matplotlib()
        ncols = min(3, len(facets))
        nrows = math.ceil(len(facets) / ncols)
        fig, axes = plt.subplots(nrows, ncols, squeeze=False, sharex=False, sharey=False)
        groups = list(df[color_col].dropna().astype("string").unique()) if color_col else [""]
        palette = get_palette(max(len(groups), 1))
        for ax, facet_value in zip(axes.flat, facets):
            subset = df[df[facet_col].astype("string") == facet_value]
            for group_value, group_color in zip(groups, palette):
                group_subset = subset
                if color_col:
                    group_subset = subset[subset[color_col].astype("string") == group_value]
                if kind == "line":
                    group_subset = group_subset.sort_values(x_col)
                    ax.plot(group_subset[x_col], group_subset[y_col], marker="o", color=group_color, label=str(group_value) if color_col else None)
                else:
                    ax.scatter(group_subset[x_col], group_subset[y_col], color=group_color, alpha=0.76, edgecolor="white", linewidth=0.5, label=str(group_value) if color_col else None)
            ax.set_title(str(facet_value), fontsize=10, fontweight="bold")
            ax.set_xlabel(humanize_label(x_col))
            ax.set_ylabel(humanize_label(y_col))
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
        for ax in axes.flat[len(facets) :]:
            ax.set_visible(False)
        if color_col:
            handles, labels = axes.flat[0].get_legend_handles_labels()
            fig.legend(handles, labels, title=humanize_label(color_col), loc="upper center", ncol=min(5, len(labels)), frameon=False)
        fig.suptitle(title or f"{humanize_label(y_col)} by {humanize_label(facet_col)}", x=0.05, ha="left", fontweight="bold", fontsize=14)
        fig.tight_layout(rect=(0, 0, 1, 0.94 if color_col else 0.97))
        destination = _save(fig, output_name, f"pretty_{facet_col}_faceted_{kind}", "wide")
        plt.close(fig)
        return _result("success", plot_type=f"faceted_{kind}", facets=facets, saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def _natural_chrom_key(value: object) -> tuple[int, object]:
    text = str(value).replace("chr", "").replace("CHR", "")
    try:
        return (0, int(text))
    except ValueError:
        return (1, text)


def pretty_manhattan(
    file_path: str,
    chromosome: str,
    position: str,
    p_value: str,
    label: str = "",
    significance: float = 5e-8,
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a polished Manhattan plot from genome-wide signal data."""

    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        chr_col, pos_col, p_col = _column(df, chromosome), _column(df, position), _column(df, p_value)
        label_col = _column(df, label, required=False) if label else ""
        df[pos_col] = pd.to_numeric(df[pos_col], errors="coerce")
        df[p_col] = pd.to_numeric(df[p_col], errors="coerce")
        df = df.dropna(subset=[chr_col, pos_col, p_col])
        df = df[(df[p_col] > 0) & (df[p_col] <= 1)]
        if df.empty:
            raise ValueError("No valid rows remain; p-values must be within (0, 1]")

        chromosomes = sorted(df[chr_col].astype(str).unique(), key=_natural_chrom_key)
        cumulative_offset = 0.0
        ticks: list[float] = []
        plotted_frames = []
        for chromosome_value in chromosomes:
            subset = df[df[chr_col].astype(str) == chromosome_value].copy().sort_values(pos_col)
            subset["_cumulative_position"] = subset[pos_col] + cumulative_offset
            ticks.append((subset["_cumulative_position"].min() + subset["_cumulative_position"].max()) / 2)
            cumulative_offset = subset["_cumulative_position"].max() + max(df[pos_col].max() * 0.01, 1)
            plotted_frames.append(subset)
        plotted = pd.concat(plotted_frames, ignore_index=True)
        plotted["_minus_log10_p"] = -np.log10(plotted[p_col])

        plt = _matplotlib()
        fig, ax = plt.subplots()
        alternating = ["#0072B2", "#56B4E9"]
        for index, chromosome_value in enumerate(chromosomes):
            subset = plotted[plotted[chr_col].astype(str) == chromosome_value]
            ax.scatter(subset["_cumulative_position"], subset["_minus_log10_p"], s=18, color=alternating[index % 2], alpha=0.78, linewidth=0)
        if 0 < significance <= 1:
            ax.axhline(-math.log10(significance), color="#B2182B", linestyle="--", linewidth=1.2, label=f"Threshold: {significance:g}")
            ax.legend(frameon=False, loc="upper right")
        if label_col:
            top = plotted.nlargest(min(15, len(plotted)), "_minus_log10_p")
            for _, row in top.iterrows():
                if pd.notna(row[label_col]):
                    ax.annotate(str(row[label_col]), (row["_cumulative_position"], row["_minus_log10_p"]), xytext=(3, 5), textcoords="offset points", fontsize=7, rotation=35)
        ax.set_xticks(ticks)
        ax.set_xticklabels(chromosomes)
        ax.set_xlabel("Chromosome")
        ax.set_ylabel(r"$-\log_{10}(p)$")
        _finish_axes(ax, title or "Genome-wide association signals")
        destination = _save(fig, output_name, "pretty_manhattan", "manhattan")
        plt.close(fig)
        return _result("success", plot_type="manhattan", rows_plotted=len(plotted), saved_plot=str(destination))
    except Exception as exc:
        return _result("error", message=str(exc))


def pretty_genomic_track(
    file_path: str,
    chrom: str = "chrom",
    start: str = "chromStart",
    end: str = "chromEnd",
    score: str = "",
    category: str = "",
    chromosome_filter: str = "",
    title: str = "",
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Create a simple polished interval track from BED-like data."""

    try:
        df = load_dataset_frame(file_path, sheet_name).copy()
        chrom_col, start_col, end_col = _column(df, chrom), _column(df, start), _column(df, end)
        score_col = _column(df, score, required=False) if score else ""
        category_col = _column(df, category, required=False) if category else ""
        df[start_col] = pd.to_numeric(df[start_col], errors="coerce")
        df[end_col] = pd.to_numeric(df[end_col], errors="coerce")
        df = df.dropna(subset=[chrom_col, start_col, end_col])
        if chromosome_filter:
            df = df[df[chrom_col].astype(str) == str(chromosome_filter)]
        if df.empty:
            raise ValueError("No genomic intervals remain for plotting")
        if not chromosome_filter and df[chrom_col].nunique() > 1:
            chromosome_filter = str(df[chrom_col].value_counts().index[0])
            df = df[df[chrom_col].astype(str) == chromosome_filter]

        categories = list(df[category_col].astype("string").fillna("Intervals").unique()) if category_col else ["Intervals"]
        y_map = {value: index for index, value in enumerate(categories)}
        colors = get_palette(len(categories))
        color_map = dict(zip(categories, colors))

        plt = _matplotlib()
        fig, ax = plt.subplots()
        for _, row in df.head(5000).iterrows():
            category_value = str(row[category_col]) if category_col else "Intervals"
            y_value = y_map.get(category_value, 0)
            linewidth = 4.0
            alpha = 0.78
            if score_col:
                numeric_score = pd.to_numeric(pd.Series([row[score_col]]), errors="coerce").iloc[0]
                if pd.notna(numeric_score):
                    linewidth = 2.5 + min(abs(float(numeric_score)), 10) * 0.25
            ax.plot([row[start_col], row[end_col]], [y_value, y_value], color=color_map[category_value], linewidth=linewidth, alpha=alpha, solid_capstyle="butt")
        ax.set_yticks(list(y_map.values()))
        ax.set_yticklabels(wrap_labels(list(y_map.keys()), 20))
        ax.set_xlabel(f"Position on {chromosome_filter or 'selected chromosome'}")
        ax.set_ylabel(humanize_label(category_col) if category_col else "Track")
        _finish_axes(ax, title or f"Genomic intervals: {chromosome_filter or 'selected chromosome'}")
        destination = _save(fig, output_name, "pretty_genomic_track", "genomic_track")
        plt.close(fig)
        return _result(
            "success",
            plot_type="genomic_track",
            chromosome=chromosome_filter,
            intervals_plotted=min(len(df), 5000),
            truncation_warning="Only the first 5,000 intervals were plotted." if len(df) > 5000 else "",
            saved_plot=str(destination),
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def create_pretty_charts(
    file_path: str,
    sheet_name: str = "",
    output_prefix: str = "eda",
) -> dict[str, Any]:
    """Automatically create a small set of polished exploratory charts.

    The function intentionally makes only a few high-value charts. For precise control,
    call an individual ``pretty_*`` function.
    """

    try:
        df = load_dataset_frame(file_path, sheet_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    saved: list[str] = []
    attempts: list[dict[str, Any]] = []
    numeric = list(df.select_dtypes(include=[np.number]).columns)
    categorical = list(df.select_dtypes(include=["object", "category", "bool"]).columns)

    for column in numeric[:3]:
        result = pretty_histogram(
            file_path=file_path,
            column=str(column),
            output_name=f"{output_prefix}_{column}_pretty_histogram.png",
            sheet_name=sheet_name,
        )
        attempts.append(result)
        if result.get("status") == "success":
            saved.append(str(result["saved_plot"]))

    for column in categorical[:2]:
        result = pretty_barplot(
            file_path=file_path,
            category=str(column),
            aggregation="count",
            output_name=f"{output_prefix}_{column}_pretty_barplot.png",
            sheet_name=sheet_name,
        )
        attempts.append(result)
        if result.get("status") == "success":
            saved.append(str(result["saved_plot"]))

    if len(numeric) >= 2:
        result = pretty_scatter(
            file_path=file_path,
            x=str(numeric[0]),
            y=str(numeric[1]),
            color=str(categorical[0]) if categorical and df[categorical[0]].nunique(dropna=True) <= 8 else "",
            trendline=True,
            output_name=f"{output_prefix}_{numeric[0]}_{numeric[1]}_pretty_scatter.png",
            sheet_name=sheet_name,
        )
        attempts.append(result)
        if result.get("status") == "success":
            saved.append(str(result["saved_plot"]))

    return _result(
        "success" if saved else "warning",
        saved_charts=saved,
        attempted_charts=attempts,
        output_dir=str(settings.plot_output_dir.resolve()),
    )
