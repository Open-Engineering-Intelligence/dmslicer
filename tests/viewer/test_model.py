"""Viewer contract tests: no CAD interpretation or snapshot repair."""

from __future__ import annotations

from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from contract_consumers.slicer_mock import decide
from dmslicer.geometry_contract.ids import snapshot_id


ROOT = Path(__file__).resolve().parents[2]


def load(name, group="geometry"):
    return json.loads(
        (ROOT / "contract_examples" / "v0.1" / group / f"{name}.json").read_text(
            encoding="utf-8"
        )
    )


def build(snapshot, decision=None, root=ROOT):
    try:
        module = importlib.import_module("dmslicer.viewer.model")
    except ModuleNotFoundError as error:
        if error.name in {"dmslicer.viewer", "dmslicer.viewer.model"}:
            pytest.fail("ViewerModel is not implemented")
        raise
    return module.build_viewer_model(snapshot, decision, repository_root=root)


@pytest.mark.parametrize(
    "name,group,counts",
    [
        ("planar_full", "geometry", (3, 3, 2, 2, 2, 0, 0)),
        ("planar_partial", "geometry", (2, 1, 1, 1, 1, 0, 3)),
        ("planar_multipatch", "geometry", (2, 1, 1, 2, 2, 0, 0)),
        ("ambiguous_relation", "negative", (2, 1, 0, 0, 0, 0, 0)),
        ("missing_semantic_binding", "negative", (2, 1, 1, 1, 1, 0, 0)),
        ("unsupported_family", "negative", (2, 1, 1, 1, 1, 0, 0)),
    ],
)
def test_valid_contract_entities_are_preserved(name, group, counts):
    view = build(load(name, group))
    assert view["validation"]["snapshot"] == {"status": "VALID", "issues": []}
    assert tuple(len(view[key]) for key in (
        "regions", "relations", "interfaces", "patches", "interface_components",
        "boundaries", "surface_partitions",
    )) == counts
    assert view["metadata"]["view_kind"] == "CONTRACT TOPOLOGY / NON-GEOMETRIC VIEW"
    assert view["decision_overlay"]["state"] == "NOT_PROVIDED"


def test_disjoint_confirmation_and_semantic_roles_are_not_reinterpreted():
    view = build(load("planar_full"))
    assert sorted((r["taxonomy"], r["confirmation"]) for r in view["relations"]) == [
        ("DISJOINT", "CONFIRMED"),
        ("FULL_FACE_OVERLAP", "CONFIRMED"),
        ("FULL_FACE_OVERLAP", "CONFIRMED"),
    ]
    assert {b["semantic_role"] for b in view["semantic_bindings"]} == {
        "SOURCE_A", "SOURCE_B", "GRADIENT_REGION",
    }
    assert view["collection_presence"]["boundaries"] == "ABSENT"


def test_common_remaining_and_equal_area_components_stay_separate():
    partial = build(load("planar_partial"))
    assert sorted((p["role"], p["area"]["value"]) for p in partial["surface_partitions"]) == [
        ("COMMON", 480.0), ("REMAINING", 320.0), ("REMAINING", 320.0),
    ]
    multi = build(load("planar_multipatch"))
    assert {tuple(c["patch_refs"]) for c in multi["interface_components"]} == {
        ("patch:e2-one",), ("patch:e2-two",),
    }
    assert multi["boundaries"] == []
    assert multi["collection_presence"]["surface_partitions"] == "ABSENT"


def test_invalid_snapshot_retains_diagnostics_but_no_authoritative_entities():
    view = build(load("unresolved_artifact", "negative"))
    assert view["validation"]["snapshot"]["status"] == "INVALID"
    assert {i["code"] for i in view["validation"]["snapshot"]["issues"]} == {
        "UNRESOLVED_ARTIFACT",
    }
    assert "outputs/missing/source.step" in str(view["validation"]["snapshot"]["issues"])
    for key in ("regions", "relations", "interfaces", "patches", "artifact_links", "provenance_links"):
        assert view[key] == []


