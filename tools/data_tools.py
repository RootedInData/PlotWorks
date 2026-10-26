from __future__ import annotations

import gzip
import hashlib
import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import settings

BED_COLUMNS = [
    "chrom",
    "chromStart",
    "chromEnd",
    "name",
    "score",
    "strand",
    "thickStart",
    "thickEnd",
    "itemRgb",
    "blockCount",
    "blockSizes",
    "blockStarts",
]
SUPPORTED_SUFFIXES = {
    ".csv",
    ".tsv",
    ".tab",
    ".xlsx",
    ".xls",
    ".json",
    ".txt",
    ".data",
    ".bed",
}


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
        if not np.isfinite(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.datetime64):
        return None if np.isnat(obj) else pd.Timestamp(obj).isoformat()
    if isinstance(obj, pd.Timedelta):
        return str(obj)
    if obj is pd.NaT:
        return None
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, np.ndarray):
        return _json_safe(obj.tolist())
    if isinstance(obj, (pd.Timestamp, date, datetime)):
        return obj.isoformat()
    if obj is pd.NA:
        return None
    return obj


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def resolve_data_path(file_path: str) -> Path:
    """Resolve source or PlotWorks-managed transformed data safely.

    Relative paths are searched first inside ``data/`` and then inside
    ``outputs/data/``. Absolute paths returned by PlotWorks tools are accepted when
    they remain inside those managed directories. Other absolute paths require
    ``ALLOW_ABSOLUTE_DATA_PATHS=true``.
    """

    clean = str(file_path).strip().strip('"').strip("'")
    candidate = Path(clean).expanduser()
    managed_roots = [
        settings.data_dir.resolve(),
        settings.data_output_dir.resolve(),
        settings.transformed_data_output_dir.resolve(),
    ]

    if candidate.is_absolute():
        resolved = candidate.resolve()
        managed = any(
            root == resolved or root in resolved.parents for root in managed_roots
        )
        if not managed and not settings.allow_absolute_data_paths:
            raise PermissionError(
                "Absolute paths outside PlotWorks-managed data directories are disabled. "
                f"Place source data in {settings.data_dir.resolve()} or use a transformed "
                f"dataset under {settings.data_output_dir.resolve()}."
            )
        path = resolved
    else:
        if ".." in candidate.parts:
            raise PermissionError(
                "Relative input paths cannot traverse parent directories"
            )
        if candidate.parts and candidate.parts[0] == "data":
            candidate = Path(*candidate.parts[1:])
        candidates = [
            (settings.data_dir / candidate).resolve(),
            (settings.data_output_dir / candidate).resolve(),
        ]
        # Allow a tool-returned package-relative path such as outputs/data/transformed/x.csv.
        if candidate.parts and candidate.parts[0] == "outputs":
            candidates.insert(0, (settings.package_dir / candidate).resolve())
        if any(
            item.exists()
            and not any(item.is_relative_to(root) for root in managed_roots)
            for item in candidates
        ):
            raise PermissionError(
                "Input symlink resolves outside managed data directories"
            )
        candidates = [
            item
            for item in candidates
            if any(item.is_relative_to(root) for root in managed_roots)
        ]
        if not candidates:
            raise PermissionError(
                "Input path resolves outside managed data directories"
            )
        path = next((item for item in candidates if item.exists()), candidates[0])

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


def _suffix(path: Path) -> str:
    if path.name.lower().endswith(".bed.gz"):
        return ".bed.gz"
    return path.suffix.lower()


