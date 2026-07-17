from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # ADK can still run if env vars are already set.
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the Data Analysis Agency."""

    provider: str = os.getenv("PROVIDER", "gemini").strip().lower()
    model: str = os.getenv("MODEL", "gemini-flash-latest").strip()
    data_dir: Path = Path(os.getenv("DATA_DIR", "./data_analysis_agency/data")).expanduser()
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./data_analysis_agency/outputs")).expanduser()
    allow_absolute_data_paths: bool = os.getenv(
        "ALLOW_ABSOLUTE_DATA_PATHS", "false"
    ).strip().lower() in {"1", "true", "yes", "y"}
    max_file_mb: int = int(os.getenv("MAX_FILE_MB", "100"))
    max_preview_rows: int = int(os.getenv("MAX_PREVIEW_ROWS", "8"))
    enable_web_search: bool = os.getenv("ENABLE_WEB_SEARCH", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
