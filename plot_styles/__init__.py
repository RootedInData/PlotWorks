"""Shared visual styling utilities for the Data Analysis Agency."""

from .accessibility import contrast_ratio, palette_accessibility_notes
from .figure_presets import FIGURE_PRESETS, FigurePreset, get_figure_preset
from .labeling import humanize_label, wrap_labels
from .palettes import (
    CATEGORICAL_OKABE_ITO,
    DIVERGING_BLUE_RED,
    MUTED_CATEGORICAL,
    SEQUENTIAL_BLUE,
    get_palette,
)

__all__ = [
    "CATEGORICAL_OKABE_ITO",
    "DIVERGING_BLUE_RED",
    "MUTED_CATEGORICAL",
    "SEQUENTIAL_BLUE",
    "FIGURE_PRESETS",
    "FigurePreset",
    "contrast_ratio",
    "get_figure_preset",
    "get_palette",
    "humanize_label",
    "palette_accessibility_notes",
    "wrap_labels",
]
