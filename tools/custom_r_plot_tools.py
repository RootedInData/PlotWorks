from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import settings
from .data_tools import _json_safe, load_dataset_frame

_ALLOWED_R_PACKAGES = {
    "ggplot2",
    "dplyr",
    "tidyr",
    "forcats",
    "stringr",
    "scales",
    "ggrepel",
    "patchwork",
    "ggforce",
    "ggridges",
    "gghalves",
    "viridisLite",
    "grid",
    "gridExtra",
    "ggrateful",
}

_FORBIDDEN_CALLS = {
    "system",
    "system2",
    "shell",
    "download.file",
    "url",
    "socketConnection",
    "file.remove",
    "unlink",
    "setwd",
    "install.packages",
    "source",
    "eval",
    "parse",
    "get",
    "assign",
    "do.call",
    "dyn.load",
    "library.dynam",
    "readRDS",
    "saveRDS",
    "load",
    "save",
    "writeLines",
    "write.csv",
    "write.table",
    "read.csv",
    "read.table",
    "file",
    "gzfile",
    "bzfile",
    "xzfile",
    "dir.create",
    "list.files",
    "Sys.getenv",
    "Sys.setenv",
    "quit",
    "q",
}


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _safe_output_filename(output_name: str) -> str:
    raw = str(output_name).strip() or "custom_r_plot.png"
    candidate = Path(raw)
    if candidate.name != raw or candidate.parent != Path("."):
        raise ValueError("output_name must be a filename only, without directory components")
    suffix = candidate.suffix.lower() or ".png"
    if suffix not in {".png", ".pdf", ".svg"}:
        raise ValueError("Custom R plot output must be PNG, PDF, or SVG")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate.stem).strip("._") or "custom_r_plot"
    return f"{stem}{suffix}"


def _package_references(code: str) -> set[str]:
    packages: set[str] = set()
    for match in re.finditer(r"\b(?:library|require)\s*\(\s*['\"]?([A-Za-z][A-Za-z0-9.]*)", code):
        packages.add(match.group(1))
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9.]*)\s*::(?!:)", code):
        packages.add(match.group(1))
    return packages


def validate_generated_r_plot_code(code: str) -> dict[str, Any]:
    """Statically validate model-generated R code intended only to build a plot.

    The code must define ``build_plot <- function(data)`` and return a ggplot-like
    object. File loading, output saving, package setup, and path handling are performed
    by a deterministic wrapper rather than by generated code.
    """

    source = str(code)
    errors: list[str] = []
    warnings: list[str] = []

    if not source.strip():
        errors.append("No R code was supplied.")
    if len(source) > settings.max_generated_r_code_chars:
        errors.append(
            f"Generated R code exceeds MAX_GENERATED_R_CODE_CHARS={settings.max_generated_r_code_chars}."
        )
    if not re.search(r"\bbuild_plot\s*<-\s*function\s*\(\s*data\s*\)", source):
        errors.append("Code must define exactly build_plot <- function(data).")
    if ":::" in source:
        errors.append("Triple-colon access is not allowed.")

    for call in sorted(_FORBIDDEN_CALLS):
        pattern = rf"(?<![A-Za-z0-9_.]){re.escape(call)}\s*\("
        if re.search(pattern, source):
            errors.append(f"Forbidden R function call detected: {call}()")

    packages = _package_references(source)
    disallowed_packages = sorted(packages - _ALLOWED_R_PACKAGES)
    if disallowed_packages:
        errors.append(
            "Only approved plotting packages are allowed. Disallowed package references: "
            + ", ".join(disallowed_packages)
        )

    if not re.search(r"\bggplot\s*\(|\bggplot2\s*::\s*ggplot\s*\(", source):
        warnings.append("No ggplot() call was detected; confirm that build_plot returns a saveable plot object.")
    if re.search(r"\bprint\s*\(", source):
        warnings.append("print() is unnecessary; build_plot should return the plot object.")

    return _result(
        "success" if not errors else "error",
        valid=not errors,
        errors=errors,
        warnings=warnings,
        referenced_packages=sorted(packages),
        allowed_packages=sorted(_ALLOWED_R_PACKAGES),
        contract=(
            "Define build_plot <- function(data) and return one ggplot/patchwork object. "
            "Do not load files, save files, install packages, change directories, or access the network."
        ),
    )


def _wrapper_text(script_name: str) -> str:
    shared = settings.r_shared_plot_dir.resolve().as_posix()
    return f'''
options(warn = 1)
suppressPackageStartupMessages(library(ggplot2))
source("{shared}/theme_plotworks.R")
source("{shared}/palettes.R")
source("{shared}/export_presets.R")
source("{shared}/annotation_helpers.R")

input_path <- Sys.getenv("PLOTWORKS_CUSTOM_R_INPUT", "")
output_path <- Sys.getenv("PLOTWORKS_CUSTOM_R_OUTPUT", "")
width <- as.numeric(Sys.getenv("PLOTWORKS_CUSTOM_R_WIDTH", "7.2"))
height <- as.numeric(Sys.getenv("PLOTWORKS_CUSTOM_R_HEIGHT", "5.0"))
dpi <- as.numeric(Sys.getenv("PLOTWORKS_CUSTOM_R_DPI", "300"))

if (!file.exists(input_path)) stop("Standardized input file is missing")
data <- read.csv(input_path, check.names = FALSE, stringsAsFactors = FALSE)
source("{script_name}", local = TRUE)
if (!exists("build_plot", mode = "function")) stop("build_plot(data) was not defined")
plot_object <- build_plot(data)
if (is.null(plot_object)) stop("build_plot(data) returned NULL")
ggplot2::ggsave(output_path, plot_object, width = width, height = height,
                units = "in", dpi = dpi, bg = "white")
cat(output_path)
'''


