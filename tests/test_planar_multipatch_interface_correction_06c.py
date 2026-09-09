import copy
import importlib
import importlib.util
import json
import math
from pathlib import Path

import pytest


MODULE_NAME = "dmslicer.planar_multipatch_interface_correction_06c"


def _module():
    return importlib.import_module(MODULE_NAME)


def _run(tmp_path: Path, scenario: str, **kwargs):
    module = _module()
    return module.run_multipatch_case(
        module.FIXTURE_ROOT, scenario, tmp_path / "runs", **kwargs
    )


def test_06c_module_exists_for_planar_multipatch_interface_correction() -> None:
    """Break caught: the new 06C public workflow is absent from the package."""
    assert importlib.util.find_spec(MODULE_NAME) is not None


def test_06c_public_api_exposes_fixture_runner_suite_and_validator() -> None:
    """Break caught: callers cannot generate, execute, or validate 06C evidence."""
    module = _module()
    for name in (
        "FIXTURE_ROOT",
        "generate_multipatch_fixtures",
        "run_multipatch_case",
        "run_multipatch_suite",
        "validate_multipatch_evidence",
    ):
        assert hasattr(module, name), name


def test_generator_creates_three_independent_step_truth_bundles(tmp_path: Path) -> None:
    """Break caught: P10/P11/P12 lack tracked-style STEP and independent truth."""
    module = _module()
    manifest = module.generate_multipatch_fixtures(tmp_path)
    assert [row["scenario_id"] for row in manifest["scenarios"]] == ["P10", "P11", "P12"]
    assert manifest["numeric_rules"] == {
        "linear_epsilon_mm": 1e-7,
        "area_epsilon_mm2": 1e-8,
        "volume_epsilon_mm3": 1e-6,
    }
    for scenario in ("P10", "P11", "P12"):
        case = tmp_path / scenario
        assert {p.name for p in case.iterdir()} >= {
            "inputs.step", "parameters.json", "policy.json", "expected.json"
        }
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        assert expected["scenario_id"] == scenario
        row = manifest["scenarios"][("P10", "P11", "P12").index(scenario)]
        assert row["step_sha256"].startswith("sha256:")


def test_p10_selects_two_coplanar_feet_and_preserves_two_equal_distinct_patches(tmp_path: Path) -> None:
    """Break caught: equal-area feet are dropped, merged, or confused with the bridge."""
    result = _run(tmp_path, "P10", create_view=True)
    operation = result["operation"]
    assert result["validation"]["status"] == "PASS"
    assert operation["status"] == "SUPPORTED_UNIQUE_INTERFACE_FACESET"
    assert operation["face_sets"]["eligible_face_set_pair_count"] == 1
    assert operation["face_sets"]["raw_face_set_count"]["Side_2"] >= 2
    selected = operation["face_sets"]["selected_pair"]
    assert selected["Side_1"]["member_face_count"] == 1
    assert selected["Side_2"]["member_face_count"] == 2
    assert selected["Side_2"]["total_area_mm2"] == pytest.approx(384.0, abs=1e-8)
    assert selected["gap_mm"] == pytest.approx(0.05, abs=1e-7)
    assert selected["gap_spread_mm"] <= 1e-7
    assert operation["motion"]["executed_translation_mm"] == pytest.approx([0.0, 0.0, -0.05], abs=1e-7)
    assert operation["motion"]["tangential_translation_norm_mm"] == pytest.approx(0.0, abs=1e-8)
    partition = operation["partition"]
    assert partition["common_area_mm2"] == pytest.approx(384.0, abs=1e-8)
    assert [patch["area_mm2"] for patch in partition["common_patches"]] == pytest.approx([192.0, 192.0], abs=1e-8)
    assert len({patch["geometry_digest"] for patch in partition["common_patches"]}) == 2
    assert partition["coverage"] == pytest.approx({"Side_1": 0.16, "Side_2": 1.0})
    assert partition["remaining_area_mm2"] == pytest.approx({"Side_1": 2016.0, "Side_2": 0.0}, abs=1e-8)
    assert partition["remaining_empty"]["Side_2"] is True
    topology = operation["topology"]
    assert (topology["patch_count"], topology["component_count"]) == (2, 2)
    assert topology["connectedness"] == "disconnected"
    assert (topology["boundary_component_count"], topology["hole_count"], topology["first_betti_number"]) == (2, 0, 0)
    assert operation["fuse"]["executed"] is True
    assert operation["fuse"]["solid_count"] == 1
    assert operation["fuse"]["valid"] is True and operation["fuse"]["closed"] is True
    assert "Fused_Solid" in operation["view_reopen"]["visible_objects"]
    assert "Original_Side_1" not in operation["view_reopen"]["visible_objects"]
    assert {path.name for path in Path(result["output_dir"]).iterdir()} >= {
        "corrected_assembly.step", "fused.step", "common.brep",
        "side_1_remaining.brep", "side_2_remaining_EMPTY.json",
    }


def test_p11_retains_one_analytic_annulus_with_outer_and_hole_loops(tmp_path: Path) -> None:
    """Break caught: an annular face is split into patches or its inner wire is not a hole."""
    result = _run(tmp_path, "P11", create_view=True)
    operation = result["operation"]
    assert result["validation"]["status"] == "PASS"
    assert operation["status"] == "SUPPORTED_UNIQUE_INTERFACE_FACESET"
    assert operation["motion"]["executed_translation_mm"] == pytest.approx([0.0, 0.0, -0.05], abs=1e-7)
    area = 300.0 * math.pi
    partition = operation["partition"]
    assert partition["common_area_mm2"] == pytest.approx(area, abs=1e-8)
    assert partition["common_patches"][0]["surface_type"] == "Plane"
    assert set(partition["common_patches"][0]["boundary_curve_types"]) == {"Circle"}
    assert partition["coverage"] == pytest.approx({"Side_1": math.pi / 12.0, "Side_2": 1.0}, abs=1e-7)
    assert partition["remaining_area_mm2"] == pytest.approx({"Side_1": 3600.0 - area, "Side_2": 0.0}, abs=1e-8)
    assert partition["remaining_empty"]["Side_2"] is True
    topology = operation["topology"]
    assert (topology["patch_count"], topology["component_count"]) == (1, 1)
    assert topology["connectedness"] == "connected"
    assert (topology["boundary_component_count"], topology["hole_count"], topology["first_betti_number"]) == (2, 1, 1)
    assert topology["annular_or_multiply_connected"] is True
    assert [loop["kind"] for loop in topology["components"][0]["boundary_loops"]] == ["outer", "hole"]
    assert operation["step_reimport"]["corrected_assembly"]["hole_count"] == 1
    assert operation["step_reimport"]["corrected_assembly"]["boundary_component_count"] == 2
    assert operation["fuse"]["executed"] is True
    assert "Fused_Solid" in operation["view_reopen"]["visible_objects"]
    assert "Original_Side_1" not in operation["view_reopen"]["visible_objects"]
    assert {path.name for path in Path(result["output_dir"]).iterdir()} >= {
        "corrected_assembly.step", "fused.step", "common.brep",
        "side_1_remaining.brep", "side_2_remaining_EMPTY.json",
    }


def test_p12_reports_both_valid_candidates_and_refuses_to_choose_nearest(tmp_path: Path) -> None:
    """Break caught: ambiguity is silently resolved by gap, area, face order, or ordinal."""
    result = _run(tmp_path, "P12", create_view=True)
    operation = result["operation"]
    assert result["validation"]["status"] == "PASS"
    assert operation["status"] == "UNSUPPORTED_AMBIGUOUS_INTERFACE_SET"
    assert operation["face_sets"]["eligible_face_set_pair_count"] == 2
    assert operation["face_sets"]["candidate_face_set_pair_count"] == 2
    candidates = operation["face_sets"]["candidate_pairs"]
    assert sorted(candidate["gap_mm"] for candidate in candidates) == pytest.approx([0.05, 0.08], abs=1e-7)
    assert all(candidate["prospective_common_area_mm2"] == pytest.approx(192.0, abs=1e-8) for candidate in candidates)
    assert operation["motion"]["motion_authorized"] is False
    assert operation["motion"]["executed_translation_mm"] == [0.0, 0.0, 0.0]
    assert operation["motion"]["executed_translation_norm_mm"] == 0.0
    assert operation["fuse"]["executed"] is False
    assert {"Original_Side_1", "Original_Side_2", "Ambiguity_Rejection"} <= set(
        operation["view_reopen"]["visible_objects"]
    )
    assert not any(name.startswith("Candidate_Set_") for name in operation["view_reopen"]["visible_objects"])
    artifacts = operation.get("artifacts", {})
    assert "corrected_assembly_step" not in artifacts
    assert "fused_step" not in artifacts
    case_output = Path(result["output_dir"])
    assert not (case_output / "corrected_assembly.step").exists()
    assert not (case_output / "fused.step").exists()


@pytest.mark.parametrize("scenario", ["P10", "P11", "P12"])
def test_face_and_patch_traversal_reversal_does_not_change_semantics(tmp_path: Path, scenario: str) -> None:
    """Break caught: list order or face ordinal controls FaceSet choice or topology."""
    first = _run(tmp_path / "one", scenario, traversal_order="normal")["operation"]
    second = _run(tmp_path / "two", scenario, traversal_order="reverse")["operation"]
    for key in ("status", "face_sets", "motion", "partition", "topology", "fuse", "provenance"):
        assert second.get(key) == first.get(key)


@pytest.mark.parametrize(
    ("scenario", "mutations"),
    [
        ("P10", {"common_area_mm2": 1.0, "patch_count": 99, "component_count": 99}),
        ("P11", {"common_area_mm2": 1.0, "hole_count": 0, "boundary_component_count": 1}),
        ("P12", {"candidate_face_set_pair_count": 1}),
    ],
)
def test_expected_mutation_changes_validation_not_actual_geometry(tmp_path: Path, scenario: str, mutations: dict) -> None:
    """Break caught: expected truth selects FaceSets or constructs actual geometry."""
    module = _module()
    first = _run(tmp_path / "first", scenario)["operation"]
    source = module.FIXTURE_ROOT / scenario
    case = tmp_path / "fixture" / scenario
    case.mkdir(parents=True)
    for name in ("inputs.step", "policy.json", "parameters.json", "expected.json"):
        (case / name).write_bytes((source / name).read_bytes())
    expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    expected.update(mutations)
    (case / "expected.json").write_text(json.dumps(expected), encoding="utf-8")
    second = module.run_multipatch_case(case.parent, scenario, tmp_path / "mutated")["operation"]
    for key in ("status", "face_sets", "motion", "partition", "topology", "fuse", "provenance"):
        assert second.get(key) == first.get(key)
    assert module.validate_multipatch_evidence(second, expected)["status"] == "FAIL"


def _set_path(value, path, replacement):
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


@pytest.mark.parametrize(
    ("path", "replacement", "kind"),
    [
        (("face_sets", "selected_pair", "gap_mm"), math.nan, "invalid_numeric"),
        (("face_sets", "selected_pair", "Side_1", "support_coordinate_mm"), math.inf, "invalid_numeric"),
        (("partition", "common_area_mm2"), math.nan, "invalid_numeric"),
        (("partition", "coverage", "Side_1"), 1.1, "coverage"),
        (("partition", "coverage", "Side_1"), True, "invalid_numeric"),
        (("partition", "remaining_area_mm2", "Side_1"), math.inf, "invalid_numeric"),
        (("topology", "components", 0, "boundary_loops", 0, "length_mm"), math.nan, "invalid_numeric"),
        (("motion", "executed_translation_mm", 0), 0.01, "tangential_translation"),
        (("fuse", "boundary_overlap_area_mm2"), math.inf, "invalid_numeric"),
    ],
)
def test_validator_rejects_nonfinite_bool_out_of_range_and_tangential_evidence(tmp_path: Path, path, replacement, kind) -> None:
    """Break caught: invalid numeric evidence is accepted or coverage is clamped."""
    module = _module()
    result = _run(tmp_path, "P10")
    evidence = copy.deepcopy(result["operation"])
    _set_path(evidence, path, replacement)
    validation = module.validate_multipatch_evidence(evidence, result["expected"])
    assert validation["status"] == "FAIL"
    assert any(failure["kind"] == kind for failure in validation["failures"])


def test_validator_rejects_deleted_duplicated_or_misassigned_common_patches(tmp_path: Path) -> None:
    """Break caught: patch loss/duplication and component-link tampering evade checks."""
    module = _module()
    result = _run(tmp_path, "P10")
    source = result["operation"]
    deleted = copy.deepcopy(source)
    deleted["partition"]["common_patches"].pop()
    assert module.validate_multipatch_evidence(deleted, result["expected"])["status"] == "FAIL"
    duplicated = copy.deepcopy(source)
    duplicated["partition"]["common_patches"].append(copy.deepcopy(duplicated["partition"]["common_patches"][0]))
    assert module.validate_multipatch_evidence(duplicated, result["expected"])["status"] == "FAIL"
    remapped = copy.deepcopy(source)
    remapped["partition"]["common_patches"][0]["component_id"] = "Component_999"
    assert module.validate_multipatch_evidence(remapped, result["expected"])["status"] == "FAIL"


