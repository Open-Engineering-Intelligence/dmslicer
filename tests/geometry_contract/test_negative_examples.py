from __future__ import annotations

import json
from pathlib import Path

import pytest

from dmslicer.geometry_contract.validation import validate_geometry_snapshot

from ._samples import REPOSITORY_ROOT


NEGATIVE_ROOT = REPOSITORY_ROOT / "contract_examples" / "v0.1" / "negative"


def _load(name: str) -> dict:
    path = NEGATIVE_ROOT / name
    if not path.is_file():
        pytest.fail(f"negative example is missing: {path.relative_to(REPOSITORY_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    [
        "ambiguous_relation.json",
        "unsupported_family.json",
        "missing_semantic_binding.json",
    ],
)
def test_consumer_negative_examples_remain_valid_geometry_snapshots(name: str) -> None:
    assert validate_geometry_snapshot(_load(name), REPOSITORY_ROOT) == ()


def test_unresolved_artifact_example_fails_at_reference_validation() -> None:
    issues = validate_geometry_snapshot(
        _load("unresolved_artifact.json"), REPOSITORY_ROOT
    )

    assert {issue.code for issue in issues} == {"UNRESOLVED_ARTIFACT"}
