"""Version 1 result archive: no extraction, executable files, or external resolution."""
import copy
import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile

from .geometry_case_viewer import validate_catalog

MAX_UPLOAD = 50 * 1024 * 1024
MAX_EXPANDED = 200 * 1024 * 1024


def safe_path(name):
    if not isinstance(name, str) or not name or any(ord(c) < 32 for c in name) or '\\' in name or ':' in name or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Unsafe package path')
    return name


def read_package(data):
    if len(data) > MAX_UPLOAD:
        raise ValueError('Package exceeds 50 MiB')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        for entry in entries:
            safe_path(entry.orig_filename.rstrip('/') if entry.is_dir() else entry.orig_filename)
        names = [e.filename for e in entries if not e.is_dir()]
        if len(entries) > 512 or len(names) != len(set(names)) or sum(e.file_size for e in entries) > MAX_EXPANDED:
            raise ValueError('Package expansion/count/duplicate limit')
        if 'manifest.json' not in names:
            raise ValueError('Missing manifest.json')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('schema') != 'dmslicer.result-package.v1':
            raise ValueError('Unsupported result package version')
        if not isinstance(manifest.get('case', {}).get('label'), str) or not isinstance(manifest.get('provenance'), dict):
            raise ValueError('Missing case/provenance')
        contents, assets, results = [], {}, {}
        for item in manifest['assets']:
            path = safe_path(item['path'])
            if path in assets:
                raise ValueError('Duplicate asset declaration')
            assets[path] = item
            present = path in names
            if not present and item.get('required', False):
                raise ValueError('Missing required asset: ' + path)
            if present:
                payload = archive.read(path)
                if hashlib.sha256(payload).hexdigest() != item.get('sha256'):
                    raise ValueError('Byte integrity mismatch: ' + path)
                if item['role'] in ('operation', 'validation'):
                    results[item['role']] = json.loads(payload)
            contents.append({'path': path, 'role': item['role'], 'status': 'PRESENT_BYTE_CHECKED' if present else 'MISSING_OPTIONAL'})
        display = manifest.get('display')
        if display and (display not in assets or assets[display]['role'] != 'display_cache'):
            raise ValueError('Invalid display cache reference')
        if not any(item['role'] == 'authoritative_geometry' and item['path'] in names and PurePosixPath(item['path']).suffix.lower() in ('.step', '.stp') for item in manifest['assets']):
            raise ValueError('No portable authoritative STEP asset')
        has_display = display in names if display else False
        value = json.loads(archive.read(display)) if has_display else {'schema': 'dmslicer.display-catalog.v1', 'cases': [{
            'case_id': manifest['case']['id'], 'label': manifest['case']['label'], 'provenance': {},
            'scene': {'kind': 'DISPLAY_ONLY_BREP_TESSELLATION', 'entities': []}}]}
        validate_catalog(value)
        if not value['cases']:
            raise ValueError('Display catalog must contain a case')
        for case in value['cases']:
            for entity in case['scene']['entities']:
                source = entity.get('source', {}).get('asset')
                if source is not None and (source not in assets or source not in names):
                    raise ValueError('Display cache references a missing geometry asset: ' + str(source))
            case['provenance'] = {**case['provenance'], 'package_case': manifest['case'],
                                  'source_evidence': manifest['provenance'], 'package_contents': contents,
                                  'computed_results': results,
                                  'display_state': 'CACHE_PRESENT_DISPLAY_ONLY' if has_display else 'NO_CACHE_REDUCED_MODE',
                                  'package_checks': {'hash_semantics': 'BYTE_INTEGRITY_ONLY', 'geometry_validation': 'NOT_PERFORMED'},
                                  'optional_assets_not_supplied': [role for role in ('operation', 'validation', 'human_review') if not any(a['role'] == role for a in assets.values())]}
        return value


def write_package(path, manifest, assets):
    """Write only explicitly supplied bytes, and validate before returning."""
    manifest = copy.deepcopy(manifest)
    manifest['assets'] = [{**item, 'sha256': hashlib.sha256(assets[item['path']]).hexdigest()} for item in manifest['assets']]
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=True, indent=2))
        for name, content in assets.items():
            archive.writestr(safe_path(name), content)
    data = target.getvalue()
    read_package(data)
    with path.open('xb') as stream:
        stream.write(data)
    return manifest
