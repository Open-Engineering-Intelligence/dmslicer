import hashlib
import io
import json
import zipfile

import pytest

from test_geometry_case_viewer import catalog


def package(extra=None):
    assets = {'display/catalog.json': json.dumps(catalog()).encode(), 'geometry/source.step': b'ISO-10303-21;'}
    manifest = {'schema': 'dmslicer.result-package.v1', 'case': {'id': 'sample', 'label': 'Sample'},
                'provenance': {'evidence_confidence': 'L'}, 'display': 'display/catalog.json',
                'assets': [{'path': name, 'role': 'display_cache' if name.startswith('display') else 'authoritative_geometry', 'required': True,
                            'sha256': hashlib.sha256(data).hexdigest()} for name, data in assets.items()]}
    assets['manifest.json'] = json.dumps(manifest).encode()
    assets.update(extra or {})
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        for name, data in assets.items():
            info = zipfile.ZipInfo()
            info.filename = name  # Preserve raw Windows separators for the hostile archive test.
            archive.writestr(info, data)
    return result.getvalue()


def test_result_package_retains_evidence_and_separates_validation():
    from dmslicer.result_package import read_package
    value = read_package(package())
    assert value['cases'][0]['provenance']['package_checks']['hash_semantics'] == 'BYTE_INTEGRITY_ONLY'
    assert value['cases'][0]['provenance']['package_checks']['geometry_validation'] == 'NOT_PERFORMED'
    assert len(value['cases'][0]['provenance']['package_contents']) == 2


@pytest.mark.parametrize('name', ['../escape.step', '/absolute.step', 'C:/escape.step', 'geometry\\escape.step'])
def test_unsafe_zip_paths_rejected(name):
    from dmslicer.result_package import read_package
    with pytest.raises(ValueError): read_package(package({name: b'bad'}))


def test_corrupted_authoritative_asset_rejected():
    from dmslicer.result_package import read_package
    with pytest.raises(ValueError, match='integrity'):
        read_package(package({'geometry/source.step': b'changed'}))


def test_no_display_cache_is_a_valid_reduced_package():
    from dmslicer.result_package import read_package
    data = package()
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        manifest = json.loads(source.read('manifest.json'))
        manifest.pop('display')
        manifest['assets'] = [a for a in manifest['assets'] if a['role'] != 'display_cache']
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as target:
            target.writestr('manifest.json', json.dumps(manifest))
            target.writestr('geometry/source.step', source.read('geometry/source.step'))
    value = read_package(output.getvalue())['cases'][0]
    assert value['scene']['entities'] == []
    assert value['provenance']['display_state'] == 'NO_CACHE_REDUCED_MODE'
