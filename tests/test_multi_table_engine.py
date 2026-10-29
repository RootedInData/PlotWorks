from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal
from PlotWorks.tests.bundle_test_support import BundleTestCase
from PlotWorks.tools.multi_table_engine import (
    apply_bundle_operations,
    interval_join,
    join_frames,
)


class MultiTableEngineTests(BundleTestCase):
    def setUp(self):
        super().setUp()
        self.left = pd.DataFrame({"id": [1, 2, 2, None], "value": [10, 20, 21, 99]})
        self.right = pd.DataFrame(
            {"sample": [2, 3, None], "group": ["A", "B", "unknown"]}
        )
        self.keys = {"left_on": ["id"], "right_on": ["sample"]}

    def test_join_variants_and_missing_keys_have_correct_row_counts(self):
        for how, rows in {
            "inner": 2,
            "left": 4,
            "right": 4,
            "outer": 6,
            "semi": 2,
            "anti": 2,
        }.items():
            with self.subTest(how=how):
                result, audit = join_frames(
                    self.left, self.right, {**self.keys, "how": how}
                )
                self.assertEqual(len(result), rows)
                self.assertEqual(audit["estimated_output_rows"], rows)
                self.assertEqual(audit["null_keys"], "never_match")
                self.assertEqual(audit["matched_left_rows"], 2)
                self.assertEqual(audit["unmatched_right_rows"], 2)
                self.assertEqual(audit["left_duplicate_key_rows"], 2)

    def test_null_matching_is_explicit(self):
        result, audit = join_frames(
            self.left, self.right, {**self.keys, "null_keys": "match"}
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(audit["left_missing_key_rows"], 1)
        self.assertEqual(audit["matched_right_rows"], 2)

    def test_multikey_join_with_different_key_names(self):
        left = pd.DataFrame({"a": [1, 1], "b": ["x", "y"]})
        right = pd.DataFrame({"c": [1, 1], "d": ["x", "z"], "n": [5, 6]})
        result, audit = join_frames(
            left,
            right,
            {
                "left_on": ["a", "b"],
                "right_on": ["c", "d"],
                "how": "left",
                "validate": "one_to_one",
            },
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "n"], 5)
        self.assertTrue(pd.isna(result.loc[1, "n"]))
        self.assertEqual(audit["cardinality"], "one_to_one")

    def test_many_to_many_is_supported_and_cardinality_validation_is_enforced(self):
        right = pd.DataFrame({"id": [2, 2], "x": ["a", "b"]})
        result, audit = join_frames(self.left, right, {"on": "id"})
        self.assertEqual(len(result), 4)
        self.assertTrue(audit["potential_row_multiplication"])
        self.assertEqual(audit["cardinality"], "many_to_many")
        with self.assertRaisesRegex(ValueError, "many_to_one"):
            join_frames(self.left, right, {"on": "id", "validate": "many_to_one"})

    def test_cross_join_is_bounded_before_materialization(self):
        result, _ = join_frames(self.left, self.right, {"how": "cross"})
        self.assertEqual(len(result), 12)
        limited = replace(self.settings, max_transform_rows=3)
        with patch("PlotWorks.tools.multi_table_engine.settings", limited):
            with self.assertRaisesRegex(ValueError, "MAX_TRANSFORM_ROWS"):
                join_frames(self.left, self.right, {"how": "cross"})

    def test_union_and_three_way_row_concat(self):
        a = pd.DataFrame({"id": [1, 2]})
        b = pd.DataFrame({"id": [2, 3]})
        c = pd.DataFrame({"id": [4]})
        for operation, expected in (
            ("union_all", 5),
            ("union_distinct", 4),
            ("concat_rows", 5),
        ):
            result, _, _ = apply_bundle_operations(
                {"a": a, "b": b, "c": c},
                [{"operation": operation, "inputs": ["a", "b", "c"]}],
            )
            self.assertEqual(len(result["result"]), expected)
        assert_frame_equal(a, pd.DataFrame({"id": [1, 2]}))

    def test_column_concat_requires_alignment_and_handles_collisions(self):
        frames = {"a": pd.DataFrame({"id": [1, 2]}), "b": pd.DataFrame({"id": [3, 4]})}
        with self.assertRaisesRegex(ValueError, "alignment"):
            apply_bundle_operations(
                frames, [{"operation": "concat_columns", "inputs": ["a", "b"]}]
            )
        with self.assertRaisesRegex(ValueError, "duplicate column"):
            apply_bundle_operations(
                frames,
                [
                    {
                        "operation": "concat_columns",
                        "inputs": ["a", "b"],
                        "alignment": "position",
                    }
                ],
            )
        outputs, _, _ = apply_bundle_operations(
            frames,
            [
                {
                    "operation": "concat_columns",
                    "inputs": ["a", "b"],
                    "alignment": "position",
                    "prefix_columns": True,
                }
            ],
        )
        self.assertEqual(list(outputs["result"]), ["a_id", "b_id"])

    def test_join_coalesce_and_single_table_steps_chain(self):
        frames = {
            "a": pd.DataFrame({"id": [1, 2], "x": [None, 4]}),
            "b": pd.DataFrame({"id": [1, 2], "fallback": [3, 5]}),
        }
        operations = [
            {
                "operation": "join",
                "left": "a",
                "right": "b",
                "on": "id",
                "output": "joined",
            },
            {
                "operation": "coalesce_columns",
                "columns": ["x", "fallback"],
                "target": "signal",
                "output": "coalesced",
            },
            {
                "operation": "select_columns",
                "columns": ["id", "signal"],
                "output": "plot_ready",
            },
        ]
        outputs, audit, last = apply_bundle_operations(frames, operations)
        self.assertEqual(last, "plot_ready")
        self.assertEqual(outputs[last]["signal"].tolist(), [3, 4])
        self.assertEqual(len(audit), 3)
        self.assertNotIn("signal", frames["a"])

    def test_ambiguous_initial_input_and_source_output_names_are_rejected(self):
        frames = {"a": self.left, "b": self.right}
        with self.assertRaisesRegex(ValueError, "Unknown dataset"):
            apply_bundle_operations(
                frames, [{"operation": "select_columns", "columns": ["id"]}]
            )
        with self.assertRaisesRegex(ValueError, "distinct from source"):
            apply_bundle_operations(
                frames,
                [
                    {
                        "operation": "select_columns",
                        "input": "a",
                        "columns": ["id"],
                        "output": "a",
                    }
                ],
            )

    def test_interval_endpoints_follow_declared_coordinate_conventions(self):
        left = pd.DataFrame({"seq": ["Gm01"], "start": [10], "end": [20]})
        right = pd.DataFrame(
            {
                "chr": ["Gm01", "Gm01", "Gm02"],
                "begin": [20, 15, 15],
                "stop": [30, 18, 18],
            }
        )
        op = {
            "left_chrom": "seq",
            "left_start": "start",
            "left_end": "end",
            "right_chrom": "chr",
            "right_start": "begin",
            "right_end": "stop",
        }
        with self.assertRaisesRegex(ValueError, "explicit coordinates"):
            interval_join(left, right, op)
        for coordinates, expected in (
            ("zero_based_half_open", 1),
            ("one_based_closed", 2),
        ):
            result, audit = interval_join(
                left, right, {**op, "coordinates": coordinates}
            )
            self.assertEqual(len(result), expected)
            self.assertEqual(audit["overlap_pairs"], expected)
