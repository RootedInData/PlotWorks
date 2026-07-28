from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from Data_analysis_agency.config import settings
from Data_analysis_agency.tools.pretty_plot_tools import pretty_barplot, pretty_scatter


class PrettyPlotToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.input_path = settings.data_dir / "_test_pretty_plots.csv"
        pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5, 6],
                "y": [2, 4, 5, 8, 9, 12],
                "group": ["A", "A", "A", "B", "B", "B"],
            }
        ).to_csv(cls.input_path, index=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.input_path.unlink(missing_ok=True)
        for name in ["test_pretty_scatter.png", "test_pretty_bar.png"]:
            (settings.plot_output_dir / name).unlink(missing_ok=True)

    def test_pretty_scatter_saves_plot(self) -> None:
        result = pretty_scatter(
            self.input_path.name,
            x="x",
            y="y",
            color="group",
            output_name="test_pretty_scatter.png",
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["saved_plot"]).exists())

    def test_output_name_rejects_directories(self) -> None:
        result = pretty_barplot(
            self.input_path.name,
            category="group",
            output_name="outputs/plots/test_pretty_bar.png",
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("filename only", result["message"])


if __name__ == "__main__":
    unittest.main()
