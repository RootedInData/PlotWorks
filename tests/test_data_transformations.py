from __future__ import annotations

import hashlib
import json
import shutil
import unittest
from pathlib import Path

import pandas as pd

from PlotWorks.config import settings
from PlotWorks.tools.data_transformation_tools import (
    execute_generated_python_transform,
    preview_data_transformations,
    save_data_transformations,
    validate_generated_python_transform_code,
)


class DataTransformationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.input_path = settings.data_dir / "_test_transform_input.csv"
        pd.DataFrame(
            {
                "Area": ["A", "A", "B", "B"],
                "Year": [2020, 2020, 2021, 2021],
                "Element": ["Area harvested", "Yield", "Area harvested", "Yield"],
                "Value": [10, 100, 11, 105],
            }
        ).to_csv(cls.input_path, index=False)
        cls.operations = json.dumps(
            [
                {
                    "operation": "pivot_table",
                    "index": ["Area", "Year"],
                    "columns": ["Element"],
                    "values": ["Value"],
                    "aggfunc": "first",
                },
                {
                    "operation": "rename_columns",
                    "mapping": {
                        "Value_Area harvested": "area_harvested",
                        "Value_Yield": "yield",
                    },
                },
            ]
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.input_path.unlink(missing_ok=True)
        shutil.rmtree(settings.transformed_data_output_dir / "tests", ignore_errors=True)
        shutil.rmtree(settings.code_output_dir / "data_transform_runs", ignore_errors=True)

    def _hash(self) -> str:
        return hashlib.sha256(self.input_path.read_bytes()).hexdigest()

    def test_preview_does_not_write_or_modify_source(self) -> None:
        before = self._hash()
        result = preview_data_transformations(self.input_path.name, self.operations)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["source_unchanged"])
        self.assertEqual(before, self._hash())
        self.assertEqual(result["transformed_columns"], ["Area", "Year", "area_harvested", "yield"])

    def test_save_writes_new_file_and_preserves_source(self) -> None:
        before = self._hash()
        result = save_data_transformations(
            self.input_path.name,
            self.operations,
            "_tests/cotton_plot_ready.csv",
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["saved_dataset"]).exists())
        self.assertTrue(Path(result["metadata_file"]).exists())
        self.assertEqual(before, self._hash())
        self.assertTrue(result["source_unchanged"])

    def test_custom_transform_validation_blocks_file_access(self) -> None:
        code = """
def transform_data(data):
    open('unsafe.txt', 'w')
    return data
"""
        result = validate_generated_python_transform_code(code)
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("open" in item for item in result["errors"]))

    def test_custom_transform_executes_in_managed_output(self) -> None:
        code = """
def transform_data(data):
    result = data.copy()
    result["Value2"] = result["Value"] * 2
    return result
"""
        result = execute_generated_python_transform(
            code,
            self.input_path.name,
            "_tests/custom_transform.csv",
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["saved_dataset"]).exists())
        self.assertTrue(result["source_unchanged"])


if __name__ == "__main__":
    unittest.main()