def test_invalid_artifact_path_exception_becomes_diagnostics():
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    snapshot["artifact_references"][0]["uri"] = "bad\x00.step"
    view = build(snapshot, decision)
    assert view["validation"]["snapshot"]["status"] == "UNAVAILABLE"
    assert {i["code"] for i in view["validation"]["snapshot"]["issues"]} == {
        "VALIDATION_UNAVAILABLE",
    }
    assert view["regions"] == view["artifact_links"] == []
    assert view["decision_overlay"]["state"] == "DISABLED"
    assert "selection" not in view["decision_overlay"]
    json.dumps(view, allow_nan=False)


@pytest.mark.parametrize("value,presence", [([], "EMPTY"), ({}, "INVALID_TYPE")])
def test_explicit_invalid_optional_collection_is_not_treated_as_absent(value, presence):
    snapshot = load("planar_full")
    snapshot["boundaries"] = value
    view = build(snapshot)
    assert view["collection_presence"]["boundaries"] == presence
    assert view["validation"]["snapshot"]["status"] == "INVALID"
    assert view["regions"] == []


@pytest.mark.parametrize("snapshot", [{}, None, [], "not a snapshot"])
def test_malformed_snapshot_is_a_diagnostic_model(snapshot):
    view = build(snapshot)
    assert view["validation"]["snapshot"]["status"] == "INVALID"
    assert view["regions"] == []
    json.dumps(view, allow_nan=False)


def test_decided_overlay_copies_all_selection_facts_without_modifying_snapshot():
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    before = deepcopy((snapshot, decision))
    view = build(snapshot, decision)
    assert view["decision_overlay"]["state"] == "ENABLED"
    selection = view["decision_overlay"]["selection"]
    assert selection["selected_patch_ids"] == ["patch:e1-common"]
    assert selection["target_region_id"] == "region:e1-side-1"
    assert selection["strategy_kind"] == "PLANAR_INTERFACE_PARTITION"
    assert selection["partition_direction"] == [0.0, 0.0, 1.0]
    for key in ("selected_interface_id", "local_frame_ref", "partition_operation", "expected_partition_refs"):
        assert selection[key] == decision[key]
    assert view["decision_overlay"]["provenance_reference"] == decision["provenance_reference"]
    assert view["decision_overlay"]["execution_state"] == "NOT_EXECUTED"
    assert view["semantic_bindings"] == build(snapshot)["semantic_bindings"]
    assert (snapshot, decision) == before
    view["regions"][0]["geometry_ref"]["locator"]["value"] = "changed in view"
    selection["partition_direction"][0] = 99
    assert (snapshot, decision) == before


@pytest.mark.parametrize("name,status,reason", [
    ("ambiguous_relation", "REJECTED", "AMBIGUOUS_INTERFACE"),
    ("missing_semantic_binding", "REJECTED", "MISSING_SEMANTIC_BINDING"),
    ("unsupported_family", "UNSUPPORTED", "UNSUPPORTED_GEOMETRY_FAMILY"),
    ("unresolved_artifact", "FAILED", "INVALID_SNAPSHOT"),
])
def test_non_decided_outcomes_never_produce_selection(name, status, reason):
    snapshot = load(name, "negative")
    view = build(snapshot, decide(snapshot, ROOT))
    overlay = view["decision_overlay"]
    assert (overlay["status"], overlay["reason_code"]) == (status, reason)
    assert overlay["state"] == "DISABLED"
    assert "selection" not in overlay


def test_invalid_snapshot_failure_without_references_remains_a_valid_decision():
    decision = decide({}, ROOT)
    view = build({}, decision)
    assert view["validation"]["decision"] == {"status": "VALID", "issues": []}
    assert view["decision_overlay"]["status"] == "FAILED"
    assert "selection" not in view["decision_overlay"]


