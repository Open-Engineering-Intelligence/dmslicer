"""09B-only material/semantic development preview; no geometry renderer."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse, json
from .geometry_import import load_samples
from .result_package import MAX_UPLOAD, read_package

def handler(samples):
    template=Path(__file__).with_name('material_semantic_preview.html').read_text(encoding='utf-8')
    annotation=Path(__file__).with_name('workspace_annotations.js').read_text(encoding='utf-8')
    page=template.replace('__ANNOTATIONS__',annotation)+"<style>body{overflow-x:hidden}.object-table{table-layout:fixed}.object-table th:nth-child(3),.object-table td:nth-child(3){width:20%}.object-table th:nth-child(2),.object-table td:nth-child(2){width:20%;overflow-wrap:anywhere}.object-table td{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#object-selection{overflow:auto}</style><script>toggle=()=>{let g=$('assignment-type').value;if(g==='Gradient')$('assignment-material').value='';$('assignment-material').disabled=g==='Gradient';$('group-wrap').classList.toggle('hidden',g!=='Gradient')};$('assignment-type').onchange=toggle;const recordedDraw=draw;draw=()=>{recordedDraw();$('preview-canvas').dataset.camera=az.toFixed(2)+','+el.toFixed(2)+','+zoom.toFixed(2)};const rawRows=rows;rows=()=>{rawRows();document.querySelectorAll('#objects tr').forEach(row=>{let cell=row.children[2],full=cell.textContent,short=full.length>18?'…'+full.slice(-16):full,button=document.createElement('button');button.className='object-ref-short';button.textContent=short;button.title='展开完整稳定引用';button.onclick=()=>{button.textContent=button.textContent===short?full:short};cell.replaceChildren(button)})};const materialCancel=$('material').querySelector('button[value=cancel]');materialCancel.type='button';materialCancel.onclick=()=>$('material').close()</script>"
    class H(BaseHTTPRequestHandler):
        def reply(self,status,value,mime='application/json'):
            data=value.encode() if isinstance(value,str) else value;self.send_response(status);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/':return self.reply(200,page,'text/html')
            if self.path=='/samples':return self.reply(200,json.dumps([{'key':k,'label':v['label']} for k,v in samples.items()]))
            key=self.path.removeprefix('/sample/')
            if self.path.startswith('/sample/') and key in samples:return self.reply(200,samples[key]['path'].read_bytes(),'application/octet-stream')
            return self.reply(404,'{}')
        def do_POST(self):
            try:
                n=int(self.headers.get('Content-Length','0'));assert 0<n<=MAX_UPLOAD;self.reply(200,json.dumps(read_package(self.rfile.read(n))))
            except Exception as e:self.reply(400,json.dumps({'error':str(e)}))
    return H
def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=56811);p.add_argument('--samples',type=Path,required=True);a=p.parse_args();s=ThreadingHTTPServer(('127.0.0.1',a.port),handler(load_samples(a.samples)));print(f'09B material/semantic preview: http://127.0.0.1:{a.port}/',flush=True);s.serve_forever()
if __name__=='__main__':main()
