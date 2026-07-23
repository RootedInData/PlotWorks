from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import settings


def save_markdown_report(markdown_text: str, file_name: str = "data_analysis_report.md") -> dict[str, Any]:
    """Save a Markdown report to the configured report output directory.

    Args:
        markdown_text: The Markdown content to save.
        file_name: Output filename. Use .md extension.
    """

    safe_name = Path(file_name).name
    if not safe_name.endswith(".md"):
        safe_name = f"{safe_name}.md"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.report_output_dir / f"{timestamp}_{safe_name}"
    settings.report_output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_text, encoding="utf-8")

    return {"status": "success", "saved_report": str(path)}
