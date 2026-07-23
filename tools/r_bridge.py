from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config import settings
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
    manifest = _read_manifest()
    for case in manifest.get("cases", []):
        if case.get("case_id") == case_id:
            return case
    raise ValueError(f"Unknown ggplot2 case_id: {case_id!r}")


def check_r_environment(check_packages: bool = False) -> dict[str, Any]:
    """Check whether Rscript and the copied ggplot2 case library are available.

    Args:
        check_packages: If true, ask R to check the packages listed in setup.R.
            Leave false for a faster structural check.
    """

    rscript = _rscript_path()
    if rscript is None:
        return _result(
            "error",
            message="Rscript was not found on PATH.",
            next_steps=[
                "Install R on the same system/environment where you run adk run or adk web.",
                "After installing R, verify with: Rscript --version",
                "Then run the plotting library setup.R to install required R packages.",
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
                  "circlize", "igraph", "ggraph", "viridisLite", "scales")
        installed <- rownames(installed.packages())
        missing <- setdiff(pkgs, installed)
        if (length(missing) > 0) {
          cat(paste(missing, collapse=","))
          quit(status = 10)
        }
        cat("OK")
        '''
        proc = subprocess.run(
            [rscript, "-e", code],
            cwd=str(cases_dir),
            text=True,
            capture_output=True,
            timeout=120,
        )
        response["package_check_returncode"] = proc.returncode
        response["package_check_stdout"] = proc.stdout.strip()
        response["package_check_stderr"] = proc.stderr.strip()
        if proc.returncode != 0:
            response["package_status"] = "missing_or_unavailable_packages"
            response["next_steps"] = [
                f"From the plotting folder, run: Rscript {setup_file}",
                "If installation fails, install system libraries requested by R, then rerun setup.R.",
                "The agency can still list cases, inspect data, and run EDA while plotting packages are being fixed.",
            ]
        else:
            response["package_status"] = "required packages appear to be installed"

    return _result("success", **response)


def validate_path_readability_for_r(input_path: str = "", output_dir: str = "") -> dict[str, Any]:
    """Verify that Python and R can see the same input/output paths.

    Args:
        input_path: Optional dataset path. Relative paths are resolved inside DATA_DIR.
        output_dir: Optional output directory. Defaults to PLOT_OUTPUT_DIR.
    """

    rscript = _rscript_path()
    if rscript is None:
        return _result("error", message="Rscript was not found on PATH.")

    resolved_input = ""
    if input_path:
        try:
            candidate = Path(str(input_path)).expanduser()
            if candidate.is_absolute():
                if not candidate.exists():
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
    if (nzchar(input_path) && !file.exists(input_path)) {
      cat(paste0("R cannot read input_path: ", input_path))
      quit(status = 20)
    }
    if (!nzchar(output_dir) || !dir.exists(output_dir)) {
      cat(paste0("R cannot access output_dir: ", output_dir))
      quit(status = 21)
    }
    test_file <- file.path(output_dir, ".adk_r_write_test")
    ok <- tryCatch({ writeLines("ok", test_file); file.remove(test_file); TRUE },
                   error = function(e) FALSE)
    if (!ok) {
      cat(paste0("R cannot write to output_dir: ", output_dir))
      quit(status = 22)
    }
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
                "Use a path that is readable from the environment where ADK is running.",
                "When running inside WSL, prefer /mnt/c/... paths rather than C:\\... paths.",
                "The safest option is to place data files inside the agency data/ directory.",
            ],
        )
    return _result(
        "success",
        python_input_path=resolved_input,
        python_output_dir=str(out_dir.resolve()),
        r_status=proc.stdout.strip(),
    )


def run_ggplot2_case(case_id: str, input_path: str = "", output_path: str = "") -> dict[str, Any]:
    """Run one approved ggplot2 case through Rscript.

    Args:
        case_id: Approved case id from plot_manifests/ggplot2_cases.json.
        input_path: Optional standardized CSV/TSV to use instead of simulated data.
        output_path: Optional final PNG path. If omitted, a timestamped file is written
            to PLOT_OUTPUT_DIR.
    """

    setup = check_r_environment(check_packages=False)
    if setup.get("status") != "success":
        return setup

    try:
        case = _case_by_id(case_id)
    except Exception as exc:
        return _result("error", message=str(exc))

    case_dir = settings.ggplot2_cases_dir / case["case_dir"]
    plot_script = case_dir / "plot.R"
    if not plot_script.exists():
        return _result("error", message=f"Missing plot.R for case {case_id}: {plot_script}")

    resolved_input = ""
    if input_path:
        try:
            resolved_input = str(resolve_data_path(input_path)) if not Path(input_path).is_absolute() else str(Path(input_path).resolve())
        except Exception as exc:
            return _result("error", message=f"Cannot read input path before R run: {exc}")

    settings.plot_output_dir.mkdir(parents=True, exist_ok=True)
    if output_path:
        out = Path(output_path).expanduser()
        if not out.is_absolute():
            out = settings.plot_output_dir / out
    else:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        first_figure = case.get("figure_files", [f"{case_id}.png"])[0]
        out = settings.plot_output_dir / f"{stamp}_{case_id}_{Path(first_figure).name}"
    out.parent.mkdir(parents=True, exist_ok=True)

    path_check = validate_path_readability_for_r(resolved_input, str(out.parent))
    if path_check.get("status") != "success":
        return path_check

    env = os.environ.copy()
    env["ADK_INPUT_PATH"] = resolved_input
    env["ADK_OUTPUT_PATH"] = str(out.resolve())
    if len(case.get("figure_files", [])) > 1:
        env["ADK_OUTPUT_DIR"] = str(out.parent.resolve())
    else:
        env.pop("ADK_OUTPUT_DIR", None)

    rscript = _rscript_path()
    assert rscript is not None
    code = f'source("{case["case_dir"]}/plot.R")'
    proc = subprocess.run(
        [rscript, "-e", code],
        cwd=str(settings.ggplot2_cases_dir),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
    )

    # Cases with multiple output files use ADK_OUTPUT_DIR and their default basenames.
    produced = []
    for fig_name in case.get("figure_files", []):
        candidate = out.parent / fig_name
        if candidate.exists():
            produced.append(str(candidate.resolve()))
    if out.exists() and str(out.resolve()) not in produced:
        produced.insert(0, str(out.resolve()))

    if proc.returncode != 0:
        return _result(
            "error",
            message=f"R failed while rendering ggplot2 case {case_id}.",
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            attempted_output=str(out.resolve()),
            next_steps=[
                "Check that R and the case-specific packages are installed.",
                "Run setup.R from the ggplot2_cases folder if packages are missing.",
                "Check that the selected case supports the provided data columns.",
            ],
        )

    if not produced:
        return _result(
            "warning",
            message="R completed but no expected output PNG was found.",
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            attempted_output=str(out.resolve()),
        )

    return _result(
        "success",
        case_id=case_id,
        used_simulated_data=not bool(resolved_input),
        input_path=resolved_input,
        saved_plots=produced,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )
