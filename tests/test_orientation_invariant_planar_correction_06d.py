"""06D rigid-transform covariance for planar interface correction."""

import importlib
import copy
import math
from pathlib import Path

import pytest


def _module():
    return importlib.import_module(
        "dmslicer.orientation_invariant_planar_correction_06d"
    )


def test_reference_direction_is_strictly_validated_and_normalized() -> None:
    """Break caught: 06D silently falls back to +Z or accepts invalid numerics."""
    module = _module()
    normalized = module.normalize_reference_direction([1, 2, 3])
    assert normalized == pytest.approx(
        [1 / math.sqrt(14), 2 / math.sqrt(14), 3 / math.sqrt(14)]
    )
    for invalid in (None, [0, 0, 0], [math.nan, 0, 1], [math.inf, 0, 1], [True, 0, 1], [0, 1]):
        assert module.normalize_reference_direction(invalid) is None


def test_pure_normal_translation_covaries_with_reference_direction() -> None:
    """Break caught: the correction remains hard-coded to world -Z."""
    module = _module()
    direction = [1 / math.sqrt(2), 0.0, 1 / math.sqrt(2)]
    assert module.pure_normal_translation(0.05, direction) == pytest.approx(
        [-0.05 / math.sqrt(2), 0.0, -0.05 / math.sqrt(2)]
    )


@pytest.mark.parametrize(
    "matrix",
    [
        [[2, 0, 0], [0, 1, 0], [0, 0, 1]],
        [[-1, 0, 0], [0, 1, 0], [0, 0, 1]],
    ],
)
def test_covariance_rotation_rejects_scale_and_reflection(matrix) -> None:
    """Break caught: scale or reflection is mislabeled as a proper rotation."""
    module = _module()
    assert module.validate_rotation_matrix(matrix)["status"] == "FAIL"


def test_d01_rotated_partial_overlap_executes_covariant_brep_correction(
    tmp_path: Path,
) -> None:
    """Break caught: FaceSet selection or correction remains tied to world Z."""
    module = _module()
    fixture_root = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixture_root, scenarios=("D01",))
    result = module.run_orientation_case(
        fixture_root, "D01", tmp_path / "output", create_view=False
    )
    operation = result["operation"]
    assert result["validation"]["status"] == "PASS"
    assert operation["status"] == "SUPPORTED_UNIQUE_INTERFACE_FACESET"
    assert operation["motion"]["executed_translation_mm"] == pytest.approx(
        [-0.05 / math.sqrt(2), 0.0, -0.05 / math.sqrt(2)], abs=1.0e-7
    )
    assert operation["partition"]["common_area_mm2"] == pytest.approx(480.0)
    assert operation["partition"]["coverage"] == pytest.approx(
        {"Side_1": 0.6, "Side_2": 0.6}
    )
    assert operation["fuse"]["executed"] is True
    assert result["covariance"]["status"] == "PASS"


@pytest.mark.parametrize(
    "invalid",
    [None, [0, 0, 0], [math.nan, 0, 1], [math.inf, 0, 1], [True, 0, 1], [0, 1]],
)
def test_invalid_reference_direction_fails_closed_in_brep_runner(
    tmp_path: Path, invalid
) -> None:
    """Break caught: the integration runner falls back to +Z and moves Side_2."""
    module = _module()
    fixture_root = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixture_root, scenarios=("D01",))
    result = module.run_orientation_case(
        fixture_root,
        "D01",
        tmp_path / "output",
        create_view=False,
        reference_direction_override=invalid,
    )
    operation = result["operation"]
    assert operation["status"] == "UNSUPPORTED_INVALID_REFERENCE_DIRECTION"
    assert operation["motion"]["executed_translation_norm_mm"] == 0.0
    assert operation["fuse"]["executed"] is False