def test_multipatch_mock_mismatch_is_preserved_and_overlay_is_disabled():
    snapshot = load("planar_multipatch")
    decision = decide(snapshot, ROOT)
    assert decision["status"] == "DECIDED"
    assert decision["expected_partition_refs"] == []
    view = build(snapshot, decision)
    assert view["validation"]["snapshot"]["status"] == "VALID"
    assert len(view["patches"]) == len(view["interface_components"]) == 2
    assert view["validation"]["decision"]["status"] == "INVALID"
    assert any(i["path"] == "expected_partition_refs" for i in view["validation"]["decision"]["issues"])
    assert view["decision_overlay"]["state"] == "DISABLED"
    assert "selection" not in view["decision_overlay"]


@pytest.mark.parametrize("decision", [{}, [], "bad"])
def test_malformed_decision_does_not_damage_snapshot(decision):
    snapshot = load("planar_partial")
    view = build(snapshot, decision)
    assert view["regions"] == build(snapshot)["regions"]
    assert view["validation"]["decision"]["status"] == "INVALID"
    assert "selection" not in view["decision_overlay"]


@pytest.mark.parametrize("field,value,code", [
    ("input_snapshot_id", "snapshot:v0.1:" + "f" * 64, "SNAPSHOT_MISMATCH"),
    ("selected_interface_id", "interface:missing", "UNRESOLVED_REFERENCE"),
    ("selected_patch_ids", ["patch:missing"], "UNRESOLVED_REFERENCE"),
    ("target_region_id", "region:missing", "UNRESOLVED_REFERENCE"),
    ("provenance_reference", "provenance:missing", "UNRESOLVED_REFERENCE"),
    ("expected_partition_refs", ["partition:missing"], "UNRESOLVED_REFERENCE"),
])
def test_approved_overlay_reference_checks_disable_only_overlay(field, value, code):
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    decision[field] = value
    view = build(snapshot, decision)
    assert view["validation"]["snapshot"]["status"] == "VALID"
    assert view["validation"]["decision"]["status"] == "VALID"
    assert code in {i["code"] for i in view["validation"]["overlay"]["issues"]}
    assert view["decision_overlay"]["state"] == "DISABLED"
    assert "selection" not in view["decision_overlay"]


@pytest.mark.parametrize("field,value", [
    ("decision_id", "decision:v0.1:" + "a" * 64),
    ("local_frame_ref", "frame:producer-local"),
    ("strategy_kind", "CYLINDRICAL_INTERFACE_PARTITION"),
    ("partition_direction", [7.0, 3.0, -2.0]),
])
def test_viewer_does_not_invent_identity_frame_strategy_or_direction_rules(field, value):
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    decision[field] = value
    view = build(snapshot, decision)
    assert view["decision_overlay"]["state"] == "ENABLED"
    assert view["validation"]["overlay"]["issues"] == []
    if field != "decision_id":
        assert view["decision_overlay"]["selection"][field] == value


def test_model_preserves_untrusted_strings_as_data_and_never_contains_hrefs():
    snapshot = load("planar_partial")
    payload = '</script><script>alert(1)</script>'
    snapshot["label"] = payload
    snapshot["regions"][0]["label"] = payload
    view = build(snapshot)
    assert view["metadata"]["label"] == payload
    assert any(r.get("label") == payload for r in view["regions"])
    assert view["artifact_links"][0]["uri"] == snapshot["artifact_references"][0]["uri"]
    assert view["artifact_links"][0]["resolution"] == "RESOLVED"
    assert "href" not in json.dumps(view)
    assert "file:///" not in json.dumps(view)


def test_collection_reordering_is_deterministic_but_vectors_keep_their_order():
    snapshot = load("planar_full")
    changed = deepcopy(snapshot)
    for key, value in changed.items():
        if isinstance(value, list):
            value.reverse()
    for interface in changed["interfaces"]:
        interface["region_refs"].reverse()
        interface["patch_refs"].reverse()
    first, second = build(snapshot), build(changed)
    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)
    assert first["metadata"]["model_frame"] == snapshot["model_frame"]
    for patch in first["patches"]:
        source = next(p for p in snapshot["patches"] if p["patch_id"] == patch["patch_id"])
        assert patch["planar_parameters"] == source["planar_parameters"]