def test_validator_rejects_lost_p11_hole_and_boundary_loop(tmp_path: Path) -> None:
    """Break caught: annulus topology can be relabeled as simply connected."""
    module = _module()
    result = _run(tmp_path, "P11")
    for mutation in ("hole_count", "boundary_loop"):
        evidence = copy.deepcopy(result["operation"])
        if mutation == "hole_count":
            evidence["topology"]["hole_count"] = 0
        else:
            evidence["topology"]["components"][0]["boundary_loops"].pop()
        assert module.validate_multipatch_evidence(evidence, result["expected"])["status"] == "FAIL"


def test_failed_validation_cannot_replace_prior_success_or_emit_p12_success_step(tmp_path: Path, monkeypatch) -> None:
    """Break caught: failed reruns destroy valid artifacts or publish rejected STEP."""
    module = _module()
    root = tmp_path / "published"
    module.run_multipatch_case(module.FIXTURE_ROOT, "P10", root)
    prior = (root / "P10" / "operation.json").read_bytes()
    original = module._run_freecad

    def invalid(request):
        response = original(request)
        if request["action"] == "analyze":
            response["operation"]["partition"]["coverage"]["Side_1"] = 2.0
        return response

    monkeypatch.setattr(module, "_run_freecad", invalid)
    rerun = module.run_multipatch_case(module.FIXTURE_ROOT, "P10", root)
    assert rerun["validation"]["status"] == "FAIL"
    assert (root / "P10" / "operation.json").read_bytes() == prior
    monkeypatch.setattr(module, "_run_freecad", original)
    rejected = module.run_multipatch_case(module.FIXTURE_ROOT, "P12", root)
    assert rejected["validation"]["status"] == "PASS"
    assert not (Path(rejected["output_dir"]) / "corrected_assembly.step").exists()
    assert not (Path(rejected["output_dir"]) / "fused.step").exists()


@pytest.mark.parametrize(
    ("policy_change", "expected_status"),
    [
        ({"allow_motion": False}, "MOTION_NOT_AUTHORIZED"),
        ({"policy_valid": False}, "MOTION_NOT_AUTHORIZED"),
        ({"tauE_mm": 0.01}, "ENGINEERING_TOLERANCE_EXCEEDED"),
        ({"max_translation_mm": 0.01}, "TRANSLATION_BUDGET_EXCEEDED"),
    ],
)
def test_p10_inherits_06b_authorization_taue_and_budget_rejections(
    tmp_path: Path, policy_change: dict, expected_status: str
) -> None:
    """Break caught: FaceSet support bypasses the established 06A/06B motion gates."""
    module = _module()
    source = module.FIXTURE_ROOT / "P10"
    case = tmp_path / "fixture" / "P10"
    case.mkdir(parents=True)
    for name in ("inputs.step", "policy.json", "parameters.json", "expected.json"):
        (case / name).write_bytes((source / name).read_bytes())
    policy = json.loads((case / "policy.json").read_text(encoding="utf-8"))
    policy.update(policy_change)
    (case / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    expected["status"] = expected_status
    expected["candidate_face_set_pair_count"] = 0
    (case / "expected.json").write_text(json.dumps(expected), encoding="utf-8")
    result = module.run_multipatch_case(case.parent, "P10", tmp_path / "rejected")
    assert result["validation"]["status"] == "PASS"
    assert result["operation"]["status"] == expected_status
    assert result["operation"]["motion"]["executed_translation_norm_mm"] == 0.0
    assert result["operation"]["fuse"]["executed"] is False
    assert "corrected_assembly_step" not in result["operation"].get("artifacts", {})


def test_suite_publishes_machine_evidence_repeatability_and_view_index(tmp_path: Path) -> None:
    """Break caught: integrated output omits evidence or two-process comparison."""
    module = _module()
    summary = module.run_multipatch_suite(module.FIXTURE_ROOT, tmp_path / "suite")
    assert summary["status"] == "PASS"
    assert summary["repeatability"] == {
        "P10": {"processes": 2, "status": "PASS"},
        "P11": {"processes": 2, "status": "PASS"},
        "P12": {"processes": 2, "status": "PASS"},
    }
    for scenario in ("P10", "P11", "P12"):
        case = tmp_path / "suite" / scenario
        assert {p.name for p in case.iterdir()} >= {
            "operation.json", "validation.json", "facesets.json", "patches.json",
            "components.json", "provenance.json", "repeatability.json", "operation_debug.FCStd",
        }
    assert (tmp_path / "suite" / "VIEW_INDEX.md").is_file()
