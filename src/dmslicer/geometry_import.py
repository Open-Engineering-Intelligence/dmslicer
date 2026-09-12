"""User-triggered loopback import helper; run with --serve. No batch analysis."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as HTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlsplit

from .geometry_case_viewer import render_catalog
from .result_package import MAX_UPLOAD, read_package
from .runner import _freecad_executable

EMPTY = {'schema': 'dmslicer.display-catalog.v1', 'cases': []}


def tessellate(sources, output):
    output.mkdir(parents=True, exist_ok=False)
    request = {'sources': sources, 'linear_deflection_mm': 0.25, 'boundary_deflection_mm': 0.25}
    script = Path(__file__).with_name('freecad_display_import.py')
    with tempfile.TemporaryDirectory(prefix='dmslicer-display-') as temporary:
        directory = Path(temporary)
        request_path, response_path = directory / 'request.json', directory / 'response.json'
        request_path.write_text(json.dumps(request), encoding='utf-8')
        env = {**os.environ, 'DMSLICER_DISPLAY_REQUEST': str(request_path), 'DMSLICER_DISPLAY_RESPONSE': str(response_path), 'DMSLICER_DISPLAY_SCRIPT': str(script)}
        result = subprocess.run([str(_freecad_executable()), '--safe-mode', '-c'], input="import os; p=os.environ['DMSLICER_DISPLAY_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n", env=env, text=True, capture_output=True, timeout=120)
        (output / 'process.json').write_text(json.dumps({'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}), encoding='utf-8')
        if not response_path.exists():
            raise ValueError('FreeCAD did not return display data; see import process log')
        data = json.loads(response_path.read_text(encoding='utf-8'))
        if result.returncode or 'error' in data:
            raise ValueError(data.get('error', 'FreeCAD import failed'))
    for snapshot in data['snapshots']:
        # One immutable file per opening/closing snapshot category and input asset.
        asset_dir = output / 'snapshots' / snapshot['asset']
        asset_dir.mkdir(parents=True)
        for stage in ('opening', 'closing'):
            for kind, value in snapshot[stage].items():
                with (asset_dir / (stage + '_' + kind + '.json')).open('x', encoding='utf-8') as stream:
                    json.dump(value, stream, indent=2)
    (output / 'extraction.json').write_text(json.dumps(data), encoding='utf-8')
    return data


def handler_for(root):
    class Handler(BaseHTTPRequestHandler):
        # Browsers may preconnect without sending headers. Such a socket must
        # neither monopolize the service nor hold an idle worker indefinitely.
        timeout = 15

        def reply(self, status, body, mime='application/json'):
            data = body.encode('utf-8') if isinstance(body, str) else body
            self.send_response(status)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def local_request(self):
            expected = '127.0.0.1:' + str(self.server.server_port)
            return self.headers.get('Host') == expected and self.headers.get('Origin', 'http://' + expected) == 'http://' + expected

        def do_GET(self):
            if not self.local_request():
                return self.reply(403, '{"error":"Local origin required"}')
            if self.path != '/':
                return self.reply(404, '{}')
            self.reply(200, render_catalog(EMPTY, import_enabled=True), 'text/html')

        def do_POST(self):
            if not self.local_request() or self.headers.get('Content-Type') != 'application/octet-stream':
                return self.reply(403, '{"error":"Local binary upload required"}')
            parsed = urlsplit(self.path)
            if parsed.path != '/package':
                return self.reply(404, '{}')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_UPLOAD:
                    raise ValueError('Upload limit: 50 MiB')
                self.connection.settimeout(30)
                data = self.rfile.read(length)
                if len(data) != length:
                    raise ValueError('Incomplete upload')
                value = read_package(data)
                self.reply(200, json.dumps(value, allow_nan=False))
            except Exception as error:
                self.reply(400, json.dumps({'error': str(error)}))
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--imports', type=Path, default=Path('evidence/GEOMETRY-MANUAL-IMPORT'))
    args = parser.parse_args()
    server = HTTPServer(('127.0.0.1', args.port), handler_for(args.imports.resolve()))
    print('DM-Slicer viewer: http://127.0.0.1:%d/ — Ctrl+C stops the local helper' % server.server_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
