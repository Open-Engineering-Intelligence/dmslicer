from __future__ import annotations

from pathlib import Path

import pytest

from dmslicer.evidence_promotion.integrity import (
    compare_bytes,
    copy_and_verify,
    file_integrity,
)


def test_file_integrity_streams_known_sha256_and_size(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"abc")

    assert file_integrity(artifact) == {
        "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "size_bytes": 3,
    }


def test_compare_bytes_reports_same_bytes(tmp_path: Path) -> None:
    first, second = tmp_path / "a.bin", tmp_path / "b.bin"
    first.write_bytes(b"same")
    second.write_bytes(b"same")

    result = compare_bytes(first, second)

    assert result["status"] == "BYTE_SAME"
    assert result["source"]["sha256"] == result["candidate"]["sha256"]
    assert result["source"]["size_bytes"] == result["candidate"]["size_bytes"] == 4


def test_compare_bytes_reports_different_bytes_without_geometry_status(tmp_path: Path) -> None:
    first, second = tmp_path / "a.bin", tmp_path / "b.bin"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    result = compare_bytes(first, second)

    assert result["status"] == "BYTE_DIFFERENT"
    assert "geometry" not in result


def test_copy_and_verify_records_exact_source_and_destination(tmp_path: Path) -> None:
    source = tmp_path / "source" / "result.json"
    destination = tmp_path / "stable" / "result.json"
    source.parent.mkdir()
    source.write_bytes(b'{"status":"FAIL"}\n')

    result = copy_and_verify(source, destination)

    assert destination.read_bytes() == source.read_bytes()
    assert result["status"] == "BYTE_SAME"
    assert result["source"] == result["destination"]


def test_copy_and_verify_refuses_to_overwrite_existing_evidence(tmp_path: Path) -> None:
    source, destination = tmp_path / "source.bin", tmp_path / "destination.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"preserved")

    with pytest.raises(FileExistsError):
        copy_and_verify(source, destination)

    assert destination.read_bytes() == b"preserved"
