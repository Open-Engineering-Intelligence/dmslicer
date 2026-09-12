"""Prepare a new portable package from an explicit existing evidence run.

Preserves historical source files. This adapter consumes saved output geometry;
it never reruns Boolean/contact experiments. BREP and FCStd are optional tiers.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .geometry_import import tessellate
from .geometry_case_viewer import render_catalog
from .result_package import write_package, read_package


def prepare(run, input_step, output, case_id, label, include_review=False):
    output.mkdir(parents=True, exist_ok=False)
    source_manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    assets, entries, sources = {}, [], []

    def add(path, name, role, required=True):
        assets[name] = path.read_bytes()
        entries.append({'path': name, 'role': role, 'required': required})

    add(input_step, 'geometry/input.step', 'authoritative_geometry')
    for name, role in [('operation.json', 'operation'), ('validation.json', 'validation'), ('manifest.json', 'source_manifest')]:
        add(run / name, 'results/' + name, role)
    preferred = run / 'corrected_assembly.step'
    if preferred.exists():
        add(preferred, 'geometry/corrected_assembly.step', 'authoritative_geometry')
        sources.append({'path': str(preferred.resolve()), 'asset': 'geometry/corrected_assembly.step', 'label': '校正几何', 'kind': 'MODEL', 'scene_role': 'corrected', 'split_objects': True, 'visible': False})
        sources.append({'path': str(input_step.resolve()), 'asset': 'geometry/input.step', 'label': '导入几何对象', 'kind': 'MODEL', 'scene_role': 'input', 'split_objects': True})
    else:
        sources.append({'path': str(input_step.resolve()), 'asset': 'geometry/input.step', 'label': '导入几何对象', 'kind': 'MODEL', 'scene_role': 'input', 'split_objects': True})
    if (run / 'fused.step').exists():
        add(run / 'fused.step', 'geometry/fused.step', 'authoritative_geometry')
        sources.append({'path': str((run / 'fused.step').resolve()), 'asset': 'geometry/fused.step', 'label': '融合结果 / Saved fused result', 'kind': 'MODEL', 'scene_role': 'fused_result', 'visible': False})
    patch_files = sorted((run / 'patches').glob('*.brep')) if (run / 'patches').is_dir() else []
    if (run / 'actual_common.brep').exists():
        patch_files.append(run / 'actual_common.brep')
    for path in patch_files:
        name = 'kernel_brep/' + path.name
        add(path, name, 'current_kernel_brep', False)
        role = 'common_interface' if 'common' in path.stem else 'remaining'
        sources.append({'path': str(path.resolve()), 'asset': name, 'label': ('公共接口补丁 / ' if role == 'common_interface' else '剩余分区 / ') + path.stem, 'kind': 'PATCH', 'scene_role': role, 'visible': role == 'common_interface'})
        # Exact exchange counterpart where the existing run supplies one.
        if path.with_suffix('.step').exists():
            add(path.with_suffix('.step'), 'geometry/patches/' + path.stem + '.step', 'authoritative_geometry', False)
    if include_review and (run / 'operation_debug.FCStd').exists():
        add(run / 'operation_debug.FCStd', 'review/operation_debug.FCStd', 'human_review', False)
    extracted = tessellate(sources, output / 'display-extraction')
    provenance = {'source_run_id': source_manifest.get('run_id'), 'source_goal_id': source_manifest.get('goal_id'),
                  'source_implementation_commit': source_manifest.get('implementation_commit'),
                  'source_evidence_state': source_manifest.get('evidence_confidence', 'U'),
                  'evidence_confidence': 'L', 'geometry_validation': 'NOT_RERUN_BY_PACKAGING',
                  'semantic_analysis': 'NO_MATERIAL_REGION_BINDING — 本包未声明材料区域绑定',
                  'identity_status': 'RUN_LOCAL_DIAGNOSTIC', 'human_review': 'PENDING',
                  'versions': extracted['versions'], 'display_linear_deflection_mm': 0.25, 'display_boundary_deflection_mm': 0.25,
                  'source_manifest': 'results/manifest.json'}
    catalog = {'schema': 'dmslicer.display-catalog.v1', 'cases': [{'case_id': case_id, 'label': label, 'provenance': provenance, 'scene': extracted['scene']}]}
    assets['display/catalog.json'] = json.dumps(catalog, ensure_ascii=True).encode('utf-8')
    entries.append({'path': 'display/catalog.json', 'role': 'display_cache', 'required': False})
    manifest = {'schema': 'dmslicer.result-package.v1', 'case': {'id': case_id, 'label': label},
                'provenance': provenance, 'display': 'display/catalog.json', 'assets': entries,
                'tiers': {'core': 'STEP + computation/validation JSON + manifest', 'optional': 'current-kernel BREP, FCStd human review, rebuildable display cache'},
                'created_utc': datetime.now(timezone.utc).isoformat()}
    manifest['scene_sources'] = [{k: v for k, v in source.items() if k != 'path'} for source in sources]
    package = output / (case_id + '.dmslicer')
    manifest = write_package(package, manifest, assets)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    # Convenient evidence preview; normal product entry remains the package picker.
    (output / 'preview.html').write_text(render_catalog(read_package(package.read_bytes())), encoding='utf-8')
    return package


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--input-step', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--include-review', action='store_true')
    args = parser.parse_args()
    print(prepare(args.run, args.input_step, args.output, args.case_id, args.label, args.include_review))
