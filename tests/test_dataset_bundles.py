from __future__ import annotations

import json

import pandas as pd
from PlotWorks.tests.bundle_test_support import BundleTestCase
from PlotWorks.tools.data_tools import load_dataset_frame, resolve_data_path
from PlotWorks.tools.dataset_bundle_tools import (
    BUNDLES_KEY,
    discover_dataset_inputs,
    inspect_dataset_bundle,
    list_workbook_sheets,
    register_dataset_bundle,
)


class DatasetBundleTests(BundleTestCase):
    def test_registration_preserves_names_hashes_dtypes_and_serializable_state(self):
        self.source("traits.csv", "sample_id,value\n001,3\n002,\n")
        self.source("metadata.tsv", "sample_id\tgroup\n001\tA\n002\tB\n")
        descriptors = {
            name: {
                "file_path": filename,
                "loading_options": {"dtype": {"sample_id": "string"}},
            }
            for name, filename in (
                ("traits", "traits.csv"),
                ("metadata", "metadata.tsv"),
            )
        }
        result = register_dataset_bundle(json.dumps(descriptors), self.context)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(set(result["bundle"]["source_assets"]), {"traits", "metadata"})
        self.assertEqual(result["previews"]["traits"][0]["sample_id"], "001")
        self.assertEqual(
            result["bundle"]["inferred_relationships"][0]["status"],
            "candidate_only_requires_key_selection",
        )
        json.dumps(result, allow_nan=False)
        json.dumps(self.context.state, allow_nan=False)
        self.assertFalse(list(self.settings.transformed_data_output_dir.iterdir()))
        self.assertEqual(
            inspect_dataset_bundle(tool_context=self.context)["status"], "success"
        )

    def test_different_sheets_of_the_same_workbook_are_distinct_assets(self):
        path = self.settings.data_dir / "book.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({"id": [1], "trait": [10]}).to_excel(
                writer, sheet_name="Traits", index=False
            )
            pd.DataFrame({"id": [1], "group": ["A"]}).to_excel(
                writer, sheet_name="Samples", index=False
            )
        self.assertEqual(
            list_workbook_sheets(path.name)["sheets"], ["Traits", "Samples"]
        )
        result = register_dataset_bundle(
            json.dumps(
                {
                    "traits": {"file_path": path.name, "sheet_name": "Traits"},
                    "samples": {"file_path": path.name, "sheet_name": "Samples"},
                }
            ),
            self.context,
        )
        self.assertEqual(result["status"], "success", result)
        a, b = result["bundle"]["source_assets"].values()
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertNotEqual(a["columns"], b["columns"])

    def test_changed_registered_source_is_rejected(self):
        path = self.source("a.csv", "id\n1\n")
        registered = register_dataset_bundle('{"a":"a.csv"}', self.context)
        path.write_text("id\n2\n", encoding="utf-8")
        result = inspect_dataset_bundle(registered["bundle_id"], self.context)
        self.assertEqual(result["status"], "error")
        self.assertIn("changed", result["message"])

    def test_folder_discovery_is_scoped_and_does_not_register_files(self):
        self.source("study/a.csv", "id\n1\n")
        self.source("study/b.tsv", "id\n2\n")
        self.source("elsewhere.csv", "id\n3\n")
        result = discover_dataset_inputs("study", "*.csv")
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(len(result["files"]), 1)
        self.assertNotIn(BUNDLES_KEY, self.context.state)
        self.assertEqual(discover_dataset_inputs("../", "*")["status"], "error")

    def test_parent_traversal_and_symlink_escape_are_rejected(self):
        outside = self.settings.data_dir.parent / "outside.csv"
        outside.write_text("secret\n1\n", encoding="utf-8")
        with self.assertRaises(PermissionError):
            resolve_data_path("../outside.csv")
        link = self.settings.data_dir / "linked.csv"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(PermissionError):
            resolve_data_path("linked.csv")

    def test_custom_two_column_bed_like_table_retains_annotations(self):
        self.source("points.bed", "sequence\tlocus\tstudy_signal\nGm01\t120\tstrong\n")
        frame = load_dataset_frame(
            "points.bed", loading_options_json='{"format":"table"}'
        )
        self.assertEqual(list(frame), ["sequence", "locus", "study_signal"])
        self.assertEqual(frame.loc[0, "study_signal"], "strong")

    def test_descriptor_validation_rejects_empty_or_unknown_options(self):
        for raw in (
            "{}",
            "[]",
            '{"bad name":"x.csv"}',
            '{"a":{"file_path":"x.csv","unrecognized":1}}',
        ):
            with self.subTest(raw=raw):
                self.assertEqual(register_dataset_bundle(raw)["status"], "error")

    def test_package_relative_data_prefix_uses_configured_data_root(self):
        path = self.source("a.csv", "id\n1\n")
        self.assertEqual(resolve_data_path("data/a.csv"), path)
