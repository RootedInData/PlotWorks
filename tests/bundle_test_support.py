"""Temporary workspaces shared by the multi-dataset regression tests."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PlotWorks.config import settings


class BundleTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="plotworks_test_")
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.settings = replace(
            settings,
            data_dir=root / "data",
            output_dir=root / "outputs",
            data_output_dir=root / "outputs/data",
            transformed_data_output_dir=root / "outputs/data/transformed",
            code_output_dir=root / "outputs/code",
            allow_absolute_data_paths=False,
        )
        for directory in (
            self.settings.data_dir,
            self.settings.transformed_data_output_dir,
            self.settings.code_output_dir,
        ):
            directory.mkdir(parents=True)
        for module in (
            "data_tools",
            "data_transformation_tools",
            "dataset_bundle_tools",
            "bundle_transformation_tools",
            "multi_table_engine",
            "generated_transform_runtime",
        ):
            self.enterContext(
                patch(f"PlotWorks.tools.{module}.settings", self.settings)
            )
        self.context = SimpleNamespace(state={})

    def source(self, name, text):
        path = self.settings.data_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
