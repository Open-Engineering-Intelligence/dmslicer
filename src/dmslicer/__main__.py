"""Command-line entry point for the CASE01 headless evidence workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import analyze_case01, generate_case01_fixture, run_capability_probe, run_repeatability


def main() -> None:
    parser = argparse.ArgumentParser(description="DM-Slicer CASE01 STEP/B-rep evidence workflow")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate-case01", help="generate the CASE01 STEP fixture through FreeCAD")
    generate.add_argument("step_path", type=Path)
    generate.add_argument("expected_path", type=Path)

    analyze = commands.add_parser("analyze-case01", help="re-import a CASE01 STEP and publish evidence JSON")
    analyze.add_argument("step_path", type=Path)
    analyze.add_argument("output_dir", type=Path)

    repeat = commands.add_parser("repeatability", help="compare two independent CASE01 FreeCADCmd analyses")
    repeat.add_argument("step_path", type=Path)
    repeat.add_argument("output_dir", type=Path)

    probe = commands.add_parser("capability-probe", help="write actual FreeCADCmd capability evidence")
    probe.add_argument("output_path", type=Path)

    arguments = parser.parse_args()
    if arguments.command == "generate-case01":
        result = generate_case01_fixture(arguments.step_path, arguments.expected_path)
    elif arguments.command == "analyze-case01":
        result = analyze_case01(arguments.step_path, arguments.output_dir)
    elif arguments.command == "repeatability":
        result = run_repeatability(arguments.step_path, arguments.output_dir)
    else:
        result = run_capability_probe(arguments.output_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
