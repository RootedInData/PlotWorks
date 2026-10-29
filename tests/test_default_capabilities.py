from __future__ import annotations

import unittest
from pathlib import Path

from PlotWorks.config import settings


class DefaultCapabilitiesTests(unittest.TestCase):
    def test_generated_code_capabilities_do_not_require_feature_flags(self) -> None:
        root = Path(__file__).resolve().parents[1]
        env_example = (root / ".env.example").read_text(encoding="utf-8")
        removed_flags = (
            "ENABLE_CUSTOM_DATA_TRANSFORMATIONS",
            "ENABLE_CUSTOM_R_PLOTTING",
            "ENABLE_CUSTOM_R_ANIMATIONS",
        )

        for flag in removed_flags:
            self.assertNotIn(flag, env_example)

        self.assertFalse(hasattr(settings, "enable_custom_data_transformations"))
        self.assertFalse(hasattr(settings, "enable_custom_r_plotting"))
        self.assertFalse(hasattr(settings, "enable_custom_r_animations"))


if __name__ == "__main__":
    unittest.main()
