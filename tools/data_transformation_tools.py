from __future__ import annotations

import ast
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

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
    "load",
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
        raw = f"{stamp}_{default_stem}_{uuid.uuid4().hex[:8]}_transformed.csv"

    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError("output_name must be relative to outputs/data/transformed")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError("output_name contains an unsafe path component")

    suffix = candidate.suffix.lower() or ".csv"
    if suffix not in _ALLOWED_OUTPUT_SUFFIXES:
        raise ValueError("Transformed data output must be CSV, TSV, JSON, or XLSX")
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
    return eval(
        compile(tree, "<derive_expression>", "eval"), {"__builtins__": {}}, environment
    )


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
                    df[column] = pd.to_numeric(df[column], errors="coerce").astype(
                        "Int64"
                    )
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
            _existing_columns(
                df, group_by + [str(column) for column in aggregations], name
            )
            for functions in aggregations.values():
                function_list = (
                    functions if isinstance(functions, list) else [functions]
                )
                invalid = [
                    str(fn)
                    for fn in function_list
                    if str(fn) not in _ALLOWED_AGGREGATIONS
                ]
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
            value_columns = (
                [str(values)]
                if isinstance(values, str)
                else [str(value) for value in values]
            )
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
        bundle_operations=[
            "join",
            "merge",
            "concat_rows",
            "concat_columns",
            "union_all",
            "union_distinct",
            "append_metadata",
            "coalesce_columns",
            "interval_join",
        ],
        bundle_preview_tool="preview_bundle_transformations",
        bundle_example={
            "operation": "join",
            "left": "traits",
            "right": "metadata",
            "on": ["sample_id"],
            "how": "left",
            "validate": "many_to_one",
            "null_keys": "never_match",
            "output": "plot_ready",
        },
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
            original_shape={
                "rows": int(source_frame.shape[0]),
                "columns": int(source_frame.shape[1]),
            },
            transformed_shape={
                "rows": int(transformed.shape[0]),
                "columns": int(transformed.shape[1]),
            },
            transformed_columns=[str(column) for column in transformed.columns],
            preview=transformed.head(max(1, min(int(preview_rows), 50))).to_dict(
                orient="records"
            ),
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
    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing data: {destination.name}"
        )
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
    file_path: str, operations_json: str, output_name: str = "", sheet_name: str = ""
) -> dict[str, Any]:
    """Backward-compatible confirmed single-file save through the bundle publisher.

    New agent workflows use the explicit preview-bound bundle interface. This
    legacy Python API retains its original signature and computes its own proposal.
    """
    from .bundle_transformation_tools import (
        preview_bundle_transformations,
        save_bundle_transformation,
    )

    preview = preview_bundle_transformations(
        operations_json=operations_json,
        datasets_json=json.dumps(
            {"source": {"file_path": file_path, "sheet_name": sheet_name}}
        ),
        output_names_json=json.dumps({"result": output_name}) if output_name else "",
    )
    if preview.get("status") != "success":
        return preview
    result = save_bundle_transformation(json.dumps(preview["proposal"]))
    if result.get("status") == "success":
        asset = preview["proposal"]["bundle"]["source_assets"]["source"]
        result.update(
            {
                "source_file": asset["file_path"],
                "source_sha256": asset["sha256"],
                "original_shape": {
                    "rows": asset["rows"],
                    "columns": len(asset["columns"]),
                },
            }
        )
    return result


