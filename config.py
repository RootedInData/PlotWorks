from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # ADK can still run if env vars are already set.
    load_dotenv = None


PACKAGE_DIR = Path(__file__).resolve().parent

if load_dotenv is not None:
    # Load variables from the package-level .env when present. This keeps the
    # workflow stable even when adk run/adk web is launched from the parent folder.
    load_dotenv(PACKAGE_DIR / ".env")
    load_dotenv()


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if raw and raw.strip():
        return Path(raw.strip()).expanduser()
    return default


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the Data Analysis Agency."""

    package_dir: Path = PACKAGE_DIR
    provider: str = os.getenv("PROVIDER", "gemini").strip().lower()
    model: str = os.getenv("MODEL", "gemini-flash-latest").strip()

    # Keep defaults anchored to this package folder instead of the shell's current
    # working directory. This prevents many WSL/Windows path surprises.
    data_dir: Path = _env_path("DATA_DIR", PACKAGE_DIR / "data")
    output_dir: Path = _env_path("OUTPUT_DIR", PACKAGE_DIR / "outputs")
    plot_output_dir: Path = _env_path("PLOT_OUTPUT_DIR", PACKAGE_DIR / "outputs" / "plots")
    report_output_dir: Path = _env_path("REPORT_OUTPUT_DIR", PACKAGE_DIR / "outputs" / "reports")
    ggplot2_cases_dir: Path = _env_path(
        "GGPLOT2_CASES_DIR", PACKAGE_DIR / "r_plot_library" / "ggplot2_cases"
    )
    ggplot2_cases_manifest: Path = _env_path(
        "GGPLOT2_CASES_MANIFEST", PACKAGE_DIR / "plot_manifests" / "ggplot2_cases.json"
    )

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
settings.plot_output_dir.mkdir(parents=True, exist_ok=True)
settings.report_output_dir.mkdir(parents=True, exist_ok=True)
