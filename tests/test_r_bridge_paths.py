from __future__ import annotations

import unittest

from PlotWorks.tools.r_bridge import _safe_managed_filename


class RBridgePathTests(unittest.TestCase):
    def test_bare_filename_is_accepted(self) -> None:
        self.assertEqual(_safe_managed_filename("demo.png", "default.png"), "demo.png")

    def test_prefixed_output_directory_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _safe_managed_filename("outputs/plots/demo.png", "default.png")


if __name__ == "__main__":
    unittest.main()
