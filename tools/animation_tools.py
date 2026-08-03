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

import pandas as pd

from ..config import settings
from .data_tools import _json_safe, load_dataset_frame

_ALLOWED_ANIMATION_PACKAGES = {
    "ggplot2",
    "gganimate",
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
    "transformr",
    "gifski",
    "av",
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
    "readLines",
    "writeBin",
    "readBin",
    "writeChar",
    "readChar",
    "sink",
    "file.copy",
    "file.rename",
    "file.create",
    "file.append",
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
    "anim_save",
    "animate",
}


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _safe_animation_filename(output_name: str) -> str:
    raw = str(output_name).strip() or "plotworks_animation.gif"
    candidate = Path(raw)
    if candidate.name != raw or candidate.parent != Path("."):
        raise ValueError("output_name must be a filename only, without directory components")
    suffix = candidate.suffix.lower() or ".gif"
    if suffix not in {".gif", ".mp4"}:
        raise ValueError("Animation output must be GIF or MP4")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate.stem).strip("._") or "plotworks_animation"
    return f"{stem}{suffix}"


def _package_references(code: str) -> set[str]:
    packages: set[str] = set()
    for match in re.finditer(r"\b(?:library|require)\s*\(\s*['\"]?([A-Za-z][A-Za-z0-9.]*)", code):
        packages.add(match.group(1))
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9.]*)\s*::(?!:)", code):
        packages.add(match.group(1))
    return packages


def check_animation_setup(output_format: str = "gif") -> dict[str, Any]:
    """Check R and the packages needed for PlotWorks animations."""

    rscript = shutil.which("Rscript")
    if not rscript:
        return _result(
            "error",
            message="Rscript was not found on PATH.",
            next_steps=["Install R where ADK runs.", "Verify with: Rscript --version"],
        )

    packages = [
        "ggplot2", "gganimate", "gifski", "transformr",
        "ggrepel", "dplyr", "tidyr", "scales"
    ]
    if str(output_format).strip().lower().lstrip(".") == "mp4":
        packages.append("av")
    expression = (
        "pkgs <- c(" + ",".join(json.dumps(pkg) for pkg in packages) + "); "
        "missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly=TRUE)]; "
        "cat(paste(missing, collapse=',')); quit(status=if(length(missing)) 2 else 0)"
    )
    proc = subprocess.run(
        [rscript, "-e", expression], text=True, capture_output=True, timeout=60
    )
    missing = [item for item in proc.stdout.strip().split(",") if item]
    return _result(
        "success" if proc.returncode == 0 else "error",
        rscript=rscript,
        required_packages=packages,
        missing_packages=missing,
        stderr=proc.stderr.strip(),
    )


def _column(frame: pd.DataFrame, name: str, required: bool = True) -> str:
    clean = str(name).strip()
    if not clean and not required:
        return ""
    if clean not in frame.columns:
        raise ValueError(f"Column not found: {clean}")
    return clean


