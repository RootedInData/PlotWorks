from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageStat

from ..config import settings
from .data_tools import _json_safe


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _resolve_plot_path(plot_path: str) -> Path:
    candidate = Path(str(plot_path).strip()).expanduser()
    if not candidate.is_absolute():
        candidate = settings.plot_output_dir / candidate
    resolved = candidate.resolve()
    output_root = settings.plot_output_dir.resolve()
    if resolved != output_root and output_root not in resolved.parents:
        raise PermissionError("Plot review is limited to files inside PLOT_OUTPUT_DIR")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"Plot file not found: {resolved}")
    return resolved


def review_plot_file(plot_path: str) -> dict[str, Any]:
    """Run deterministic quality checks on a generated raster image."""

    try:
        path = _resolve_plot_path(plot_path)
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return _result(
                "warning",
                message="Detailed pixel checks currently support raster images only.",
                file_path=str(path),
                size_bytes=path.stat().st_size,
            )

        with Image.open(path) as image:
            image.load()
            rgb = image.convert("RGB")
            width, height = rgb.size
            gray = np.asarray(rgb.convert("L"), dtype=float)
            variance = float(np.var(gray))
            unique_sample = len(np.unique(gray[:: max(1, height // 300), :: max(1, width // 300)]))
            extrema = ImageStat.Stat(rgb).extrema

        warnings: list[str] = []
        if width < 1000 or height < 600:
            warnings.append("The raster dimensions may be low for publication or presentation use.")
        if path.stat().st_size < 5_000:
            warnings.append("The output file is unusually small and may be blank or incomplete.")
        if variance < 25 or unique_sample < 8:
            warnings.append("The image has very low visual variation and may be blank or nearly blank.")
        aspect_ratio = round(width / max(height, 1), 3)
        if aspect_ratio > 4.0 or aspect_ratio < 0.25:
            warnings.append("The extreme aspect ratio may make labels difficult to read.")

        return _result(
            "success" if not warnings else "warning",
            file_path=str(path),
            size_bytes=path.stat().st_size,
            dimensions_pixels={"width": width, "height": height},
            aspect_ratio=aspect_ratio,
            grayscale_variance=round(variance, 2),
            sampled_unique_gray_levels=unique_sample,
            channel_extrema=extrema,
            warnings=warnings,
            review_scope=(
                "This is a deterministic technical check for file validity, dimensions, and blankness. "
                "It does not verify scientific correctness or replace human visual review."
            ),
        )
    except Exception as exc:
        return _result("error", message=str(exc))
