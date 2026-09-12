from __future__ import annotations

import json
from pathlib import Path

from dmslicer.case01_display import build_case01_display_bundle
from dmslicer.geometry_contract.validation import validate_geometry_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_case01_real_brep_display_bundle_has_authoritative_refs_and_derived_meshes(tmp_path: Path) -> None:
    """The display bridge tessellates real imported B-reps; it never invents boxes."""
    bundle = build_case01_display_bundle(
        ROOT / "benchmarks/interface_case01/case01.step", tmp_path / "bundle", repository_root=ROOT
    )

    snapshot = json.loads((tmp_path / "bundle" / "geometry_snapshot.json").read_text(encoding="utf-8"))
    scene = json.loads((tmp_path / "bundle" / "display_scene.json").read_text(encoding="utf-8"))
    assert validate_geometry_snapshot(snapshot, ROOT) == ()
    assert scene["kind"] == "DISPLAY_ONLY_BREP_TESSELLATION"
    assert len(scene["entities"]) == 5
    assert {entity["entity_kind"] for entity in scene["entities"]} == {"REGION", "PATCH"}
    assert all(entity["mesh"]["provenance"] == "BREP_TESSELLATION" for entity in scene["entities"])
    assert all(len(entity["mesh"]["positions"]) >= 3 for entity in scene["entities"])
    assert all(len(entity["mesh"]["positions"]) == 8 for entity in scene["entities"] if entity["entity_kind"] == "REGION")
    assert all(len(entity["mesh"]["triangles"]) == 12 for entity in scene["entities"] if entity["entity_kind"] == "REGION")
    for entity in scene["entities"]:
        if entity["entity_kind"] == "REGION":
            edges: dict[tuple[int, int], int] = {}
            for triangle in entity["mesh"]["triangles"]:
                for first, second in zip(triangle, triangle[1:] + triangle[:1]):
                    key = tuple(sorted((first, second)))
                    edges[key] = edges.get(key, 0) + 1
            assert set(edges.values()) == {2}, "real Region tessellation is a closed surface"
    assert all(len(entity["mesh"]["triangles"]) >= 2 for entity in scene["entities"])
    assert all(entity["entity_ref"] in bundle["entity_index"] for entity in scene["entities"])
    html = (tmp_path / "bundle" / "case01_3d.html").read_text(encoding="utf-8")
    assert "<canvas" in html
    assert "Selection traceability" in html
    assert "checkbox" in html
    assert "pointerdown" in html
    assert "wheel" in html
    assert "hitTest" in html
    assert "A / SOURCE" in html
    assert "A-G common face" in html
    assert "depth" in html
    assert "shade" in html
    assert "facetEdges" in html
