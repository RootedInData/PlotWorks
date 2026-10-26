"""Preview-bound multi-dataset transformations and confirmed artifact publication."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from google.adk.tools.tool_context import ToolContext
except ModuleNotFoundError:
    ToolContext = Any

from ..config import settings
from ..contracts import DataAsset, TransformationProposal
from .data_tools import _json_safe
from .data_transformation_tools import (
    _parse_operations,
    _safe_relative_output_path,
    _write_frame,
)
from .dataset_bundle_tools import (
    ARTIFACTS_KEY,
    PROPOSALS_KEY,
    file_sha256,
    load_bundle,
    store_bundle,
    verify_sources,
)
from .generated_transform_runtime import (
    WRAPPER,
    allowed_imports,
    run_generated_transform,
)
from .multi_table_engine import apply_bundle_operations, check_frame_limits

RECEIPTS_KEY = "plotworks:transformation_receipts"


def _limits() -> dict[str, int]:
    return {
        name: int(getattr(settings, name))
        for name in (
            "max_transform_rows",
            "max_transform_memory_mb",
            "generated_transform_memory_mb",
            "max_transform_output_mb",
            "data_transform_timeout_seconds",
        )
    }


def _fingerprint(proposal: TransformationProposal) -> str:
    content = proposal.model_dump(mode="json", exclude={"proposal_id"})
    return hashlib.sha256(
        json.dumps(
            content, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def _output_names(
    raw: str, outputs: dict[str, pd.DataFrame], last: str
) -> dict[str, str]:
    names = json.loads(raw) if raw else {last: ""}
    if (
        not isinstance(names, dict)
        or not names
        or not all(isinstance(v, str) for v in names.values())
    ):
        raise ValueError(
            "output_names_json must map output dataset IDs to relative filenames"
        )
    if set(names) - set(outputs):
        raise ValueError(
            f"Output names reference unknown results: {sorted(set(names) - set(outputs))}"
        )
    effective = {}
    for name, filename in names.items():
        destination = _safe_relative_output_path(filename, name)
        effective[name] = str(
            destination.relative_to(settings.transformed_data_output_dir.resolve())
        )
    return effective


def _destinations(proposal: TransformationProposal) -> dict[str, Path]:
    result = {
        name: _safe_relative_output_path(filename, name)
        for name, filename in proposal.output_names.items()
    }
    all_paths = [
        path
        for output in result.values()
        for path in (output, output.with_suffix(output.suffix + ".metadata.json"))
    ]
    if len(set(all_paths)) != len(all_paths):
        raise ValueError("Output or metadata paths collide after path normalization")
    sources = {
        Path(asset.file_path).resolve()
        for asset in proposal.bundle.source_assets.values()
    }
    if sources & set(all_paths):
        raise ValueError("Output cannot overwrite a source or its metadata")
    for path in all_paths:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Output exists; choose a new filename: {path.name}")
    return result


def _preview(
    mode,
    datasets_json,
    bundle_id,
    operations_json,
    code,
    output_names_json,
    preview_rows,
    tool_context,
):
    try:
        bundle, frames = load_bundle(datasets_json, bundle_id, tool_context)
        if mode == "deterministic_bundle":
            operations = _parse_operations(operations_json)
            outputs, audit, last = apply_bundle_operations(frames, operations)
            execution = {}
        else:
            operations = []
            outputs, execution = run_generated_transform(code, frames)
            audit = []
            last = next(iter(outputs))
        verify_sources(bundle)
        names = _output_names(output_names_json, outputs, last)
        proposal = TransformationProposal(
            bundle=bundle,
            mode=mode,
            operations=operations,
            code=code,
            output_names=names,
            limits=_limits(),
            runtime_versions=execution.get("versions", _versions()),
            approved_imports=sorted(allowed_imports()) if code else [],
            result_shapes={name: list(outputs[name].shape) for name in names},
        )
        proposal.proposal_id = _fingerprint(proposal)
        _destinations(proposal)  # no output is created by preview
        store_bundle(bundle, tool_context)
        if tool_context is not None:
            pending = dict(tool_context.state.get(PROPOSALS_KEY, {}))
            pending[proposal.proposal_id] = proposal.model_dump(mode="json")
            # Keep session handoffs bounded; no DataFrames enter state.
            tool_context.state[PROPOSALS_KEY] = dict(list(pending.items())[-20:])
        count = max(1, min(int(preview_rows), 50))
        return _json_safe(
            {
                "status": "success",
                "mode": "preview_only",
                "source_unchanged": True,
                "bundle_id": bundle.bundle_id,
                "proposal_id": proposal.proposal_id,
                "proposal": proposal.model_dump(mode="json"),
                "audit": audit,
                "outputs": {
                    name: {
                        "shape": {
                            "rows": len(outputs[name]),
                            "columns": len(outputs[name].columns),
                        },
                        "columns": [str(c) for c in outputs[name].columns],
                        "dtypes": {
                            str(c): str(outputs[name][c].dtype) for c in outputs[name]
                        },
                        "preview": outputs[name].head(count).to_dict(orient="records"),
                        "output_name": filename,
                    }
                    for name, filename in names.items()
                },
                "execution": {
                    key: value
                    for key, value in execution.items()
                    if key not in {"stdout", "stderr"}
                },
                "next_step": "Present input hashes, operations or code, join diagnostics and outputs; pass the unchanged proposal JSON to the root confirmed save_bundle_transformation tool.",
            }
        )
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def preview_bundle_transformations(
    operations_json: str,
    datasets_json: str = "",
    bundle_id: str = "",
    output_names_json: str = "",
    preview_rows: int = 8,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Preview multi-table operations without saving datasets.

    Supply datasets_json or a registered bundle_id (blank selects the session's active bundle).
    A join declares left/right dataset IDs, on or left_on/right_on keys, how,
    null_keys (never_match or match), validate and an output dataset ID.
    output_names_json selects derived IDs and their final relative filenames.
    """
    return _preview(
        "deterministic_bundle",
        datasets_json,
        bundle_id,
        operations_json,
        "",
        output_names_json,
        preview_rows,
        tool_context,
    )


