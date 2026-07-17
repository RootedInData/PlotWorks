from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import settings


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if np.isnan(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if obj is pd.NA:
        return None
    return obj


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _resolve_data_path(file_path: str) -> Path:
    clean = file_path.strip().strip('"').strip("'")
    candidate = Path(clean).expanduser()

    if candidate.is_absolute():
        if not settings.allow_absolute_data_paths:
            raise PermissionError(
                "Absolute paths are disabled. Place the data file inside DATA_DIR "
                f"instead: {settings.data_dir.resolve()}"
            )
        path = candidate.resolve()
    else:
        path = (settings.data_dir / candidate).resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.is_dir():
        raise IsADirectoryError(f"Expected a file, got directory: {path}")

    max_bytes = settings.max_file_mb * 1024 * 1024
    if path.stat().st_size > max_bytes:
        raise ValueError(
            f"File exceeds MAX_FILE_MB={settings.max_file_mb}: {path.name}"
        )

    return path


def _load_dataset(file_path: str, sheet_name: str = "") -> pd.DataFrame:
    path = _resolve_data_path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".tsv", ".tab"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".xlsx", ".xls"}:
        selected_sheet = sheet_name if sheet_name else 0
        return pd.read_excel(path, sheet_name=selected_sheet)
    if suffix == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    if suffix in {".txt", ".data"}:
        return pd.read_csv(path, sep=None, engine="python")

    raise ValueError(
        f"Unsupported file type: {suffix}. Supported: .csv, .tsv, .tab, "
        ".xlsx, .xls, .json, .txt, .data"
    )


def list_available_datasets() -> dict[str, Any]:
    """List supported dataset files in the configured DATA_DIR."""

    supported = {".csv", ".tsv", ".tab", ".xlsx", ".xls", ".json", ".txt", ".data"}
    files = []
    for path in sorted(settings.data_dir.glob("**/*")):
        if path.is_file() and path.suffix.lower() in supported:
            files.append(
                {
                    "relative_path": str(path.relative_to(settings.data_dir)),
                    "size_mb": round(path.stat().st_size / 1_000_000, 3),
                    "suffix": path.suffix.lower(),
                }
            )

    return _result("success", data_dir=str(settings.data_dir.resolve()), files=files)


