"""Package the existing CASE01 display/analysis artifacts without any CAD call."""
import argparse
import json
from pathlib import Path

from .geometry_case_viewer import case01_entry, render_catalog
from .result_package import read_package, write_package
from .result_labels import apply_sample_labels


def prepare(root, output):
    directory = root / 'evidence/CASE01-GEOMETRY-DISPLAY-01/case01-brep-display-20260912-006'
    entry = case01_entry(directory, root)
    entry['case_id'], entry['label'] = 'CASE01', 'CASE01 · A–G–B 三对象 / 两公共接口'
    entry['provenance'].update({'geometry_validation': 'SAVED_SOURCE_REPORT_ONLY_NOT_RERUN',
        'semantic_analysis': 'A/G/B 为已保存来源标签；本次打包不激活材料语义',
        'role_states': {'fused_result': 'NOT_PRODUCED_IN_SUPPLIED_EVIDENCE', 'remaining': 'NOT_SUPPLIED'},
        'source_run_id': directory.name, 'manifest': 'results/display_manifest.json'})
    for entity in entry['scene']['entities']:
        entity['scene_role'] = 'input' if entity['entity_kind'] == 'REGION' else 'common_interface'
        entity['default_visible'] = True
        entity['source'] = {'asset': 'geometry/input.step', 'stable_reference': entity['entity_ref']}
        entity['reference_provenance'] = {'snapshot_asset': 'results/geometry_snapshot.json', 'source_manifest': 'results/display_manifest.json'}
    assets, descriptors = {}, []

    def add(name, content, role, required=True):
        assets[name] = content
        descriptors.append({'path': name, 'role': role, 'required': required})

    add('geometry/input.step', (root / 'benchmarks/interface_case01/case01.step').read_bytes(), 'authoritative_geometry')
    for filename in ('geometry_snapshot.json', 'display_manifest.json'):
        add('results/' + filename, (directory / filename).read_bytes(), 'source_manifest')
    for filename in ('manifest.json', 'regions.json', 'relations.json', 'interface_patches.json', 'interface_source_boundaries.json', 'geometry.json', 'provenance.json'):
        add('results/analysis/' + filename, (directory / 'analysis' / filename).read_bytes(), 'source_manifest')
    add('results/validation.json', (directory / 'analysis/validation.json').read_bytes(), 'validation')
    operation = {'source_analysis': 'results/analysis/manifest.json', 'packaging_geometry_computation': 'NONE',
                 'relations': json.loads((directory / 'analysis/relations.json').read_text(encoding='utf-8')),
                 'interface_patches': json.loads((directory / 'analysis/interface_patches.json').read_text(encoding='utf-8')),
                 'fused_result': {'state': 'NOT_PRODUCED_IN_SUPPLIED_EVIDENCE'},
                 'geometry_validation': 'READ_SAVED_VALIDATION_ONLY',
                 'source_digest_note': 'Any historical validation digest is preserved as source data, not used as geometric equivalence evidence'}
    add('results/operation.json', json.dumps(operation).encode(), 'operation')
    catalog = {'schema': 'dmslicer.display-catalog.v1', 'cases': [entry]}
    apply_sample_labels(entry)
    add('display/catalog.json', json.dumps(catalog).encode(), 'display_cache', False)
    output.mkdir(parents=True, exist_ok=False)
    path = output / 'CASE01.dmslicer'
    manifest = write_package(path, {'schema': 'dmslicer.result-package.v1',
        'case': {'id': 'CASE01', 'label': entry['label']}, 'provenance': entry['provenance'],
        'display': 'display/catalog.json', 'assets': descriptors}, assets)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'preview.html').write_text(render_catalog(read_package(path.read_bytes())), encoding='utf-8')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(prepare(args.root, args.output))
