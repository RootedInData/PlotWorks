from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import settings
from .data_tools import _json_safe, load_dataset_frame, resolve_data_path

_ALLOWED_OUTPUT_SUFFIXES = {".csv", ".tsv", ".json", ".xlsx"}
_ALLOWED_AGGREGATIONS = {
    "count",
    "first",
    "last",
    "max",
    "mean",
    "median",
    "min",
    "nunique",
    "size",
    "std",
    "sum",
    "var",
}
_ALLOWED_DERIVE_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.BitAnd,
    ast.BitOr,
)

_FORBIDDEN_PYTHON_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
_FORBIDDEN_PYTHON_MODULES = {
    "builtins",
    "ctypes",
    "importlib",
    "io",
    "os",
    "pathlib",
    "pickle",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}
_FORBIDDEN_ATTRIBUTE_NAMES = {
    "dump",
    "dumps",
    "load",
    "loads",
    "read_csv",
    "read_excel",
    "read_feather",
    "read_fwf",
    "read_hdf",
    "read_html",
    "read_json",
    "read_orc",
    "read_parquet",
    "read_pickle",
    "read_sas",
    "read_sql",
    "read_stata",
    "read_table",
    "system",
    "popen",
    "environ",
    "urlopen",
    "connect",
    "to_clipboard",
    "to_csv",
    "to_excel",
    "to_feather",
    "to_hdf",
    "to_html",
    "to_json",
    "to_latex",
    "to_markdown",
    "to_orc",
    "to_parquet",
    "to_pickle",
    "to_sql",
    "to_stata",
    "to_xml",
}


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_output_path(output_name: str, default_stem: str) -> Path:
    raw = str(output_name).strip().strip('"').strip("'")
    if not raw:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw = f"{stamp}_{default_stem}_transformed.csv"

    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError("output_name must be relative to outputs/data/transformed")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError("output_name contains an unsafe path component")

    suffix = candidate.suffix.lower() or ".csv"
    if suffix not in _ALLOWED_OUTPUT_SUFFIXES:
        raise ValueError(
            "Transformed data output must be CSV, TSV, JSON, or XLSX"
        )
    if not candidate.suffix:
        candidate = candidate.with_suffix(suffix)

    safe_parts = [
        re.sub(r"[^A-Za-z0-9_.-]+", "_", part).strip("._") or "output"
        for part in candidate.parts
    ]
    safe_relative = Path(*safe_parts)
    destination = (settings.transformed_data_output_dir / safe_relative).resolve()
    root = settings.transformed_data_output_dir.resolve()
    if root not in destination.parents:
        raise ValueError("output_name must remain inside outputs/data/transformed")
    return destination


def _parse_operations(operations_json: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(str(operations_json))
    except json.JSONDecodeError as exc:
        raise ValueError(f"operations_json is not valid JSON: {exc}") from exc
    if not isinstance(parsed, list) or not parsed:
        raise ValueError("operations_json must be a non-empty JSON list")
    for index, operation in enumerate(parsed, start=1):
        if not isinstance(operation, dict):
            raise ValueError(f"Operation {index} must be a JSON object")
        if not str(operation.get("operation", "")).strip():
            raise ValueError(f"Operation {index} is missing the 'operation' field")
    return parsed


def _existing_columns(df: pd.DataFrame, columns: list[str], context: str) -> list[str]:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{context} references missing columns: {missing}")
    return columns


def _evaluate_derive_expression(df: pd.DataFrame, expression: str) -> pd.Series:
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_DERIVE_NODES):
            raise ValueError(
                f"Unsupported expression element in derive operation: {type(node).__name__}"
            )
        if isinstance(node, ast.Name) and node.id not in df.columns:
            raise ValueError(f"Derive expression references missing column: {node.id}")
    environment = {str(column): df[column] for column in df.columns}
    return eval(compile(tree, "<derive_expression>", "eval"), {"__builtins__": {}}, environment)


