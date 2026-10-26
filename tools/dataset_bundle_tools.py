"""Named, immutable source registration and session-scoped dataset metadata."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from google.adk.tools.tool_context import ToolContext
except ModuleNotFoundError:  # local tools remain usable without the agent framework
    ToolContext = Any

from ..config import settings
from ..contracts import DataAsset, DatasetBundle
from .data_tools import (
    SUPPORTED_SUFFIXES,
    _json_safe,
    _suffix,
    load_dataset_frame,
    resolve_data_path,
)

BUNDLES_KEY = "plotworks:dataset_bundles"
ACTIVE_BUNDLE_KEY = "plotworks:active_bundle_id"
PROPOSALS_KEY = "plotworks:transformation_proposals"
ARTIFACTS_KEY = "plotworks:derived_assets"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", str(name)):
        raise ValueError(
            f"Dataset ID {name!r} must start with a letter and use letters, digits, _ or -"
        )
    return name


def _descriptors(datasets_json: str) -> dict[str, dict]:
    try:
        raw = json.loads(datasets_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "datasets_json must be a named JSON object of file descriptors"
        ) from exc
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Provide at least one named dataset")
    if len(raw) > settings.max_bundle_datasets:
        raise ValueError(
            f"Too many datasets; MAX_BUNDLE_DATASETS={settings.max_bundle_datasets}"
        )
    result = {}
    for name, value in raw.items():
        _asset_name(name)
        item = {"file_path": value} if isinstance(value, str) else value
        if not isinstance(item, dict) or not isinstance(item.get("file_path"), str):
            raise ValueError(f"Dataset {name} requires file_path")
        allowed = {
            "file_path",
            "sheet_name",
            "loading_options",
            "roles",
            "coordinate_convention",
        }
        if set(item) - allowed:
            raise ValueError(
                f"Unknown dataset descriptor fields for {name}: {sorted(set(item) - allowed)}"
            )
        result[name] = item
    return result


def verify_sources(bundle: DatasetBundle) -> None:
    for name, asset in bundle.source_assets.items():
        path = resolve_data_path(asset.file_path)
        if file_sha256(path) != asset.sha256:
            raise ValueError(
                f"Source {name} changed since registration or preview; register and preview again"
            )


def load_bundle(
    datasets_json: str = "", bundle_id: str = "", tool_context=None
) -> tuple[DatasetBundle, dict[str, pd.DataFrame]]:
    if datasets_json and bundle_id:
        raise ValueError("Supply datasets_json or bundle_id, not both")
    if not datasets_json:
        if tool_context is None:
            raise ValueError("datasets_json is required outside an ADK session")
        selected = bundle_id or tool_context.state.get(ACTIVE_BUNDLE_KEY, "")
        stored = tool_context.state.get(BUNDLES_KEY, {}).get(selected)
        if stored is None:
            raise ValueError(
                "No registered bundle found; call register_dataset_bundle first"
            )
        bundle = DatasetBundle.model_validate(stored)
        verify_sources(bundle)
        descriptors = {
            name: asset.model_dump(
                include={
                    "file_path",
                    "sheet_name",
                    "loading_options",
                    "roles",
                    "coordinate_convention",
                }
            )
            for name, asset in bundle.source_assets.items()
        }
    else:
        descriptors = _descriptors(datasets_json)
        bundle = DatasetBundle(
            bundle_id=f"bundle_{uuid.uuid4().hex[:12]}", source_assets={}
        )
    frames = {}
    total_bytes = 0
    for name, descriptor in descriptors.items():
        path = resolve_data_path(descriptor["file_path"])
        before = file_sha256(path)
        options = descriptor.get("loading_options", {})
        frame = load_dataset_frame(
            str(path), descriptor.get("sheet_name", ""), json.dumps(options)
        )
        if file_sha256(path) != before:
            raise RuntimeError(f"Source {name} changed while being loaded")
        if frame.columns.has_duplicates:
            raise ValueError(
                f"Dataset {name} has duplicate column names; provide unambiguous headers"
            )
        if not all(isinstance(c, str) for c in frame.columns):
            frame.columns = [str(c) for c in frame.columns]
        if frame.columns.has_duplicates:
            raise ValueError(f"Dataset {name} has conflicting column labels")
        memory = int(frame.memory_usage(deep=True).sum())
        total_bytes += memory
        if total_bytes > settings.max_bundle_memory_mb * 1024**2:
            raise ValueError(
                f"Loaded datasets exceed MAX_BUNDLE_MEMORY_MB={settings.max_bundle_memory_mb}"
            )
        bundle.source_assets[name] = DataAsset(
            asset_id=name,
            file_path=str(path),
            sha256=before,
            sheet_name=descriptor.get("sheet_name", ""),
            loading_options=options,
            rows=len(frame),
            columns=list(frame.columns),
            dtypes={c: str(frame[c].dtype) for c in frame},
            memory_bytes=memory,
            roles=descriptor.get("roles", {}),
            coordinate_convention=descriptor.get("coordinate_convention", "unknown"),
        )
        frames[name] = frame
    verify_sources(bundle)
    return bundle, frames


def store_bundle(bundle: DatasetBundle, tool_context=None) -> None:
    if tool_context is not None:
        bundles = dict(tool_context.state.get(BUNDLES_KEY, {}))
        bundles[bundle.bundle_id] = bundle.model_dump(mode="json")
        tool_context.state[BUNDLES_KEY] = bundles
        tool_context.state[ACTIVE_BUNDLE_KEY] = bundle.bundle_id


def list_workbook_sheets(file_path: str) -> dict[str, Any]:
    """List Excel worksheet names before selecting one or several as named datasets."""
    try:
        path = resolve_data_path(file_path)
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError("Select an Excel workbook")
        with pd.ExcelFile(path) as book:
            return {
                "status": "success",
                "file_path": str(path),
                "sheets": book.sheet_names,
            }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def discover_dataset_inputs(
    folder_path: str = ".", file_pattern: str = "*"
) -> dict[str, Any]:
    """List files only in a user-selected input folder; does not register or combine them."""
    try:
        candidate = Path(folder_path).expanduser()
        root = (
            candidate if candidate.is_absolute() else settings.data_dir / candidate
        ).resolve()
        if not settings.allow_absolute_data_paths and not root.is_relative_to(
            settings.data_dir.resolve()
        ):
            raise ValueError("Select a folder inside DATA_DIR")
        if not root.is_dir():
            raise ValueError("Input folder does not exist")
        if Path(file_pattern).is_absolute() or ".." in Path(file_pattern).parts:
            raise ValueError("file_pattern must remain inside the selected folder")
        files = []
        for path in sorted(root.glob(file_pattern)):
            if not path.is_file() or _suffix(path) not in SUPPORTED_SUFFIXES | {
                ".bed.gz"
            }:
                continue
            resolved = resolve_data_path(str(path))
            if not resolved.is_relative_to(root):
                raise ValueError("Discovered file escapes selected folder")
            files.append(
                {"file_path": str(resolved), "size_bytes": path.stat().st_size}
            )
            if len(files) > settings.max_bundle_datasets:
                raise ValueError("Too many files; narrow the folder or file_pattern")
        return {
            "status": "success",
            "files": files,
            "next_step": "Select files and assign distinct IDs in register_dataset_bundle datasets_json",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def register_dataset_bundle(
    datasets_json: str, tool_context: ToolContext = None
) -> dict[str, Any]:
    """Inspect and register named files or selected workbook sheets without combining them.

    datasets_json example: {"traits":{"file_path":"traits.csv","loading_options":{"dtype":{"sample_id":"string"}}},"metadata":{"file_path":"samples.xlsx","sheet_name":"Samples"}}
    DataFrames stay in the execution layer. Session state holds only serializable metadata.
    """
    try:
        bundle, frames = load_bundle(datasets_json, tool_context=tool_context)
        names = list(frames)
        bundle.inferred_relationships = [
            {
                "left": a,
                "right": b,
                "shared_column_names": sorted(set(frames[a]) & set(frames[b])),
                "status": "candidate_only_requires_key_selection",
            }
            for i, a in enumerate(names)
            for b in names[i + 1 :]
            if set(frames[a]) & set(frames[b])
        ]
        store_bundle(bundle, tool_context)
        return _json_safe(
            {
                "status": "success",
                "bundle_id": bundle.bundle_id,
                "bundle": bundle.model_dump(mode="json"),
                "source_unchanged": True,
                "previews": {
                    name: frame.head(settings.max_preview_rows).to_dict(
                        orient="records"
                    )
                    for name, frame in frames.items()
                },
            }
        )
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def inspect_dataset_bundle(
    bundle_id: str = "", tool_context: ToolContext = None
) -> dict[str, Any]:
    """Get the active bundle schema and bounded previews, verifying source hashes."""
    try:
        bundle, frames = load_bundle(bundle_id=bundle_id, tool_context=tool_context)
        return _json_safe(
            {
                "status": "success",
                "bundle": bundle.model_dump(mode="json"),
                "previews": {
                    name: frame.head(settings.max_preview_rows).to_dict(
                        orient="records"
                    )
                    for name, frame in frames.items()
                },
            }
        )
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
