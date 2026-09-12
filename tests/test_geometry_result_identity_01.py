import copy
import json
from pathlib import Path

from dmslicer.geometry_contract.validation import validate_geometry_snapshot
from dmslicer.geometry_result_identity_01 import (
    load_publication_map,
    publish_identity_bound_snapshot,
    validate_result_bindings,
)
from dmslicer.planar_partial_overlap_correction_06b import FIXTURE_ROOT, run_partial_overlap_case


ROOT = Path(__file__).resolve().parents[1]
P07 = ROOT / "benchmarks" / "planar_partial_overlap_correction_06b" / "P07"
MAP = P07 / "result_identity_publication.json"
SNAPSHOT = ROOT / "contract_examples" / "v0.1" / "geometry" / "planar_partial.json"


def _operation() -> dict:
    return {
        "scenario_id": "P07",
        "status": "CORRECTED_PARTIAL_INTERFACE_FUSED",
        "result_bindings": [
            {
                "result_ref": "result:source-region:side-1",
                "role": "INPUT_REGION",
                "source_role": "Side_1",
                "artifact": {"kind": "STEP", "uri": "inputs.step"},
            },
            {
                "result_ref": "result:source-region:side-2",
                "role": "INPUT_REGION",
                "source_role": "Side_2",
                "artifact": {"kind": "STEP", "uri": "inputs.step"},
            },
            {
                "result_ref": "result:partition:common",
                "role": "COMMON",
                "artifact": {"kind": "BREP", "uri": "patches/common.brep"},
            },
            {
                "result_ref": "result:partition:remaining-side-1",
                "role": "REMAINING",
                "source_role": "Side_1",
                "artifact": {"kind": "BREP", "uri": "patches/side_1_remaining.brep"},
            },
            {
                "result_ref": "result:partition:remaining-side-2",
                "role": "REMAINING",
                "source_role": "Side_2",
                "artifact": {"kind": "BREP", "uri": "patches/side_2_remaining.brep"},
            },
        ],
    }


def _prepared_repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repository"
    source = repository / "benchmarks" / "planar_partial_overlap_correction_06b" / "P07"
    source.mkdir(parents=True)
    (source / "inputs.step").write_bytes((P07 / "inputs.step").read_bytes())
    operation_root = repository / "run"
    patches = operation_root / "patches"
    patches.mkdir(parents=True)
    for name in ("common.brep", "side_1_remaining.brep", "side_2_remaining.brep"):
        (patches / name).write_text(name, encoding="utf-8")
    for name in ("corrected_assembly.step", "fused.step"):
        (operation_root / name).write_text(name, encoding="utf-8")
    return repository, source, operation_root


def test_p07_bindings_publish_existing_entity_ids_to_explicit_result_artifacts(tmp_path: Path) -> None:
    publication_map = load_publication_map(MAP)
    operation = _operation()
    repository, source_root, operation_root = _prepared_repository(tmp_path)
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    operation["artifacts"] = {
        "corrected_assembly_step": str(operation_root / "corrected_assembly.step"),
        "fused_step": str(operation_root / "fused.step"),
    }

    validate_result_bindings(operation, publication_map, source_root, operation_root)
    published = publish_identity_bound_snapshot(
        snapshot,
        operation,
        publication_map,
        source_root=source_root,
        operation_root=operation_root,
        repository_root=repository,
        evidence_root=repository / "evidence" / "GEOMETRY-RESULT-IDENTITY-01" / "p07-test",
        implementation_commit="289567dbaaf3f89809dbbd82d71bf190a3aa7a13",
        parent_baseline="289567dbaaf3f89809dbbd82d71bf190a3aa7a13",
        branch="test/geometry-result-identity",
        command="test publication",
    )

    assert {row["entity_id"] for row in publication_map["entity_bindings"]} == {
        "region:e1-side-1",
        "region:e1-side-2",
        "partition:v0.1:577e8c1b352a5c5dc8293e98fcd98a19d254f52832745aa8a1aacaeb50e7adcc",
        "partition:v0.1:90333b6845c2be8f430414638167c61b9368b76a3ecc0d2c832ef281df2275e0",
        "partition:v0.1:27f32a0dbe49477c236caaed6f9adf6907a34de3553a3e6c478b8ad2118b0421",
    }
    partitions = {item["partition_id"]: item for item in published["surface_partitions"]}
    for binding in publication_map["entity_bindings"][2:]:
        geometry_ref = partitions[binding["entity_id"]]["geometry_ref"]
        assert geometry_ref["locator"] == {"scheme": "BREP_ROOT", "value": "$"}
        assert geometry_ref["artifact_ref"].startswith("artifact:p07-result-")
    assert published["snapshot_id"] != snapshot["snapshot_id"]
    assert validate_geometry_snapshot(published, repository) == ()
    manifest = json.loads((repository / "evidence" / "GEOMETRY-RESULT-IDENTITY-01" / "p07-test" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["goal_id"] == "GEOMETRY-RESULT-IDENTITY-01"
    assert manifest["implementation_commit"] == "289567dbaaf3f89809dbbd82d71bf190a3aa7a13"
    assert manifest["parent_baseline"] == "289567dbaaf3f89809dbbd82d71bf190a3aa7a13"
    assert manifest["command"] == "test publication"
    assert manifest["geometry_snapshot"] == "geometry_snapshot.json"
    published_operation = json.loads((repository / "evidence" / "GEOMETRY-RESULT-IDENTITY-01" / "p07-test" / "operation.json").read_text(encoding="utf-8"))
    assert published_operation["artifacts"] == {
        "corrected_assembly_step": "artifacts/corrected_assembly.step",
        "fused_step": "artifacts/fused.step",
    }


def test_binding_validation_rejects_unknown_entity_duplicate_result_and_missing_brep(tmp_path: Path) -> None:
    publication_map = load_publication_map(MAP)
    operation = _operation()
    _, source_root, operation_root = _prepared_repository(tmp_path)

    duplicate = copy.deepcopy(operation)
    duplicate["result_bindings"][1]["result_ref"] = duplicate["result_bindings"][0]["result_ref"]
    try:
        validate_result_bindings(duplicate, publication_map, source_root, operation_root)
    except ValueError as error:
        assert "duplicate result_ref" in str(error)
    else:
        raise AssertionError("duplicate result ref was accepted")

    (operation_root / "patches" / "common.brep").unlink()
    try:
        validate_result_bindings(operation, publication_map, source_root, operation_root)
    except ValueError as error:
        assert "missing artifact" in str(error)
    else:
        raise AssertionError("missing BREP was accepted")


def test_successful_p07_operation_emits_all_five_backend_neutral_result_bindings(tmp_path: Path) -> None:
    result = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "runs")
    publication_map = load_publication_map(MAP)

    validate_result_bindings(
        result["operation"],
        publication_map,
        P07,
        tmp_path / "runs" / "P07",
    )
