"""Byte-integrity evidence; no function in this module evaluates geometry."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
from typing import Any

from .models import BYTE_DIFFERENT, BYTE_SAME


_BLOCK_SIZE = 1024 * 1024


def file_integrity(path: Path) -> dict[str, int | str]:
    path = Path(path)
    digest = sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_BLOCK_SIZE), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def compare_bytes(first: Path, second: Path) -> dict[str, Any]:
    source = file_integrity(first)
    candidate = file_integrity(second)
    return {
        "status": BYTE_SAME if source == candidate else BYTE_DIFFERENT,
        "source": source,
        "candidate": candidate,
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
    }


def copy_and_verify(source: Path, destination: Path) -> dict[str, Any]:
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with source.open("rb") as source_handle, destination.open("xb") as destination_handle:
            created = True
            shutil.copyfileobj(source_handle, destination_handle, length=_BLOCK_SIZE)
        shutil.copystat(source, destination)
        comparison = compare_bytes(source, destination)
        if comparison["status"] != BYTE_SAME:
            raise OSError("Copied artifact failed byte-integrity verification")
        return {
            "status": comparison["status"],
            "source": comparison["source"],
            "destination": comparison["candidate"],
            "sha256_role": comparison["sha256_role"],
        }
    except Exception:
        if created and destination.exists():
            destination.unlink()
        raise
