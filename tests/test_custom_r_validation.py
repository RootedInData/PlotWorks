from __future__ import annotations

import os
import unittest
from dataclasses import replace
from unittest.mock import patch

from Data_analysis_agency.config import settings
from Data_analysis_agency.tools.custom_r_plot_tools import validate_generated_r_plot_code


class CustomRValidationTests(unittest.TestCase):
    def test_valid_plot_contract(self) -> None:
        enabled = replace(settings, enable_custom_r_plotting=True)
        code = """
build_plot <- function(data) {
  ggplot(data, aes(x = x, y = y)) +
    geom_point() +
    theme_agency()
}
"""
        with patch("Data_analysis_agency.tools.custom_r_plot_tools.settings", enabled):
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
        with patch("Data_analysis_agency.tools.custom_r_plot_tools.settings", enabled):
            result = validate_generated_r_plot_code(code)
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("system" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