def inspect_dataset(file_path: str, sheet_name: str = "") -> dict[str, Any]:
    """Inspect a local dataset's structure and format.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
    """

    try:
        path = _resolve_data_path(file_path)
        df = _load_dataset(file_path, sheet_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    rows, cols = df.shape
    column_profiles = []

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        column_profiles.append(
            {
                "column": str(col),
                "dtype": str(series.dtype),
                "missing_count": int(series.isna().sum()),
                "missing_percent": round(float(series.isna().mean() * 100), 2),
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": non_null.head(settings.max_preview_rows).astype(str).tolist(),
            }
        )

    return _result(
        "success",
        file_path=str(path),
        shape={"rows": rows, "columns": cols},
        memory_usage_mb=round(float(df.memory_usage(deep=True).sum() / 1_000_000), 3),
        duplicate_rows=int(df.duplicated().sum()),
        columns=column_profiles,
        likely_id_columns=[
            str(col)
            for col in df.columns
            if rows > 0 and df[col].nunique(dropna=True) / rows > 0.95
        ],
        empty_columns=[str(col) for col in df.columns if df[col].isna().sum() == rows],
        constant_columns=[str(col) for col in df.columns if df[col].nunique(dropna=True) <= 1],
    )


def run_eda(file_path: str, sheet_name: str = "") -> dict[str, Any]:
    """Run deterministic exploratory data analysis using pandas.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
    """

    try:
        df = _load_dataset(file_path, sheet_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    rows, cols = df.shape
    numeric_df = df.select_dtypes(include=[np.number])
    categorical_df = df.select_dtypes(include=["object", "category", "bool"])

    missingness = (
        df.isna()
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"index": "column", 0: "missing_count"})
    )
    missingness["missing_percent"] = (missingness["missing_count"] / max(rows, 1) * 100).round(2)

    numeric_summary = {}
    if not numeric_df.empty:
        numeric_summary = (
            numeric_df.describe()
            .T.round(4)
            .replace([np.inf, -np.inf], np.nan)
            .to_dict(orient="index")
        )

    categorical_summary = {}
    for col in categorical_df.columns[:30]:
        counts = categorical_df[col].astype("string").fillna("<MISSING>").value_counts().head(10)
        categorical_summary[str(col)] = {
            "unique_count": int(categorical_df[col].nunique(dropna=True)),
            "top_values": {str(k): int(v) for k, v in counts.items()},
        }

    correlations = []
    if numeric_df.shape[1] >= 2:
        corr_df = numeric_df.corr(numeric_only=True)
        columns = list(corr_df.columns)
        for i, col_a in enumerate(columns):
            for col_b in columns[i + 1 :]:
                value = corr_df.loc[col_a, col_b]
                if pd.notna(value):
                    correlations.append(
                        {
                            "feature_a": str(col_a),
                            "feature_b": str(col_b),
                            "correlation": round(float(value), 4),
                            "abs_correlation": round(abs(float(value)), 4),
                        }
                    )
        correlations = sorted(correlations, key=lambda x: x["abs_correlation"], reverse=True)[:15]

    outliers = {}
    for col in numeric_df.columns[:50]:
        s = numeric_df[col].dropna()
        if s.empty:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            count = 0
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            count = int(((s < lower) | (s > upper)).sum())
        outliers[str(col)] = {
            "iqr_outlier_count": count,
            "iqr_outlier_percent": round(float(count / max(len(s), 1) * 100), 2),
        }

    warnings = []
    high_missing = missingness[missingness["missing_percent"] >= 30]
    if not high_missing.empty:
        warnings.append(
            {
                "type": "high_missingness",
                "columns": high_missing["column"].astype(str).head(20).tolist(),
            }
        )

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        warnings.append(
            {
                "type": "duplicate_rows",
                "count": duplicate_rows,
                "percent": round(float(duplicate_rows / max(rows, 1) * 100), 2),
            }
        )

    constant_columns = [str(col) for col in df.columns if df[col].nunique(dropna=True) <= 1]
    if constant_columns:
        warnings.append({"type": "constant_or_empty_columns", "columns": constant_columns[:30]})

    return _result(
        "success",
        shape={"rows": rows, "columns": cols},
        column_type_counts={
            "numeric": int(numeric_df.shape[1]),
            "categorical_or_boolean": int(categorical_df.shape[1]),
            "other": int(cols - numeric_df.shape[1] - categorical_df.shape[1]),
        },
        missingness_top_20=missingness.head(20).to_dict(orient="records"),
        numeric_summary=numeric_summary,
        categorical_summary=categorical_summary,
        top_numeric_correlations=correlations,
        outlier_summary=outliers,
        warnings=warnings,
    )


def create_basic_charts(file_path: str, sheet_name: str = "", output_prefix: str = "eda") -> dict[str, Any]:
    """Create basic charts for numeric and categorical columns.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
        output_prefix: Prefix for saved chart filenames.
    """

    try:
        df = _load_dataset(file_path, sheet_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)[:5]
    for col in numeric_cols:
        fig = plt.figure()
        df[col].dropna().plot(kind="hist", bins=30)
        plt.title(f"Distribution of {col}")
        plt.xlabel(str(col))
        plt.ylabel("Frequency")
        out = settings.output_dir / f"{output_prefix}_{col}_hist.png"
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        saved.append(str(out))

    cat_cols = list(df.select_dtypes(include=["object", "category", "bool"]).columns)[:3]
    for col in cat_cols:
        counts = df[col].astype("string").fillna("<MISSING>").value_counts().head(15)
        fig = plt.figure()
        counts.plot(kind="bar")
        plt.title(f"Top values: {col}")
        plt.xlabel(str(col))
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        out = settings.output_dir / f"{output_prefix}_{col}_bar.png"
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        saved.append(str(out))

    return _result("success", saved_charts=saved, output_dir=str(settings.output_dir.resolve()))