def _deterministic_animation_script(
    x: str,
    y: str,
    time: str,
    color: str,
    color_mode: str,
    size: str,
    label: str,
    title: str,
    x_label: str,
    y_label: str,
    legend_title: str,
    transition_mode: str,
    shadow_wake: float,
) -> str:
    shared = settings.r_shared_plot_dir.resolve().as_posix()
    subtitle = "Frame: {frame_time}" if transition_mode == "time" else "Frame: {closest_state}"
    if not color:
        color_scale = ""
    elif color_mode == "continuous":
        color_scale = '''
  scale_colour_viridis_c(option = "D") +'''
    else:
        color_scale = '''
  scale_colour_manual(values = plotworks_palette(length(unique(data[[color_col]])))) +'''
    size_scale = "" if not size else '''
  scale_size_continuous(range = c(2.5, 9), guide = guide_legend(override.aes = list(alpha = 1))) +'''
    label_layer = "" if not label else '''
  ggrepel::geom_text_repel(show.legend = FALSE, size = 3, max.overlaps = 20) +'''
    transition = (
        f'''transition_time(.data[[time_col]]) +
  ease_aes("linear") +
  shadow_wake(wake_length = {shadow_wake}, alpha = 0.25) +'''
        if transition_mode == "time"
        else '''transition_states(.data[[time_col]], transition_length = 2, state_length = 1) +
  ease_aes("cubic-in-out") +'''
    )

    return f'''
options(warn = 1)
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(gganimate))
suppressPackageStartupMessages(library(ggrepel))
source("{shared}/theme_plotworks.R")
source("{shared}/palettes.R")

input_path <- Sys.getenv("PLOTWORKS_ANIMATION_INPUT", "")
output_path <- Sys.getenv("PLOTWORKS_ANIMATION_OUTPUT", "")
fps <- as.integer(Sys.getenv("PLOTWORKS_ANIMATION_FPS", "20"))
duration <- as.numeric(Sys.getenv("PLOTWORKS_ANIMATION_DURATION", "10"))
width <- as.integer(Sys.getenv("PLOTWORKS_ANIMATION_WIDTH", "1200"))
height <- as.integer(Sys.getenv("PLOTWORKS_ANIMATION_HEIGHT", "800"))
res <- as.integer(Sys.getenv("PLOTWORKS_ANIMATION_RES", "150"))

if (!file.exists(input_path)) stop("Standardized animation input is missing")
data <- read.csv(input_path, check.names = FALSE, stringsAsFactors = FALSE)
x_col <- {json.dumps(x)}
y_col <- {json.dumps(y)}
time_col <- {json.dumps(time)}
color_col <- {json.dumps(color)}
size_col <- {json.dumps(size)}
label_col <- {json.dumps(label)}

quote_column <- function(value) {{
  if (!nzchar(value)) return(NULL)
  paste0("`", gsub("`", "", value, fixed = TRUE), "`")
}}
mapping <- ggplot2::aes_string(
  x = quote_column(x_col),
  y = quote_column(y_col),
  colour = quote_column(color_col),
  size = quote_column(size_col),
  label = quote_column(label_col)
)
animation_plot <- ggplot(data, mapping) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = -Inf, ymax = Inf,
           fill = "grey98", alpha = 0.1) +
  geom_point(alpha = 0.82, stroke = 0.5) +{label_layer}{color_scale}{size_scale}
  labs(
    title = {json.dumps(title or 'Animated scatter plot')},
    subtitle = {json.dumps(subtitle)},
    x = {json.dumps(x_label or x)},
    y = {json.dumps(y_label or y)},
    colour = {json.dumps(legend_title or color or 'Group')},
    size = {json.dumps(size or 'Size')}
  ) +
  theme_plotworks() +
  theme(legend.position = "right") +
  {transition}
  enter_fade() +
  exit_fade()

if (grepl("\\.gif$", output_path, ignore.case = TRUE)) {{
  rendered <- animate(
    animation_plot,
    fps = fps,
    duration = duration,
    width = width,
    height = height,
    res = res,
    renderer = gifski_renderer(loop = TRUE)
  )
}} else {{
  rendered <- animate(
    animation_plot,
    fps = fps,
    duration = duration,
    width = width,
    height = height,
    res = res,
    renderer = av_renderer()
  )
}}
anim_save(output_path, animation = rendered)
cat(output_path)
'''