def _open_text(path: Path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def _bed_data_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with _open_text(path) as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if (
                lower.startswith("track")
                or lower.startswith("browser")
                or stripped.startswith("#")
            ):
                continue
            lines.append(stripped)
    return lines


def load_bed_file(file_path: str) -> pd.DataFrame:
    """Load a BED file into a DataFrame with standard BED column names."""

    path = resolve_data_path(file_path)
    lines = _bed_data_lines(path)
    if not lines:
        raise ValueError(
            "BED file contains no data rows after skipping track/browser/comment lines."
        )

    split_rows = [line.split("\t") if "\t" in line else line.split() for line in lines]
    field_counts = {len(row) for row in split_rows}
    max_fields = max(field_counts)
    min_fields = min(field_counts)
    if min_fields < 3:
        raise ValueError(
            "BED files require at least 3 columns: chrom, chromStart, chromEnd."
        )

    # BED optional fields should usually be consistent, but real files sometimes
    # have missing trailing optional fields. Pad those rows instead of failing.
    split_rows = [row + [pd.NA] * (max_fields - len(row)) for row in split_rows]
    n_fields = max_fields

    if n_fields <= len(BED_COLUMNS):
        columns = BED_COLUMNS[:n_fields]
    else:
        columns = BED_COLUMNS + [f"extra_{i}" for i in range(13, n_fields + 1)]

    df = pd.DataFrame(split_rows, columns=columns)
    for col in [
        "chromStart",
        "chromEnd",
        "score",
        "thickStart",
        "thickEnd",
        "blockCount",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if {"chromStart", "chromEnd"}.issubset(df.columns):
        df["interval_length"] = df["chromEnd"] - df["chromStart"]

    return df


def _managed_schema_options(path: Path) -> dict[str, Any]:
    if not path.is_relative_to(settings.transformed_data_output_dir.resolve()):
        return {}
    sidecar = path.with_suffix(path.suffix + ".metadata.json")
    if not sidecar.is_file():
        return {}
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    asset = metadata.get("output_asset", {})
    if not asset.get("loading_options"):
        return {}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != asset.get("sha256"):
        raise ValueError(
            "Managed dataset changed since saving; verify it before reusing its recorded schema"
        )
    return dict(asset["loading_options"])


def load_dataset_frame(
    file_path: str, sheet_name: str = "", loading_options_json: str = ""
) -> pd.DataFrame:
    """Load a supported dataset file into a pandas DataFrame."""

    path = resolve_data_path(file_path)
    suffix = _suffix(path)

    supplied_options = json.loads(loading_options_json) if loading_options_json else {}
    if not isinstance(supplied_options, dict):
        raise ValueError("loading_options_json must be a JSON object")
    options = {**_managed_schema_options(path), **supplied_options}
    allowed = {
        "dtype",
        "header",
        "names",
        "sep",
        "na_values",
        "keep_default_na",
        "parse_dates",
        "skiprows",
        "usecols",
        "encoding",
        "format",
    }
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError(
            "Unsupported loading options; use dtype, header, names, sep, na_values, keep_default_na, parse_dates, skiprows, usecols, encoding, format"
        )
    if isinstance(options.get("dtype"), dict) and not all(
        isinstance(v, str) for v in options["dtype"].values()
    ):
        raise ValueError("dtype must use pandas dtype names as strings")
    selected_format = options.pop("format", "")
    if selected_format not in {"", "table"}:
        raise ValueError("loading_options format must be table when specified")
    table_mode = selected_format == "table"
    if suffix == ".csv":
        return pd.read_csv(path, **options)
    if suffix in {".tsv", ".tab"}:
        options.setdefault("sep", "\t")
        return pd.read_csv(path, **options)
    if suffix in {".xlsx", ".xls"}:
        selected_sheet = sheet_name if sheet_name else 0
        options.pop("encoding", None)
        options.pop("sep", None)
        return pd.read_excel(path, sheet_name=selected_sheet, **options)
    if suffix == ".json":
        if "parse_dates" in options:
            options["convert_dates"] = options.pop("parse_dates")
        try:
            return pd.read_json(path, **options)
        except ValueError:
            return pd.read_json(path, lines=True, **options)
    if suffix in {".txt", ".data"}:
        options.setdefault("sep", None)
        return pd.read_csv(path, engine="python", **options)
    if suffix in {".bed", ".bed.gz"}:
        if table_mode:
            options.setdefault("sep", "\t")
            options.setdefault("comment", "#")
            return pd.read_csv(path, **options)
        if options:
            raise ValueError(
                "Use loading_options format=table for custom BED-like headers or column types"
            )
        return load_bed_file(file_path)

    raise ValueError(
        f"Unsupported file type: {suffix}. Supported: .csv, .tsv, .tab, "
        ".xlsx, .xls, .json, .txt, .data, .bed, .bed.gz"
    )


def _load_dataset(file_path: str, sheet_name: str = "") -> pd.DataFrame:
    return load_dataset_frame(file_path, sheet_name)


def _bed_summary(df: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if {"chrom", "chromStart", "chromEnd"}.issubset(df.columns):
        chrom_counts = df["chrom"].astype(str).value_counts().head(50)
        inferred_sizes_df = (
            df.groupby("chrom", dropna=False)["chromEnd"]
            .max()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"chromEnd": "inferred_size_from_max_chromEnd"})
        )
        summary.update(
            {
                "bed_field_count": len(
                    [
                        c
                        for c in df.columns
                        if c in BED_COLUMNS or c.startswith("extra_")
                    ]
                ),
                "chromosome_or_scaffold_count": int(df["chrom"].nunique(dropna=True)),
                "top_chromosomes_or_scaffolds": {
                    str(k): int(v) for k, v in chrom_counts.items()
                },
                "inferred_chromosome_sizes_top_50": inferred_sizes_df.head(50).to_dict(
                    orient="records"
                ),
                "coordinate_system_note": (
                    "BED convention uses zero-based chromStart and half-open chromEnd. "
                    "Interval length is chromEnd - chromStart."
                ),
            }
        )
    if "interval_length" in df.columns:
        lengths = df["interval_length"].dropna()
        if not lengths.empty:
            summary["interval_length_summary"] = {
                "min": float(lengths.min()),
                "median": float(lengths.median()),
                "mean": float(lengths.mean()),
                "max": float(lengths.max()),
            }
    if "score" in df.columns:
        score = pd.to_numeric(df["score"], errors="coerce").dropna()
        if not score.empty:
            summary["score_summary"] = {
                "min": float(score.min()),
                "median": float(score.median()),
                "mean": float(score.mean()),
                "max": float(score.max()),
            }
    if "strand" in df.columns:
        summary["strand_counts"] = {
            str(k): int(v) for k, v in df["strand"].astype(str).value_counts().items()
        }
    return summary


def infer_bed_chrom_sizes(
    file_path: str, genome_sizes_path: str = ""
) -> dict[str, Any]:
    """Infer or read chromosome sizes for a BED file.

    Args:
        file_path: BED file path. Relative paths are resolved inside DATA_DIR.
        genome_sizes_path: Optional two-column genome sizes file with chrom and size.

    Returns:
        A dictionary with explicit genome sizes when supplied, otherwise sizes inferred
        from the maximum chromEnd present in the BED file.
    """

    try:
        bed = load_bed_file(file_path)
        if genome_sizes_path:
            sizes_path = resolve_data_path(genome_sizes_path)
            sizes = pd.read_csv(
                sizes_path,
                sep=None,
                engine="python",
                header=None,
                names=["chrom", "size"],
            )
            sizes["size"] = pd.to_numeric(sizes["size"], errors="coerce")
            return _result(
                "success",
                mode="provided_genome_sizes_file",
                genome_sizes_path=str(sizes_path),
                chromosome_sizes=sizes.dropna().to_dict(orient="records"),
            )

        inferred = (
            bed.groupby("chrom", dropna=False)["chromEnd"]
            .max()
            .reset_index()
            .rename(columns={"chromEnd": "size"})
            .sort_values("chrom")
        )
        return _result(
            "success",
            mode="inferred_from_bed_max_chromEnd",
            warning=(
                "No genome sizes file was provided. Sizes were inferred from the maximum "
                "chromEnd in the BED file. This may underestimate true chromosome lengths "
                "if the BED file does not cover chromosome ends."
            ),
            chromosome_sizes=inferred.to_dict(orient="records"),
        )
    except Exception as exc:
        return _result("error", message=str(exc))


def list_available_datasets() -> dict[str, Any]:
    """List source datasets and PlotWorks-managed transformed datasets."""

    files = []
    locations = [
        ("source", settings.data_dir),
        ("transformed", settings.transformed_data_output_dir),
    ]
    for kind, root in locations:
        for path in sorted(root.glob("**/*")):
            suffix = _suffix(path)
            if path.is_file() and (suffix in SUPPORTED_SUFFIXES or suffix == ".bed.gz"):
                files.append(
                    {
                        "kind": kind,
                        "relative_path": str(path.relative_to(root)),
                        "managed_path": str(path.resolve()),
                        "size_mb": round(path.stat().st_size / 1_000_000, 3),
                        "suffix": suffix,
                    }
                )

    return _result(
        "success",
        source_data_dir=str(settings.data_dir.resolve()),
        transformed_data_dir=str(settings.transformed_data_output_dir.resolve()),
        files=files,
    )


def inspect_dataset(file_path: str, sheet_name: str = "") -> dict[str, Any]:
    """Inspect a local dataset's structure and format.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
    """

    try:
        path = resolve_data_path(file_path)
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
                "sample_values": non_null.head(settings.max_preview_rows)
                .astype(str)
                .tolist(),
            }
        )

    suffix = _suffix(path)
    extras: dict[str, Any] = {}
    if suffix in {".bed", ".bed.gz"}:
        extras["bed_summary"] = _bed_summary(df)
        extras["format_notes"] = [
            "BED files are read as tab-delimited genomic intervals.",
            "The first three columns are interpreted as chrom, chromStart, and chromEnd.",
            "track, browser, and comment lines are ignored during loading.",
        ]

    return _result(
        "success",
        file_path=str(path),
        file_type=suffix,
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
        constant_columns=[
            str(col) for col in df.columns if df[col].nunique(dropna=True) <= 1
        ],
        **extras,
    )


