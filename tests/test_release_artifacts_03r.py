import json
import os
import subprocess
import sys
from pathlib import Path


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "dmslicer", *arguments],
        cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False,
    )


def test_release_packaging_writes_portable_reference_and_verified_debug_models(tmp_path: Path) -> None:
    """Catches release artifacts that retain output paths or copy unverified FCStd files."""
    repository_root = Path(__file__).resolve().parents[1]
    artifact_root = tmp_path / "artifacts"

    completed = _command(
        "package-contact-artifacts",
        str(repository_root / "outputs" / "contact_canonical_03a"),
        str(artifact_root),
    )

    assert completed.returncode == 0, completed.stderr
    reference_path = artifact_root / "reference_results" / "contact_canonical_03a.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    assert set(reference["cases"]) == {"A01", "A02", "A03", "A04", "A05", "A06"}
    encoded = reference_path.read_text(encoding="utf-8")
    slash = chr(92)
    forbidden = ("C:" + slash + "Users", "D:" + slash + "Agent", "App" + "Data", "T" + "emp")
    assert not any(value in encoded for value in forbidden)
    for case_id, row in reference["cases"].items():
        assert row["step_sha256"]
        assert row["relation"]
        assert row["dimension"]
        assert "freecad_version" in row and "occt_version" in row
        assert (artifact_root / "freecad_debug" / f"{case_id}.FCStd").is_file()
    verification = json.loads((artifact_root / "freecad_debug" / "verification.json").read_text(encoding="utf-8"))
    assert verification["status"] == "PASS"
    assert all(record["body_count"] == 2 and record["result_object"] == "Actual_Result" for record in verification["cases"].values())


def test_versioned_reference_snapshot_matches_current_canonical_outputs() -> None:
    """Catches a committed reference snapshot drifting from the verified canonical fields."""
    repository_root = Path(__file__).resolve().parents[1]
    reference = json.loads((repository_root / "artifacts" / "reference_results" / "contact_canonical_03a.json").read_text(encoding="utf-8"))
    summary = json.loads((repository_root / "outputs" / "contact_canonical_03a" / "summary.json").read_text(encoding="utf-8"))

    for case_id, row in reference["cases"].items():
        actual = json.loads((repository_root / "outputs" / "contact_canonical_03a" / case_id / "actual.json").read_text(encoding="utf-8"))
        assert row["step_sha256"] == actual["step_sha256"]
        assert row["relation"] == actual["relation"]["relation"]
        assert row["dimension"] == actual["relation"]["dimension"]
        assert row["actual_measure"] == summary["cases"][case_id]["actual_measure"]
        assert row["absolute_error"] == summary["cases"][case_id]["absolute_error"]