def _filter_mask(series: pd.Series, operator: str, value: Any) -> pd.Series:
    op = operator.strip().lower()
    if op == "eq":
        return series == value
    if op == "ne":
        return series != value
    if op in {"gt", "ge", "lt", "le"}:
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_value = float(value)
        return {
            "gt": numeric > numeric_value,
            "ge": numeric >= numeric_value,
            "lt": numeric < numeric_value,
            "le": numeric <= numeric_value,
        }[op]
    if op == "in":
        values = value if isinstance(value, list) else [value]
        return series.isin(values)
    if op == "not_in":
        values = value if isinstance(value, list) else [value]
        return ~series.isin(values)
    if op in {"contains", "startswith", "endswith"}:
        text = series.astype("string")
        pattern = str(value)
        if op == "contains":
            return text.str.contains(pattern, case=False, na=False, regex=False)
        if op == "startswith":
            return text.str.startswith(pattern, na=False)
        return text.str.endswith(pattern, na=False)
    if op == "isna":
        return series.isna()
    if op == "notna":
        return series.notna()
    raise ValueError(f"Unsupported filter operator: {operator}")


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = [
            "_".join(str(part) for part in column if str(part) not in {"", "None"})
            for column in result.columns.to_flat_index()
        ]
    else:
        result.columns = [str(column) for column in result.columns]
    return result


