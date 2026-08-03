from __future__ import annotations

from itertools import cycle, islice
import re
from typing import Any

# PlotWorks-native palettes used by deterministic Python plotting.
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

# Palette-provider metadata shared with the agent tools. The actual ggrateful
# colors remain owned and supplied by the installed R package at render time.
# Adding another external provider later requires one registry entry here and a
# provider adapter in r_plot_library/shared/palettes.R; no new Python tool file
# is required.
GGRATEFUL_PALETTES: dict[str, dict[str, Any]] = {
    "dancing_bears": {"colors": 6, "continuous": False, "diverging": False},
    "blues_for_allah": {"colors": 11, "continuous": False, "diverging": False},
    "american_beauty": {"colors": 11, "continuous": False, "diverging": False},
    "best_of": {"colors": 12, "continuous": True, "diverging": False},
    "steal_your_face": {"colors": 6, "continuous": True, "diverging": True},
    "terrapin_station": {"colors": 11, "continuous": False, "diverging": False},
    "wake_of_the_flood": {"colors": 11, "continuous": True, "diverging": False},
    "from_the_mars_hotel": {"colors": 11, "continuous": False, "diverging": False},
    "in_the_dark": {"colors": 11, "continuous": False, "diverging": False},
    "workingmans_dead": {"colors": 11, "continuous": True, "diverging": False},
    "europe_72": {"colors": 11, "continuous": False, "diverging": False},
    "complete_studio_rarities": {"colors": 11, "continuous": True, "diverging": False},
    "cornell_77": {"colors": 11, "continuous": False, "diverging": False},
    "go_to_heaven": {"colors": 11, "continuous": False, "diverging": False},
    "shakedown_street": {"colors": 11, "continuous": False, "diverging": False},
    "bertha": {"colors": 11, "continuous": False, "diverging": False},
}

PALETTE_PROVIDERS: dict[str, dict[str, Any]] = {
    "recipe": {
        "description": "Use the original colors defined by each approved ggplot2 recipe.",
        "palettes": {},
        "r_package": "",
    },
    "plotworks": {
        "description": "Built-in PlotWorks palettes used by Python and R helpers.",
        "palettes": {
            "categorical": {"colors": len(CATEGORICAL_OKABE_ITO), "continuous": False, "diverging": False},
            "muted": {"colors": len(MUTED_CATEGORICAL), "continuous": False, "diverging": False},
            "sequential_blue": {"colors": len(SEQUENTIAL_BLUE), "continuous": True, "diverging": False},
            "diverging_blue_red": {"colors": len(DIVERGING_BLUE_RED), "continuous": True, "diverging": True},
        },
        "r_package": "",
    },
    "ggrateful": {
        "description": "Grateful Dead-inspired ggplot2 palettes supplied by the ggrateful R package.",
        "palettes": GGRATEFUL_PALETTES,
        "r_package": "ggrateful",
    },
}


def get_palette(n: int, kind: str = "categorical") -> list[str]:
    """Return a deterministic PlotWorks-native palette of at least ``n`` colors."""

    if n < 1:
        return []

    normalized = kind.strip().lower()
    if normalized in {"sequential", "sequence", "continuous", "sequential_blue"}:
        base = SEQUENTIAL_BLUE
    elif normalized in {"diverging", "divergent", "diverging_blue_red"}:
        base = DIVERGING_BLUE_RED
    elif normalized in {"muted", "soft"}:
        base = MUTED_CATEGORICAL
    else:
        base = CATEGORICAL_OKABE_ITO

    if n <= len(base):
        return base[:n]
    return list(islice(cycle(base), n))


def list_palette_catalog(provider: str = "") -> dict[str, Any]:
    """Return JSON-safe metadata for available palette providers and names."""

    normalized = str(provider).strip().lower()
    if normalized:
        if normalized not in PALETTE_PROVIDERS:
            raise ValueError(
                f"Unknown palette provider {provider!r}. "
                f"Available providers: {', '.join(sorted(PALETTE_PROVIDERS))}"
            )
        return {normalized: PALETTE_PROVIDERS[normalized]}
    return PALETTE_PROVIDERS


def _normalize_palette_name(value: str) -> str:
    """Normalize conversational palette names to manifest/R identifiers."""

    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def validate_palette_choice(provider: str, palette_name: str = "") -> dict[str, Any]:
    """Validate a provider/name pair without loading R or an external package."""

    normalized_provider = str(provider or "recipe").strip().lower()
    normalized_name = _normalize_palette_name(palette_name)
    if normalized_provider not in PALETTE_PROVIDERS:
        raise ValueError(
            f"Unknown palette provider {provider!r}. "
            f"Available providers: {', '.join(sorted(PALETTE_PROVIDERS))}"
        )

    provider_info = PALETTE_PROVIDERS[normalized_provider]
    if normalized_provider == "recipe":
        if normalized_name:
            raise ValueError("The recipe provider does not accept a palette name.")
        return {
            "provider": "recipe",
            "palette_name": "",
            "continuous": False,
            "diverging": False,
            "r_package": "",
        }

    palettes = provider_info["palettes"]
    if normalized_name not in palettes:
        raise ValueError(
            f"Unknown {normalized_provider} palette {palette_name!r}. "
            f"Available palettes: {', '.join(sorted(palettes))}"
        )
    metadata = palettes[normalized_name]
    return {
        "provider": normalized_provider,
        "palette_name": normalized_name,
        "continuous": bool(metadata.get("continuous")),
        "diverging": bool(metadata.get("diverging")),
        "colors": int(metadata.get("colors", 0)),
        "r_package": str(provider_info.get("r_package", "")),
    }