def preview_generated_bundle_transform(
    code: str,
    datasets_json: str = "",
    bundle_id: str = "",
    output_names_json: str = "",
    preview_rows: int = 8,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Run transform_data(datasets) against working copies in a temporary process.

    Return a DataFrame or named DataFrames. pd and np are supplied. Temporary
    previews do not publish datasets, code or provenance. Use the unchanged
    returned proposal with the supervisor's confirmed save tool to publish them.
    """
    return _preview(
        "generated_python_bundle",
        datasets_json,
        bundle_id,
        "",
        code,
        output_names_json,
        preview_rows,
        tool_context,
    )


def _publish_exclusive(source: Path, destination: Path, created: list[Path]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects existing files even if a second run wins a race.
    with destination.open("xb") as target:
        created.append(destination)
        with source.open("rb") as origin:
            shutil.copyfileobj(origin, target)


def _frame_loading_options(frame: pd.DataFrame) -> dict:
    dtypes = {}
    dates = []
    for column in frame:
        kind = str(frame[column].dtype)
        if kind.startswith("datetime64"):
            dates.append(str(column))
        elif kind in {
            "object",
            "string",
            "category",
            "bool",
            "boolean",
            "Int8",
            "Int16",
            "Int32",
            "Int64",
            "UInt8",
            "UInt16",
            "UInt32",
            "UInt64",
            "Float32",
            "Float64",
            "int8",
            "int16",
            "int32",
            "int64",
            "uint8",
            "uint16",
            "uint32",
            "uint64",
            "float32",
            "float64",
        }:
            dtypes[str(column)] = kind
    result = {"dtype": dtypes} if dtypes else {}
    if dates:
        result["parse_dates"] = dates
    return result


def _versions() -> dict[str, str]:
    result = {"python": sys.version.split()[0]}
    for package in ("pandas", "numpy", "google-adk"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    return result


def save_bundle_transformation(
    proposal_json: str, tool_context: ToolContext = None
) -> dict[str, Any]:
    """Publish exactly a previewed proposal after root-level ADK confirmation.

    Rejects altered plans, changed sources, changed limits, output collisions,
    and unpreviewed proposals in an ADK session. Repeated confirmed invocations
    in the same session return the prior receipt if its output hashes still match.
    """
    created: list[Path] = []
    run_dir = None
    try:
        proposal = TransformationProposal.model_validate_json(proposal_json)
        if proposal.version != 1 or proposal.proposal_id != _fingerprint(proposal):
            raise ValueError("Proposal changed after preview; preview again")
        if proposal.limits != _limits():
            raise ValueError("Execution limits changed after preview; preview again")
        if proposal.code and proposal.approved_imports != sorted(allowed_imports()):
            raise ValueError("Approved imports changed after preview; preview again")
        verify_sources(proposal.bundle)
        if tool_context is not None:
            receipt = tool_context.state.get(RECEIPTS_KEY, {}).get(proposal.proposal_id)
            if receipt:
                for asset in receipt["output_assets"]:
                    if (
                        not Path(asset["file_path"]).is_file()
                        or file_sha256(Path(asset["file_path"])) != asset["sha256"]
                        or not Path(asset["metadata_file"]).is_file()
                        or file_sha256(Path(asset["metadata_file"]))
                        != asset["metadata_sha256"]
                    ):
                        raise ValueError(
                            "A previously saved output changed; preview again with a new filename"
                        )
                return {**receipt, "already_saved": True}
            expected = tool_context.state.get(PROPOSALS_KEY, {}).get(
                proposal.proposal_id
            )
            if expected != proposal.model_dump(mode="json"):
                raise ValueError(
                    "Proposal was not previewed in this session; preview again"
                )
        destinations = _destinations(proposal)
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
            for name, asset in proposal.bundle.source_assets.items()
        }
        loaded, frames = load_bundle(json.dumps(descriptors))
        for name, asset in loaded.source_assets.items():
            if asset.sha256 != proposal.bundle.source_assets[name].sha256:
                raise ValueError("Source changed since preview; preview again")
        if proposal.mode == "deterministic_bundle":
            outputs, audit, _ = apply_bundle_operations(frames, proposal.operations)
            execution = {}
        else:
            outputs, execution = run_generated_transform(proposal.code, frames)
            audit = []
        if set(destinations) - set(outputs) or any(
            list(outputs[name].shape) != proposal.result_shapes[name]
            for name in destinations
        ):
            raise ValueError(
                "Output shape changed since preview; preview the transformation again"
            )
        verify_sources(proposal.bundle)
        run_id = uuid.uuid4().hex
        run_dir = settings.code_output_dir / "data_transform_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        if proposal.runtime_versions != execution.get("versions", _versions()):
            raise ValueError(
                "Runtime package versions changed after preview; preview again"
            )
        metadata = {
            "proposal_id": proposal.proposal_id,
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": proposal.mode,
            "source_assets": {
                name: asset.model_dump(mode="json")
                for name, asset in proposal.bundle.source_assets.items()
            },
            "source_unchanged": True,
            "operations": proposal.operations,
            "audit": audit,
            "package_versions": _versions(),
            "execution": execution,
            "limits": proposal.limits,
        }
        if proposal.code:
            (run_dir / "generated_transform.py").write_text(
                proposal.code, encoding="utf-8"
            )
            (run_dir / "run_transform.py").write_text(WRAPPER, encoding="utf-8")
            metadata["code_sha256"] = hashlib.sha256(proposal.code.encode()).hexdigest()
            metadata["approved_imports"] = sorted(allowed_imports())
        (run_dir / "proposal.json").write_text(
            proposal.model_dump_json(indent=2), encoding="utf-8"
        )
        saved = []
        total_bytes = 0
        with tempfile.TemporaryDirectory(prefix="plotworks_publish_") as folder:
            staging = Path(folder)
            staged = []
            for index, (name, destination) in enumerate(destinations.items()):
                frame = outputs[name]
                check_frame_limits(frame)
                temporary = staging / f"data_{index}{destination.suffix}"
                _write_frame(frame, temporary)
                total_bytes += temporary.stat().st_size
                if total_bytes > settings.max_transform_output_mb * 1024**2:
                    raise ValueError("Published data exceed MAX_TRANSFORM_OUTPUT_MB")
                asset = DataAsset(
                    asset_id=name,
                    file_path=str(destination),
                    sha256=file_sha256(temporary),
                    kind="derived",
                    rows=len(frame),
                    loading_options=_frame_loading_options(frame),
                    columns=[str(c) for c in frame.columns],
                    dtypes={str(c): str(frame[c].dtype) for c in frame},
                    memory_bytes=int(frame.memory_usage(deep=True).sum()),
                )
                sidecar = destination.with_suffix(destination.suffix + ".metadata.json")
                detail = {
                    **metadata,
                    "output_asset": asset.model_dump(mode="json"),
                    "output_sha256": asset.sha256,
                    "output_file": str(destination),
                    "transformed_shape": list(frame.shape),
                }
                temp_sidecar = staging / f"metadata_{index}.json"
                temp_sidecar.write_text(
                    json.dumps(_json_safe(detail), indent=2, allow_nan=False),
                    encoding="utf-8",
                )
                staged.extend(((temporary, destination), (temp_sidecar, sidecar)))
                saved.append(
                    {
                        **asset.model_dump(mode="json"),
                        "metadata_file": str(sidecar),
                        "metadata_sha256": file_sha256(temp_sidecar),
                    }
                )
            verify_sources(proposal.bundle)
            for temporary, destination in staged:
                _publish_exclusive(temporary, destination, created)
            verify_sources(proposal.bundle)
        metadata["output_assets"] = saved
        (run_dir / "run_metadata.json").write_text(
            json.dumps(_json_safe(metadata), indent=2, allow_nan=False),
            encoding="utf-8",
        )
        result = {
            "status": "success",
            "proposal_id": proposal.proposal_id,
            "bundle_id": proposal.bundle.bundle_id,
            "source_unchanged": True,
            "output_assets": saved,
            "run_metadata": str(run_dir / "run_metadata.json"),
            "audit": audit,
            "plotting_inputs": {
                asset["asset_id"]: asset["file_path"] for asset in saved
            },
        }
        if len(saved) == 1:
            asset = saved[0]
            result.update(
                {
                    "saved_dataset": asset["file_path"],
                    "plotting_input_path": asset["file_path"],
                    "metadata_file": asset["metadata_file"],
                    "transformed_shape": {
                        "rows": asset["rows"],
                        "columns": len(asset["columns"]),
                    },
                    "transformed_columns": asset["columns"],
                }
            )
        if proposal.code:
            result["generated_script"] = str(run_dir / "generated_transform.py")
        if tool_context is not None:
            # Extend the source registry only with derived metadata; original assets
            # retain their identities, hashes and loading options.
            for asset in saved:
                proposal.bundle.derived_assets[asset["asset_id"]] = (
                    DataAsset.model_validate(
                        {
                            k: v
                            for k, v in asset.items()
                            if k not in {"metadata_file", "metadata_sha256"}
                        }
                    )
                )
            store_bundle(proposal.bundle, tool_context)
            derived = dict(tool_context.state.get(ARTIFACTS_KEY, {}))
            derived[proposal.proposal_id] = saved
            tool_context.state[ARTIFACTS_KEY] = derived
            receipts = dict(tool_context.state.get(RECEIPTS_KEY, {}))
            receipts[proposal.proposal_id] = result
            tool_context.state[RECEIPTS_KEY] = receipts
        return _json_safe(result)
    except Exception as exc:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        # Keep approved code and an error record for debugging, without claiming success.
        if run_dir is not None:
            (run_dir / "error.json").write_text(
                json.dumps({"status": "error", "message": str(exc)}), encoding="utf-8"
            )
        return {"status": "error", "message": str(exc)}
