from __future__ import annotations


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    value = color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected six-digit hex color, got {color!r}")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(color: str) -> float:
    channels = []
    for channel in _hex_to_rgb(color):
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(color_a: str, color_b: str = "#FFFFFF") -> float:
    light = max(_relative_luminance(color_a), _relative_luminance(color_b))
    dark = min(_relative_luminance(color_a), _relative_luminance(color_b))
    return round((light + 0.05) / (dark + 0.05), 2)


def palette_accessibility_notes(colors: list[str]) -> list[str]:
    notes: list[str] = []
    if len(colors) > 8:
        notes.append(
            "More than eight categorical colors are difficult to distinguish; consider faceting, "
            "direct labels, or grouping rare categories."
        )
    low_contrast = [color for color in colors if contrast_ratio(color) < 2.0]
    if low_contrast:
        notes.append(
            "Very light colors may need dark outlines or direct labels on a white background: "
            + ", ".join(low_contrast)
        )
    return notes
