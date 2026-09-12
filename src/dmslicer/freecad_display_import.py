"""Executed in FreeCADCmd: read STEP/BREP assets and emit display data only.

No boolean operation, contact analysis, source save, or semantic activation.
Face/wire indexes below are scoped diagnostics, never persistent geometry IDs.
"""
import json
import os
from pathlib import Path

import FreeCAD
import Import
import Part


def vec(value):
    return [float(value.x), float(value.y), float(value.z)]


def capture(shape):
    box = shape.BoundBox
    return {'geometry_semantic_snapshot': {'area_mm2': shape.Area, 'volume_mm3': shape.Volume,
            'bounding_box_mm': [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax],
            'semantic_analysis': 'NOT_PERFORMED'},
            'topology_snapshot': {**{name.lower(): len(getattr(shape, name)) for name in ('Solids', 'Shells', 'Faces', 'Edges', 'Vertexes')},
                                  'closure': shape.isClosed(), 'adjacency': 'NOT_CAPTURED', 'holes': 'NOT_CLASSIFIED'},
            'ui_state_snapshot': {'mode': 'HEADLESS', 'camera': None, 'source_saved': False}}


def execute(request):
    entities, snapshots = [], []
    for source in request['sources']:
        path = Path(source['path'])
        document = None
        try:
            if path.suffix.lower() in ('.step', '.stp'):
                document = FreeCAD.newDocument('DisplayImport')
                Import.insert(str(path), document.Name)
                shapes = [o.Shape for o in document.Objects if hasattr(o, 'Shape') and not o.Shape.isNull() and not o.InList]
                if not shapes:
                    raise ValueError('No STEP shape')
                shape = Part.makeCompound(shapes)
                display_shapes = [(o.Name, o.Label, o.Shape) for o in document.Objects if hasattr(o, 'Shape') and not o.Shape.isNull() and not o.InList] if source.get('split_objects') else [('', source['label'], shape)]
                if source.get('split_objects'):
                    expanded = []
                    for locator, label, item in display_shapes:
                        if len(item.Solids) > 1:
                            # Explicitly diagnostic per-import ordinal, never a geometry identity.
                            expanded.extend((locator + '/Solid' + str(i), label + ' / object ' + str(i), solid)
                                            for i, solid in enumerate(item.Solids, 1))
                        else:
                            expanded.append((locator, label, item))
                    display_shapes = expanded
            elif path.suffix.lower() == '.brep':
                shape = Part.Shape()
                shape.read(str(path))
                display_shapes = [('', source['label'], shape)]
            else:
                raise ValueError('Only STEP and BREP supported by display extraction')
            before = capture(shape)
            for locator, label, display_shape in display_shapes:
                vertices, triangles = display_shape.tessellate(request['linear_deflection_mm'])
                if not triangles:
                    raise ValueError('No display triangles in ' + source['asset'])
                lines = []
                # Use B-rep wires, never triangulation edges, for the boundary overlay.
                for face in display_shape.Faces:
                    for wire in face.Wires:
                        for edge in wire.Edges:
                            if edge.Length > 0:
                                lines.append([vec(v) for v in edge.discretize(Deflection=request['boundary_deflection_mm'])])
                entities.append({'entity_ref': 'run-local:' + source['asset'] + ('#' + locator if locator else ''), 'identity_status': 'RUN_LOCAL_DIAGNOSTIC',
                             'entity_kind': source.get('kind', 'MODEL'), 'display_name': source['label'] + (' / ' + label if locator else ''),
                             'scene_role': source.get('scene_role', 'input'),
                             'default_visible': source.get('visible', True),
                             'source': {'asset': source['asset'], 'object_locator': locator or None, 'locator_scope': 'RUN_LOCAL_DIAGNOSTIC', 'geometry_identity': 'NOT_ASSIGNED'},
                             'mesh': {'provenance': 'BREP_TESSELLATION', 'linear_deflection_mm': request['linear_deflection_mm'],
                                      'positions': [vec(v) for v in vertices], 'triangles': [list(t) for t in triangles],
                                      'boundary_polylines': lines, 'boundary_provenance': 'BREP_WIRE_EDGE_DISCRETIZATION',
                                      'boundary_deflection_mm': request['boundary_deflection_mm']}})
            snapshots.append({'asset': source['asset'], 'opening': before, 'closing': capture(shape)})
        finally:
            if document:
                FreeCAD.closeDocument(document.Name)
    return {'scene': {'kind': 'DISPLAY_ONLY_BREP_TESSELLATION', 'entities': entities}, 'snapshots': snapshots,
            'versions': {'freecad': '.'.join(FreeCAD.Version()), 'occt': Part.OCC_VERSION},
            'geometry_validation': 'NOT_PERFORMED'}


try:
    request = json.loads(Path(os.environ['DMSLICER_DISPLAY_REQUEST']).read_text(encoding='utf-8'))
    result = execute(request)
except Exception as error:
    result = {'error': str(error)}
Path(os.environ['DMSLICER_DISPLAY_RESPONSE']).write_text(json.dumps(result, allow_nan=False), encoding='utf-8')
