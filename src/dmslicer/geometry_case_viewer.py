"""Small display catalog boundary, shared by manual imports and saved evidence."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path


def validate_catalog(value):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(isinstance(value, dict) and value.get('schema') == 'dmslicer.display-catalog.v1', 'Unsupported display schema')
    require(isinstance(value.get('cases'), list), 'cases must be a list')
    ids = set()
    for case in value['cases']:
        require(isinstance(case.get('case_id'), str) and case['case_id'] not in ids, 'Duplicate/missing case ID')
        ids.add(case['case_id'])
        require(isinstance(case.get('label'), str) and isinstance(case.get('provenance'), dict), 'Missing provenance or label')
        scene = case['scene']
        require(scene.get('kind') == 'DISPLAY_ONLY_BREP_TESSELLATION', 'Display only scenes required')
        refs = set()
        for entity in scene['entities']:
            ref = entity.get('entity_ref')
            require(isinstance(ref, str) and ref not in refs, 'Duplicate/missing entity reference')
            refs.add(ref)
            require(entity.get('entity_kind') in ('REGION', 'INTERFACE', 'PATCH', 'MODEL'), 'Unsupported display group')
            require(entity.get('scene_role') in (None, 'input', 'corrected', 'common_interface', 'remaining', 'fused_result'), 'Unknown scene role')
            identity = entity.get('identity_status')
            require(identity in ('STABLE_REFERENCE', 'RUN_LOCAL_DIAGNOSTIC'), 'Missing identity status')
            require(identity != 'STABLE_REFERENCE' or isinstance(entity.get('reference_provenance'), dict), 'Stable reference requires source provenance')
            mesh = entity['mesh']
            require(mesh.get('provenance') == 'BREP_TESSELLATION', 'Mesh must carry B-rep tessellation provenance')
            require(isinstance(mesh.get('linear_deflection_mm'), (float, int)) and math.isfinite(mesh['linear_deflection_mm']) and mesh['linear_deflection_mm'] > 0, 'Invalid display deflection')
            positions = mesh['positions']
            require(len(positions) >= 3, 'Empty mesh')
            for point in positions:
                require(len(point) == 3 and all(type(v) in (float, int) and math.isfinite(v) for v in point), 'Non-finite/invalid point')
            for triangle in mesh['triangles']:
                require(len(triangle) == 3 and all(type(i) is int and 0 <= i < len(positions) for i in triangle), 'Invalid triangle index')
            for line in mesh.get('boundary_polylines', []):
                require(mesh.get('boundary_provenance') == 'BREP_WIRE_EDGE_DISCRETIZATION', 'Missing boundary provenance')
                for point in line:
                    require(len(point) == 3 and all(type(v) in (float, int) and math.isfinite(v) for v in point), 'Invalid boundary point')


def render_catalog(value, *, import_enabled=False):
    validate_catalog(value)
    payload = json.dumps(value, ensure_ascii=True, allow_nan=False).replace('<', '\\u003c')
    template = Path(__file__).with_name('geometry_import_viewer.html').read_text(encoding='utf-8')
    layout = Path(__file__).with_name('viewer_layout.js').read_text(encoding='utf-8')
    return template.replace('__LAYOUT_CODE__', layout).replace('__CATALOG_JSON__', payload).replace('__IMPORT_ENABLED__', 'true' if import_enabled else 'false')


def case01_entry(directory: Path, root: Path):
    scene = json.loads((directory / 'display_scene.json').read_text(encoding='utf-8'))
    provenance = {'confidence': 'L', 'manifest': (directory / 'display_manifest.json').relative_to(root).as_posix(), 'geometry_validation': 'SAVED_SOURCE_REPORT_ONLY', 'human_review': 'PENDING'}
    for entity in scene['entities']:
        entity['identity_status'] = 'STABLE_REFERENCE'
        entity['reference_provenance'] = copy.deepcopy(provenance)
    return {'case_id': directory.name, 'label': 'CASE01 — saved display evidence', 'provenance': provenance, 'scene': scene}
