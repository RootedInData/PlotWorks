"""Deterministic multi-table preparation with explicit keys and bounded joins."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import settings


def check_frame_limits(frame: pd.DataFrame) -> None:
    if len(frame.columns) == 0:
        raise ValueError("A derived dataset must contain at least one column")
    if len(frame) > settings.max_transform_rows:
        raise ValueError(
            f"Result exceeds MAX_TRANSFORM_ROWS={settings.max_transform_rows}"
        )
    if (
        int(frame.memory_usage(deep=True).sum())
        > settings.max_transform_memory_mb * 1024**2
    ):
        raise ValueError(
            f"Result exceeds MAX_TRANSFORM_MEMORY_MB={settings.max_transform_memory_mb}"
        )
    if frame.columns.has_duplicates:
        raise ValueError(
            "Transformation produces duplicate column names; rename or set suffixes explicitly"
        )


def _preflight_size(rows: int, left: pd.DataFrame, right: pd.DataFrame) -> None:
    if rows > settings.max_transform_rows:
        raise ValueError(
            f"Join would produce {rows} rows; MAX_TRANSFORM_ROWS={settings.max_transform_rows}"
        )
    row_bytes = sum(
        max(1, int(f.memory_usage(deep=True, index=False).sum()) // max(1, len(f)))
        for f in (left, right)
    )
    if rows * row_bytes > settings.max_transform_memory_mb * 1024**2:
        raise ValueError(
            "Estimated join memory exceeds MAX_TRANSFORM_MEMORY_MB; filter or aggregate first"
        )


def _keys(
    op: dict, left: pd.DataFrame, right: pd.DataFrame
) -> tuple[list[str], list[str]]:
    def as_list(value):
        return [value] if isinstance(value, str) else list(value or [])

    if op.get("on") and (op.get("left_on") or op.get("right_on")):
        raise ValueError("Use on or left_on/right_on, not both")
    left_keys = as_list(op.get("on") or op.get("left_on"))
    right_keys = as_list(op.get("on") or op.get("right_on"))
    if (
        not left_keys
        or len(left_keys) != len(right_keys)
        or len(set(left_keys)) != len(left_keys)
        or len(set(right_keys)) != len(right_keys)
    ):
        raise ValueError(
            "Join requires equal nonempty lists of distinct on or left_on/right_on keys"
        )
    for frame, columns, label in (
        (left, left_keys, "left"),
        (right, right_keys, "right"),
    ):
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f"Missing {label} join keys: {sorted(missing)}")
    return left_keys, right_keys


def _merge(left, right, lk, rk, how, null_keys, **kwargs):
    arguments = {"left_on": lk, "right_on": rk, "how": how, **kwargs}
    if null_keys == "match":
        return pd.merge(left, right, **arguments)
    lnull = left[lk].isna().any(axis=1)
    rnull = right[rk].isna().any(axis=1)
    parts = [pd.merge(left.loc[~lnull], right.loc[~rnull], **arguments)]
    # SQL-style missing keys remain unmatched. Empty-side merges preserve pandas'
    # normal output names and suffixes without mutating any original key values.
    extras = {k: v for k, v in arguments.items() if k not in {"how", "validate"}}
    if how in {"left", "outer"} and lnull.any():
        parts.append(pd.merge(left.loc[lnull], right.iloc[:0], how="left", **extras))
    if how in {"right", "outer"} and rnull.any():
        parts.append(pd.merge(left.iloc[:0], right.loc[rnull], how="right", **extras))
    if len(parts) == 1:
        return parts[0]
    return pd.concat(parts, ignore_index=True)


def join_frames(
    left: pd.DataFrame, right: pd.DataFrame, op: dict
) -> tuple[pd.DataFrame, dict]:
    how = str(op.get("how", "inner")).lower()
    how = {"full": "outer", "full_outer": "outer", "full outer": "outer"}.get(how, how)
    if how not in {"inner", "left", "right", "outer", "cross", "semi", "anti"}:
        raise ValueError(f"Unsupported join type: {how}")
    null_keys = op.get("null_keys", "never_match")
    if null_keys not in {"match", "never_match"}:
        raise ValueError("null_keys must be match or never_match")
    suffixes = op.get("suffixes", ["_x", "_y"])
    if (
        not isinstance(suffixes, list)
        or len(suffixes) != 2
        or not all(isinstance(s, str) for s in suffixes)
    ):
        raise ValueError("suffixes must contain two strings")
    if how == "cross":
        if any(op.get(k) for k in ("on", "left_on", "right_on")):
            raise ValueError("Cross joins do not take join keys")
        rows = len(left) * len(right)
        _preflight_size(rows, left, right)
        return pd.merge(left, right, how="cross", suffixes=tuple(suffixes)), {
            "how": how,
            "estimated_output_rows": rows,
            "potential_row_multiplication": rows > max(len(left), len(right)),
            "conflicting_columns": sorted(set(left) & set(right)),
            "null_keys": "not_applicable",
        }
    lk, rk = _keys(op, left, right)
    lmissing = left[lk].isna().any(axis=1)
    rmissing = right[rk].isna().any(axis=1)
    lvalid = left if null_keys == "match" else left.loc[~lmissing]
    rvalid = right if null_keys == "match" else right.loc[~rmissing]
    key_names = [f"key_{i}" for i in range(len(lk))]
    lc = (
        lvalid[lk]
        .set_axis(key_names, axis=1)
        .value_counts(dropna=False, sort=False)
        .rename("left_count")
        .reset_index()
    )
    rc = (
        rvalid[rk]
        .set_axis(key_names, axis=1)
        .value_counts(dropna=False, sort=False)
        .rename("right_count")
        .reset_index()
    )
    counts = pd.merge(lc, rc, on=key_names, how="outer")
    lcount = counts.left_count.fillna(0)
    rcount = counts.right_count.fillna(0)
    both = (lcount > 0) & (rcount > 0)
    pairs = sum(int(a) * int(b) for a, b in zip(lcount[both], rcount[both]))
    matched_left = int(lcount[both].sum())
    matched_right = int(rcount[both].sum())
    unmatched_left = len(left) - matched_left
    unmatched_right = len(right) - matched_right
    rows = {
        "inner": pairs,
        "left": pairs + unmatched_left,
        "right": pairs + unmatched_right,
        "outer": pairs + unmatched_left + unmatched_right,
        "semi": matched_left,
        "anti": unmatched_left,
    }[how]
    _preflight_size(rows, left, right)
    left_unique = not lvalid.duplicated(lk).any()
    right_unique = not rvalid.duplicated(rk).any()
    cardinality = (
        ("one" if left_unique else "many")
        + "_to_"
        + ("one" if right_unique else "many")
    )
    validate = op.get("validate", "many_to_many")
    aliases = {
        "1:1": "one_to_one",
        "1:m": "one_to_many",
        "m:1": "many_to_one",
        "m:m": "many_to_many",
    }
    validate = aliases.get(validate, validate)
    if validate not in {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}:
        raise ValueError(
            "validate must be one_to_one, one_to_many, many_to_one or many_to_many"
        )
    if (validate in {"one_to_one", "one_to_many"} and not left_unique) or (
        validate in {"one_to_one", "many_to_one"} and not right_unique
    ):
        raise ValueError(
            f"Join expected {validate}, but observed {cardinality}; inspect duplicate keys"
        )
    diagnostics = {
        "how": how,
        "left_keys": lk,
        "right_keys": rk,
        "left_key_dtypes": {k: str(left[k].dtype) for k in lk},
        "right_key_dtypes": {k: str(right[k].dtype) for k in rk},
        "left_duplicate_key_rows": int(lvalid.duplicated(lk, keep=False).sum()),
        "right_duplicate_key_rows": int(rvalid.duplicated(rk, keep=False).sum()),
        "left_missing_key_rows": int(lmissing.sum()),
        "right_missing_key_rows": int(rmissing.sum()),
        "cardinality": cardinality,
        "expected_cardinality": validate,
        "null_keys": null_keys,
        "matched_left_rows": matched_left,
        "matched_right_rows": matched_right,
        "matched_row_pairs": pairs,
        "unmatched_left_rows": unmatched_left,
        "unmatched_right_rows": unmatched_right,
        "estimated_output_rows": rows,
        "potential_row_multiplication": pairs > matched_left or pairs > matched_right,
        "conflicting_columns": sorted(
            (set(left) & set(right)) - {a for a, b in zip(lk, rk) if a == b}
        ),
        "unmatched_left_key_preview": counts.loc[
            (lcount > 0) & (rcount == 0), key_names
        ]
        .head(settings.max_preview_rows)
        .to_dict(orient="records"),
        "unmatched_right_key_preview": counts.loc[
            (rcount > 0) & (lcount == 0), key_names
        ]
        .head(settings.max_preview_rows)
        .to_dict(orient="records"),
    }
    if how in {"semi", "anti"}:
        marker = "_plotworks_left_row"
        while (
            marker in left
            or marker in right
            or marker + "_match" in left
            or marker + "_match" in right
        ):
            marker += "_"
        probe = left[lk].copy()
        probe[marker] = np.arange(len(left))
        indicator = marker + "_match"
        matched = _merge(
            probe,
            right[rk].drop_duplicates(),
            lk,
            rk,
            "left",
            null_keys,
            indicator=indicator,
        )
        ids = matched.loc[
            matched[indicator] == ("both" if how == "semi" else "left_only"), marker
        ]
        result = left.iloc[sorted(ids.astype(int).tolist())].copy()
    else:
        result = _merge(
            left,
            right,
            lk,
            rk,
            how,
            null_keys,
            suffixes=tuple(suffixes),
            validate=validate,
        )
    return result.reset_index(drop=True), diagnostics


def interval_join(
    left: pd.DataFrame, right: pd.DataFrame, op: dict
) -> tuple[pd.DataFrame, dict]:
    """Sweep interval endpoints; report exact overlap count without a chromosome cross product."""
    coordinates = op.get("coordinates")
    if coordinates not in {"zero_based_half_open", "one_based_closed"}:
        raise ValueError(
            "interval_join requires explicit coordinates: zero_based_half_open or one_based_closed; normalize differing conventions first"
        )

    def roles(side, frame):
        columns = [op.get(f"{side}_{role}", "") for role in ("chrom", "start", "end")]
        if not all(c in frame for c in columns) or len(set(columns)) != 3:
            raise ValueError(
                f"Declare distinct {side}_chrom, {side}_start and {side}_end columns"
            )
        start = pd.to_numeric(frame[columns[1]], errors="raise")
        end = pd.to_numeric(frame[columns[2]], errors="raise")
        invalid = (
            start.isna()
            | end.isna()
            | (start % 1 != 0)
            | (end % 1 != 0)
            | (start < (0 if coordinates == "zero_based_half_open" else 1))
        )
        invalid |= (
            (end <= start) if coordinates == "zero_based_half_open" else (end < start)
        )
        if invalid.any() or frame[columns[0]].isna().any():
            raise ValueError(f"Invalid {side} genomic intervals")
        return columns, start.astype("int64"), end.astype("int64")

    lcols, ls, le = roles("left", left)
    rcols, rs, re = roles("right", right)
    how = op.get("how", "inner")
    if how not in {"inner", "left", "right", "outer"}:
        raise ValueError("interval_join how must be inner, left, right or outer")
    events = {}
    # Zero-based half-open: end events precede start events at the same position.
    start_order, end_order = (1, 0) if coordinates == "zero_based_half_open" else (0, 1)
    for side, frame, cols, starts, ends in (
        (0, left, lcols, ls, le),
        (1, right, rcols, rs, re),
    ):
        for row, (chrom, start, end) in enumerate(
            zip(frame[cols[0]].astype(str), starts, ends)
        ):
            events.setdefault(chrom, []).extend(
                (
                    (int(start), start_order, side, row, True),
                    (int(end), end_order, side, row, False),
                )
            )
    pairs = []
    for chrom_events in events.values():
        active = [set(), set()]
        for _, _, side, row, is_start in sorted(chrom_events):
            if is_start:
                for other in sorted(active[1 - side]):
                    pairs.append((row, other) if side == 0 else (other, row))
                    if len(pairs) > settings.max_transform_rows:
                        raise ValueError("Interval overlap exceeds MAX_TRANSFORM_ROWS")
                active[side].add(row)
            else:
                active[side].discard(row)
    seen_left = {a for a, _ in pairs}
    seen_right = {b for _, b in pairs}
    overlaps = len(pairs)
    if how in {"left", "outer"}:
        pairs.extend((i, None) for i in range(len(left)) if i not in seen_left)
    if how in {"right", "outer"}:
        pairs.extend((None, i) for i in range(len(right)) if i not in seen_right)
    _preflight_size(len(pairs), left, right)
    # Nullable indices produce missing cells without assigning any genomic meaning
    # to study-specific annotation columns.
    a = (
        left.reset_index(drop=True)
        .reindex([i if i is not None else -1 for i, _ in pairs])
        .reset_index(drop=True)
    )
    b = (
        right.reset_index(drop=True)
        .reindex([i if i is not None else -1 for _, i in pairs])
        .reset_index(drop=True)
    )
    conflicts = set(a) & set(b)
    suffixes = op.get("suffixes", ["_x", "_y"])
    if (
        not isinstance(suffixes, list)
        or len(suffixes) != 2
        or not all(isinstance(x, str) for x in suffixes)
    ):
        raise ValueError("suffixes must contain two strings")
    a = a.rename(columns={c: c + suffixes[0] for c in conflicts})
    b = b.rename(columns={c: c + suffixes[1] for c in conflicts})
    return pd.concat([a, b], axis=1), {
        "coordinates": coordinates,
        "how": how,
        "overlap_pairs": overlaps,
        "unmatched_left_rows": len(left) - len(seen_left),
        "unmatched_right_rows": len(right) - len(seen_right),
        "estimated_output_rows": len(pairs),
        "potential_row_multiplication": overlaps > len(seen_left)
        or overlaps > len(seen_right),
    }


def apply_bundle_operations(
    frames: dict[str, pd.DataFrame], operations: list[dict]
) -> tuple[dict[str, pd.DataFrame], list[dict], str]:
    from .data_transformation_tools import _apply_operations

    tables = {name: frame.copy(deep=True) for name, frame in frames.items()}
    derived = {}
    audit = []
    current = next(iter(frames)) if len(frames) == 1 else ""

    def table(name):
        if name not in tables:
            raise ValueError(f"Unknown dataset {name!r}; select one of {list(tables)}")
        return tables[name]

    for step, raw in enumerate(operations, 1):
        op = dict(raw)
        name = str(op["operation"]).lower().strip()
        output = op.get("output", "result")
        if not isinstance(output, str) or not output or output in frames:
            raise ValueError(
                "output must name a derived dataset, distinct from source dataset IDs"
            )
        diagnostics = {}
        if name in {
            "join",
            "merge",
            "append_metadata",
            "inner_join",
            "left_join",
            "right_join",
            "full_join",
            "cross_join",
            "semi_join",
            "anti_join",
        }:
            if name.endswith("_join"):
                op["how"] = name.removesuffix("_join")
            if name == "append_metadata":
                op.setdefault("how", "left")
                op.setdefault("validate", "many_to_one")
            left_name = op.get("left", op.get("input", current))
            right_name = op.get("right", "")
            result, diagnostics = join_frames(table(left_name), table(right_name), op)
            inputs = [left_name, right_name]
        elif name == "interval_join":
            inputs = [op.get("left", current), op.get("right", "")]
            result, diagnostics = interval_join(table(inputs[0]), table(inputs[1]), op)
        elif name in {
            "concat",
            "concat_rows",
            "concat_columns",
            "union_all",
            "union_distinct",
        }:
            inputs = op.get("inputs", [])
            if not isinstance(inputs, list) or not inputs:
                raise ValueError(
                    "Concatenation requires a nonempty inputs list of dataset IDs"
                )
            selected = [table(n) for n in inputs]
            axis = 1 if name == "concat_columns" else int(op.get("axis", 0))
            if axis == 1 and name not in {"concat", "concat_columns"}:
                raise ValueError("Row concatenation and unions require axis=0")
            if axis not in {0, 1}:
                raise ValueError("concat axis must be 0 or 1")
            alignment = op.get("alignment", "")
            if axis == 1:
                if alignment not in {"position", "index"}:
                    raise ValueError(
                        "Column concatenation requires alignment=position or index"
                    )
                if alignment == "position":
                    if len({len(f) for f in selected}) != 1:
                        raise ValueError(
                            "Position-aligned column concatenation requires equal row counts"
                        )
                    selected = [f.reset_index(drop=True) for f in selected]
                elif any(not f.index.is_unique for f in selected):
                    raise ValueError("Index alignment requires unique indices")
                if op.get("prefix_columns", False):
                    selected = [f.add_prefix(n + "_") for n, f in zip(inputs, selected)]
            join = op.get("join", "outer")
            if join not in {"inner", "outer"}:
                raise ValueError("concat join must be inner or outer")
            if (
                axis == 0
                and sum(len(f) for f in selected) > settings.max_transform_rows
            ):
                raise ValueError("Concatenation exceeds MAX_TRANSFORM_ROWS")
            result = pd.concat(selected, axis=axis, join=join, ignore_index=(axis == 0))
            if name == "union_distinct":
                result = result.drop_duplicates().reset_index(drop=True)
            diagnostics = {
                "axis": axis,
                "join": join,
                "alignment": alignment or "rows",
                "duplicates_removed": name == "union_distinct",
            }
        else:
            selected = op.get("input", current)
            frame = table(selected)
            inputs = [selected]
            if name == "coalesce_columns":
                columns = op.get("columns", [])
                target = op.get("target", "")
                if not columns or not target or any(c not in frame for c in columns):
                    raise ValueError(
                        "coalesce_columns requires existing columns and a target"
                    )
                result = frame.copy(deep=True)
                values = frame[columns[0]].copy()
                for column in columns[1:]:
                    values = values.combine_first(frame[column])
                result[target] = values
            else:
                result, _ = _apply_operations(frame, [op])
        check_frame_limits(result)
        tables[output] = result
        derived[output] = result
        current = output
        audit.append(
            {
                "step": step,
                "operation": name,
                "inputs": inputs,
                "output": output,
                "shape": [len(result), len(result.columns)],
                "diagnostics": diagnostics,
            }
        )
    return derived, audit, current
