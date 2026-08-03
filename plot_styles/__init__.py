"""Shared visual styling utilities for PlotWorks."""

from .accessibility import contrast_ratio, palette_accessibility_notes
from .figure_presets import FIGURE_PRESETS, FigurePreset, get_figure_preset
from .labeling import humanize_label, wrap_labels
from .palettes import (
    CATEGORICAL_OKABE_ITO,
    DIVERGING_BLUE_RED,
    GGRATEFUL_PALETTES,
    MUTED_CATEGORICAL,
    PALETTE_PROVIDERS,
    SEQUENTIAL_BLUE,
    get_palette,
    list_palette_catalog,
    validate_palette_choice,
)

__all__ = [
    "CATEGORICAL_OKABE_ITO",
    "DIVERGING_BLUE_RED",
    "FIGURE_PRESETS",
    "FigurePreset",
    "GGRATEFUL_PALETTES",
    "MUTED_CATEGORICAL",
    "PALETTE_PROVIDERS",
    "SEQUENTIAL_BLUE",
    "contrast_ratio",
    "get_figure_preset",
    "get_palette",
    "humanize_label",
    "list_palette_catalog",
    "palette_accessibility_notes",
    "validate_palette_choice",
    "wrap_labels",
]
