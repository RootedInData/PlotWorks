from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FigurePreset:
    width: float
    height: float
    dpi: int = 300


FIGURE_PRESETS: dict[str, FigurePreset] = {
    "single": FigurePreset(7.2, 5.0),
    "wide": FigurePreset(10.0, 5.5),
    "tall": FigurePreset(6.5, 8.0),
    "square": FigurePreset(6.5, 6.5),
    "small": FigurePreset(5.0, 3.5),
    "manhattan": FigurePreset(11.0, 5.5),
    "heatmap": FigurePreset(8.5, 7.0),
    "genomic_track": FigurePreset(11.0, 4.5),
}


def get_figure_preset(name: str = "single") -> FigurePreset:
    return FIGURE_PRESETS.get(name.strip().lower(), FIGURE_PRESETS["single"])