def execute_generated_r_plot(
    code: str,
    file_path: str,
    output_name: str = "custom_r_plot.png",
    sheet_name: str = "",
    width: float = 7.2,
    height: float = 5.0,
    dpi: int = 300,
) -> dict[str, Any]:
    """Validate and execute generated R plotting code in a controlled run directory.

    Args:
        code: R code defining ``build_plot <- function(data)``.
        file_path: Input dataset; Python standardizes it to CSV before R runs.
        output_name: Filename only. Directory components are rejected.
        sheet_name: Optional Excel sheet name.
        width: Figure width in inches.
        height: Figure height in inches.
        dpi: Output resolution for raster formats.
    """

    validation = validate_generated_r_plot_code(code)
    if validation.get("status") != "success":
        return _result("error", message="Generated R code failed static validation.", validation=validation)

    rscript = shutil.which("Rscript")
    if not rscript:
        return _result(
            "error",
            message="Rscript was not found on PATH.",
            next_steps=["Install R in the environment where ADK runs.", "Verify with: Rscript --version"],
        )

    try:
        output_filename = _safe_output_filename(output_name)
        frame = load_dataset_frame(file_path, sheet_name)
        if frame.empty:
            raise ValueError("The selected dataset is empty")
        if width <= 0 or height <= 0 or width > 20 or height > 20:
            raise ValueError("width and height must be greater than 0 and no more than 20 inches")
        if dpi < 72 or dpi > 1200:
            raise ValueError("dpi must be between 72 and 1200")
    except Exception as exc:
        return _result("error", message=str(exc))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{stamp}_{uuid.uuid4().hex[:8]}"
    run_dir = settings.code_output_dir / "custom_r_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_csv = run_dir / "input.csv"
    generated_script = run_dir / "generated_plot.R"
    wrapper_script = run_dir / "run_plot.R"
    metadata_path = run_dir / "run_metadata.json"
    output_path = settings.plot_output_dir / output_filename
    settings.plot_output_dir.mkdir(parents=True, exist_ok=True)

    frame.to_csv(input_csv, index=False)
    try:
        input_csv.chmod(0o444)
    except OSError:
        pass
    generated_script.write_text(code, encoding="utf-8")
    wrapper_script.write_text(_wrapper_text(generated_script.name), encoding="utf-8")

    parse_check = subprocess.run(
        [rscript, "-e", f'parse(file="{generated_script.name}")'],
        cwd=str(run_dir),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if parse_check.returncode != 0:
        return _result(
            "error",
            message="Generated R code is not syntactically valid.",
            validation=validation,
            parse_stderr=parse_check.stderr.strip(),
            generated_script=str(generated_script),
        )

    if output_path.exists():
        output_path.unlink()

    env = os.environ.copy()
    env.update(
        {
            "PLOTWORKS_CUSTOM_R_INPUT": str(input_csv.resolve()),
            "PLOTWORKS_CUSTOM_R_OUTPUT": str(output_path.resolve()),
            "PLOTWORKS_CUSTOM_R_WIDTH": str(width),
            "PLOTWORKS_CUSTOM_R_HEIGHT": str(height),
            "PLOTWORKS_CUSTOM_R_DPI": str(dpi),
        }
    )

    try:
        proc = subprocess.run(
            [rscript, wrapper_script.name],
            cwd=str(run_dir),
            env=env,
            text=True,
            capture_output=True,
            timeout=settings.r_plot_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _result(
            "error",
            message=f"Custom R plot exceeded the {settings.r_plot_timeout_seconds}-second timeout.",
            generated_script=str(generated_script),
            run_directory=str(run_dir),
        )

    metadata = {
        "run_id": run_id,
        "input_file": file_path,
        "standardized_input": str(input_csv),
        "output": str(output_path.resolve()),
        "width": width,
        "height": height,
        "dpi": dpi,
        "validation": validation,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if proc.returncode != 0:
        if output_path.exists():
            output_path.unlink()
        return _result(
            "error",
            message="R failed while executing the generated plotting function.",
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            generated_script=str(generated_script),
            run_metadata=str(metadata_path),
        )

    if not output_path.exists() or output_path.stat().st_size < 100:
        return _result(
            "error",
            message="R completed but did not create a valid non-empty plot file.",
            generated_script=str(generated_script),
            run_metadata=str(metadata_path),
        )

    return _result(
        "success",
        saved_plot=str(output_path.resolve()),
        generated_script=str(generated_script.resolve()),
        run_metadata=str(metadata_path.resolve()),
        validation=validation,
        warning=(
            "Custom R plotting uses static validation and managed execution, but this is not a full OS-level sandbox. "
            "Review the saved script and figure before professional use."
        ),
    )
