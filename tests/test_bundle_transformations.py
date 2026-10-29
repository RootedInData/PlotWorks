from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal
from PlotWorks.tests.bundle_test_support import BundleTestCase
from PlotWorks.tools.bundle_transformation_tools import (
    preview_bundle_transformations,
    preview_generated_bundle_transform,
    save_bundle_transformation,
)
from PlotWorks.tools.data_transformation_tools import (
    validate_generated_python_transform_code,
)
from PlotWorks.tools.dataset_bundle_tools import register_dataset_bundle
from PlotWorks.tools.generated_transform_runtime import run_generated_transform


class BundleTransformationTests(BundleTestCase):
    def setUp(self):
        super().setUp()
        self.a = self.source("traits.csv", "id,value\n001,10\n002,20\n003,30\n")
        self.b = self.source("meta.csv", "sample,group\n001,A\n002,B\n004,C\n")
        self.descriptors = {
            "traits": {
                "file_path": "traits.csv",
                "loading_options": {"dtype": {"id": "string"}},
            },
            "metadata": {
                "file_path": "meta.csv",
                "loading_options": {"dtype": {"sample": "string"}},
            },
        }
        self.operations = [
            {
                "operation": "join",
                "left": "traits",
                "right": "metadata",
                "left_on": "id",
                "right_on": "sample",
                "how": "left",
                "validate": "many_to_one",
                "output": "plot_ready",
            }
        ]
        registered = register_dataset_bundle(json.dumps(self.descriptors), self.context)
        self.assertEqual(registered["status"], "success", registered)
        self.bundle_id = registered["bundle_id"]

    def preview(self):
        result = preview_bundle_transformations(
            json.dumps(self.operations),
            bundle_id=self.bundle_id,
            output_names_json='{"plot_ready":"project/joined.csv"}',
            tool_context=self.context,
        )
        self.assertEqual(result["status"], "success", result)
        return result

    def test_preview_save_lineage_and_session_receipt(self):
        hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (self.a, self.b)
        }
        preview = self.preview()
        self.assertEqual(preview["audit"][0]["diagnostics"]["unmatched_right_rows"], 1)
        self.assertEqual(preview["outputs"]["plot_ready"]["preview"][0]["id"], "001")
        self.assertFalse(list(self.settings.transformed_data_output_dir.rglob("*.csv")))
        proposal = json.dumps(preview["proposal"])
        result = save_bundle_transformation(proposal, self.context)
        self.assertEqual(result["status"], "success", result)
        from PlotWorks.tools.data_tools import load_dataset_frame

        self.assertEqual(
            load_dataset_frame(result["saved_dataset"]).iloc[0]["id"], "001"
        )
        metadata = json.loads(Path(result["metadata_file"]).read_text())
        self.assertEqual(set(metadata["source_assets"]), {"traits", "metadata"})
        self.assertEqual(
            metadata["output_sha256"],
            hashlib.sha256(Path(result["saved_dataset"]).read_bytes()).hexdigest(),
        )
        for path, digest in hashes.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        json.dumps(self.context.state, allow_nan=False)
        again = save_bundle_transformation(proposal, self.context)
        self.assertTrue(again["already_saved"])
        self.assertEqual(again["saved_dataset"], result["saved_dataset"])

    def test_stale_input_or_altered_proposal_cannot_be_saved(self):
        preview = self.preview()
        changed = json.loads(json.dumps(preview["proposal"]))
        changed["operations"][0]["how"] = "inner"
        result = save_bundle_transformation(json.dumps(changed), self.context)
        self.assertEqual(result["status"], "error")
        self.assertIn("changed", result["message"])
        self.b.write_text("sample,group\n001,different\n", encoding="utf-8")
        result = save_bundle_transformation(
            json.dumps(preview["proposal"]), self.context
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("changed", result["message"])
        self.assertFalse(list(self.settings.transformed_data_output_dir.rglob("*.csv")))

    def test_session_cannot_save_a_proposal_from_another_session(self):
        from types import SimpleNamespace

        preview = self.preview()
        result = save_bundle_transformation(
            json.dumps(preview["proposal"]), SimpleNamespace(state={})
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("not previewed in this session", result["message"])

    def test_existing_outputs_are_never_overwritten(self):
        preview = self.preview()
        destination = self.settings.transformed_data_output_dir / "project/joined.csv"
        destination.parent.mkdir(parents=True)
        destination.write_text("keep me", encoding="utf-8")
        result = save_bundle_transformation(
            json.dumps(preview["proposal"]), self.context
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(destination.read_text(), "keep me")

    def test_partial_publication_is_rolled_back_without_deleting_existing_files(self):
        preview = self.preview()
        from PlotWorks.tools import bundle_transformation_tools as module

        original = module._publish_exclusive
        count = []

        def failing(source, destination, created):
            count.append(destination)
            if len(count) == 2:
                raise OSError("simulated publication failure")
            return original(source, destination, created)

        with patch.object(module, "_publish_exclusive", side_effect=failing):
            result = save_bundle_transformation(
                json.dumps(preview["proposal"]), self.context
            )
        self.assertEqual(result["status"], "error")
        self.assertFalse(list(self.settings.transformed_data_output_dir.rglob("*.csv")))

    def test_multiple_generated_inputs_and_outputs_are_published_with_lineage(self):
        code = """import pandas as pd

def clean(frame):
    return frame.assign(value=frame["value"].map(lambda x: x * 2))

def transform_data(datasets):
    joined = clean(datasets["traits"]).merge(datasets["metadata"], left_on="id", right_on="sample", how="left", validate="many_to_one")
    unmatched = joined[joined["group"].isna()].copy()
    return {"plot_ready": joined, "unmatched": unmatched}
"""
        preview = preview_generated_bundle_transform(
            code,
            bundle_id=self.bundle_id,
            output_names_json='{"plot_ready":"generated/ready.tsv","unmatched":"generated/unmatched.csv"}',
            tool_context=self.context,
        )
        self.assertEqual(preview["status"], "success", preview)
        self.assertEqual(preview["outputs"]["plot_ready"]["preview"][0]["id"], "001")
        self.assertEqual(preview["outputs"]["plot_ready"]["preview"][0]["value"], 20)
        result = save_bundle_transformation(
            json.dumps(preview["proposal"]), self.context
        )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(set(result["plotting_inputs"]), {"plot_ready", "unmatched"})
        self.assertTrue(Path(result["generated_script"]).exists())
        for asset in result["output_assets"]:
            self.assertEqual(
                set(
                    json.loads(Path(asset["metadata_file"]).read_text())[
                        "source_assets"
                    ]
                ),
                {"traits", "metadata"},
            )

    def test_runtime_transfer_preserves_nullable_dates_categories_and_leading_zeros(
        self,
    ):
        frame = pd.DataFrame(
            {
                "id": pd.Series(["001", "002"], dtype="string"),
                "count": pd.Series([1, None], dtype="Int64"),
                "time": pd.to_datetime(["2020-01-01", None]),
                "group": pd.Series(["A", "B"], dtype="category"),
            }
        )
        result, _ = run_generated_transform(
            "def transform_data(data):\n    return data", {"source": frame}
        )
        assert_frame_equal(result["result"], frame)

    def test_legacy_generated_contract_does_not_silently_choose_one_of_many_inputs(
        self,
    ):
        result = preview_generated_bundle_transform(
            "def transform_data(data):\n    return data",
            bundle_id=self.bundle_id,
            tool_context=self.context,
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("exactly one input", result["message"])

    def test_generated_output_shape_is_checked_again_after_preview(self):
        preview = self.preview()
        from PlotWorks.tools import bundle_transformation_tools as module

        original = module.apply_bundle_operations

        def changed(*args):
            outputs, audit, last = original(*args)
            outputs[last] = outputs[last].iloc[:1]
            return outputs, audit, last

        with patch.object(module, "apply_bundle_operations", side_effect=changed):
            result = save_bundle_transformation(
                json.dumps(preview["proposal"]), self.context
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("shape changed", result["message"])

    def test_codegen_validation_allows_analysis_but_blocks_external_effects(self):
        valid = 'import numpy as np\ndef helper(x):\n    return x * 2\ndef transform_data(datasets):\n    return {name: frame.assign(x=frame["value"].map(lambda x: helper(x))) for name, frame in datasets.items()}'
        self.assertTrue(validate_generated_python_transform_code(valid)["valid"])
        for body in (
            'open("/tmp/x", "w")',
            'pd.read_csv("secret.csv")',
            'data.to_csv("/tmp/x")',
            "import os",
            'pd.io.common.os.listdir("/")',
        ):
            code = "def transform_data(data):\n    " + body + "\n    return data"
            with self.subTest(body=body):
                self.assertFalse(
                    validate_generated_python_transform_code(code)["valid"]
                )

    def test_runtime_audit_blocks_unanticipated_file_writes(self):
        outside = self.settings.data_dir / "should_not_exist.txt"
        code = f"def transform_data(data):\n    data.to_string(buf={str(outside)!r})\n    return data"
        self.assertTrue(validate_generated_python_transform_code(code)["valid"])
        with self.assertRaisesRegex(ValueError, "outside its managed workspace"):
            run_generated_transform(code, {"source": pd.DataFrame({"x": [1]})})
        self.assertFalse(outside.exists())

    def test_runtime_timeout_is_enforced(self):
        limited = replace(self.settings, data_transform_timeout_seconds=1)
        with patch("PlotWorks.tools.generated_transform_runtime.settings", limited):
            with self.assertRaisesRegex(ValueError, "timeout"):
                run_generated_transform(
                    "def transform_data(data):\n    while True:\n        pass\n    return data",
                    {"source": pd.DataFrame({"x": [1]})},
                )

    def test_output_names_are_bound_and_collisions_rejected(self):
        result = preview_bundle_transformations(
            json.dumps(self.operations),
            bundle_id=self.bundle_id,
            output_names_json='{"plot_ready":"../../escape.csv"}',
            tool_context=self.context,
        )
        self.assertEqual(result["status"], "error")
        result = preview_generated_bundle_transform(
            'def transform_data(datasets):\n    return {"a": datasets["traits"], "b": datasets["metadata"]}',
            bundle_id=self.bundle_id,
            output_names_json='{"a":"same.csv","b":"same.csv"}',
            tool_context=self.context,
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("collide", result["message"])
