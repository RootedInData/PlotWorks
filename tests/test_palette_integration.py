from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PlotWorks.plot_styles.palettes import (
    GGRATEFUL_PALETTES,
    list_palette_catalog,
    validate_palette_choice,
)
from PlotWorks.tools import publication_plot_tools as publication
from PlotWorks.tools.r_bridge import _resolve_palette_choice, _safe_output_subfolder


class PaletteIntegrationTests(unittest.TestCase):
    def test_ggrateful_catalog_contains_all_documented_palettes(self) -> None:
        catalog = list_palette_catalog("ggrateful")["ggrateful"]["palettes"]
        self.assertEqual(len(catalog), 16)
        self.assertEqual(set(catalog), set(GGRATEFUL_PALETTES))
        self.assertTrue(catalog["best_of"]["continuous"])
        self.assertTrue(catalog["steal_your_face"]["diverging"])

    def test_palette_validation_rejects_unknown_name(self) -> None:
        with self.assertRaises(ValueError):
            validate_palette_choice("ggrateful", "not_a_palette")

    def test_palette_validation_normalizes_conversational_name(self) -> None:
        choice = validate_palette_choice("ggrateful", "Terrapin Station")
        self.assertEqual(choice["palette_name"], "terrapin_station")

    def test_explicit_palette_overrides_case_default(self) -> None:
        case = {
            "palette_default": {
                "provider": "ggrateful",
                "name": "bertha",
                "reverse": False,
            }
        }
        choice = _resolve_palette_choice(
            case,
            palette_provider="ggrateful",
            palette_name="terrapin_station",
            palette_reverse=True,
        )
        self.assertEqual(choice["palette_name"], "terrapin_station")
        self.assertTrue(choice["reverse"])
        self.assertEqual(choice["source"], "explicit_user_request")

    def test_safe_palette_output_subfolders(self) -> None:
        self.assertEqual(
            _safe_output_subfolder("palette_tests/06-raincloud/bertha"),
            Path("palette_tests/06-raincloud/bertha"),
        )
        with self.assertRaises(ValueError):
            _safe_output_subfolder("../outside")

    def test_every_case_has_palette_default_and_modes(self) -> None:
        manifest = json.loads(publication.settings.ggplot2_cases_manifest.read_text())
        self.assertEqual(len(manifest["cases"]), 20)
        for case in manifest["cases"]:
            self.assertIn("palette_default", case)
            self.assertIn("palette_modes", case)
            self.assertGreaterEqual(len(case["palette_modes"]), 1)

    def test_all_approved_r_cases_use_shared_palette_layer(self) -> None:
        root = publication.settings.ggplot2_cases_dir
        manifest = json.loads(publication.settings.ggplot2_cases_manifest.read_text())
        self.assertEqual(len(manifest["cases"]), 20)
        for case in manifest["cases"]:
            plot_path = root / case["case_dir"] / "plot.R"
            source = plot_path.read_text(encoding="utf-8")
            self.assertRegex(
                source,
                r"plotworks_(?:discrete|continuous|diverging)_values|shared/palettes\.R",
                msg=f"{case['case_id']} is not wired to the shared palette layer",
            )

    def test_setup_installs_ggrateful_through_remotes(self) -> None:
        setup = (publication.settings.ggplot2_cases_dir / "setup.R").read_text(
            encoding="utf-8"
        )
        self.assertIn('remotes::install_github("RandomForestz/ggrateful"', setup)
        self.assertIn('"ggrateful"', setup)

    def test_default_palette_write_uses_existing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "ggplot2_cases.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": "test",
                        "cases": [
                            {
                                "case_id": "01-error-dotplot",
                                "palette_default": {
                                    "provider": "recipe",
                                    "name": "",
                                    "reverse": False,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fake_settings = SimpleNamespace(ggplot2_cases_manifest=manifest_path)
            with patch.object(publication, "settings", fake_settings):
                result = publication.set_ggplot2_case_palette_default(
                    "01-error-dotplot", "ggrateful", "bertha", True
                )
            self.assertEqual(result["status"], "success")
            saved = json.loads(manifest_path.read_text())
            self.assertEqual(
                saved["cases"][0]["palette_default"],
                {"provider": "ggrateful", "name": "bertha", "reverse": True},
            )

    def test_standalone_selected_case_palette_runner_is_available(self) -> None:
        runner = Path(__file__).with_name("render_case_palette_variants.py")
        source = runner.read_text(encoding="utf-8")
        self.assertIn("--case", source)
        self.assertIn("--all", source)
        self.assertIn("--palettes", source)
        self.assertIn("render_ggplot2_case_demo", source)
        self.assertNotIn("render_all_" + "ggplot2_palette_variants", source)

        spec = importlib.util.spec_from_file_location("plotworks_palette_runner", runner)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        all_palettes = module.resolve_palettes(True, None)
        self.assertEqual(len(all_palettes), 16)
        selected = module.resolve_palettes(
            False, ["Terrapin Station", "bertha", "Terrapin Station"]
        )
        self.assertEqual(selected, ["terrapin_station", "bertha"])


if __name__ == "__main__":
    unittest.main()
