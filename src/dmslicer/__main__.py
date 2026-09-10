"""Command-line entry point for the CASE01 headless evidence workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import analyze_case01, generate_case01_fixture, run_capability_probe, run_repeatability
from .contact_canonical_03a import analyze_contact_canonical, generate_contact_canonical, run_contact_canonical_repeatability, run_contact_canonical_suite
from .contact_canonical_03b import analyze_contact_canonical_analytic, generate_contact_canonical_analytic, run_contact_canonical_analytic_repeatability, run_contact_canonical_analytic_suite
from .contact_canonical_03c import analyze_contact_canonical_interface_topology, generate_contact_canonical_interface_topology, run_contact_canonical_interface_topology_repeatability, run_contact_canonical_interface_topology_suite
from .contact_partition_union_04a import run_contact_partition_union, run_contact_partition_union_suite, validate_partition_union_facts_file
from .shell_fill_04a2 import generate_shell_fill_cases, run_shell_fill_case, run_shell_fill_suite
from .cylinder_partition_union_04b import generate_cylinder_fit_cases, run_cylinder_fit_case, run_cylinder_fit_suite
from .contact_tolerance_pilot_05a import generate_contact_tolerance_pilot, run_contact_tolerance_pilot_suite
from .cylindrical_interface_repair_07a import (
    generate_cylindrical_interface_repair_fixtures,
    run_cylindrical_repair_case,
    run_cylindrical_repair_suite,
)


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

    topology_generate = commands.add_parser("generate-contact-canonical-interface-topology", help="generate A11-A12 topology STEP fixtures")
    topology_generate.add_argument("fixture_root", type=Path)

    topology_analyze = commands.add_parser("analyze-contact-canonical-interface-topology", help="analyze one tracked A11/A12 STEP fixture")
    topology_analyze.add_argument("step_path", type=Path)
    topology_analyze.add_argument("output_dir", type=Path)

    topology_repeat = commands.add_parser("repeat-contact-canonical-interface-topology", help="compare two A11/A12 analyses in independent FreeCADCmd processes")
    topology_repeat.add_argument("step_path", type=Path)
    topology_repeat.add_argument("output_dir", type=Path)

    topology_suite = commands.add_parser("run-contact-canonical-interface-topology-suite", help="publish 03C topology evidence, debug models, and repeatability")
    topology_suite.add_argument("fixture_root", type=Path)
    topology_suite.add_argument("output_root", type=Path)

    partition_union = commands.add_parser("run-contact-partition-union", help="partition actual common faces and fuse one A02/A08 STEP pair")
    partition_union.add_argument("step_path", type=Path)
    partition_union.add_argument("output_dir", type=Path)

    partition_union_suite = commands.add_parser("run-contact-partition-union-suite", help="publish 04A A02/A08 operation evidence and repeatability")
    partition_union_suite.add_argument("output_root", type=Path)

    partition_union_validate = commands.add_parser("validate-contact-partition-union-facts", help="apply the production 04A final status gate to recorded facts")
    partition_union_validate.add_argument("facts_path", type=Path)
    partition_union_validate.add_argument("volume_epsilon_mm3", type=float)

    shell_fill_generate = commands.add_parser("generate-shell-fill-cases", help="generate tracked-style U01-U03 shell-fill STEP bundles")
    shell_fill_generate.add_argument("fixture_root", type=Path)

    shell_fill_case = commands.add_parser("run-shell-fill-case", help="run one tracked U01-U03 shell-fill operation")
    shell_fill_case.add_argument("case_dir", type=Path)
    shell_fill_case.add_argument("output_dir", type=Path)

    shell_fill_suite = commands.add_parser("run-shell-fill-suite", help="run U01-U03 with two-process repeatability")
    shell_fill_suite.add_argument("fixture_root", type=Path)
    shell_fill_suite.add_argument("output_root", type=Path)

    cylinder_generate = commands.add_parser("generate-cylinder-fit-cases", help="generate tracked U04-U06 cylinder STEP bundles")
    cylinder_generate.add_argument("fixture_root", type=Path)

    cylinder_case = commands.add_parser("run-cylinder-fit-case", help="run one U04-U06 cylindrical partition and union operation")
    cylinder_case.add_argument("case_dir", type=Path)
    cylinder_case.add_argument("output_dir", type=Path)

    cylinder_suite = commands.add_parser("run-cylinder-fit-suite", help="run U04-U06 with two-process repeatability")
    cylinder_suite.add_argument("fixture_root", type=Path)
    cylinder_suite.add_argument("output_root", type=Path)

    tolerance_generate = commands.add_parser("generate-contact-tolerance-pilot", help="generate limited A01/A07 tolerance-pilot STEP bundles")
    tolerance_generate.add_argument("fixture_root", type=Path)
    tolerance_suite = commands.add_parser("run-contact-tolerance-pilot-suite", help="run the limited A01/A07 tolerance pilot")
    tolerance_suite.add_argument("fixture_root", type=Path)
    tolerance_suite.add_argument("output_root", type=Path)

    cylindrical_repair_generate = commands.add_parser("generate-cylindrical-interface-repair-07a", help="generate C01-C05 and ambiguity-control STEP bundles")
    cylindrical_repair_generate.add_argument("fixture_root", type=Path)
    cylindrical_repair_case = commands.add_parser("run-cylindrical-interface-repair-case-07a", help="classify and conditionally correct one 07A cylindrical interface")
    cylindrical_repair_case.add_argument("case_dir", type=Path)
    cylindrical_repair_case.add_argument("output_dir", type=Path)
    cylindrical_repair_suite = commands.add_parser("run-cylindrical-interface-repair-suite-07a", help="run 07A scenarios with B-rep evidence and repeatability")
    cylindrical_repair_suite.add_argument("fixture_root", type=Path)
    cylindrical_repair_suite.add_argument("output_root", type=Path)

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
    elif arguments.command == "generate-contact-canonical-interface-topology":
        result = generate_contact_canonical_interface_topology(arguments.fixture_root)
    elif arguments.command == "analyze-contact-canonical-interface-topology":
        result = analyze_contact_canonical_interface_topology(arguments.step_path, arguments.output_dir)
    elif arguments.command == "repeat-contact-canonical-interface-topology":
        result = run_contact_canonical_interface_topology_repeatability(arguments.step_path, arguments.output_dir)
    elif arguments.command == "run-contact-canonical-interface-topology-suite":
        result = run_contact_canonical_interface_topology_suite(arguments.fixture_root, arguments.output_root)
    elif arguments.command == "run-contact-partition-union":
        result = run_contact_partition_union(arguments.step_path, arguments.output_dir)
    elif arguments.command == "run-contact-partition-union-suite":
        result = run_contact_partition_union_suite(arguments.output_root)
    elif arguments.command == "validate-contact-partition-union-facts":
        result = validate_partition_union_facts_file(arguments.facts_path, arguments.volume_epsilon_mm3)
    elif arguments.command == "generate-shell-fill-cases":
        result = generate_shell_fill_cases(arguments.fixture_root)
    elif arguments.command == "run-shell-fill-case":
        result = run_shell_fill_case(arguments.case_dir, arguments.output_dir)
    elif arguments.command == "run-shell-fill-suite":
        result = run_shell_fill_suite(arguments.fixture_root, arguments.output_root)
    elif arguments.command == "generate-cylinder-fit-cases":
        result = generate_cylinder_fit_cases(arguments.fixture_root)
    elif arguments.command == "run-cylinder-fit-case":
        result = run_cylinder_fit_case(arguments.case_dir, arguments.output_dir)
    elif arguments.command == "run-cylinder-fit-suite":
        result = run_cylinder_fit_suite(arguments.fixture_root, arguments.output_root)
    elif arguments.command == "generate-contact-tolerance-pilot":
        result = generate_contact_tolerance_pilot(arguments.fixture_root)
    elif arguments.command == "run-contact-tolerance-pilot-suite":
        result = run_contact_tolerance_pilot_suite(arguments.fixture_root, arguments.output_root)
    elif arguments.command == "generate-cylindrical-interface-repair-07a":
        result = generate_cylindrical_interface_repair_fixtures(arguments.fixture_root)
    elif arguments.command == "run-cylindrical-interface-repair-case-07a":
        result = run_cylindrical_repair_case(arguments.case_dir, arguments.output_dir)
    elif arguments.command == "run-cylindrical-interface-repair-suite-07a":
        result = run_cylindrical_repair_suite(arguments.fixture_root, arguments.output_root)
    else:
        result = run_capability_probe(arguments.output_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