def _apply_operations(
    frame: pd.DataFrame, operations: list[dict[str, Any]]
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    df = frame.copy(deep=True)
    audit: list[dict[str, Any]] = []

    for index, operation in enumerate(operations, start=1):
        name = str(operation["operation"]).strip().lower()
        before_shape = [int(df.shape[0]), int(df.shape[1])]

        if name == "select_columns":
            columns = [str(value) for value in operation.get("columns", [])]
            _existing_columns(df, columns, name)
            df = df.loc[:, columns].copy()

        elif name == "drop_columns":
            columns = [str(value) for value in operation.get("columns", [])]
            _existing_columns(df, columns, name)
            df = df.drop(columns=columns)

        elif name == "rename_columns":
            mapping = {str(k): str(v) for k, v in operation.get("mapping", {}).items()}
            _existing_columns(df, list(mapping), name)
            if len(set(mapping.values())) != len(mapping.values()):
                raise ValueError("rename_columns produces duplicate target names")
            df = df.rename(columns=mapping)

        elif name == "filter_rows":
            column = str(operation.get("column", ""))
            _existing_columns(df, [column], name)
            operator = str(operation.get("operator", "eq"))
            mask = _filter_mask(df[column], operator, operation.get("value"))
            df = df.loc[mask.fillna(False)].copy()

        elif name == "convert_types":
            mapping = operation.get("mapping", {})
            _existing_columns(df, [str(column) for column in mapping], name)
            for column, target in mapping.items():
                target_name = str(target).strip().lower()
                if target_name in {"numeric", "float"}:
                    df[column] = pd.to_numeric(df[column], errors="coerce")
                elif target_name in {"integer", "int"}:
                    df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
                elif target_name in {"string", "text"}:
                    df[column] = df[column].astype("string")
                elif target_name == "category":
                    df[column] = df[column].astype("category")
                elif target_name in {"boolean", "bool"}:
                    df[column] = df[column].astype("boolean")
                elif target_name in {"datetime", "date"}:
                    df[column] = pd.to_datetime(df[column], errors="coerce")
                else:
                    raise ValueError(f"Unsupported target type: {target}")

        elif name == "fill_missing":
            values = operation.get("values", {})
            method = str(operation.get("method", "")).strip().lower()
            if values:
                _existing_columns(df, [str(column) for column in values], name)
                df = df.fillna(values)
            elif method in {"ffill", "bfill"}:
                df = df.ffill() if method == "ffill" else df.bfill()
            else:
                raise ValueError("fill_missing requires 'values' or method ffill/bfill")

        elif name == "drop_missing":
            subset = [str(value) for value in operation.get("subset", [])]
            if subset:
                _existing_columns(df, subset, name)
            how = str(operation.get("how", "any")).lower()
            if how not in {"any", "all"}:
                raise ValueError("drop_missing how must be 'any' or 'all'")
            df = df.dropna(subset=subset or None, how=how).copy()

        elif name == "drop_duplicates":
            subset = [str(value) for value in operation.get("subset", [])]
            if subset:
                _existing_columns(df, subset, name)
            keep = operation.get("keep", "first")
            if keep not in {"first", "last", False}:
                raise ValueError("drop_duplicates keep must be first, last, or false")
            df = df.drop_duplicates(subset=subset or None, keep=keep).copy()

        elif name == "replace_values":
            column = str(operation.get("column", ""))
            _existing_columns(df, [column], name)
            mapping = operation.get("mapping", {})
            df[column] = df[column].replace(mapping)

        elif name == "derive_column":
            target = str(operation.get("target", "")).strip()
            expression = str(operation.get("expression", "")).strip()
            if not target or not expression:
                raise ValueError("derive_column requires target and expression")
            df[target] = _evaluate_derive_expression(df, expression)

        elif name == "sort_values":
            columns = [str(value) for value in operation.get("columns", [])]
            _existing_columns(df, columns, name)
            ascending = operation.get("ascending", True)
            df = df.sort_values(columns, ascending=ascending).reset_index(drop=True)

        elif name == "aggregate":
            group_by = [str(value) for value in operation.get("group_by", [])]
            aggregations = operation.get("aggregations", {})
            _existing_columns(df, group_by + [str(column) for column in aggregations], name)
            for functions in aggregations.values():
                function_list = functions if isinstance(functions, list) else [functions]
                invalid = [str(fn) for fn in function_list if str(fn) not in _ALLOWED_AGGREGATIONS]
                if invalid:
                    raise ValueError(f"Unsupported aggregation functions: {invalid}")
            if group_by:
                df = df.groupby(group_by, dropna=False).agg(aggregations).reset_index()
            else:
                df = df.agg(aggregations).to_frame().T
            df = _flatten_columns(df)

        elif name == "pivot_table":
            index_columns = [str(value) for value in operation.get("index", [])]
            column_columns = [str(value) for value in operation.get("columns", [])]
            values = operation.get("values", [])
            value_columns = [str(values)] if isinstance(values, str) else [str(value) for value in values]
            _existing_columns(df, index_columns + column_columns + value_columns, name)
            aggfunc = str(operation.get("aggfunc", "first"))
            if aggfunc not in _ALLOWED_AGGREGATIONS:
                raise ValueError(f"Unsupported pivot aggfunc: {aggfunc}")
            df = pd.pivot_table(
                df,
                index=index_columns or None,
                columns=column_columns or None,
                values=value_columns or None,
                aggfunc=aggfunc,
                fill_value=operation.get("fill_value"),
                dropna=bool(operation.get("dropna", True)),
            ).reset_index()
            df = _flatten_columns(df)

        elif name == "melt":
            id_vars = [str(value) for value in operation.get("id_vars", [])]
            value_vars = [str(value) for value in operation.get("value_vars", [])]
            _existing_columns(df, id_vars + value_vars, name)
            df = df.melt(
                id_vars=id_vars or None,
                value_vars=value_vars or None,
                var_name=str(operation.get("var_name", "variable")),
                value_name=str(operation.get("value_name", "value")),
            )

        elif name == "reset_index":
            df = df.reset_index(drop=bool(operation.get("drop", True)))

        else:
            raise ValueError(f"Unsupported transformation operation: {name}")

        audit.append(
            {
                "step": index,
                "operation": name,
                "before_shape": before_shape,
                "after_shape": [int(df.shape[0]), int(df.shape[1])],
                "columns": [str(column) for column in df.columns],
            }
        )

    return df, audit


def list_data_transformation_operations() -> dict[str, Any]:
    """List deterministic data transformations supported by PlotWorks."""

    return _result(
        "success",
        operations=[
            "select_columns",
            "drop_columns",
            "rename_columns",
            "filter_rows",
            "convert_types",
            "fill_missing",
            "drop_missing",
            "drop_duplicates",
            "replace_values",
            "derive_column",
            "sort_values",
            "aggregate",
            "pivot_table",
            "melt",
            "reset_index",
        ],
        example_operations_json=json.dumps(
            [
                {
                    "operation": "filter_rows",
                    "column": "Element",
                    "operator": "in",
                    "value": ["Area harvested", "Yield"],
                },
                {
                    "operation": "pivot_table",
                    "index": ["Area", "Year"],
                    "columns": ["Element"],
                    "values": ["Value"],
                    "aggfunc": "first",
                },
                {
                    "operation": "rename_columns",
                    "mapping": {
                        "Value_Area harvested": "area_harvested",
                        "Value_Yield": "yield",
                    },
                },
            ]
        ),
        note=(
            "Preview operations first. Saving a transformed dataset requires explicit "
            "ADK user confirmation and always writes a new file under outputs/data/transformed."
        ),
    )


def preview_data_transformations(
    file_path: str,
    operations_json: str,
    sheet_name: str = "",
    preview_rows: int = 8,
) -> dict[str, Any]:
    """Apply deterministic transformations to an in-memory copy for review only."""

    try:
        source_path = resolve_data_path(file_path)
        source_hash = _sha256(source_path)
        source_frame = load_dataset_frame(file_path, sheet_name)
        operations = _parse_operations(operations_json)
        transformed, audit = _apply_operations(source_frame, operations)
        source_hash_after = _sha256(source_path)
        if source_hash != source_hash_after:
            raise RuntimeError("Source file changed unexpectedly during preview")
        return _result(
            "success",
            mode="preview_only",
            source_file=str(source_path),
            source_sha256=source_hash,
            source_unchanged=True,
            original_shape={"rows": int(source_frame.shape[0]), "columns": int(source_frame.shape[1])},
            transformed_shape={"rows": int(transformed.shape[0]), "columns": int(transformed.shape[1])},
            transformed_columns=[str(column) for column in transformed.columns],
            preview=transformed.head(max(1, min(int(preview_rows), 50))).to_dict(orient="records"),
            audit=audit,
            operations=operations,
            next_step=(
                "Present this preview and operation list to the user. Call the confirmed "
                "save_data_transformations tool only after approval."
            ),
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def _write_frame(frame: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = destination.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(destination, index=False)
    elif suffix == ".tsv":
        frame.to_csv(destination, sep="\t", index=False)
    elif suffix == ".json":
        frame.to_json(destination, orient="records", indent=2, date_format="iso")
    elif suffix == ".xlsx":
        frame.to_excel(destination, index=False)
    else:  # pragma: no cover - protected by path validation
        raise ValueError(f"Unsupported output suffix: {suffix}")


def save_data_transformations(
    file_path: str,
    operations_json: str,
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Save an approved deterministic transformation as a new managed dataset.

    This function is registered with ADK action confirmation. It never writes to the
    source path and verifies the source file hash before and after execution.
    """

    try:
        source_path = resolve_data_path(file_path)
        source_hash_before = _sha256(source_path)
        source_frame = load_dataset_frame(file_path, sheet_name)
        operations = _parse_operations(operations_json)
        transformed, audit = _apply_operations(source_frame, operations)
        destination = _safe_relative_output_path(output_name, source_path.stem)
        if destination == source_path.resolve():
            raise ValueError("Transformed output cannot overwrite the source dataset")
        _write_frame(transformed, destination)
        source_hash_after = _sha256(source_path)
        if source_hash_before != source_hash_after:
            destination.unlink(missing_ok=True)
            raise RuntimeError("Source file hash changed; transformed output was removed")

        metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
        metadata = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": str(source_path),
            "source_sha256_before": source_hash_before,
            "source_sha256_after": source_hash_after,
            "source_unchanged": True,
            "output_file": str(destination),
            "original_shape": [int(source_frame.shape[0]), int(source_frame.shape[1])],
            "transformed_shape": [int(transformed.shape[0]), int(transformed.shape[1])],
            "operations": operations,
            "audit": audit,
        }
        metadata_path.write_text(json.dumps(_json_safe(metadata), indent=2), encoding="utf-8")
        return _result(
            "success",
            saved_dataset=str(destination),
            plotting_input_path=str(destination),
            metadata_file=str(metadata_path),
            source_file=str(source_path),
            source_sha256=source_hash_before,
            source_unchanged=True,
            original_shape={"rows": int(source_frame.shape[0]), "columns": int(source_frame.shape[1])},
            transformed_shape={"rows": int(transformed.shape[0]), "columns": int(transformed.shape[1])},
            transformed_columns=[str(column) for column in transformed.columns],
            audit=audit,
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def validate_generated_python_transform_code(code: str) -> dict[str, Any]:
    """Statically validate generated Python limited to transform_data(data)."""

    source = str(code)
    errors: list[str] = []
    warnings: list[str] = []

    if not settings.enable_custom_data_transformations:
        errors.append(
            "Custom data transformations are disabled. Set "
            "ENABLE_CUSTOM_DATA_TRANSFORMATIONS=true to enable them."
        )
    if not source.strip():
        errors.append("No Python code was supplied.")
    if len(source) > settings.max_generated_transform_code_chars:
        errors.append(
            "Generated transformation code exceeds "
            f"MAX_GENERATED_TRANSFORM_CODE_CHARS={settings.max_generated_transform_code_chars}."
        )

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        errors.append(f"Python syntax error: {exc}")
        tree = None

    function_names: list[str] = []
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                errors.append("Import statements are not allowed; pd and np are supplied by the wrapper.")
            if isinstance(node, ast.FunctionDef):
                function_names.append(node.name)
            if isinstance(node, ast.Name) and node.id in _FORBIDDEN_PYTHON_NAMES | _FORBIDDEN_PYTHON_MODULES:
                errors.append(f"Forbidden Python name detected: {node.id}")
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("_"):
                    errors.append(f"Private/dunder attribute access is not allowed: {node.attr}")
                if node.attr in _FORBIDDEN_ATTRIBUTE_NAMES:
                    errors.append(f"File or serialization method is not allowed: {node.attr}")
            if isinstance(node, (ast.With, ast.AsyncWith, ast.ClassDef, ast.AsyncFunctionDef, ast.Lambda)):
                errors.append(f"Unsupported Python construct: {type(node).__name__}")

        top_level_functions = [
            node for node in tree.body if isinstance(node, ast.FunctionDef)
        ]
        matching = [
            node for node in top_level_functions if node.name == "transform_data"
        ]
        if len(matching) != 1 or len(top_level_functions) != 1:
            errors.append("Code must define exactly one top-level def transform_data(data).")
        else:
            function = matching[0]
            arg_names = [argument.arg for argument in function.args.args]
            if arg_names != ["data"]:
                errors.append("transform_data must accept exactly one positional argument named data.")
        extra_top_level = [
            node
            for node in tree.body
            if not isinstance(node, (ast.FunctionDef, ast.Expr))
            or (isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant))
        ]
        if extra_top_level:
            errors.append("Only the transform_data function and an optional module docstring are allowed at top level.")

    if "return" not in source:
        warnings.append("No return statement was detected; transform_data must return a DataFrame.")

    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    return _result(
        "success" if not errors else "error",
        valid=not errors,
        errors=errors,
        warnings=warnings,
        contract=(
            "Define def transform_data(data): and return a pandas DataFrame. "
            "Do not import modules, read or write files, access the network, or invoke system commands."
        ),
    )


def _generated_transform_wrapper_text(script_name: str) -> str:
    return f'''from __future__ import annotations
import json
import sys
import pandas as pd
import numpy as np

SAFE_BUILTINS = {{
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "zip": zip,
}}

input_path = sys.argv[1]
output_path = sys.argv[2]
script_path = {script_name!r}
data = pd.read_csv(input_path)
namespace = {{"pd": pd, "np": np, "__builtins__": SAFE_BUILTINS}}
with open(script_path, "r", encoding="utf-8") as handle:
    compiled = compile(handle.read(), script_path, "exec")
exec(compiled, namespace, namespace)
result = namespace["transform_data"](data.copy(deep=True))
if not isinstance(result, pd.DataFrame):
    raise TypeError("transform_data(data) must return a pandas DataFrame")
result.to_csv(output_path, index=False)
print(json.dumps({{"rows": int(result.shape[0]), "columns": int(result.shape[1]), "column_names": [str(c) for c in result.columns]}}))
'''


def execute_generated_python_transform(
    code: str,
    file_path: str,
    output_name: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Execute approved custom transformation code and save a new dataset.

    This function is registered with ADK action confirmation. Static validation and
    a restricted Python namespace reduce risk but do not provide an OS-level sandbox.
    """

    validation = validate_generated_python_transform_code(code)
    if validation.get("status") != "success":
        return _result(
            "error",
            message="Generated Python transformation code failed static validation.",
            validation=validation,
        )

    try:
        source_path = resolve_data_path(file_path)
        source_hash_before = _sha256(source_path)
        frame = load_dataset_frame(file_path, sheet_name)
        if frame.empty:
            raise ValueError("The selected dataset is empty")
        destination = _safe_relative_output_path(output_name, source_path.stem)
    except Exception as exc:
        return _result("error", message=str(exc))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{stamp}_{uuid.uuid4().hex[:8]}"
    run_dir = settings.code_output_dir / "data_transform_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_csv = run_dir / "input.csv"
    generated_script = run_dir / "generated_transform.py"
    wrapper_script = run_dir / "run_transform.py"
    temp_output = run_dir / "transformed.csv"
    metadata_path = run_dir / "run_metadata.json"

    frame.to_csv(input_csv, index=False)
    try:
        input_csv.chmod(0o444)
    except OSError:
        pass
    generated_script.write_text(code, encoding="utf-8")
    wrapper_script.write_text(
        _generated_transform_wrapper_text(generated_script.name), encoding="utf-8"
    )

    env = os.environ.copy()
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONHASHSEED": "0"})
    for key in list(env):
        if key.endswith("_API_KEY") or key in {"GOOGLE_APPLICATION_CREDENTIALS"}:
            env.pop(key, None)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", wrapper_script.name, str(input_csv), str(temp_output)],
            cwd=str(run_dir),
            env=env,
            text=True,
            capture_output=True,
            timeout=settings.data_transform_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _result(
            "error",
            message=(
                "Custom data transformation exceeded the "
                f"{settings.data_transform_timeout_seconds}-second timeout."
            ),
            generated_script=str(generated_script),
            run_directory=str(run_dir),
        )

    metadata = {
        "run_id": run_id,
        "source_file": str(source_path),
        "source_sha256_before": source_hash_before,
        "requested_output": str(destination),
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "validation": validation,
    }

    if proc.returncode != 0 or not temp_output.exists():
        metadata_path.write_text(json.dumps(_json_safe(metadata), indent=2), encoding="utf-8")
        return _result(
            "error",
            message="Custom Python data transformation failed.",
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            generated_script=str(generated_script),
            run_metadata=str(metadata_path),
        )

    transformed = pd.read_csv(temp_output)
    _write_frame(transformed, destination)
    source_hash_after = _sha256(source_path)
    if source_hash_before != source_hash_after:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Source file hash changed; transformed output was removed")

    metadata.update(
        {
            "source_sha256_after": source_hash_after,
            "source_unchanged": True,
            "saved_output": str(destination),
            "transformed_shape": [int(transformed.shape[0]), int(transformed.shape[1])],
            "transformed_columns": [str(column) for column in transformed.columns],
        }
    )
    metadata_path.write_text(json.dumps(_json_safe(metadata), indent=2), encoding="utf-8")
    output_metadata = destination.with_suffix(destination.suffix + ".metadata.json")
    output_metadata.write_text(json.dumps(_json_safe(metadata), indent=2), encoding="utf-8")

    return _result(
        "success",
        saved_dataset=str(destination),
        plotting_input_path=str(destination),
        output_metadata=str(output_metadata),
        generated_script=str(generated_script),
        run_metadata=str(metadata_path),
        source_file=str(source_path),
        source_sha256=source_hash_before,
        source_unchanged=True,
        original_shape={"rows": int(frame.shape[0]), "columns": int(frame.shape[1])},
        transformed_shape={"rows": int(transformed.shape[0]), "columns": int(transformed.shape[1])},
        transformed_columns=[str(column) for column in transformed.columns],
        warning=(
            "Custom data transformation code is experimental. Static validation and "
            "an isolated subprocess reduce risk but are not a full OS-level sandbox."
        ),
    )
