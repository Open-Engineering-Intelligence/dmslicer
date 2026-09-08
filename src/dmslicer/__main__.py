"""Command-line entry point for the CASE01 headless evidence workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import analyze_case01, generate_case01_fixture, run_capability_probe, run_repeatability
from .contact_canonical_03a import analyze_contact_canonical, generate_contact_canonical, run_contact_canonical_repeatability, run_contact_canonical_suite
from .contact_canonical_03b import analyze_contact_canonical_analytic, generate_contact_canonical_analytic, run_contact_canonical_analytic_repeatability, run_contact_canonical_analytic_suite


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

    canonical_generate = commands.add_parser("generate-contact-canonical", help="generate A01-A06 canonical STEP fixtures")
    canonical_generate.add_argument("fixture_root", type=Path)

    canonical_analyze = commands.add_parser("analyze-contact-canonical", help="analyze one tracked canonical STEP fixture")
    canonical_analyze.add_argument("step_path", type=Path)
    canonical_analyze.add_argument("output_dir", type=Path)

    canonical_repeat = commands.add_parser("repeat-contact-canonical", help="compare two canonical analyses in independent FreeCADCmd processes")
    canonical_repeat.add_argument("step_path", type=Path)
    canonical_repeat.add_argument("output_dir", type=Path)

    canonical_suite = commands.add_parser("run-contact-canonical-suite", help="publish 03A evidence, debug models, and repeatability")
    canonical_suite.add_argument("fixture_root", type=Path)
    canonical_suite.add_argument("output_root", type=Path)

    analytic_generate = commands.add_parser("generate-contact-canonical-analytic", help="generate A07-A09 analytic curve STEP fixtures")
    analytic_generate.add_argument("fixture_root", type=Path)

    analytic_analyze = commands.add_parser("analyze-contact-canonical-analytic", help="analyze one tracked A07-A09 STEP fixture")
    analytic_analyze.add_argument("step_path", type=Path)
    analytic_analyze.add_argument("output_dir", type=Path)

    analytic_repeat = commands.add_parser("repeat-contact-canonical-analytic", help="compare two A07-A09 analyses in independent FreeCADCmd processes")
    analytic_repeat.add_argument("step_path", type=Path)
    analytic_repeat.add_argument("output_dir", type=Path)

    analytic_suite = commands.add_parser("run-contact-canonical-analytic-suite", help="publish 03B evidence, debug models, and repeatability")
    analytic_suite.add_argument("fixture_root", type=Path)
    analytic_suite.add_argument("output_root", type=Path)

    arguments = parser.parse_args()
    if arguments.command == "generate-case01":
        result = generate_case01_fixture(arguments.step_path, arguments.expected_path)
    elif arguments.command == "analyze-case01":
        result = analyze_case01(arguments.step_path, arguments.output_dir)
    elif arguments.command == "repeatability":
        result = run_repeatability(arguments.step_path, arguments.output_dir)
    elif arguments.command == "generate-contact-canonical":
        result = generate_contact_canonical(arguments.fixture_root)
    elif arguments.command == "analyze-contact-canonical":
        result = analyze_contact_canonical(arguments.step_path, arguments.output_dir)
    elif arguments.command == "repeat-contact-canonical":
        result = run_contact_canonical_repeatability(arguments.step_path, arguments.output_dir)
    elif arguments.command == "run-contact-canonical-suite":
        result = run_contact_canonical_suite(arguments.fixture_root, arguments.output_root)
    elif arguments.command == "generate-contact-canonical-analytic":
        result = generate_contact_canonical_analytic(arguments.fixture_root)
    elif arguments.command == "analyze-contact-canonical-analytic":
        result = analyze_contact_canonical_analytic(arguments.step_path, arguments.output_dir)
    elif arguments.command == "repeat-contact-canonical-analytic":
        result = run_contact_canonical_analytic_repeatability(arguments.step_path, arguments.output_dir)
    elif arguments.command == "run-contact-canonical-analytic-suite":
        result = run_contact_canonical_analytic_suite(arguments.fixture_root, arguments.output_root)
    else:
        result = run_capability_probe(arguments.output_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
