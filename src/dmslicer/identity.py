"""Canonical geometry fingerprints and deterministic persistent identifiers."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Any


_QUANTUM = Decimal("0.000000001")


def canonical_json(value: Any) -> str:
    """Return a key-sorted canonical JSON representation for digest inputs."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def canonical_digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def quantized_number(value: float) -> float:
    """Normalize kernel floats to a 1e-9 mm/mm² identity grid."""
    return float(Decimal(str(value)).quantize(_QUANTUM, rounding=ROUND_HALF_UP))


def normalized_vector(vector: list[float]) -> list[float]:
    return [quantized_number(component) for component in vector]


def normalized_box(box: dict[str, float]) -> dict[str, float]:
    return {key: quantized_number(box[key]) for key in sorted(box)}


def face_geometry_fingerprint(face: dict[str, Any]) -> str:
    """Fingerprint an orientation-independent source face description."""
    payload = {
        "schema": "face-geometry:v1",
        "surface_type": face["surface_type"],
        "area_mm2": quantized_number(face["area_mm2"]),
        "center_of_mass_mm": normalized_vector(face["center_of_mass_mm"]),
        "bounding_box_mm": normalized_box(face["bounding_box_mm"]),
        "edge_count": face["edge_count"],
        "wire_count": face["wire_count"],
    }
    return f"facegeo:v1:{canonical_digest(payload)}"


def solid_geometry_fingerprint(solid: dict[str, Any], face_fingerprints: list[str]) -> str:
    payload = {
        "schema": "solid-geometry:v1",
        "volume_mm3": quantized_number(solid["volume_mm3"]),
        "area_mm2": quantized_number(solid["area_mm2"]),
        "center_of_mass_mm": normalized_vector(solid["center_of_mass_mm"]),
        "bounding_box_mm": normalized_box(solid["bounding_box_mm"]),
        "face_fingerprints": sorted(face_fingerprints),
    }
    return f"solidgeo:v1:{canonical_digest(payload)}"


def document_id(step_sha256: str) -> str:
    return f"stepdoc:v1:{step_sha256}"


def region_id(source_document_id: str, solid_fingerprint: str) -> str:
    return f"region:v1:{source_document_id}:{canonical_digest({'solid': solid_fingerprint})}"


def source_face_id(region_identifier: str, face_fingerprint: str) -> str:
    return f"face:v1:{canonical_digest({'region': region_identifier, 'face': face_fingerprint})}"


def patch_id(
    region_identifiers: list[str], source_face_identifiers: list[str], patch_fingerprint: str
) -> str:
    return (
        "patch:v1:"
        + canonical_digest(
            {
                "regions": sorted(region_identifiers),
                "source_faces": sorted(source_face_identifiers),
                "patch_geometry": patch_fingerprint,
                "operation": "face_common_brep:v1",
            }
        )
    )