def validate_generated_python_transform_code(code: str) -> dict[str, Any]:
    """Validate a transformation function while allowing ordinary analytical Python.

    Both transform_data(data) and transform_data(datasets) are supported. Helper
    functions, comprehensions, lambdas and approved analytical imports are allowed.
    This is application validation; process isolation is documented in the README.
    """
    from .generated_transform_runtime import allowed_imports

    source = str(code)
    errors: list[str] = []
    warnings: list[str] = []
    if not source.strip():
        errors.append("No Python code was supplied.")
    if len(source) > settings.max_generated_transform_code_chars:
        errors.append(
            "Generated transformation code exceeds MAX_GENERATED_TRANSFORM_CODE_CHARS"
        )
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return _result(
            "error", valid=False, errors=[f"Python syntax error: {exc}"], warnings=[]
        )
    imports = allowed_imports()
    blocked_attributes = (
        _FORBIDDEN_ATTRIBUTE_NAMES
        | _FORBIDDEN_PYTHON_NAMES
        | _FORBIDDEN_PYTHON_MODULES
        | {
            "savefig",
            "imsave",
            "ctypes",
            "save",
            "savez",
            "savez_compressed",
            "fromfile",
            "tofile",
            "memmap",
            "ctypeslib",
            "f2py",
            "get_handle",
            "get_data",
            "DataSource",
            "ExcelWriter",
            "HDFStore",
            "read_xml",
            "read_spss",
            "read_gbq",
            "loadtxt",
            "genfromtxt",
            "savetxt",
            "read",
            "write",
            "execfile",
            "fetch",
            "download",
            "request",
            "getenv",
            "putenv",
            "remove",
            "unlink",
            "rmdir",
            "chdir",
            "mkdir",
            "makedirs",
        }
    )
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if isinstance(node, ast.ImportFrom) and (
                node.level or any(a.name == "*" for a in node.names)
            ):
                errors.append("Relative and wildcard imports are not allowed")
            for module in modules:
                if module.split(".")[0] not in imports or any(
                    p.startswith("_") for p in module.split(".")
                ):
                    errors.append(f"Import is not approved: {module}")
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in blocked_attributes or alias.name.startswith("_"):
                        errors.append(
                            f"Imported operation is not allowed: {alias.name}"
                        )
        if isinstance(node, ast.Name) and (
            node.id in _FORBIDDEN_PYTHON_NAMES | _FORBIDDEN_PYTHON_MODULES
            or node.id.startswith("__")
        ):
            errors.append(f"Forbidden Python name detected: {node.id}")
        if isinstance(node, ast.Attribute) and (
            node.attr.startswith("_") or node.attr in blocked_attributes
        ):
            errors.append(
                f"File, system or private operation is not allowed: {node.attr}"
            )
        if isinstance(
            node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Global, ast.Nonlocal)
        ):
            errors.append(f"Unsupported Python construct: {type(node).__name__}")
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            errors.append("Function decorators are not supported")
    matching = [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "transform_data"
    ]
    contract = ""
    if len(matching) != 1:
        errors.append("Define exactly one top-level transform_data function")
    else:
        args = matching[0].args
        names = [a.arg for a in args.posonlyargs + args.args]
        if (
            names not in (["data"], ["datasets"])
            or args.vararg
            or args.kwarg
            or args.kwonlyargs
            or args.defaults
        ):
            errors.append(
                "transform_data must accept exactly one argument named data or datasets"
            )
        else:
            contract = names[0]
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            continue
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        errors.append(
            "Only imports, function definitions and a module docstring are allowed at top level"
        )
    if not any(isinstance(n, ast.Return) for n in ast.walk(tree)):
        warnings.append("No return statement detected")
    errors = list(dict.fromkeys(errors))
    return _result(
        "success" if not errors else "error",
        valid=not errors,
        errors=errors,
        warnings=warnings,
        input_contract=contract,
        approved_imports=sorted(imports),
        contract="Return a DataFrame or a dict of named DataFrames. PlotWorks loads inputs and saves outputs; generated code must not read/write files or access system/network services.",
    )


def execute_generated_python_transform(
    code: str, file_path: str, output_name: str = "", sheet_name: str = ""
) -> dict[str, Any]:
    """Backward-compatible confirmed single-input execution using the bundle runtime."""
    from .bundle_transformation_tools import (
        preview_generated_bundle_transform,
        save_bundle_transformation,
    )

    preview = preview_generated_bundle_transform(
        code=code,
        datasets_json=json.dumps(
            {"source": {"file_path": file_path, "sheet_name": sheet_name}}
        ),
        output_names_json=json.dumps({"result": output_name}) if output_name else "",
    )
    if preview.get("status") != "success":
        return preview
    result = save_bundle_transformation(json.dumps(preview["proposal"]))
    if result.get("status") == "success":
        result["original_shape"] = {
            "rows": preview["proposal"]["bundle"]["source_assets"]["source"]["rows"],
            "columns": len(
                preview["proposal"]["bundle"]["source_assets"]["source"]["columns"]
            ),
        }
        result["source_file"] = preview["proposal"]["bundle"]["source_assets"][
            "source"
        ]["file_path"]
        result["source_sha256"] = preview["proposal"]["bundle"]["source_assets"][
            "source"
        ]["sha256"]
    return result
