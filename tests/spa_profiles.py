"""Verify the packaged same-host SPA, REST and real WebSocket tunnel example."""
import base64
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import struct
import subprocess
import tempfile
import threading
import time

SPA_CHECKS = ['spa:'+name for name in [
    'configuration','canonical-http','static-fallback','rest-routing','storage-routing',
    'forwarded-headers','cache-isolation','guard-precedence','websocket-tunnel',
    'websocket-origin','policy-toggles','missing-index',
    'upload-large-body','upload-total-limit','upload-default-limit',
    'stylesheet-assets','style-policy','javascript-module-assets']]

def receive(stream, count):
    data=b''
    while len(data)<count:
        block=stream.read(count-len(data)) if hasattr(stream,'read') else stream.recv(count-len(data))
        if not block: raise AssertionError('Unexpected WebSocket EOF')
        data+=block
    return data

class RouteBackend(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def reply(self):
        size=int(self.headers.get('Content-Length','0'))
        if size: self.rfile.read(size)
        value=dict(role=self.server.role,path=self.path,method=self.command,
                   headers={key.lower():value for key,value in self.headers.items()})
        if self.headers.get('Upgrade','').lower()=='websocket':
            self.connection.settimeout(6)
            key=self.headers['Sec-WebSocket-Key']
            accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            self.send_response(101)
            self.send_header('Upgrade','websocket')
            self.send_header('Connection','Upgrade')
            self.send_header('Sec-WebSocket-Accept',accept)
            self.end_headers(); self.wfile.flush()
            head=receive(self.rfile,2)
            if head[0]!=0x81 or not head[1]&0x80: raise AssertionError('Expected masked client text frame')
            length=head[1]&127
            if length==126: length=struct.unpack('!H',receive(self.rfile,2))[0]
            if length>4096: raise AssertionError('Oversize fixture frame')
            mask=receive(self.rfile,4); encoded=receive(self.rfile,length)
            value['message']=bytes(byte^mask[index%4] for index,byte in enumerate(encoded)).decode()
            data=json.dumps(value).encode()
            frame=b'\x81'+(bytes([len(data)]) if len(data)<126 else b'\x7e'+struct.pack('!H',len(data)))
            self.wfile.write(frame+data); self.wfile.flush()
            self.close_connection=True
            return
        failed=self.path.split('?',1)[0].endswith('/fail')
        data=b'SENSITIVE BACKEND ERROR' if failed else json.dumps(value).encode()
        self.send_response(500 if failed else 200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','public, max-age=86400')
        self.send_header('Expires','Thu, 01 Jan 2037 00:00:00 GMT')
        self.send_header('Content-Security-Policy','default-src *')
        self.send_header('X-Frame-Options','DENY')
        self.end_headers()
        self.wfile.write(data)
    do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=reply
    def log_message(self,*args): pass

def run_spa_profiles(binary,runtime,target,root,check,done):
    binary,runtime,root=Path(binary),Path(runtime),Path(root)
    backends=[]
    for role in ['spring','storage']:
        backend=HTTPServer(('127.0.0.1',0),RouteBackend); backend.role=role
        threading.Thread(target=backend.serve_forever,daemon=True).start()
        backends.append(backend)
    def free_port():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); return sock.getsockname()[1]
    ports=set()
    while len(ports)<3: ports.add(free_port())
    http_port,https_port,preview_port=sorted(ports)
    context=ssl._create_unverified_context()
    process=None
    try:
        with tempfile.TemporaryDirectory(prefix='forge-spa-') as temp:
            base=Path(temp)
            shutil.copytree(str(runtime/'conf'),str(base/'conf'))
            shutil.copytree(str(runtime/'html'),str(base/'html'))
            (base/'logs').mkdir(); (base/'temp').mkdir()
            site=base/'sites/example.test/public'; site.mkdir(parents=True)
            (site/'index.html').write_bytes(b'SPA ENTRY\n')
            (site/'app.js').write_bytes(b'PUBLIC SCRIPT\n')
            stylesheet=b'.forge-css-check { color: rgb(12, 34, 56); }\n'
            (site/'app.css').write_bytes(stylesheet)
            module=b'export const forgeModule = "MODULE READY";\n'
            (site/'app.mjs').write_bytes(module)
            (site/'secret.key').write_bytes(b'PRIVATE KEY FIXTURE')
            conf=(runtime/'conf/nginx.conf').read_text(encoding='utf-8')
            conf='daemon off;\nmaster_process off;\n'+conf.replace('127.0.0.1:8080','127.0.0.1:'+str(preview_port))
            template=(runtime/'conf/examples/spa-api-websocket.conf.example').read_text(encoding='utf-8')
            template=template.replace('listen 80','listen 127.0.0.1:'+str(http_port)).replace('listen 443','listen 127.0.0.1:'+str(https_port))
            template=template.replace('127.0.0.1:9090','127.0.0.1:'+str(backends[0].server_port))
            template=template.replace('127.0.0.1:9080','127.0.0.1:'+str(backends[1].server_port))
            main_path=base/'conf/nginx.conf'; site_path=base/'conf/conf.d/site.conf'
            main_path.write_text(conf,encoding='utf-8'); site_path.write_text(template,encoding='utf-8')
            defaults=base/'conf/policies/http/default-listeners.conf'
            defaults.write_text(defaults.read_text(encoding='utf-8').replace('listen 80','listen 127.0.0.1:'+str(http_port))
                                .replace('listen 443','listen 127.0.0.1:'+str(https_port)),encoding='utf-8')
            cert=base/'conf/certs/example.test'; cert.mkdir(parents=True)
            shutil.copy2(str(root/'tests/fixtures/cert.pem'),str(cert/'fullchain.pem'))
            shutil.copy2(str(root/'tests/fixtures/key.pem'),str(cert/'privkey.pem'))
            command=[str(binary),'-p',base.resolve().as_posix()+'/','-c','conf/nginx.conf']
            def syntax():
                result=subprocess.run(command+['-t'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                      universal_newlines=True,timeout=30)
                check(result.returncode==0,result.stdout)
            syntax(); done('spa:configuration')
            def disabled(source,names):
                return '\n'.join('# '+line if any(line.lstrip().startswith('include '+name+';') for name in names)
                                 else line for line in source.splitlines())+'\n'
            # Map declarations are required infrastructure; every selected policy is independently optional.
            policies=set(re.findall(r'^\s*include (policies/[^;]+);',conf+'\n'+template,re.M))
            try:
                for names in [{name} for name in sorted(policies)]+[policies]:
                    main_path.write_text(disabled(conf,names),encoding='utf-8')
                    site_path.write_text(disabled(template,names),encoding='utf-8')
                    syntax()
            finally:
                main_path.write_text(conf,encoding='utf-8'); site_path.write_text(template,encoding='utf-8')
            log=open(str(base/'process.log'),'wb')
            def stop():
                if process is not None and process.poll() is None:
                    try:
                        subprocess.run(command+['-s','quit'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
                        process.wait(timeout=10)
                    except (OSError,subprocess.TimeoutExpired):
                        process.kill(); process.wait(timeout=10)
            def start():
                nonlocal process
                process=subprocess.Popen(command,stdout=log,stderr=log,
                    **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
                for _ in range(100):
                    check(process.poll() is None,'SPA server exited: '+(base/'process.log').read_text())
                    try:
                        with socket.create_connection(('127.0.0.1',http_port),timeout=.2): return
                    except OSError: time.sleep(.1)
                raise AssertionError('SPA server did not start')
            def request(path,method='GET',headers=None,secure=True,body=None):
                time.sleep(.12)
                connection=http.client.HTTPConnection('127.0.0.1',https_port if secure else http_port,timeout=10)
                if secure:
                    connection.sock=context.wrap_socket(socket.create_connection(('127.0.0.1',https_port),timeout=10),
                                                        server_hostname='example.test')
                values={'Host':'example.test','Connection':'close'}
                values.update(headers or {})
                connection.request(method,path,body=body,headers=values)
                response=connection.getresponse(); data=response.read(); hdr=response.headers
                status=response.status; connection.close()
                return status,hdr,data
            def websocket(origin='https://example.test'):
                time.sleep(.12)
                sock=context.wrap_socket(socket.create_connection(('127.0.0.1',https_port),timeout=10),
                                         server_hostname='example.test')
                sock.settimeout(10)
                key='dGhlIHNhbXBsZSBub25jZQ=='
                lines=['GET /process_file/echo?job=7 HTTP/1.1','Host: example.test','Upgrade: websocket',
                       'Connection: Upgrade','Sec-WebSocket-Version: 13','Sec-WebSocket-Key: '+key,
                       'X-Forwarded-For: 203.0.113.55','Forwarded: for=203.0.113.55']
                if origin is not None: lines.append('Origin: '+origin)
                sock.sendall(('\r\n'.join(lines)+'\r\n\r\n').encode())
                head=b''
                while b'\r\n\r\n' not in head:
                    head+=receive(sock,1)
                    check(len(head)<16384,'Oversize WebSocket headers')
                status=int(head.split(b' ',2)[1])
                return sock,status,head
            try:
                start()
                status,headers,data=request('/screen/view?x=1',secure=False)
                check(status==308 and headers.get('Location')=='https://example.test/screen/view?x=1','SPA HTTPS redirect failed')
                for path in ['/api','/storagewiz','/process_file']:
                    status,headers,data=request(path+'?x=1',method='POST')
                    check(status==308 and headers.get('Location','').endswith(path+'/?x=1'),'Bare API prefix fell through to SPA')
                done('spa:canonical-http')
                status,headers,data=request('/documents/123')
                check(status==200 and data==b'SPA ENTRY\n','SPA history fallback failed')
                status,headers,data=request('/app.js')
                check(status==200 and data==b'PUBLIC SCRIPT\n' and headers.get('Cache-Control') is None,'Static cache policy changed')
                for path in ['/documents/123','/index.html']:
                    status,headers,data=request(path,method='POST')
                    check(status==405,'Static method restriction missing')
                done('spa:static-fallback')
                status,headers,data=request('/app.css')
                check(status==200 and data==stylesheet and headers.get_content_type()=='text/css'
                      and headers.get('X-Content-Type-Options')=='nosniff',
                      'Stylesheet was blocked, replaced by SPA HTML, or served with the wrong MIME type')
                done('spa:stylesheet-assets')
                values=headers.get_all('Content-Security-Policy') or []
                check(len(values)==1,'Multiple CSP headers may intersect and block inline CSS')
                directives={parts[0]:set(parts[1:]) for parts in
                            (entry.split() for entry in values[0].split(';')) if parts}
                check(directives.get('style-src')=={"'self'","'unsafe-inline'"}
                      and directives.get('script-src')=={"'self'"}
                      and directives.get('default-src')=={"'self'"}
                      and not {'style-src-elem','style-src-attr'} & set(directives),
                      'SPA CSS compatibility or JavaScript/source restrictions changed')
                done('spa:style-policy')
                status,headers,data=request('/app.mjs')
                check(status==200 and data==module and headers.get_content_type()=='application/javascript'
                      and headers.get('X-Content-Type-Options')=='nosniff',
                      'ES module was blocked, replaced by SPA HTML, or served with a non-JavaScript MIME type')
                done('spa:javascript-module-assets')
                for method in ['GET','POST','PUT','PATCH','DELETE','OPTIONS']:
                    status,headers,data=request('/api/items?x=1',method=method)
                    seen=json.loads(data.decode()) if status==200 else {}
                    check(status==200 and seen.get('role')=='spring' and seen.get('path')=='/api/items?x=1'
                          and seen.get('method')==method,'REST route/method changed: '+method)
                done('spa:rest-routing')
                status,headers,data=request('/storagewiz/items?x=2',method='POST')
                seen=json.loads(data.decode())
                check(status==200 and seen['role']=='storage' and seen['path']=='/storagewiz/items?x=2','Storage destination/prefix changed')
                done('spa:storage-routing')
                status,headers,data=request('/process_file/status?x=3',method='POST',headers={
                    'X-Forwarded-For':'203.0.113.55','X-Real-IP':'203.0.113.55','Forwarded':'for=203.0.113.55'})
                seen=json.loads(data.decode()); forwarded=seen['headers']
                check(status==200 and seen['role']=='spring' and seen['path']=='/process_file/status?x=3'
                      and forwarded.get('host')=='example.test' and forwarded.get('x-forwarded-for')=='127.0.0.1'
                      and forwarded.get('x-real-ip')=='127.0.0.1' and forwarded.get('x-forwarded-proto')=='https'
                      and forwarded.get('x-forwarded-host')=='example.test' and 'forwarded' not in forwarded,
                      'WebSocket location lost regular HTTP or forwarding policy')
                done('spa:forwarded-headers')
                for path,expected in [('/api/items',200),('/%61pi/items',200),('/storagewiz/items',200),
                                      ('/process_file/status',200),('/api/fail',500)]:
                    status,headers,data=request(path)
                    check(status==expected and headers.get_all('Cache-Control')==['no-store']
                          and headers.get('Expires') is None,'Private API cache missing or duplicated: '+path)
                    check(len(headers.get_all('Content-Security-Policy') or [])==1
                          and headers.get('Content-Security-Policy').startswith("default-src 'self'")
                          and headers.get_all('X-Frame-Options')==['SAMEORIGIN'],'Upstream response policy leaked')
                    if expected==500: check(b'SENSITIVE BACKEND' not in data,'API error body leaked')
                done('spa:cache-isolation')
                for path in ['/secret.key','/deep/secret.key','/api/secret.key','/process_file/payload.php',
                             '/storagewiz/.env','/actuator/env','/bundle.js.map']:
                    status,headers,data=request(path)
                    check(status==404 and data!=b'SPA ENTRY\n' and b'PRIVATE KEY' not in data,
                          'SPA/proxy route bypassed a regex guard: '+path)
                done('spa:guard-precedence')
                sock,status,head=websocket()
                try:
                    check(status==101 and b'Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=' in head,
                          'WebSocket upgrade failed: '+repr(head))
                    message=b'NGINXFORGE WEBSOCKET ECHO'; mask=b'abcd'
                    sock.sendall(b'\x81'+bytes([0x80|len(message)])+mask+
                                 bytes(byte^mask[index%4] for index,byte in enumerate(message)))
                    first=receive(sock,2); length=first[1]&127
                    if length==126: length=struct.unpack('!H',receive(sock,2))[0]
                    check(first[0]==0x81 and not first[1]&0x80,'Invalid backend text frame')
                    seen=json.loads(receive(sock,length).decode()); forwarded=seen['headers']
                    check(seen['message']==message.decode() and seen['role']=='spring'
                          and seen['path']=='/process_file/echo?job=7'
                          and forwarded.get('x-forwarded-for')=='127.0.0.1'
                          and forwarded.get('host')=='example.test' and forwarded.get('x-forwarded-proto')=='https'
                          and forwarded.get('upgrade','').lower()=='websocket'
                          and 'upgrade' in forwarded.get('connection','').lower() and 'forwarded' not in forwarded,
                          'Real WebSocket frame or forwarding policy failed')
                finally: sock.close()
                done('spa:websocket-tunnel')
                for origin in ['https://evil.invalid','https://example.test.evil.invalid','null',None]:
                    sock,status,head=websocket(origin)
                    sock.close(); check(status==403,'Unreviewed WebSocket origin accepted: '+str(origin))
                done('spa:websocket-origin')
                for name in ['policies/location/websocket.conf','policies/server/private-cache-spa.conf']:
                    stop(); site_path.write_text(disabled(template,{name}),encoding='utf-8'); start()
                    if name.endswith('/websocket.conf'):
                        sock,status,head=websocket(); sock.close()
                        check(status==200,'WebSocket OFF still upgraded')
                    else:
                        status,headers,data=request('/api/items')
                        check(status==200 and headers.get_all('Cache-Control')==['public, max-age=86400'],
                              'SPA cache switch OFF did not restore backend policy')
                        check(headers.get_all('X-Frame-Options')==['SAMEORIGIN'],'Cache toggle removed unrelated policy')
                done('spa:policy-toggles')

                # Enable the packaged file-server alternative exactly as an operator does.
                stop()
                upload_template=template.replace('    include policies/server/body-size.conf;',
                                                  '    # include policies/server/body-size.conf;')
                upload_template=upload_template.replace('    # include policies/server/upload-body-size.conf;',
                                                        '    include policies/server/upload-body-size.conf;')
                check(upload_template!=template,'Upload option was not selected')
                site_path.write_text(upload_template,encoding='utf-8'); syntax(); start()
                # A real multipart request larger than the previous 5 MiB cap reaches the backend.
                boundary='nginxforge-upload-boundary'
                payload=(('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="fixture.bin"\r\n'
                          'Content-Type: application/octet-stream\r\n\r\n').encode()+b'x'*(6*1024*1024)+
                         ('\r\n--'+boundary+'--\r\n').encode())
                status,headers,data=request('/api/upload',method='POST',body=payload,
                    headers={'Content-Type':'multipart/form-data; boundary='+boundary})
                check(status==200 and json.loads(data.decode()).get('path')=='/api/upload',
                      'Multipart request above 5 MiB did not reach backend under 1 GiB policy')
                done('spa:upload-large-body')
                # Reject an oversized Content-Length before sending or allocating a 1 GiB body.
                status,headers,data=request('/api/upload',method='POST',headers={'Content-Length':str(1024**3+1)})
                check(status==413,'1 GiB request ceiling was not enforced')
                done('spa:upload-total-limit')
                stop(); site_path.write_text(template,encoding='utf-8'); start()
                status,headers,data=request('/api/upload',method='POST',headers={'Content-Length':str(len(payload))})
                check(status==413,'Turning off upload alternative did not restore the default 5 MiB cap')
                done('spa:upload-default-limit')
                stop(); site_path.write_text(template,encoding='utf-8')
                (site/'index.html').unlink(); start()
                status,headers,data=request('/documents/123')
                check(status==404,'Missing SPA entry caused a redirect loop')
                done('spa:missing-index')
            finally:
                stop(); log.close()
    finally:
        for backend in backends:
            backend.shutdown(); backend.server_close()
