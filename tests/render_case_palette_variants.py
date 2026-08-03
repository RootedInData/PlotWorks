#!/usr/bin/env python3
"""Render one approved ggplot2 case with selected ggrateful palettes.

This script runs outside the PlotWorks agent and uses the simulated data bundled
with the selected case.

Examples, run from the directory containing ``PlotWorks/``::

    python PlotWorks/tests/render_case_palette_variants.py \
        --case 06-raincloud --all

    python PlotWorks/tests/render_case_palette_variants.py \
        --case 06-raincloud \
        --palettes bertha terrapin_station steal_your_face

    python PlotWorks/tests/render_case_palette_variants.py --list-cases
    python PlotWorks/tests/render_case_palette_variants.py --list-palettes
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

# Running this file directly places tests/ on sys.path. Add the directory that
# contains the PlotWorks package so normal package imports work reliably.
PROJECT_PARENT = Path(__file__).resolve().parents[2]
if str(PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(PROJECT_PARENT))

from PlotWorks.config import settings
from PlotWorks.plot_styles.palettes import (
    GGRATEFUL_PALETTES,
    validate_palette_choice,
)
from PlotWorks.tools.publication_plot_tools import (
    check_publication_plot_setup,
    list_ggplot2_cases,
    render_ggplot2_case_demo,
)


def _safe_subfolder(value: str) -> Path:
    """Return a safe relative path beneath PlotWorks' managed plot directory."""

    raw = str(value).strip().replace("\\", "/")
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise ValueError(
            "output_subfolder must be a non-empty relative path without '.' or '..'."
        )

    clean_parts: list[str] = []
    for part in candidate.parts:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", part).strip("._")
        if not cleaned:
            raise ValueError("output_subfolder contains an invalid path component.")
        clean_parts.append(cleaned)
    return Path(*clean_parts)


def available_cases() -> list[dict[str, Any]]:
    """Return the approved case catalog or raise a useful error."""

    result = list_ggplot2_cases(include_demo_only=True)
    if result.get("status") != "success":
        raise RuntimeError(result.get("message", "Could not load ggplot2 cases."))
    return list(result.get("cases", []))


def resolve_palettes(use_all: bool, requested: Sequence[str] | None) -> list[str]:
    """Resolve all 16 palettes or validate a user-selected subset."""

    if use_all:
        return list(GGRATEFUL_PALETTES)

    values = [str(value).strip() for value in (requested or []) if str(value).strip()]
    if not values:
        raise ValueError("Choose --all or provide one or more names with --palettes.")

    selected: list[str] = []
    for value in values:
        canonical = validate_palette_choice("ggrateful", value)["palette_name"]
        if canonical not in selected:
            selected.append(canonical)
    return selected


def render_case_palettes(
    case_id: str,
    palettes: Sequence[str],
    *,
    reverse: bool = False,
    output_subfolder: str = "palette_tests",
) -> dict[str, Any]:
    """Render one selected case with each supplied ggrateful palette."""

    cases = {str(item["case_id"]): item for item in available_cases()}
    if case_id not in cases:
        raise ValueError(
            f"Unknown case {case_id!r}. Available cases: {', '.join(sorted(cases))}"
        )

    safe_base = _safe_subfolder(output_subfolder)
    setup = check_publication_plot_setup(check_r_packages=True)
    if setup.get("status") != "success":
        raise RuntimeError(
            "R plotting setup is incomplete. Run "
            "PlotWorks/r_plot_library/ggplot2_cases/setup.R, then retry.\n"
            + json.dumps(setup, indent=2)
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    records: list[dict[str, Any]] = []

    for palette in palettes:
        metadata = validate_palette_choice("ggrateful", palette)
        canonical = str(metadata["palette_name"])
        subfolder = safe_base / case_id / canonical
        output_name = f"{case_id}_{canonical}.png"

        result = render_ggplot2_case_demo(
            plot_case_id=case_id,
            output_name=output_name,
            palette_provider="ggrateful",
            palette_name=canonical,
            palette_reverse=reverse,
            output_subfolder=subfolder.as_posix(),
        )
        status = str(result.get("status", "error"))
        records.append(
            {
                "case_id": case_id,
                "case_title": cases[case_id].get("title", ""),
                "palette": canonical,
                "reverse": bool(reverse),
                "status": status,
                "saved_plots": result.get("saved_plots", []),
                "message": result.get("message", ""),
                "stderr": result.get("stderr", ""),
            }
        )

        saved = result.get("saved_plots", [])
        print(f"{canonical:28} {status:8} {', '.join(saved) if saved else '-'}")

    case_output_dir = settings.plot_output_dir / safe_base / case_id
    case_output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = case_output_dir / f"palette_test_{stamp}.csv"
    json_path = case_output_dir / f"palette_test_{stamp}.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "case_title",
                "palette",
                "reverse",
                "status",
                "saved_plots",
                "message",
                "stderr",
            ],
        )
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["saved_plots"] = " | ".join(record["saved_plots"])
            writer.writerow(row)

    succeeded = sum(record["status"] == "success" for record in records)
    summary = {
        "case_id": case_id,
        "case_title": cases[case_id].get("title", ""),
        "palette_provider": "ggrateful",
        "palettes": list(palettes),
        "reverse": bool(reverse),
        "total": len(records),
        "succeeded": succeeded,
        "failed": len(records) - succeeded,
        "output_directory": str(case_output_dir.resolve()),
        "csv_summary": str(csv_path.resolve()),
        "records": records,
    }
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["json_summary"] = str(json_path.resolve())
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render one approved ggplot2 case with all 16 or selected ggrateful palettes."
        )
    )
    parser.add_argument("--case", dest="case_id", help="Approved case id, e.g. 06-raincloud.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--all",
        action="store_true",
        help="Render the selected case with all 16 ggrateful palettes.",
    )
    selection.add_argument(
        "--palettes",
        nargs="+",
        metavar="NAME",
        help="One or more ggrateful palette names.",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse each selected palette.",
    )
    parser.add_argument(
        "--output-subfolder",
        default="palette_tests",
        help="Relative folder beneath outputs/plots (default: palette_tests).",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List approved case ids and exit.",
    )
    parser.add_argument(
        "--list-palettes",
        action="store_true",
        help="List all 16 ggrateful palette names and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_cases:
            for case in available_cases():
                print(f"{case['case_id']:28} {case.get('title', '')}")
            return 0

        if args.list_palettes:
            for palette in GGRATEFUL_PALETTES:
                print(palette)
            return 0

        if not args.case_id:
            parser.error("--case is required unless --list-cases or --list-palettes is used.")
        if not args.all and not args.palettes:
            parser.error("Choose either --all or --palettes NAME [NAME ...].")

        palettes = resolve_palettes(args.all, args.palettes)
        summary = render_case_palettes(
            args.case_id,
            palettes,
            reverse=args.reverse,
            output_subfolder=args.output_subfolder,
        )
        print(f"\nSucceeded: {summary['succeeded']}/{summary['total']}")
        print(f"Outputs:   {summary['output_directory']}")
        print(f"CSV:       {summary['csv_summary']}")
        print(f"JSON:      {summary['json_summary']}")
        return 0 if summary["failed"] == 0 else 1
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
