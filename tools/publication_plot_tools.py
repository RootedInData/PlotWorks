from __future__ import annotations

import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import settings
from .data_tools import _json_safe, load_dataset_frame, resolve_data_path
from .r_bridge import check_r_environment, run_ggplot2_case, validate_path_readability_for_r


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _load_manifest() -> dict[str, Any]:
    if not settings.ggplot2_cases_manifest.exists():
        raise FileNotFoundError(f"Missing plot manifest: {settings.ggplot2_cases_manifest}")
    return json.loads(settings.ggplot2_cases_manifest.read_text(encoding="utf-8"))


def _cases() -> list[dict[str, Any]]:
    return _load_manifest().get("cases", [])


def _case(case_id: str) -> dict[str, Any]:
    for item in _cases():
        if item.get("case_id") == case_id:
            return item
    raise ValueError(f"Unknown ggplot2 case_id: {case_id!r}")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.92
    return SequenceMatcher(None, na, nb).ratio()


def _best_column_match(role: str, candidates: list[str], columns: list[str], used: set[str]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for col in columns:
        if col in used:
            continue
        scores = [_similarity(col, role)] + [_similarity(col, cand) for cand in candidates]
        score = max(scores)
        if best is None or score > best["confidence"]:
            best = {"role": role, "column": col, "confidence": round(float(score), 3)}
    if best is None:
        return None
    if best["confidence"] >= 0.72:
        return best
    return None


def _decode_for_case(df: pd.DataFrame, case: dict[str, Any]) -> dict[str, Any]:
    columns = [str(c) for c in df.columns]
    used: set[str] = set()
    mapping: dict[str, str] = {}
    matches: list[dict[str, Any]] = []

    roles = case.get("column_roles", {})
    for role in case.get("expected_columns", []):
        match = _best_column_match(role, roles.get(role, []), columns, used)
        if match:
            mapping[role] = match["column"]
            used.add(match["column"])
            matches.append(match)

    optional_mapping: dict[str, str] = {}
    for role in case.get("optional_columns", []):
        match = _best_column_match(role, roles.get(role, []), columns, used)
        if match:
            optional_mapping[role] = match["column"]
            used.add(match["column"])
            matches.append({**match, "optional": True})

    missing_required = [role for role in case.get("expected_columns", []) if role not in mapping]
    required_count = max(len(case.get("expected_columns", [])), 1)
    score = round((required_count - len(missing_required)) / required_count, 3)

    return {
        "case_id": case.get("case_id"),
        "title": case.get("title"),
        "real_data_supported": bool(case.get("real_data_supported")),
        "support_score": score if case.get("real_data_supported") else 0.0,
        "mapping": mapping,
        "optional_mapping": optional_mapping,
        "matches": matches,
        "missing_required_columns": missing_required,
        "expected_columns": case.get("expected_columns", []),
        "optional_columns": case.get("optional_columns", []),
        "keywords": case.get("keywords", []),
    }


def _prepare_standardized_input(case: dict[str, Any], df: pd.DataFrame, decoded: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    mapping = decoded.get("mapping", {})
    optional_mapping = decoded.get("optional_mapping", {})
    out = pd.DataFrame()

    for role in case.get("expected_columns", []):
        src = mapping.get(role)
        if src is None:
            raise ValueError(f"Cannot standardize data; missing required role: {role}")
        out[role] = df[src]

    for role in case.get("optional_columns", []):
        src = optional_mapping.get(role)
        if src is not None:
            out[role] = df[src]

    case_id = case.get("case_id")
    if case_id == "03-multigroup-volcano" and "type" not in out.columns:
        out["type"] = np.where(pd.to_numeric(out["avg_log2FC"], errors="coerce") >= 0, "UP_Highly", "Down_Highly")
        warnings.append("Column 'type' was generated from avg_log2FC because no direction/type column was supplied.")

    if case_id == "04-manhattan-twas":
        out["BP"] = pd.to_numeric(out["BP"], errors="coerce")
        out["P"] = pd.to_numeric(out["P"], errors="coerce")
        missing_p = int(out["P"].isna().sum())
        if missing_p:
            warnings.append(f"{missing_p} rows had non-numeric or missing P values and may not plot correctly.")
        bad_p = int(((out["P"] <= 0) | (out["P"] > 1)).fillna(False).sum())
        if bad_p:
            warnings.append(
                f"{bad_p} rows have P values outside (0, 1]. Manhattan plots expect p-values."
            )
        if "gene" not in out.columns:
            out["gene"] = pd.NA
        if "chromStart" in df.columns or "chromEnd" in df.columns:
            warnings.append(
                "For BED-derived data, BP was mapped from the best available start/position column. "
                "If a genome sizes file is needed for other genome-wide plots, provide one explicitly."
            )

    if case_id == "07-swimmer":
        for bool_col in ["ongoing", "progression", "rt"]:
            if bool_col in out.columns:
                out[bool_col] = out[bool_col].astype(str).str.lower().isin({"true", "t", "1", "yes", "y"})
        for num_col in ["weeks", "rt_week"]:
            if num_col in out.columns:
                out[num_col] = pd.to_numeric(out[num_col], errors="coerce")

    if case_id in {"01-error-dotplot", "02-grouped-error-dotplot", "06-raincloud", "20-split-violin"}:
        value_cols = [col for col in ["value", "leafout"] if col in out.columns]
        for col in value_cols:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if case_id == "09-variance-bars":
        for col in ["mean", "se"]:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if case_id in {"17-multilevel-sankey", "18-treemap"} and "n" in out.columns:
        out["n"] = pd.to_numeric(out["n"], errors="coerce")

    if case_id == "20-split-violin":
        levels = set(out["risk"].dropna().astype(str).unique())
        expected = {"low-risk", "high-risk"}
        if not expected.issubset(levels):
            warnings.append(
                "Case 20 expects risk groups named 'low-risk' and 'high-risk'. "
                "Rename/recode your grouping column if the R plot does not render as expected."
            )

    return out, warnings


def list_ggplot2_cases(include_demo_only: bool = True) -> dict[str, Any]:
    """List approved ggplot2 publication-style plot cases.

    Args:
        include_demo_only: If false, return only cases currently configured for real tabular input.
    """

    try:
        cases = _cases()
        if not include_demo_only:
            cases = [c for c in cases if c.get("real_data_supported")]
        return _result(
            "success",
            cases=[
                {
                    "case_id": c.get("case_id"),
                    "title": c.get("title"),
                    "real_data_supported": c.get("real_data_supported"),
                    "expected_columns": c.get("expected_columns"),
                    "optional_columns": c.get("optional_columns"),
                    "keywords": c.get("keywords"),
                }
                for c in cases
            ],
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def check_publication_plot_setup(check_r_packages: bool = False) -> dict[str, Any]:
    """Check whether publication-style plotting can run on this system.

    Args:
        check_r_packages: If true, also ask R whether expected packages are installed.
    """

    manifest_ok = settings.ggplot2_cases_manifest.exists()
    r_check = check_r_environment(check_packages=check_r_packages)
    return _result(
        "success" if manifest_ok and r_check.get("status") == "success" else "error",
        manifest_path=str(settings.ggplot2_cases_manifest),
        manifest_found=manifest_ok,
        r_environment=r_check,
    )


def decode_column_roles(file_path: str, plot_case_id: str = "", sheet_name: str = "") -> dict[str, Any]:
    """Decode likely column roles for publication-style plot cases.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        plot_case_id: Optional specific ggplot2 case id to evaluate.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
    """

    try:
        df = load_dataset_frame(file_path, sheet_name)
        cases = [_case(plot_case_id)] if plot_case_id else [c for c in _cases() if c.get("real_data_supported")]
        decoded = [_decode_for_case(df, c) for c in cases]
        decoded = sorted(decoded, key=lambda x: x["support_score"], reverse=True)
        return _result(
            "success",
            file_path=str(resolve_data_path(file_path)),
            columns=[str(c) for c in df.columns],
            decoded_cases=decoded,
            guidance=(
                "Column matching is heuristic. Obvious variants such as start, Start, "
                "chrom_start, and chromStart are treated as similar, but uncertain mappings "
                "should be verified before submitting final figures."
            ),
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def match_ggplot2_cases_to_dataset(file_path: str, sheet_name: str = "") -> dict[str, Any]:
    """Rank approved ggplot2 cases by how well the dataset columns match each recipe.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
    """

    return decode_column_roles(file_path=file_path, plot_case_id="", sheet_name=sheet_name)


def render_ggplot2_case_demo(plot_case_id: str, output_name: str = "") -> dict[str, Any]:
    """Render a publication-style plot using the case's simulated data.

    Args:
        plot_case_id: Approved case id from list_ggplot2_cases.
        output_name: Optional output PNG filename.
    """

    try:
        _case(plot_case_id)  # validate approved case
        return run_ggplot2_case(plot_case_id, input_path="", output_path=output_name)
    except Exception as exc:
        return _result("error", message=str(exc))


def render_ggplot2_case(plot_case_id: str, file_path: str = "", sheet_name: str = "", output_name: str = "") -> dict[str, Any]:
    """Render an approved ggplot2 publication-style plot.

    Args:
        plot_case_id: Approved case id from list_ggplot2_cases.
        file_path: Optional real dataset path. If blank, use render_ggplot2_case_demo instead.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
        output_name: Optional output PNG filename.

    Notes:
        This tool never runs arbitrary user-supplied R code. It only calls approved plot recipes
        from the copied ggplot2_cases library using controlled arguments.
    """

    try:
        case = _case(plot_case_id)
    except Exception as exc:
        return _result("error", message=str(exc))

    if not file_path:
        return _result(
            "error",
            message=(
                "No input data file was provided. To make a demo plot from simulated data, "
                "call render_ggplot2_case_demo."
            ),
        )

    if not case.get("real_data_supported"):
        return _result(
            "error",
            message=f"Case {plot_case_id} is currently demo-only for predefined simulated data.",
            reason=(
                "This case expects a complex object such as a list, matrix, graph, or multiple "
                "linked tables rather than one simple data frame."
            ),
            supported_action="Use render_ggplot2_case_demo for this case, or adapt a controlled case-specific importer later.",
        )

    try:
        df = load_dataset_frame(file_path, sheet_name)
        decoded = _decode_for_case(df, case)
        if decoded["missing_required_columns"]:
            extra: dict[str, Any] = {}
            if Path(str(file_path)).suffix.lower() == ".bed" or set(["chrom", "chromStart", "chromEnd"]).issubset(df.columns):
                extra["bed_note"] = (
                    "This looks like BED-style data. The agency can inspect intervals and infer "
                    "chromosome sizes from max chromEnd, but some publication plots require extra "
                    "metadata such as p-values, scores, groups, or labels."
                )
            return _result(
                "error",
                message="The dataset does not contain enough recognizable columns for this plot case.",
                case_id=plot_case_id,
                title=case.get("title"),
                expected_columns=case.get("expected_columns"),
                recognized_mapping=decoded.get("mapping"),
                missing_required_columns=decoded["missing_required_columns"],
                guidance="Rename columns using standardized terms or choose another plot case.",
                **extra,
            )

        standardized, warnings = _prepare_standardized_input(case, df, decoded)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_dir = settings.plot_output_dir / "_standardized_inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        std_path = input_dir / f"{stamp}_{plot_case_id}_input.csv"
        standardized.to_csv(std_path, index=False)

        out_name = output_name or f"{stamp}_{plot_case_id}.png"
        run = run_ggplot2_case(plot_case_id, input_path=str(std_path), output_path=out_name)
        return _result(
            run.get("status", "error"),
            case_id=plot_case_id,
            title=case.get("title"),
            standardized_input=str(std_path),
            column_mapping=decoded.get("mapping"),
            optional_mapping=decoded.get("optional_mapping"),
            warnings=warnings,
            render_result=run,
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def validate_publication_plot_paths(file_path: str = "") -> dict[str, Any]:
    """Check that Python and R can read/write the paths needed for publication plots.

    Args:
        file_path: Optional dataset path. Relative paths are resolved inside DATA_DIR.
    """

    return validate_path_readability_for_r(input_path=file_path, output_dir=str(settings.plot_output_dir))
