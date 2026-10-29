from __future__ import annotations

import os
import unittest
from pathlib import Path


# Check project text, not installed dependencies, user datasets, or run artifacts.
_IGNORED_DIRECTORIES = {
    ".adk",
    ".git",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "env",
    "node_modules",
    "outputs",
    "renv",
    "venv",
}
_TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".mplstyle",
    ".py",
    ".r",
    ".rst",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
_TEXT_FILENAMES = {
    ".env.example", ".gitignore", "Dockerfile", "LICENSE", "Makefile", "NOTICE",
}
_MAX_TEXT_BYTES = 2 * 1024 * 1024


class BrandingTests(unittest.TestCase):
    def test_legacy_brand_name_is_absent_from_text_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        forbidden = (
            "Data" + " Analysis" + " Agency",
            "Data" + "_analysis" + "_agency",
            "data" + "_analysis" + "_agency",
        )
        hits: list[str] = []
        this_file = Path(__file__).resolve()
        for directory, directories, filenames in os.walk(
            root, topdown=True, followlinks=False
        ):
            current = Path(directory)
            # Recognize virtual environments even when they have custom names.
            if "pyvenv.cfg" in filenames or "conda-meta" in directories:
                directories[:] = []
                continue
            # Prune before descending: filtering rglob results still walks .venv.
            directories[:] = sorted(
                name
                for name in directories
                if name not in _IGNORED_DIRECTORIES
                and not (current / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = current / filename
                if path == this_file or path.is_symlink():
                    continue
                if (
                    path.suffix.lower() not in _TEXT_SUFFIXES
                    and filename not in _TEXT_FILENAMES
                ):
                    continue
                if not path.is_file() or path.stat().st_size > _MAX_TEXT_BYTES:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for term in forbidden:
                    if term in text:
                        hits.append(f"{path.relative_to(root)}: {term}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