@pytest.mark.parametrize("uri,status", [
    ("docs/missing.txt", "MISSING"),
    ("javascript:alert(1)", "UNSAFE"),
    ("docs/%2e%2e/secret", "UNSAFE"),
    ("docs\\file.txt", "UNSAFE"),
])
def test_provenance_resolution_is_separate_from_snapshot_validity(uri, status):
    snapshot = load("planar_partial")
    snapshot["provenance_references"][0]["evidence_uri"] = uri
    snapshot["snapshot_id"] = snapshot_id(snapshot)
    view = build(snapshot)
    assert view["provenance_links"][0]["evidence_uri"] == uri
    assert view["provenance_links"][0]["resolution"]["evidence_uri"] == status
    assert "href" not in json.dumps(view)


@pytest.mark.parametrize("uri", ["../outside.txt", "C:/outside.txt", "//server/share/file.txt"])
def test_schema_invalid_provenance_path_cannot_publish_entity_or_link_views(uri):
    snapshot = load("planar_partial")
    snapshot["provenance_references"][0]["evidence_uri"] = uri
    snapshot["snapshot_id"] = snapshot_id(snapshot)
    view = build(snapshot)
    assert view["validation"]["snapshot"]["status"] == "INVALID"
    assert view["provenance_links"] == []
    assert view["regions"] == []


def test_existing_patch_from_another_interface_cannot_be_highlighted():
    snapshot = load("planar_full")
    decision = decide(load("planar_partial"), ROOT)
    decision.update(
        input_snapshot_id=snapshot["snapshot_id"],
        selected_interface_id=snapshot["interfaces"][0]["interface_id"],
        selected_patch_ids=snapshot["interfaces"][1]["patch_refs"],
        target_region_id=snapshot["regions"][0]["region_id"],
        provenance_reference=snapshot["provenance_references"][0]["provenance_id"],
    )
    view = build(snapshot, decision)
    assert "MEMBERSHIP_MISMATCH" in {i["code"] for i in view["validation"]["overlay"]["issues"]}
    assert view["decision_overlay"]["state"] == "DISABLED"
    assert len(view["interfaces"]) == 2


def test_rejected_decision_with_selection_is_invalid_but_geometry_stays_visible():
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    decision.update(status="REJECTED", reason_code="MISSING_SEMANTIC_BINDING")
    view = build(snapshot, decision)
    assert view["validation"]["decision"]["status"] == "INVALID"
    assert "selection" not in view["decision_overlay"]
    assert view["regions"] == build(snapshot)["regions"]


def test_valid_decision_cannot_enable_overlay_on_an_invalid_snapshot():
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    snapshot["artifact_references"][0]["uri"] = "outputs/missing/cad.step"
    view = build(snapshot, decision)
    assert view["validation"]["decision"]["status"] == "VALID"
    assert view["decision_overlay"]["disabled_reason"] == "INVALID_SNAPSHOT"
    assert "selection" not in view["decision_overlay"]
    assert view["patches"] == []


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_data_produces_serializable_diagnostics(number):
    snapshot = load("planar_partial")
    # The frozen mock aliases its direction to the Snapshot's normal array.
    decision = deepcopy(decide(snapshot, ROOT))
    decision["partition_direction"][0] = number
    view = build(snapshot, decision)
    assert view["validation"]["decision"]["status"] == "INVALID"
    assert view["regions"]
    json.dumps(view, allow_nan=False)
    snapshot["model_frame"]["origin"][0] = number
    view = build(snapshot)
    assert view["validation"]["snapshot"]["status"] == "INVALID"
    json.dumps(view, allow_nan=False)