@pytest.mark.parametrize(
    ("scenario", "common_area", "patches", "components", "loops", "holes"),
    [
        ("D02", 384.0, 2, 2, 2, 0),
        ("D03", 300.0 * math.pi, 1, 1, 2, 1),
    ],
)
def test_generic_orientation_preserves_multipatch_and_annular_topology(
    tmp_path: Path,
    scenario: str,
    common_area: float,
    patches: int,
    components: int,
    loops: int,
    holes: int,
) -> None:
    """Break caught: generic rotations change patch/component/hole geometry truth."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=(scenario,))
    result = module.run_orientation_case(fixtures, scenario, tmp_path / "output")
    operation = result["operation"]
    assert result["validation"]["status"] == "PASS"
    assert result["covariance"]["status"] == "PASS"
    assert result["covariance"]["geometric_equivalence"] == "PASS"
    assert operation["partition"]["common_area_mm2"] == pytest.approx(common_area)
    assert operation["topology"]["patch_count"] == patches
    assert operation["topology"]["component_count"] == components
    assert operation["topology"]["boundary_component_count"] == loops
    assert operation["topology"]["hole_count"] == holes
    families = result["generation"]["representation_families"]
    assert families["pre_surface"] == families["post_surface"]
    assert families["pre_boundary_curve"] == families["post_boundary_curve"]
    if scenario == "D03":
        assert "Plane" in families["post_surface"]
        assert "Circle" in families["post_boundary_curve"]


def test_reversed_reference_is_not_auto_flipped(tmp_path: Path) -> None:
    """Break caught: -n is silently replaced with +n and executes the original result."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D01",))
    semantics = module.read_json(fixtures / "D01" / "orientation_semantics.json")
    reversed_direction = [-value for value in semantics["reference_direction"]]
    result = module.run_orientation_case(
        fixtures,
        "D01",
        tmp_path / "output",
        reference_direction_override=reversed_direction,
    )
    assert result["operation"]["status"] != "SUPPORTED_UNIQUE_INTERFACE_FACESET"
    assert result["operation"]["motion"]["executed_translation_norm_mm"] == 0.0
    assert result["operation"]["fuse"]["executed"] is False


def test_translation_only_control_changes_support_not_relative_geometry(tmp_path: Path) -> None:
    """Break caught: absolute world support is used as the gap."""
    module = _module()
    control = module.run_translation_only_control(tmp_path)
    assert control["status"] == "PASS"
    assert control["base_support_coordinate_mm"] != pytest.approx(
        control["translated_support_coordinate_mm"]
    )
    assert control["gap_invariant"] == "PASS"
    assert control["translation_vector_invariant"] == "PASS"


def test_covariance_validator_rejects_vector_scalar_and_topology_tampering(
    tmp_path: Path,
) -> None:
    """Break caught: covariance trusts JSON labels instead of measured relations."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D02",))
    result = module.run_orientation_case(fixtures, "D02", tmp_path / "output")
    base = result["base_operation"]
    generation = result["generation"]
    for path, replacement in (
        (("motion", "executed_translation_mm"), [0.01, 0.0, -0.05]),
        (("partition", "common_area_mm2"), 385.0),
        (("topology", "component_count"), 1),
    ):
        tampered = copy.deepcopy(result["operation"])
        target = tampered
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        assert module.validate_covariance(tampered, generation, base)["status"] == "FAIL"
    corrupted_base = copy.deepcopy(base)
    corrupted_base["reference_direction"]["normalized_reference_direction"] = [1.0, 0.0, 0.0]
    corrupted_base["motion"]["executed_translation_mm"] = [99.0, 98.0, 97.0]
    assert module.validate_covariance(
        result["operation"], generation, corrupted_base,
        geometry_equivalence=result["covariance"]["geometric_equivalence"],
    )["status"] == "FAIL"


def test_inverse_brep_equivalence_records_topology_and_analytic_families(
    tmp_path: Path,
) -> None:
    """Break caught: set equivalence passes without boundary/topology/family evidence."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D03",))
    result = module.run_orientation_case(fixtures, "D03", tmp_path / "output")
    details = result["covariance"]["geometry_equivalence_details"]
    assert details["Common"]["boundary_topology_match"] is True
    assert details["Common"]["boundary_curve_family_match"] is True
    for name in ("Corrected_Side_1", "Corrected_Side_2", "Fused"):
        assert details[name]["topology_match"] is True
        assert details[name]["surface_family_match"] is True
        assert details[name]["boundary_curve_family_match"] is True