def render_animated_scatter(
    file_path: str,
    x: str,
    y: str,
    time: str,
    color: str = "",
    size: str = "",
    label: str = "",
    output_name: str = "plotworks_animated_scatter.gif",
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    legend_title: str = "",
    fps: int = 20,
    duration: float = 10.0,
    width: int = 1200,
    height: int = 800,
    dpi: int = 150,
    shadow_wake: float = 0.15,
    sheet_name: str = "",
) -> dict[str, Any]:
    """Render a controlled animated scatter plot from a plot-ready dataset."""

    try:
        output_filename = _safe_animation_filename(output_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    setup = check_animation_setup(Path(output_filename).suffix)
    if setup.get("status") != "success":
        return setup

    try:
        frame = load_dataset_frame(file_path, sheet_name).copy()
        x_col = _column(frame, x)
        y_col = _column(frame, y)
        time_col = _column(frame, time)
        color_col = _column(frame, color, required=False) if color else ""
        size_col = _column(frame, size, required=False) if size else ""
        label_col = _column(frame, label, required=False) if label else ""
        frame[x_col] = pd.to_numeric(frame[x_col], errors="coerce")
        frame[y_col] = pd.to_numeric(frame[y_col], errors="coerce")
        color_mode = "categorical"
        if color_col:
            numeric_color = pd.to_numeric(frame[color_col], errors="coerce")
            if numeric_color.notna().sum() == frame[color_col].notna().sum():
                frame[color_col] = numeric_color
                color_mode = "continuous"
        if size_col:
            frame[size_col] = pd.to_numeric(frame[size_col], errors="coerce")
        frame = frame.dropna(subset=[x_col, y_col, time_col])
        if frame.empty:
            raise ValueError("No rows remain after validating animation columns")
        if not (1 <= int(fps) <= 60):
            raise ValueError("fps must be between 1 and 60")
        if not (1 <= float(duration) <= 120):
            raise ValueError("duration must be between 1 and 120 seconds")
        if not (320 <= int(width) <= 3840 and 240 <= int(height) <= 2160):
            raise ValueError("width and height must be within 320x240 and 3840x2160")
        if not (72 <= int(dpi) <= 600):
            raise ValueError("dpi must be between 72 and 600")
        if not (0 <= float(shadow_wake) <= 1):
            raise ValueError("shadow_wake must be between 0 and 1")

        numeric_time = pd.to_numeric(frame[time_col], errors="coerce")
        if numeric_time.notna().all():
            frame[time_col] = numeric_time
            transition_mode = "time"
        else:
            transition_mode = "states"
    except Exception as exc:
        return _result("error", message=str(exc))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{stamp}_{uuid.uuid4().hex[:8]}"
    run_dir = settings.code_output_dir / "animation_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_csv = run_dir / "input.csv"
    script_path = run_dir / "render_animation.R"
    metadata_path = run_dir / "run_metadata.json"
    output_path = settings.animation_output_dir / output_filename
    settings.animation_output_dir.mkdir(parents=True, exist_ok=True)

    frame.to_csv(input_csv, index=False)
    script_path.write_text(
        _deterministic_animation_script(
            x_col,
            y_col,
            time_col,
            color_col,
            color_mode,
            size_col,
            label_col,
            title,
            x_label,
            y_label,
            legend_title,
            transition_mode,
            float(shadow_wake),
        ),
        encoding="utf-8",
    )
    output_path.unlink(missing_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "PLOTWORKS_ANIMATION_INPUT": str(input_csv.resolve()),
            "PLOTWORKS_ANIMATION_OUTPUT": str(output_path.resolve()),
            "PLOTWORKS_ANIMATION_FPS": str(int(fps)),
            "PLOTWORKS_ANIMATION_DURATION": str(float(duration)),
            "PLOTWORKS_ANIMATION_WIDTH": str(int(width)),
            "PLOTWORKS_ANIMATION_HEIGHT": str(int(height)),
            "PLOTWORKS_ANIMATION_RES": str(int(dpi)),
        }
    )

    rscript = setup["rscript"]
    try:
        proc = subprocess.run(
            [rscript, script_path.name],
            cwd=str(run_dir),
            env=env,
            text=True,
            capture_output=True,
            timeout=settings.r_animation_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _result(
            "error",
            message=f"Animation exceeded the {settings.r_animation_timeout_seconds}-second timeout.",
            run_directory=str(run_dir),
        )

    metadata = {
        "run_id": run_id,
        "input_file": file_path,
        "standardized_input": str(input_csv),
        "output": str(output_path),
        "columns": {
            "x": x_col,
            "y": y_col,
            "time": time_col,
            "color": color_col,
            "color_mode": color_mode,
            "size": size_col,
            "label": label_col,
        },
        "animation": {
            "fps": int(fps),
            "duration": float(duration),
            "width": int(width),
            "height": int(height),
            "dpi": int(dpi),
            "transition_mode": transition_mode,
        },
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    metadata_path.write_text(json.dumps(_json_safe(metadata), indent=2), encoding="utf-8")

    if proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size < 1000:
        output_path.unlink(missing_ok=True)
        return _result(
            "error",
            message="R failed to create the animated scatter plot.",
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            script=str(script_path),
            run_metadata=str(metadata_path),
        )

    return _result(
        "success",
        saved_animation=str(output_path.resolve()),
        script=str(script_path.resolve()),
        run_metadata=str(metadata_path.resolve()),
        rows_animated=int(frame.shape[0]),
        transition_mode=transition_mode,
    )


def validate_generated_r_animation_code(code: str) -> dict[str, Any]:
    """Validate generated R code limited to build_animation(data)."""

    source = str(code)
    errors: list[str] = []
    warnings: list[str] = []

    if not source.strip():
        errors.append("No R code was supplied.")
    if len(source) > settings.max_generated_r_code_chars:
        errors.append(
            f"Generated R code exceeds MAX_GENERATED_R_CODE_CHARS={settings.max_generated_r_code_chars}."
        )
    if not re.search(r"\bbuild_animation\s*<-\s*function\s*\(\s*data\s*\)", source):
        errors.append("Code must define exactly build_animation <- function(data).")
    if ":::" in source:
        errors.append("Triple-colon access is not allowed.")

    for call in sorted(_FORBIDDEN_CALLS):
        pattern = rf"(?<![A-Za-z0-9_.]){re.escape(call)}\s*\("
        if re.search(pattern, source):
            errors.append(f"Forbidden R function call detected: {call}()")

    packages = _package_references(source)
    disallowed = sorted(packages - _ALLOWED_ANIMATION_PACKAGES)
    if disallowed:
        errors.append(
            "Only approved animation/plotting packages are allowed. Disallowed references: "
            + ", ".join(disallowed)
        )
    if not re.search(r"\btransition_(?:time|states|reveal|manual|filter|layers)\s*\(", source):
        warnings.append("No gganimate transition_*() call was detected.")
    if not re.search(r"\bggplot\s*\(|\bggplot2\s*::\s*ggplot\s*\(", source):
        warnings.append("No ggplot() call was detected.")

    return _result(
        "success" if not errors else "error",
        valid=not errors,
        errors=list(dict.fromkeys(errors)),
        warnings=list(dict.fromkeys(warnings)),
        referenced_packages=sorted(packages),
        allowed_packages=sorted(_ALLOWED_ANIMATION_PACKAGES),
        contract=(
            "Define build_animation <- function(data) and return one gganim object. "
            "Do not read or write files, render/save the animation, install packages, "
            "change directories, or access the network."
        ),
    )


def _custom_animation_wrapper_text(script_name: str) -> str:
    shared = settings.r_shared_plot_dir.resolve().as_posix()
    return f'''
options(warn = 1)
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(gganimate))
source("{shared}/theme_plotworks.R")
source("{shared}/palettes.R")
source("{shared}/annotation_helpers.R")

input_path <- Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_INPUT", "")
output_path <- Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_OUTPUT", "")
fps <- as.integer(Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_FPS", "20"))
duration <- as.numeric(Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_DURATION", "10"))
width <- as.integer(Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_WIDTH", "1200"))
height <- as.integer(Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_HEIGHT", "800"))
res <- as.integer(Sys.getenv("PLOTWORKS_CUSTOM_ANIMATION_RES", "150"))

if (!file.exists(input_path)) stop("Standardized animation input is missing")
data <- read.csv(input_path, check.names = FALSE, stringsAsFactors = FALSE)
source("{script_name}", local = TRUE)
if (!exists("build_animation", mode = "function")) stop("build_animation(data) was not defined")
animation_object <- build_animation(data)
if (is.null(animation_object)) stop("build_animation(data) returned NULL")

if (grepl("\\.gif$", output_path, ignore.case = TRUE)) {{
  rendered <- animate(animation_object, fps = fps, duration = duration,
                      width = width, height = height, res = res,
                      renderer = gifski_renderer(loop = TRUE))
}} else {{
  rendered <- animate(animation_object, fps = fps, duration = duration,
                      width = width, height = height, res = res,
                      renderer = av_renderer())
}}
anim_save(output_path, animation = rendered)
cat(output_path)
'''


def execute_generated_r_animation(
    code: str,
    file_path: str,
    output_name: str = "custom_animation.gif",
    sheet_name: str = "",
    fps: int = 20,
    duration: float = 10.0,
    width: int = 1200,
    height: int = 800,
    dpi: int = 150,
) -> dict[str, Any]:
    """Execute an approved custom R animation after ADK user confirmation."""

    validation = validate_generated_r_animation_code(code)
    if validation.get("status") != "success":
        return _result(
            "error",
            message="Generated R animation code failed static validation.",
            validation=validation,
        )
    try:
        output_filename = _safe_animation_filename(output_name)
    except Exception as exc:
        return _result("error", message=str(exc))

    setup = check_animation_setup(Path(output_filename).suffix)
    if setup.get("status") != "success":
        return setup

    try:
        frame = load_dataset_frame(file_path, sheet_name)
        if frame.empty:
            raise ValueError("The selected dataset is empty")
        if not (1 <= int(fps) <= 60):
            raise ValueError("fps must be between 1 and 60")
        if not (1 <= float(duration) <= 120):
            raise ValueError("duration must be between 1 and 120 seconds")
        if not (320 <= int(width) <= 3840 and 240 <= int(height) <= 2160):
            raise ValueError("width and height must be within 320x240 and 3840x2160")
        if not (72 <= int(dpi) <= 600):
            raise ValueError("dpi must be between 72 and 600")
    except Exception as exc:
        return _result("error", message=str(exc))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{stamp}_{uuid.uuid4().hex[:8]}"
    run_dir = settings.code_output_dir / "custom_r_animation_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_csv = run_dir / "input.csv"
    generated_script = run_dir / "generated_animation.R"
    wrapper_script = run_dir / "run_animation.R"
    metadata_path = run_dir / "run_metadata.json"
    output_path = settings.animation_output_dir / output_filename
    settings.animation_output_dir.mkdir(parents=True, exist_ok=True)

    frame.to_csv(input_csv, index=False)
    try:
        input_csv.chmod(0o444)
    except OSError:
        pass
    generated_script.write_text(code, encoding="utf-8")
    wrapper_script.write_text(
        _custom_animation_wrapper_text(generated_script.name), encoding="utf-8"
    )

    rscript = setup["rscript"]
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
            message="Generated R animation code is not syntactically valid.",
            parse_stderr=parse_check.stderr.strip(),
            generated_script=str(generated_script),
        )

    output_path.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "PLOTWORKS_CUSTOM_ANIMATION_INPUT": str(input_csv.resolve()),
            "PLOTWORKS_CUSTOM_ANIMATION_OUTPUT": str(output_path.resolve()),
            "PLOTWORKS_CUSTOM_ANIMATION_FPS": str(int(fps)),
            "PLOTWORKS_CUSTOM_ANIMATION_DURATION": str(float(duration)),
            "PLOTWORKS_CUSTOM_ANIMATION_WIDTH": str(int(width)),
            "PLOTWORKS_CUSTOM_ANIMATION_HEIGHT": str(int(height)),
            "PLOTWORKS_CUSTOM_ANIMATION_RES": str(int(dpi)),
        }
    )

    try:
        proc = subprocess.run(
            [rscript, wrapper_script.name],
            cwd=str(run_dir),
            env=env,
            text=True,
            capture_output=True,
            timeout=settings.r_animation_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _result(
            "error",
            message=f"Custom animation exceeded the {settings.r_animation_timeout_seconds}-second timeout.",
            generated_script=str(generated_script),
            run_directory=str(run_dir),
        )

    metadata = {
        "run_id": run_id,
        "input_file": file_path,
        "standardized_input": str(input_csv),
        "output": str(output_path),
        "fps": int(fps),
        "duration": float(duration),
        "width": int(width),
        "height": int(height),
        "dpi": int(dpi),
        "validation": validation,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    metadata_path.write_text(json.dumps(_json_safe(metadata), indent=2), encoding="utf-8")

    if proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size < 1000:
        output_path.unlink(missing_ok=True)
        return _result(
            "error",
            message="R failed while executing the generated animation function.",
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            generated_script=str(generated_script),
            run_metadata=str(metadata_path),
        )

    return _result(
        "success",
        saved_animation=str(output_path.resolve()),
        generated_script=str(generated_script.resolve()),
        run_metadata=str(metadata_path.resolve()),
        validation=validation,
        warning=(
            "Custom R animations use static validation and managed rendering, but "
            "is not a full OS-level sandbox. Review the saved code and animation."
        ),
    )
