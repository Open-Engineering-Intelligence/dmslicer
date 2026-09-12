from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "evidence_preservation" / "build_07a_closeout_request.py"
SPEC = importlib.util.spec_from_file_location("build_07a_closeout_request", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def test_request_preserves_principal_07a_evidence_without_promoting_missing_results() -> None:
    request = GENERATOR.build_request(
        run_id="07a-evidence-closeout-001",
        timestamp="2026-09-12T00:00:00+08:00",
        python_version="3.12.0",
        pytest_version="8.4.2",
        freecad_version="0.21.2",
        occt_version="7.7.2",
    )

    artifact_ids = {artifact["artifact_id"] for artifact in request["source"]["allowlist"]}
    assert request["identity"]["implementation_commit"] == (
        "c7db3501cdfc1971ecb2a4f81e1dcd17eddff18b"
    )
    assert {"c01-fcstd", "c02-fcstd", "c02-actual-common", "c02-corrected-step", "c02-fused-step"} <= artifact_ids
    assert {"c01-repeat-operation", "c02-repeat-operation", "rotated-c02-repeat-operation"} <= artifact_ids
    assert request["results"]["scientific_experiment_result"] == {
        "status": "NOT_EVALUATED",
        "evidence_artifact_ids": [],
    }
    assert request["results"]["pytest_result"]["status"] == "NOT_EVALUATED"
    assert request["results"]["human_inspection_result"]["status"] == "NOT_EVALUATED"
    assert request["custody"] == {"off_host_copies": [], "publication_authorized": False}
