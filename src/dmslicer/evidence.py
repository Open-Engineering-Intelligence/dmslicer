"""Evidence serialization and repository state capture."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any

from .identity import canonical_digest


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_metadata(repository_root: Path) -> dict[str, Any]:
    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments], cwd=repository_root, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    dirty = git("status", "--short")
    diff = subprocess.run(
        ["git", "diff", "--binary"], cwd=repository_root, check=True, capture_output=True
    ).stdout
    return {
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "dirty": bool(dirty),
        "dirty_entries": dirty.splitlines(),
        "diff_sha256": sha256(diff).hexdigest(),
    }


def artifact_digest(value: Any) -> str:
    return f"sha256:{canonical_digest(value)}"
