import json
from pathlib import Path
import socket
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from dmslicer.geometry_import import HTTPServer, handler_for, tessellate
from test_result_package import package


@pytest.fixture
def server(tmp_path):
    instance = HTTPServer(('127.0.0.1', 0), handler_for(tmp_path))
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield 'http://127.0.0.1:' + str(instance.server_port)
    instance.shutdown()
    instance.server_close()
    thread.join()


def test_primary_page_and_cached_import_do_not_call_freecad(server, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Cached package must not invoke CAD')
    monkeypatch.setattr('dmslicer.geometry_import.tessellate', forbidden)
    html = urlopen(server).read().decode()
    assert 'id="package-file"' in html and 'id="model-file"' not in html
    assert '导入 DM-Slicer 结果包' in html
    request = Request(server + '/package', data=package(), headers={'Content-Type': 'application/octet-stream'})
    value = json.load(urlopen(request))
    assert value['cases'][0]['scene']['entities']


def test_cross_origin_import_and_unknown_paths_are_rejected(server):
    request = Request(server + '/package', data=package(), headers={'Content-Type': 'application/octet-stream', 'Origin': 'https://example.invalid'})
    with pytest.raises(HTTPError) as error: urlopen(request)
    assert error.value.code == 403
    with pytest.raises(HTTPError) as error: urlopen(server + '/source.step')
    assert error.value.code == 404


def test_idle_browser_connection_cannot_block_homepage_or_package(server):
    port = int(server.rsplit(':', 1)[1])
    # A preconnected/unfinished browser request used to occupy the only worker.
    idle = socket.create_connection(('127.0.0.1', port))
    try:
        idle.sendall(b'GET / HTTP/1.1\r\n')
        with urlopen(server, timeout=1) as response:
            assert response.status == 200
        request = Request(server + '/package', data=package(), headers={'Content-Type': 'application/octet-stream'})
        with urlopen(request, timeout=1) as response:
            assert json.load(response)['cases']
    finally:
        idle.close()


@pytest.mark.freecad
def test_package_input_assembly_exposes_two_independent_diagnostic_objects(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / 'benchmarks/cylindrical_interface_repair_07a/C02/inputs.step'
    value = tessellate([{'path': str(source), 'asset': 'geometry/input.step', 'label': '导入几何对象', 'kind': 'MODEL', 'scene_role': 'input', 'split_objects': True}], tmp_path / 'extracted')
    entities = value['scene']['entities']
    assert len(entities) == 2
    assert len({e['entity_ref'] for e in entities}) == 2
    assert all(e['identity_status'] == 'RUN_LOCAL_DIAGNOSTIC' for e in entities)
