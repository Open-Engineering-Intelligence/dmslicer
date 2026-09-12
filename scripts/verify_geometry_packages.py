"""Inspect explicit local sample packages and exercise the running import endpoint."""
import argparse
import io
import json
from pathlib import Path
import zipfile
from urllib.request import Request, urlopen

from dmslicer.geometry_case_viewer import render_catalog
from dmslicer.result_package import read_package, write_package


parser = argparse.ArgumentParser()
parser.add_argument('--url', required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('packages', type=Path, nargs='+')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
records = []
for path in args.packages:
    data = path.read_bytes()
    local = read_package(data)
    request = Request(args.url + '/package', data=data, headers={'Content-Type': 'application/octet-stream'})
    remote = json.load(urlopen(request))
    assert local == remote
    entry = remote['cases'][0]
    entities = entry['scene']['entities']
    assert sum(e.get('scene_role') == 'input' for e in entities) == (3 if path.stem == 'CASE01' else 2)
    assert sum(e.get('scene_role') == 'common_interface' for e in entities) == (2 if path.stem == 'CASE01' else 1)
    if path.stem == 'CASE01':
        assert not any(e.get('scene_role') == 'fused_result' for e in entities)
        assert entry['provenance']['role_states']['fused_result'] == 'NOT_PRODUCED_IN_SUPPLIED_EVIDENCE'
    else:
        assert any(e.get('scene_role') == 'fused_result' and not e['default_visible'] for e in entities)
    html = render_catalog(remote)
    assert 'id="model-file"' not in html and 'id="rebuild"' not in html
    (args.output / (path.stem + '.html')).write_text(html, encoding='utf-8')
    records.append({'package': str(path).replace('\\', '/'), 'http_import': 'PASS',
                    'entity_count': len(entities), 'entities': [{'name': e['display_name'], 'role': e.get('scene_role'),
                    'identity': e['identity_status'], 'triangles': len(e['mesh']['triangles'])} for e in entities],
                    'geometry_validation': 'NOT_PERFORMED', 'human_visual_review': 'PENDING'})
    if path.stem == 'C02':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            manifest.pop('display')
            manifest['assets'] = [a for a in manifest['assets'] if a['role'] not in ('display_cache', 'human_review', 'current_kernel_brep')]
            assets = {a['path']: archive.read(a['path']) for a in manifest['assets']}
        core = args.output / 'C02-portable-core.dmslicer'
        write_package(core, manifest, assets)
        value = json.load(urlopen(Request(args.url + '/package', data=core.read_bytes(), headers={'Content-Type': 'application/octet-stream'})))
        assert value['cases'][0]['scene']['entities'] == []
        assert value['cases'][0]['provenance']['computed_results']
        records.append({'package': str(core).replace('\\', '/'), 'http_import': 'PASS', 'display_state': 'NO_CACHE_REDUCED_MODE', 'freecad_artifacts': 'ABSENT'})
(args.output / 'checks.json').write_text(json.dumps(records, ensure_ascii=True, indent=2), encoding='utf-8')
print(json.dumps(records, ensure_ascii=True))
