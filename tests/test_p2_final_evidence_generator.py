from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = (
    ROOT / "scripts" / "evidence_preservation" / "generate_p2_final_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("p2_final_evidence_generator", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def _write_junit(path: Path, *, tests: int = 1, failures: int = 0,
                 errors: int = 0, skipped: int = 0) -> None:
    path.write_text(
        f'<testsuites><testsuite tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}" hostname="private-host" />'
        '</testsuites>',
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "counts",
    [
        {"tests": 0},
        {"failures": 1},
        {"errors": 1},
        {"skipped": 1},
    ],
)
def test_junit_input_must_be_complete_and_green(tmp_path: Path, counts: dict) -> None:
    source = tmp_path / "source.xml"
    destination = tmp_path / "public.xml"
    _write_junit(source, **counts)

    with pytest.raises(ValueError, match="JUnit"):
        GENERATOR._sanitized_junit(source, destination)


def test_junit_hostname_is_sanitized_and_counts_are_derived(tmp_path: Path) -> None:
    source = tmp_path / "source.xml"
    destination = tmp_path / "public.xml"
    _write_junit(source, tests=7)

    counts = GENERATOR._sanitized_junit(source, destination)

    assert counts == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}
    assert "private-host" not in destination.read_text(encoding="utf-8")
    assert "LOCAL_HOST" in destination.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("case_a_geometry", "case_a_semantic", "case_a_ui", "case_b", "reopen"),
    [
        ("GEOMETRY_DIFFERENT", "SEMANTIC_EQUIVALENT", "UI_DIFFERENT", "GEOMETRY_DIFFERENT", "GEOMETRY_EQUIVALENT"),
        ("GEOMETRY_EQUIVALENT", "SEMANTIC_DIFFERENT", "UI_DIFFERENT", "GEOMETRY_DIFFERENT", "GEOMETRY_EQUIVALENT"),
        ("GEOMETRY_EQUIVALENT", "SEMANTIC_EQUIVALENT", "UI_SAME", "GEOMETRY_DIFFERENT", "GEOMETRY_EQUIVALENT"),
    ],
)
def test_scientific_pass_requires_all_case_a_case_b_and_reopen_conditions(
    case_a_geometry: str,
    case_a_semantic: str,
    case_a_ui: str,
    case_b: str,
    reopen: str,
) -> None:
    assert GENERATOR._scientific_status(
        case_a_geometry,
        case_a_semantic,
        case_a_ui,
        case_b,
        reopen,
    ) == "FAIL"


def test_scientific_pass_is_derived_from_all_required_conditions() -> None:
    assert GENERATOR._scientific_status(
        "GEOMETRY_EQUIVALENT",
        "SEMANTIC_EQUIVALENT",
        "UI_DIFFERENT",
        "GEOMETRY_DIFFERENT",
        "GEOMETRY_EQUIVALENT",
    ) == "PASS"
