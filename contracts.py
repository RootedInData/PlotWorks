"""Serializable dataset and transformation contracts shared by tools and agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DataAsset(BaseModel):
    asset_id: str
    file_path: str
    sheet_name: str = ""
    sha256: str
    loading_options: dict[str, Any] = Field(default_factory=dict)
    rows: int
    columns: list[str]
    dtypes: dict[str, str]
    memory_bytes: int
    coordinate_convention: Literal[
        "unknown", "zero_based_half_open", "one_based_closed"
    ] = "unknown"
    roles: dict[str, str] = Field(default_factory=dict)
    kind: Literal["source", "derived"] = "source"


class DatasetBundle(BaseModel):
    bundle_id: str
    source_assets: dict[str, DataAsset]
    derived_assets: dict[str, DataAsset] = Field(default_factory=dict)
    inferred_relationships: list[dict[str, Any]] = Field(default_factory=list)
    selected_join_keys: dict[str, Any] = Field(default_factory=dict)


class TransformationProposal(BaseModel):
    version: int = 1
    proposal_id: str = ""
    bundle: DatasetBundle
    mode: Literal["deterministic_bundle", "generated_python_bundle"]
    operations: list[dict[str, Any]] = Field(default_factory=list)
    code: str = ""
    output_names: dict[str, str]
    limits: dict[str, int]
    result_shapes: dict[str, list[int]] = Field(default_factory=dict)
    approved_imports: list[str] = Field(default_factory=list)
    runtime_versions: dict[str, str] = Field(default_factory=dict)
