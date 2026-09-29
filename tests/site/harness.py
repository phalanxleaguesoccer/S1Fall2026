import json, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright
ROOT='/home/claude/s1fall2026/public'
FAKE=open(__import__('os').path.join(__import__('os').path.dirname(__file__),'fake_supabase.js')+'').read()
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
def serve(port=8137):
    handler=functools.partial(H,directory=ROOT)
    socketserver.TCPServer.allow_reuse_address=True; srv=socketserver.TCPServer(('127.0.0.1',port),handler)
    threading.Thread(target=srv.serve_forever,daemon=True).start();return srv
class Site:
    def __init__(self,pw,db,admin=False):
        self.br=pw.chromium.launch()
        self.ctx=self.br.new_context(viewport={'width':1280,'height':900})
        db=dict(db);db['__admin']=admin
        self.ctx.add_init_script('window.__DB='+json.dumps(db)+';')
        self.ctx.route('**/*supabase*.js',lambda r:r.fulfill(body=FAKE,content_type='application/javascript') if 'cdn.jsdelivr' in r.request.url else r.continue_())
        self.ctx.route('**/fonts.g*/**',lambda r:r.abort())
        self.errors=[]
    def page(self,path,wait=900):
        p=self.ctx.new_page();errs=[]
        p.on('pageerror',lambda e:errs.append('PAGEERROR '+str(e)))
        p.on('console',lambda m:errs.append('CONSOLE '+m.text) if m.type=='error' and 'fonts' not in m.text and 'ERR_FAILED' not in m.text else None)
        p.on('dialog',lambda d:(errs.append('DIALOG '+d.message),d.accept()))
        p.goto('http://127.0.0.1:8137/'+path);p.wait_for_timeout(wait);p.errs=errs;return p