def test_covariance_checks_measured_normals_and_centroids(tmp_path: Path) -> None:
    """Break caught: covariance checks only reference/translation and omits c'=Rc+q."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D02",))
    result = module.run_orientation_case(fixtures, "D02", tmp_path / "output")
    vectors = result["covariance"]["vector_covariants"]
    assert vectors["normal_vectors"] == "PASS"
    assert vectors["centroids"]
    assert set(vectors["centroids"].values()) == {"PASS"}


def test_patch_id_reordering_does_not_define_covariance(tmp_path: Path) -> None:
    """Break caught: patch IDs or AABB order replace inverse-transform B-rep matching."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D02",))
    result = module.run_orientation_case(fixtures, "D02", tmp_path / "output")
    reordered = copy.deepcopy(result["operation"])
    reordered["partition"]["common_patches"].reverse()
    for index, patch in enumerate(reordered["partition"]["common_patches"], start=1):
        patch["patch_id"] = f"Rotated_Local_{index}"
    covariance = module.validate_covariance(
        reordered, result["generation"], result["base_operation"],
        geometry_equivalence=result["covariance"]["geometric_equivalence"],
    )
    assert covariance["status"] == "PASS"


def test_suite_publishes_views_two_process_repeatability_and_controls(
    tmp_path: Path,
) -> None:
    """Break caught: integrated 06D evidence omits repeatability, FCStd, or +Z control."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures)
    output = tmp_path / "suite"
    summary = module.run_orientation_suite(fixtures, output)
    assert summary["status"] == "PASS"
    assert summary["repeatability"] == {
        scenario: {"processes": 2, "status": "PASS"}
        for scenario in ("D01", "D02", "D03")
    }
    assert summary["controls"]["translation_only"] == "PASS"
    assert summary["controls"]["plus_z_compatibility"] == "PASS"
    assert summary["controls"]["reference_direction"] == "PASS"
    for scenario in ("D01", "D02", "D03"):
        case = output / scenario
        assert {path.name for path in case.iterdir()} >= {
            "operation.json", "validation.json", "covariance.json",
            "facesets.json", "patches.json", "components.json",
            "provenance.json", "repeatability.json", "operation_debug.FCStd",
            "corrected_assembly.step", "fused.step",
        }
    assert (output / "VIEW_INDEX.md").is_file()


def test_expected_mutation_cannot_change_actual_geometry_or_action(tmp_path: Path) -> None:
    """Break caught: expected truth leaks into FaceSet/gap/translation/common production logic."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D01",))
    first = module.run_orientation_case(fixtures, "D01", tmp_path / "first")
    expected_path = fixtures / "D01" / "expected.json"
    expected = module.read_json(expected_path)
    expected["common_area_mm2"] = 1.0
    module.write_json(expected_path, expected)
    second = module.run_orientation_case(fixtures, "D01", tmp_path / "second")
    assert second["validation"]["status"] == "FAIL"
    assert module.actual_geometry_projection(first["operation"]) == module.actual_geometry_projection(second["operation"])


def test_artifact_byte_failure_is_separate_from_geometry_equivalence(tmp_path: Path) -> None:
    """Break caught: a replaced artifact is mislabeled as a proved geometry difference."""
    module = _module()
    fixtures = tmp_path / "fixtures"
    module.generate_orientation_fixtures(fixtures, scenarios=("D01",))
    result = module.run_orientation_case(fixtures, "D01", tmp_path / "output")
    output = Path(result["output_dir"])
    (output / "fused.step").write_bytes(b"replaced")
    validation = module.validate_published_artifacts(result["operation"], output)
    assert validation["artifact_byte_integrity"] == "FAIL"
    assert validation["geometric_equivalence"] == "NOT_EVALUATED_INVALID_ARTIFACT"


def test_real_brep_patch_motion_fails_even_if_recorded_hash_is_unchanged() -> None:
    """Break caught: an unchanged digest field overrides actual B-rep displacement."""
    module = _module()
    probe = module._run_freecad(
        {"action": "probe_moved_patch_equivalence", "rules": module.RULES}
    )
    assert probe["recorded_hash_fields_equal"] is True
    assert probe["geometric_equivalence"] == "FAIL"
    assert probe["minimum_distance_mm"] > module.RULES["linear_epsilon_mm"]
