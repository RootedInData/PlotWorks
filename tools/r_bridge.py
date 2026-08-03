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
from ..plot_styles.palettes import validate_palette_choice
from .data_tools import _json_safe, resolve_data_path


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return _json_safe({"status": status, **kwargs})


def _rscript_path() -> str | None:
    return shutil.which("Rscript")


def _read_manifest() -> dict[str, Any]:
    if not settings.ggplot2_cases_manifest.exists():
        raise FileNotFoundError(f"Missing plot manifest: {settings.ggplot2_cases_manifest}")
    return json.loads(settings.ggplot2_cases_manifest.read_text(encoding="utf-8"))


def _case_by_id(case_id: str) -> dict[str, Any]:
    for case in _read_manifest().get("cases", []):
        if case.get("case_id") == case_id:
            return case
    raise ValueError(f"Unknown ggplot2 case_id: {case_id!r}")


def _safe_managed_filename(output_path: str, default_name: str) -> str:
    raw = str(output_path).strip() if output_path else default_name
    candidate = Path(raw)
    if candidate.name != raw or candidate.parent != Path("."):
        raise ValueError(
            "output_path must be a filename only. Do not include outputs/plots or other directories."
        )
    suffix = candidate.suffix.lower() or ".png"
    if suffix != ".png":
        raise ValueError("Approved ggplot2 case recipes currently produce PNG files only.")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate.stem).strip("._") or "ggplot2_case"
    return f"{stem}.png"