def run_eda(file_path: str, sheet_name: str = "") -> dict[str, Any]:
    """Run deterministic exploratory data analysis using pandas.

    Args:
        file_path: Dataset path. Relative paths are resolved inside DATA_DIR.
        sheet_name: Optional Excel sheet name. Leave blank for the first sheet.
    """

    try:
        path = resolve_data_path(file_path)
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
    missingness["missing_percent"] = (
        missingness["missing_count"] / max(rows, 1) * 100
    ).round(2)

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
        counts = (
            categorical_df[col]
            .astype("string")
            .fillna("<MISSING>")
            .value_counts()
            .head(10)
        )
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
        correlations = sorted(
            correlations, key=lambda x: x["abs_correlation"], reverse=True
        )[:15]

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

    constant_columns = [
        str(col) for col in df.columns if df[col].nunique(dropna=True) <= 1
    ]
    if constant_columns:
        warnings.append(
            {"type": "constant_or_empty_columns", "columns": constant_columns[:30]}
        )

    extras: dict[str, Any] = {}
    if _suffix(path) in {".bed", ".bed.gz"}:
        extras["bed_summary"] = _bed_summary(df)

    return _result(
        "success",
        file_type=_suffix(path),
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
        **extras,
    )


def create_basic_charts(
    file_path: str, sheet_name: str = "", output_prefix: str = "eda"
) -> dict[str, Any]:
    """Backward-compatible wrapper around the polished Python chart system.

    New code should call ``create_pretty_charts`` or an individual ``pretty_*``
    function. This wrapper remains so existing prompts and saved workflows do not break.
    """

    from .pretty_plot_tools import create_pretty_charts

    return create_pretty_charts(
        file_path=file_path,
        sheet_name=sheet_name,
        output_prefix=output_prefix,
    )
