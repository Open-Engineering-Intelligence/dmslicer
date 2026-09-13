"""Create 09B sample copies with explicit, evidence-backed display linkage.

The source packages are immutable.  This script only adds display metadata; it
does not change authoritative geometry, operation results, or validation data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from dmslicer.result_package import read_package, write_package


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001"
TARGET = ROOT / "evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/display-links-001"

PROVENANCE = {
    "C02": [
        "operation.selected_candidates",
        "operation.artifact_verification.actual_common",
        "display scene source.asset references",
    ],
    "U05": [
        "operation.source_ids and operation.side_order",
        "operation.common_patches",
        "operation.partitions.side_1.remaining_patches",
    ],
    "S04_full_sphere_upper_shell": [
        "operation.decision (confirmed contact)",
        "operation.partitions.b_remaining_area_mm2",
        "display scene source.asset references",
    ],
    "P-MULTI": [
        "operation.relation.object_refs",
        "operation.interface.patch_refs",
        "operation.patches geometry_asset/object_refs",
    ],
}


def links_for(case: dict) -> dict:
    entities = case["scene"]["entities"]
    inputs = [e["entity_ref"] for e in entities if e.get("scene_role") == "input"]
    fused = [e["entity_ref"] for e in entities if e.get("scene_role") == "fused_result"]
    operation = case.get("provenance", {}).get("computed_results", {}).get("operation", {})

    if case["case_id"] == "CASE01":
        patches = operation["interface_patches"]["interface_patches"]
        relations = []
        for relation in operation["relations"]["relations"]:
            if relation.get("confirmed") is not True or relation.get("intersection_dimension") != 2:
                continue
            pair = relation["region_pair"]
            patch_refs = [
                patch["patch_id"]
                for patch in patches
                if {patch["region_a_id"], patch["region_b_id"]} == set(pair)
            ]
            relations.append({
                "relation_ref": relation["relation_id"],
                "input_refs": pair,
                "interface_refs": [],
                "patch_refs": patch_refs,
                "remaining_refs": [],
                "provenance_basis": [
                    "operation.relations.relations exact region refs",
                    "operation.interface_patches.interface_patches exact patch refs",
                ],
            })
    else:
        common = [e for e in entities if e.get("scene_role") == "common_interface"]
        relation_ref = {
            "C02": "display-link:C02:confirmed-contact",
            "U05": "display-link:U05:confirmed-contact",
            "S04_full_sphere_upper_shell": "display-link:S04:confirmed-contact",
            "P-MULTI": "interface:p-multi:a-b",
        }[case["case_id"]]
        relations = [{
            "relation_ref": relation_ref,
            "input_refs": inputs,
            "interface_refs": [e["entity_ref"] for e in common if e.get("entity_kind") == "INTERFACE"],
            "patch_refs": [e["entity_ref"] for e in common if e.get("entity_kind") == "PATCH"],
            "remaining_refs": [e["entity_ref"] for e in entities if e.get("scene_role") == "remaining"],
            "provenance_basis": PROVENANCE[case["case_id"]],
        }]
    return {"schema": "dmslicer.display-links.v1", "relations": relations, "fused_result_refs": fused}


def rebuild(source: Path, target: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assets = {item["path"]: archive.read(item["path"]) for item in manifest["assets"] if item["path"] in archive.namelist()}
    display_path = manifest["display"]
    catalog = json.loads(assets[display_path])
    for case in catalog["cases"]:
        case["scene"]["display_links"] = links_for(read_package(source.read_bytes())["cases"][0])
    assets[display_path] = json.dumps(catalog, ensure_ascii=False, indent=2).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    write_package(target, manifest, assets)


def main() -> None:
    source_manifest = json.loads((SOURCE / "samples.json").read_text(encoding="utf-8"))
    output_manifest = {"samples": []}
    custody = []
    for item in source_manifest["samples"]:
        source = SOURCE / item["path"]
        target = TARGET / "samples" / source.name
        rebuild(source, target)
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        target_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        output_manifest["samples"].append({
            **item,
            "path": f"samples/{source.name}",
            "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "sha256": target_sha,
            "hash_semantics": "BYTE_INTEGRITY_ONLY",
        })
        custody.append({"key": item["key"], "source_sha256": source_sha, "linked_copy_sha256": target_sha})
    (TARGET / "samples.json").write_text(json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (TARGET / "linkage_sources.json").write_text(json.dumps({"schema": "dmslicer.display-links-custody.v1", "packages": custody}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