def _safe_output_subfolder(output_subfolder: str) -> Path:
    """Resolve a relative subfolder beneath outputs/plots without traversal."""

    raw = str(output_subfolder).strip().replace("\\", "/")
    if not raw:
        return Path()
    candidate = Path(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(
            "output_subfolder must be a safe relative path beneath outputs/plots."
        )
    cleaned_parts = []
    for part in candidate.parts:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", part).strip("._")
        if not cleaned:
            raise ValueError("output_subfolder contains an invalid path component.")
        cleaned_parts.append(cleaned)
    return Path(*cleaned_parts)


def _resolve_palette_choice(
    case: dict[str, Any],
    palette_provider: str,
    palette_name: str,
    palette_reverse: bool,
) -> dict[str, Any]:
    """Apply explicit request > case default > original recipe precedence."""

    explicit_provider = str(palette_provider).strip().lower()
    explicit_name = str(palette_name).strip()
    if explicit_provider or explicit_name:
        provider = explicit_provider or "ggrateful"
        choice = validate_palette_choice(provider, explicit_name)
        choice["reverse"] = bool(palette_reverse)
        choice["source"] = "explicit_user_request"
        return choice

    default = case.get("palette_default", {})
    provider = str(default.get("provider", "recipe") or "recipe")
    name = str(default.get("name", "") or "")
    choice = validate_palette_choice(provider, name)
    choice["reverse"] = bool(default.get("reverse", False))
    choice["source"] = "case_palette_default" if provider != "recipe" else "original_recipe_colors"
    return choice


def _valid_nonempty_file(path: Path) -> bool:
    if not path.exists() or not path.is_file() or path.stat().st_size < 100:
        return False
    if path.suffix.lower() == ".png":
        try:
            return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        except OSError:
            return False
    return True


def check_r_environment(check_packages: bool = False) -> dict[str, Any]:
    """Check Rscript, plotting-library paths, and optionally package availability."""

    rscript = _rscript_path()
    if rscript is None:
        return _result(
            "error",
            message="Rscript was not found on PATH.",
            next_steps=[
                "Install R on the same system/environment where you run adk run or adk web.",
                "Verify with: Rscript --version",
                "Then run setup.R in r_plot_library/ggplot2_cases.",
            ],
        )

    cases_dir = settings.ggplot2_cases_dir
    setup_file = cases_dir / "setup.R"
    required_paths = {
        "ggplot2_cases_dir": str(cases_dir),
        "setup_R": str(setup_file),
        "cases_folder": str(cases_dir / "cases"),
        "theme_case_R": str(cases_dir / "R" / "theme_case.R"),
        "adk_data_bridge_R": str(cases_dir / "R" / "adk_data_bridge.R"),
        "shared_palettes_R": str(settings.r_shared_plot_dir / "palettes.R"),
    }
    missing_paths = [label for label, value in required_paths.items() if not Path(value).exists()]
    if missing_paths:
        return _result(
            "error",
            message="The R plotting library is incomplete or not in the expected location.",
            rscript=rscript,
            required_paths=required_paths,
            missing_paths=missing_paths,
        )

    response: dict[str, Any] = {
        "rscript": rscript,
        "ggplot2_cases_dir": str(cases_dir.resolve()),
        "setup_file": str(setup_file.resolve()),
        "path_status": "required R plotting paths exist",
    }

    if check_packages:
        code = r'''
        pkgs <- c("ggplot2", "dplyr", "tidyr", "ggrepel", "patchwork",
                  "gghalves", "ggforce", "ggalluvial", "treemapify",
                  "circlize", "igraph", "tidygraph", "graphlayouts",
                  "ggraph", "viridisLite", "scales", "ggh4x", "ggridges",
                  "ggrateful", "remotes")
        rows <- lapply(pkgs, function(pkg) {
          if (requireNamespace(pkg, quietly = TRUE)) {
            c(package = pkg,
              version = as.character(packageVersion(pkg)),
              location = find.package(pkg))
          } else {
            c(package = pkg, version = "MISSING", location = "")
          }
        })
        for (row in rows) cat(paste(row, collapse = "\t"), "\n")
        if (any(vapply(rows, function(x) x[["version"]] == "MISSING", logical(1))))
          quit(status = 10)
        '''
        proc = subprocess.run(
            [rscript, "-e", code],
            cwd=str(cases_dir),
            text=True,
            capture_output=True,
            timeout=120,
        )
        package_rows = []
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                package_rows.append(
                    {"package": parts[0], "version": parts[1], "location": parts[2]}
                )
        missing = [row["package"] for row in package_rows if row["version"] == "MISSING"]
        response.update(
            {
                "package_check_returncode": proc.returncode,
                "packages": package_rows,
                "missing_packages": missing,
                "package_check_stderr": proc.stderr.strip(),
            }
        )
        if proc.returncode != 0:
            response["package_status"] = "missing_or_unavailable_packages"
            response["next_steps"] = [
                f"From the plotting folder, run: Rscript {setup_file}",
                "On WSL/Linux, prefer available Ubuntu r-cran-* packages for difficult dependencies.",
                "If ggplot2 and ggraph are incompatible, install the current CRAN ggraph into the user R library.",
            ]
            return _result("error", **response)
        response["package_status"] = "required packages appear to be installed"

    return _result("success", **response)


def validate_path_readability_for_r(input_path: str = "", output_dir: str = "") -> dict[str, Any]:
    """Verify that Python and R can see the same input/output paths."""

    rscript = _rscript_path()
    if rscript is None:
        return _result("error", message="Rscript was not found on PATH.")

    resolved_input = ""
    if input_path:
        try:
            candidate = Path(str(input_path)).expanduser()
            if candidate.is_absolute():
                if not candidate.exists() or not candidate.is_file():
                    raise FileNotFoundError(f"File not found: {candidate}")
                resolved_input = str(candidate.resolve())
            else:
                resolved_input = str(resolve_data_path(input_path))
        except Exception as exc:
            return _result("error", message=f"Python cannot read the input path: {exc}")

    out_dir = Path(output_dir).expanduser() if output_dir else settings.plot_output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    code = r'''
    input_path <- Sys.getenv("ADK_INPUT_PATH", "")
    output_dir <- Sys.getenv("ADK_OUTPUT_DIR", "")
    if (nzchar(input_path) && !file.exists(input_path)) quit(status = 20)
    if (!nzchar(output_dir) || !dir.exists(output_dir)) quit(status = 21)
    test_file <- file.path(output_dir, ".adk_r_write_test")
    ok <- tryCatch({ writeLines("ok", test_file); file.remove(test_file); TRUE },
                   error = function(e) FALSE)
    if (!ok) quit(status = 22)
    cat("OK")
    '''
    env = os.environ.copy()
    env["ADK_INPUT_PATH"] = resolved_input
    env["ADK_OUTPUT_DIR"] = str(out_dir.resolve())
    proc = subprocess.run(
        [rscript, "-e", code],
        cwd=str(settings.ggplot2_cases_dir),
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return _result(
            "error",
            message="R path-readability check failed.",
            python_input_path=resolved_input,
            python_output_dir=str(out_dir.resolve()),
            r_stdout=proc.stdout.strip(),
            r_stderr=proc.stderr.strip(),
            next_steps=[
                "Use a path readable from the environment where ADK is running.",
                "Inside WSL, prefer /mnt/c/... paths rather than C:\\... paths.",
                "The safest option is to place source data files inside the PlotWorks data/ directory.",
            ],
        )
    return _result(
        "success",
        python_input_path=resolved_input,
        python_output_dir=str(out_dir.resolve()),
        r_status=proc.stdout.strip(),
    )


def run_ggplot2_case(
    case_id: str,
    input_path: str = "",
    output_path: str = "",
    palette_provider: str = "",
    palette_name: str = "",
    palette_reverse: bool = False,
    output_subfolder: str = "",
) -> dict[str, Any]:
    """Run one approved ggplot2 recipe through Rscript with managed paths.

    Palette precedence is explicit arguments, then the case default stored in the
    existing ggplot2 manifest, then the original recipe colors.
    """

    setup = check_r_environment(check_packages=False)
    if setup.get("status") != "success":
        return setup

    try:
        case = _case_by_id(case_id)
        case_dir = settings.ggplot2_cases_dir / case["case_dir"]
        plot_script = case_dir / "plot.R"
        if not plot_script.exists():
            raise FileNotFoundError(f"Missing plot.R for case {case_id}: {plot_script}")

        resolved_input = ""
        if input_path:
            candidate = Path(input_path).expanduser()
            if candidate.is_absolute():
                if not candidate.exists():
                    raise FileNotFoundError(f"Input file not found: {candidate}")
                resolved_input = str(candidate.resolve())
            else:
                resolved_input = str(resolve_data_path(input_path))

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        figure_files = [Path(name).name for name in case.get("figure_files", [f"{case_id}.png"])]
        default_name = f"{stamp}_{case_id}.png"
        managed_name = _safe_managed_filename(output_path, default_name)
        managed_subfolder = _safe_output_subfolder(output_subfolder)
        palette_choice = _resolve_palette_choice(
            case, palette_provider, palette_name, palette_reverse
        )
    except Exception as exc:
        return _result("error", message=str(exc))

    final_output_dir = settings.plot_output_dir / managed_subfolder
    final_output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = settings.code_output_dir / "r_case_runs" / f"{stamp}_{case_id}_{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    temporary_single = run_dir / managed_name

    path_check = validate_path_readability_for_r(resolved_input, str(run_dir))
    if path_check.get("status") != "success":
        return path_check

    env = os.environ.copy()
    env["ADK_INPUT_PATH"] = resolved_input
    env["ADK_OUTPUT_PATH"] = str(temporary_single.resolve())
    env["ADK_OUTPUT_DIR"] = str(run_dir.resolve())
    env["PLOTWORKS_PALETTE_PROVIDER"] = str(palette_choice["provider"])
    env["PLOTWORKS_PALETTE_NAME"] = str(palette_choice["palette_name"])
    env["PLOTWORKS_PALETTE_REVERSE"] = "true" if palette_choice["reverse"] else "false"

    rscript = _rscript_path()
    assert rscript is not None
    proc = subprocess.run(
        [rscript, "-e", f'source("{case["case_dir"]}/plot.R")'],
        cwd=str(settings.ggplot2_cases_dir),
        env=env,
        text=True,
        capture_output=True,
        timeout=max(settings.r_plot_timeout_seconds, 300),
    )

    if proc.returncode != 0:
        return _result(
            "error",
            message=f"R failed while rendering ggplot2 case {case_id}.",
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            run_directory=str(run_dir.resolve()),
            next_steps=[
                "Check the case-specific R package versions and dependencies.",
                "Run setup.R from the ggplot2_cases folder if packages are missing.",
                "Use check_publication_plot_setup(check_r_packages=True) to see package versions and locations.",
            ],
        )

    temporary_outputs: list[Path] = []
    if len(figure_files) == 1:
        candidates = [temporary_single, run_dir / figure_files[0]]
        temporary_outputs = [path for path in candidates if _valid_nonempty_file(path)]
        if temporary_outputs:
            temporary_outputs = [temporary_outputs[0]]
    else:
        temporary_outputs = [run_dir / name for name in figure_files if _valid_nonempty_file(run_dir / name)]

    if not temporary_outputs:
        return _result(
            "error",
            message="R completed but no valid expected output PNG was found.",
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            run_directory=str(run_dir.resolve()),
        )

    final_outputs: list[str] = []
    requested_stem = Path(managed_name).stem
    for index, temporary in enumerate(temporary_outputs):
        if len(temporary_outputs) == 1:
            final_name = managed_name
        else:
            final_name = f"{requested_stem}_{Path(figure_files[index]).stem}.png"
        final_path = final_output_dir / final_name
        if final_path.exists():
            final_path.unlink()
        shutil.move(str(temporary), str(final_path))
        if not _valid_nonempty_file(final_path):
            return _result("error", message=f"Generated output failed validation: {final_path}")
        final_outputs.append(str(final_path.resolve()))

    return _result(
        "success",
        case_id=case_id,
        used_simulated_data=not bool(resolved_input),
        input_path=resolved_input,
        palette=palette_choice,
        output_subfolder=managed_subfolder.as_posix() if managed_subfolder.parts else "",
        output_directory=str(final_output_dir.resolve()),
        saved_plots=final_outputs,
        run_directory=str(run_dir.resolve()),
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )
