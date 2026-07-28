from __future__ import annotations

from itertools import cycle, islice

# Okabe-Ito: a widely used colorblind-aware qualitative palette.
CATEGORICAL_OKABE_ITO = [
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
    "#7F7F7F",
]

MUTED_CATEGORICAL = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
    "#FF9DA6",
    "#9D755D",
    "#BAB0AC",
]

SEQUENTIAL_BLUE = [
    "#EFF3FF",
    "#C6DBEF",
    "#9ECAE1",
    "#6BAED6",
    "#4292C6",
    "#2171B5",
    "#084594",
]

DIVERGING_BLUE_RED = [
    "#2166AC",
    "#67A9CF",
    "#D1E5F0",
    "#F7F7F7",
    "#FDDBC7",
    "#EF8A62",
    "#B2182B",
]


def get_palette(n: int, kind: str = "categorical") -> list[str]:
    """Return a deterministic palette of at least ``n`` colors."""

    if n < 1:
        return []

    normalized = kind.strip().lower()
    if normalized in {"sequential", "sequence", "continuous"}:
        base = SEQUENTIAL_BLUE
    elif normalized in {"diverging", "divergent"}:
        base = DIVERGING_BLUE_RED
    elif normalized in {"muted", "soft"}:
        base = MUTED_CATEGORICAL
    else:
        base = CATEGORICAL_OKABE_ITO

    if n <= len(base):
        return base[:n]
    return list(islice(cycle(base), n))
