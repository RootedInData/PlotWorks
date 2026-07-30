from __future__ import annotations

import os
import unittest
from dataclasses import replace
from unittest.mock import patch

from PlotWorks.config import settings
from PlotWorks.tools.custom_r_plot_tools import validate_generated_r_plot_code


class CustomRValidationTests(unittest.TestCase):
    def test_valid_plot_contract(self) -> None:
        enabled = replace(settings, enable_custom_r_plotting=True)
        code = """
build_plot <- function(data) {
  ggplot(data, aes(x = x, y = y)) +
    geom_point() +
    theme_plotworks()
}
"""
        with patch("PlotWorks.tools.custom_r_plot_tools.settings", enabled):
            result = validate_generated_r_plot_code(code)
        self.assertEqual(result["status"], "success")

    def test_forbidden_system_call(self) -> None:
        enabled = replace(settings, enable_custom_r_plotting=True)
        code = """
build_plot <- function(data) {
  system("echo unsafe")
  ggplot(data, aes(x = x, y = y)) + geom_point()
}
"""
        with patch("PlotWorks.tools.custom_r_plot_tools.settings", enabled):
            result = validate_generated_r_plot_code(code)
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("system" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