def test_empty_relation_collection_is_valid_and_region_validity_is_only_observed():
    snapshot = load("ambiguous_relation", "negative")
    snapshot["relations"] = []
    snapshot["regions"][0]["validity_state"] = "INVALID"
    snapshot["snapshot_id"] = snapshot_id(snapshot)
    view = build(snapshot)
    assert view["validation"]["snapshot"]["status"] == "VALID"
    assert view["collection_presence"]["relations"] == "EMPTY"
    assert any(r["validity_state"] == "INVALID" for r in view["regions"])


def test_decision_set_references_are_sorted_without_resigning_or_reordering_vectors():
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    reordered = deepcopy(decision)
    reordered["expected_partition_refs"].reverse()
    reordered["selected_patch_ids"].reverse()
    assert build(snapshot, decision) == build(snapshot, reordered)
    assert build(snapshot, reordered)["decision_overlay"]["decision_id"] == decision["decision_id"]


def test_symlink_escape_is_not_marked_as_a_resolved_provenance_file(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "evidence.txt").write_text("reference only", encoding="utf-8")
    root = tmp_path / "repository"
    root.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if sys.platform != "win32":
            pytest.skip(f"Symlink creation is unavailable: {error}")
        # Windows junctions exercise the same containment boundary without
        # requiring the optional symbolic-link privilege.
        quoted_link = str(link).replace("'", "''")
        quoted_target = str(outside).replace("'", "''")
        junction = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"New-Item -ItemType Junction -Path '{quoted_link}' -Target '{quoted_target}' | Out-Null"],
            capture_output=True, text=True, check=False,
        )
        assert junction.returncode == 0, junction.stderr
    # The artifact need only exist. Its contents must never be read by Viewer.
    (root / "fixture.step").write_text("not CAD; existence-only fixture", encoding="utf-8")
    snapshot = load("planar_partial")
    snapshot["artifact_references"][0]["uri"] = "fixture.step"
    snapshot["provenance_references"][0]["evidence_uri"] = "escape/evidence.txt"
    snapshot["snapshot_id"] = snapshot_id(snapshot)
    view = build(snapshot, root=root)
    assert view["validation"]["snapshot"]["status"] == "VALID"
    assert view["provenance_links"][0]["resolution"]["evidence_uri"] == "UNSAFE"


def test_model_runs_in_fresh_process_without_geometry_imports_or_cad_reads():
    snapshot = load("planar_partial")
    decision = decide(snapshot, ROOT)
    script = textwrap.dedent('''
        import json, sys
        from pathlib import Path
        root = Path(sys.argv[1])
        sys.path.insert(0, str(root / "src"))
        allowed = {
            "dmslicer", "dmslicer.identity", "dmslicer.viewer", "dmslicer.viewer.model",
            "dmslicer.geometry_contract", "dmslicer.geometry_contract.schema",
            "dmslicer.geometry_contract.validation", "dmslicer.geometry_contract.ids",
            "dmslicer.geometry_contract.schemas",
        }
        def guard(event, args):
            if event == "import":
                name = args[0]
                if (name.split(".")[0] in {"FreeCAD", "Part", "OCCT", "OCC", "OCP", "contract_consumers"}
                    or (name.startswith("dmslicer.") and name not in allowed)):
                    raise AssertionError("Forbidden import: " + name)
            if event == "open" and isinstance(args[0], (str, bytes)):
                path = args[0].decode() if isinstance(args[0], bytes) else args[0]
                if Path(path).suffix.lower() in {".step", ".stp", ".brep", ".fcstd"}:
                    raise AssertionError("CAD content access: " + path)
        sys.addaudithook(guard)
        from dmslicer.viewer import build_viewer_model
        inputs = json.load(sys.stdin)
        result = build_viewer_model(inputs[0], inputs[1], repository_root=root)
        print(json.dumps(result, allow_nan=False))
    ''')
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(ROOT)],
        input=json.dumps([snapshot, decision]), capture_output=True, text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    view = json.loads(result.stdout)
    assert view["decision_overlay"]["state"] == "ENABLED"
    assert view["validation"]["snapshot"]["status"] == "VALID"
