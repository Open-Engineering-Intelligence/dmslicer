import json
import os
from pathlib import Path
import subprocess
import sys

from dmslicer.runner import analyze_case01, generate_case01_fixture, run_capability_probe, run_repeatability


def make_fixture(tmp_path: Path) -> Path:
    step_path = tmp_path / "case01.step"
    generate_case01_fixture(step_path, tmp_path / "expected.json")
    return step_path


def analyze_fixture(tmp_path: Path) -> tuple[Path, dict]:
    step_path = make_fixture(tmp_path)
    output_dir = tmp_path / "evidence"
    return output_dir, analyze_case01(step_path, output_dir)


def relation_by_pair(result: dict, semantic_pair: list[str]) -> dict:
    return next(relation for relation in result["relations"] if relation["semantic_pair"] == semantic_pair)


def test_case01_reimports_step_into_exactly_three_solid_regions(tmp_path: Path) -> None:
    """Catches an adapter that analyzes generator memory rather than the re-imported STEP."""
    output_dir, result = analyze_fixture(tmp_path)

    assert result["manifest"]["analysis_input"] == "reimported_step"
    assert result["manifest"]["imported_solid_count"] == 3
    assert len(result["regions"]) == 3
    assert all(region["validation"]["is_valid"] for region in result["regions"])
    for filename in (
        "manifest.json",
        "regions.json",
        "relations.json",
        "interface_patches.json",
        "provenance.json",
    ):
        assert (output_dir / filename).is_file()


def test_case01_has_two_face_contacts_and_one_disjoint_relation(tmp_path: Path) -> None:
    """Catches wrong pair classification or an AABB candidate being promoted without B-rep evidence."""
    _, result = analyze_fixture(tmp_path)

    for pair in (["A", "G"], ["G", "B"]):
        relation = relation_by_pair(result, pair)
        assert relation["relation_type"] == "FACE_CONTACT"
        assert relation["intersection_dimension"] == 2
        assert relation["confirmed"] is True
        assert relation["evidence"]["method"] == "face_common_brep"
    relation_ab = relation_by_pair(result, ["A", "B"])
    assert relation_ab["relation_type"] == "DISJOINT"
    assert relation_ab["confirmed"] is True


def test_case01_patches_have_400_square_mm_and_two_sided_provenance(tmp_path: Path) -> None:
    """Catches accepted contact patches with wrong area or missing source-face lineage."""
    _, result = analyze_fixture(tmp_path)

    patches = result["interface_patches"]
    assert len(patches) == 2
    assert {patch["area_mm2"] for patch in patches} == {400.0}
    for patch in patches:
        assert patch["relation_type"] == "FACE_CONTACT"
        assert patch["intersection_dimension"] == 2
        assert patch["source_face_a_id"]
        assert patch["source_face_b_id"]
        assert patch["provenance_method"] == "explicit_geometric_matching"
        assert patch["provenance_status"] == "COMPLETE"


def test_case01_ids_relations_and_provenance_are_repeatable_across_processes(tmp_path: Path) -> None:
    """Catches identities derived from process-specific topology ordering or object addresses."""
    step_path = make_fixture(tmp_path)
    repeatability = run_repeatability(step_path, tmp_path / "evidence")

    assert repeatability["status"] == "PASS"
    assert repeatability["comparison"]["document_ids_match"] is True
    assert repeatability["comparison"]["region_ids_match"] is True
    assert repeatability["comparison"]["face_ids_match"] is True
    assert repeatability["comparison"]["patch_ids_match"] is True
    assert repeatability["comparison"]["relation_mappings_match"] is True
    assert repeatability["comparison"]["provenance_mappings_match"] is True
    assert (tmp_path / "evidence" / "repeatability.json").is_file()


def test_capability_probe_records_actual_boolean_history_limit_and_face_common_path(tmp_path: Path) -> None:
    """Catches a probe that assumes unavailable native history or skips the working B-rep path."""
    output_path = tmp_path / "capability_probe.json"
    probe = run_capability_probe(output_path)

    assert probe["step_export"]["status"] == "AVAILABLE"
    assert probe["step_import"]["status"] == "AVAILABLE"
    assert probe["face_common"]["status"] == "AVAILABLE"
    assert probe["native_boolean_history"]["status"] == "NOT_AVAILABLE"
    assert json.loads(output_path.read_text(encoding="utf-8"))["opencascade"]["status"] == "AVAILABLE"


def test_case01_headless_cli_publishes_analysis_evidence(tmp_path: Path) -> None:
    """Catches a package that works only through Python imports rather than the required headless command."""
    step_path = make_fixture(tmp_path)
    output_dir = tmp_path / "cli_evidence"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())

    completed = subprocess.run(
        [sys.executable, "-m", "dmslicer", "analyze-case01", str(step_path), str(output_dir)],
        cwd=Path.cwd(),
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output_dir / "manifest.json").is_file()
