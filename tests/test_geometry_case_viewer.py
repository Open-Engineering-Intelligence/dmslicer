import copy
import json
from pathlib import Path
import subprocess

import pytest


def catalog():
    return {"schema": "dmslicer.display-catalog.v1", "cases": [{
        "case_id": "offset-sample", "label": "Offset sample", "provenance": {"confidence": "L"},
        "scene": {"kind": "DISPLAY_ONLY_BREP_TESSELLATION", "entities": [{
            "entity_ref": "run-a/Face1", "identity_status": "RUN_LOCAL_DIAGNOSTIC",
            "entity_kind": "PATCH", "display_name": "Face1",
            "mesh": {"provenance": "BREP_TESSELLATION", "linear_deflection_mm": 0.25,
                     "positions": [[1000, 0, 0], [1010, 0, 0], [1000, 10, 0]], "triangles": [[0, 1, 2]]}
        }]}}]}


def test_catalog_roundtrip_is_safe_and_does_not_mutate():
    from dmslicer.geometry_case_viewer import render_catalog
    value = catalog()
    value["cases"][0]["label"] = "</script><img onerror=alert(1)>"
    before = copy.deepcopy(value)
    html = render_catalog(value)
    assert value == before
    data = html.split('<script id="catalog-data" type="application/json">')[1].split('</script>')[0]
    assert json.loads(data) == value
    assert '</script>' not in data
    code = html.split('<script id="viewer-code">')[1].split('</script>')[0]
    result = subprocess.run(['node', '--check', '-'], input=code, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('damage', ['index', 'nan', 'identity', 'duplicate', 'authority'])
def test_bad_catalog_is_rejected(damage):
    from dmslicer.geometry_case_viewer import validate_catalog
    value = catalog()
    entity = value['cases'][0]['scene']['entities'][0]
    if damage == 'index': entity['mesh']['triangles'][0][2] = 9
    if damage == 'nan': entity['mesh']['positions'][0][0] = float('nan')
    if damage == 'identity': entity['identity_status'] = 'STABLE_REFERENCE'
    if damage == 'duplicate': value['cases'].append(copy.deepcopy(value['cases'][0]))
    if damage == 'authority': entity['mesh']['provenance'] = 'INFERRED_TRUTH'
    with pytest.raises(ValueError): validate_catalog(value)


def test_case01_adapter_preserves_ids_and_absent_fields():
    from dmslicer.geometry_case_viewer import case01_entry
    root = Path(__file__).resolve().parents[1]
    directory = root / 'evidence/CASE01-GEOMETRY-DISPLAY-01/case01-brep-display-20260912-006'
    entry = case01_entry(directory, root)
    original = json.loads((directory / 'display_scene.json').read_text())
    assert [e['entity_ref'] for e in entry['scene']['entities']] == [e['entity_ref'] for e in original['entities']]
    assert all(e['identity_status'] == 'STABLE_REFERENCE' for e in entry['scene']['entities'])
    assert all('boundary_polylines' not in e['mesh'] for e in entry['scene']['entities'])
