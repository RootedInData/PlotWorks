from __future__ import annotations

import unittest

from PlotWorks.tools.animation_tools import validate_generated_r_animation_code


class AnimationValidationTests(unittest.TestCase):
    def test_valid_animation_contract(self) -> None:
        code = """
build_animation <- function(data) {
  ggplot(data, aes(x = x, y = y)) +
    geom_point() +
    transition_time(year) +
    theme_plotworks()
}
"""
        result = validate_generated_r_animation_code(code)
        self.assertEqual(result["status"], "success")

    def test_animation_cannot_save_itself(self) -> None:
        code = """
build_animation <- function(data) {
  p <- ggplot(data, aes(x = x, y = y)) + transition_time(year)
  anim_save("unsafe.gif", p)
  p
}
"""
        result = validate_generated_r_animation_code(code)
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("anim_save" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
