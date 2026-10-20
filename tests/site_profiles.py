"""Exercise one-file site controls against the exact packaged split policies."""
import hashlib
import http.client
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
from fixture_backend import FixtureServer, RouteBackend, receive
from site_config import render_sites

PROFILE_CHECKS=['profile:'+name for name in [
    'package-integrity','policy-layout','configuration','http-redirect','unknown-host','unknown-sni',
    'static-https','security-headers','directory-listing','hidden-files','backup-config-files','traversal',
    'script-mapping','methods','request-size','proxy-fixed-destination','forwarded-headers','upstream-errors',
    'uploads-denied','session-cookie-flags','admin-acl','tls12','tls13','rate-limit','browser-policy',
    'cors-preflight','cors-rejection','cors-no-origin','api-no-store','management-denial','sourcemap-denial',
    'cookie-scope','policy-toggle-syntax','policy-toggle-isolation']]
SPA_CHECKS=['spa:'+name for name in [
    'configuration','canonical-http','static-fallback','rest-routing','storage-routing','forwarded-headers',
    'cache-isolation','guard-precedence','websocket-tunnel','websocket-origin','policy-toggles','missing-index',
    'upload-large-body','upload-total-limit','upload-default-limit','stylesheet-assets','style-policy','javascript-module-assets']]
SITE_CHECKS=['site:'+name for name in [
    'same-origin-port','virtualhost-backends','external-origin-isolation','wildcard-boundaries',
    'dynamic-csp-host','public-api-isolation','public-api-credentials','websocket-api-independence',
    'originless-websocket-option','site-limit-isolation','common-policy-unchanged']]

def run_site_profiles(binary,runtime,metadata,target,root,check,done):
    runtime,binary,root=Path(runtime),Path(binary),Path(root)
    for name,digest in metadata['configuration_sha256'].items():
        check(hashlib.sha256((runtime/name).read_bytes()).hexdigest()==digest,'Packaged file changed: '+name)
    mapping=json.loads((runtime/'security/kisa-2026.json').read_text(encoding='utf-8'))
    check(mapping['control_count']==26 and not mapping['certification_claim'] and len(mapping['controls'])==26,'KISA scope missing')
    done('profile:package-integrity')
    policies={p.relative_to(runtime/'conf').as_posix() for p in (runtime/'conf/policies').rglob('*.conf')}
    check(len(policies)==38,'Expected 38 separate policy files')
    check({p.relative_to(runtime/'conf').as_posix() for p in (runtime/'conf').rglob('*') if p.is_file()}==
          policies|{'nginx.conf','mime.types','site.conf'},'Operational conf contains sample/legacy files')
    for name in ['nginx.conf']+sorted(policies):
        text=(runtime/'conf'/name).read_text(encoding='utf-8')
        check(not any(v in text for v in ['example.test','edoc.','proxy_pass','wss://']),
              'Site values leaked into '+name)
    check(not (runtime/'backend').exists() and not (runtime/'prompts').exists(),'Reference examples leaked into runtime')
    done('profile:policy-layout')
    servers=[]
    for role in ['alpha','storage','beta']:
        server=FixtureServer(('127.0.0.1',0),RouteBackend);server.role=role
        threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)
    def port():
        with socket.socket() as sock: sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
    ports=set()
    while len(ports)<2:ports.add(port())
    http_port,https_port=sorted(ports)
    context=ssl._create_unverified_context()
    process=None
    try:
        with tempfile.TemporaryDirectory(prefix='forge-sites-') as temp:
            # Windows runners can expose TEMP through an 8.3 alias such as RUNNER~1.
            # NGINX rejects short-name file paths; normalize before rendering absolute roots.
            base=Path(temp).resolve();shutil.copytree(str(runtime/'conf'),str(base/'conf'));shutil.copytree(str(runtime/'html'),str(base/'html'))
            (base/'logs').mkdir();(base/'temp').mkdir()
            roots={}
            for host in ['alpha.test','beta.test']:
                site=base/'sites'/host.replace('.test','');site.mkdir(parents=True);roots[host]=site
                (site/'index.html').write_bytes(('SPA '+host+'\n').encode())
                (site/'app.css').write_bytes(b'.forge { color: rgb(12,34,56); }\n')
                (site/'app.mjs').write_bytes(b'export const ready="MODULE READY";\n')
                (site/'app.js').write_bytes(b'PUBLIC SCRIPT\n')
                (site/'listing').mkdir();(site/'listing/file.txt').write_bytes(b'FILE')
                (site/'uploads').mkdir();(site/'uploads/file.txt').write_bytes(b'PRIVATE FIXTURE')
                for name in ['.env','backup.bak','nginx.conf','secret.key','payload.php','payload.exe','payload.dll','bundle.js.map']:
                    (site/name).write_bytes(b'PRIVATE FIXTURE')
            (base/'outside.txt').write_bytes(b'OUTSIDE SECRET')
            if target.startswith('linux-'):(roots['alpha.test']/'linked.txt').symlink_to(base/'outside.txt')
            main='daemon off;\nmaster_process off;\n'+(base/'conf/nginx.conf').read_text(encoding='utf-8')
            (base/'conf/nginx.conf').write_text(main,encoding='utf-8')
            specs=[]
            for host,backend in [('alpha.test',servers[0]),('beta.test',servers[2])]:
                specs.append(dict(host=host,cert=root/'tests/fixtures/cert.pem',key=root/'tests/fixtures/key.pem',root=roots[host],
                    spring='127.0.0.1:'+str(backend.server_port),storage='127.0.0.1:'+str(servers[1].server_port),
                    http_listen='127.0.0.1:'+str(http_port),https_listen='127.0.0.1:'+str(https_port),https_auth_port=':'+str(https_port),
                    body='1g' if host=='alpha.test' else '5m'))
            template=render_sites(specs,[('beta.test','https://portal.partner.test'),('beta.test','https://*.trusted.test')])
            site_path=base/'conf/site.conf';site_path.write_bytes(template.encode('utf-8'))
            policy_bytes={name:(base/'conf'/name).read_bytes() for name in policies}
            check(all(template.count(spec['host'])==1 for spec in specs),'Domain must appear exactly once per site')
            command=[str(binary),'-p',base.resolve().as_posix()+'/','-c','conf/nginx.conf']
            def syntax(text=None):
                if text is not None:site_path.write_bytes(text.encode('utf-8'))
                result=subprocess.run(command+['-t'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=30)
                check(result.returncode==0,result.stdout)
            syntax();done('profile:configuration');done('spa:configuration')
            includes=re.findall(r'^    include (policies/[^;]+);',template,re.M)
            for name in sorted(set(includes)):
                syntax(template.replace('include '+name+';','# include '+name+';'))
            for text in [re.sub(r'^( +)include policies/[^;]+;',r'\1# policy OFF',template,flags=re.M),
                         template.replace('set $site_cors_mode restricted;','set $site_cors_mode public;'),
                         template.replace('set $site_ws_mode restricted;','set $site_ws_mode public;'),
                         template.replace('set $site_allow_originless_ws 0;','set $site_allow_originless_ws 1;')]:syntax(text)
            syntax(template);done('profile:policy-toggle-syntax')
            log=open(str(base/'process.log'),'wb')
            def stop():
                if process is not None and process.poll() is None:
                    try:
                        subprocess.run(command+['-s','quit'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
                        process.wait(timeout=5)
                    except (OSError,subprocess.TimeoutExpired):process.kill();process.wait(timeout=10)
            def start(text):
                nonlocal process
                syntax(text)
                process=subprocess.Popen(command,stdout=log,stderr=log,**({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
                for _ in range(100):
                    check(process.poll() is None,'Server exited: '+(base/'process.log').read_text())
                    try:
                        with socket.create_connection(('127.0.0.1',http_port),timeout=.2):return
                    except OSError:time.sleep(.1)
                raise AssertionError('Server did not start')
            def origin(host):return 'https://'+host+':'+str(https_port)
            def request(host,path='/',method='GET',headers=None,secure=True,body=None,paced=True,tls=None):
                if paced:time.sleep(.12)
                connection=http.client.HTTPConnection('127.0.0.1',https_port if secure else http_port,timeout=12)
                if secure:connection.sock=(tls or context).wrap_socket(socket.create_connection(('127.0.0.1',https_port),timeout=12),server_hostname=host)
                values={'Host':host+':'+str(https_port if secure else http_port),'Connection':'close'};values.update(headers or {})
                connection.request(method,path,body=body,headers=values)
                response=connection.getresponse();data=response.read();status=response.status;hdr=response.headers;connection.close()
                return status,hdr,data
            def websocket(host='alpha.test',value='self',echo=False):
                time.sleep(.12)
                sock=context.wrap_socket(socket.create_connection(('127.0.0.1',https_port),timeout=10),server_hostname=host);sock.settimeout(10)
                lines=['GET /process_file/echo?job=7 HTTP/1.1','Host: '+host+':'+str(https_port),'Upgrade: websocket',
                       'Connection: Upgrade','Sec-WebSocket-Version: 13','Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==',
                       'X-Forwarded-For: 203.0.113.55','Forwarded: for=203.0.113.55']
                if value is not None:lines.append('Origin: '+(origin(host) if value=='self' else value))
                sock.sendall(('\r\n'.join(lines)+'\r\n\r\n').encode());head=b''
                while b'\r\n\r\n' not in head:
                    head+=receive(sock,1);check(len(head)<16384,'Oversize WS headers')
                status=int(head.split(b' ',2)[1]);result=None
                if status==101 and echo:
                    check(b'Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=' in head,'Bad WS handshake')
                    text=b'NGINXFORGE ECHO';mask=b'abcd';sock.sendall(b'\x81'+bytes([128|len(text)])+mask+bytes(b^mask[i%4] for i,b in enumerate(text)))
                    frame=receive(sock,2);length=frame[1]&127
                    if length==126:length=struct.unpack('!H',receive(sock,2))[0]
                    check(frame[0]==0x81 and not frame[1]&128,'Bad WS frame')
                    result=json.loads(receive(sock,length).decode());check(result['message']==text.decode(),'WS payload changed')
                sock.close();return status,result
            def section_change(text,host,change):
                site_id='site_'+str([spec['host'] for spec in specs].index(host)+1)
                marker='# BEGIN SITE: '+site_id+'\n';before,part=text.split(marker,1);block,after=part.split('# END SITE: '+site_id,1)
                return before+marker+change(block)+'# END SITE: '+site_id+after
            def denied(path,allow_spa=False):
                status,headers,data=request('alpha.test',path)
                safe_status=status in (400,403,404) or (allow_spa and status==200 and data==b'SPA alpha.test\n')
                check(safe_status and b'PRIVATE FIXTURE' not in data and b'OUTSIDE SECRET' not in data,'Forbidden file served: '+path)
            try:
                start(template)
                status,headers,data=request('alpha.test','/screen?x=1',secure=False)
                check(status==308 and headers['Location']==origin('alpha.test')+'/screen?x=1','Redirect failed');done('profile:http-redirect')
                try:request('unknown.invalid',secure=False)
                except http.client.RemoteDisconnected:pass
                else:raise AssertionError('Unknown Host accepted')
                done('profile:unknown-host')
                try:request('alpha.test',headers={'Host':'unknown.invalid'})
                except http.client.RemoteDisconnected:pass
                else:raise AssertionError('Known SNI accepted unknown HTTP Host')
                try:
                    with socket.create_connection(('127.0.0.1',https_port),timeout=10) as raw:
                        with context.wrap_socket(raw,server_hostname='unknown.invalid'):pass
                except ssl.SSLError:pass
                else:raise AssertionError('Unknown SNI accepted')
                done('profile:unknown-sni')
                for host in roots:
                    status,headers,data=request(host,'/index.html')
                    check(status==200 and data==('SPA '+host+'\n').encode(),'Wrong virtualhost root for '+host+': status='+str(status)+' body='+repr(data[:200])+' root='+str(roots[host])+' log='+(base/'logs/error.log').read_text(encoding='utf-8',errors='replace')[-2000:])
                    check(('wss://'+host+':'+str(https_port)) in headers['Content-Security-Policy'],'CSP used another host/port')
                done('profile:static-https');done('site:dynamic-csp-host')
                for path in ['/index.html','/secret.key','/api/fail']:
                    status,headers,data=request('alpha.test',path)
                    for key,value in [('X-Content-Type-Options','nosniff'),('X-Frame-Options','SAMEORIGIN'),
                                      ('Referrer-Policy','strict-origin-when-cross-origin'),('Strict-Transport-Security','max-age=31536000')]:
                        check(headers.get_all(key)==[value],'Missing/duplicate security header '+key)
                    check(headers.get('Server') is None and headers.get('X-Powered-By') is None,'Identity leaked')
                done('profile:security-headers')
                status,headers,data=request('alpha.test','/listing/');check(status==403 and b'file.txt' not in data,'Directory listed');done('profile:directory-listing')
                denied('/.env');done('profile:hidden-files')
                for path in ['/backup.bak','/nginx.conf','/deep/secret.key']:denied(path)
                done('profile:backup-config-files')
                for path in ['/../outside.txt','/%2e%2e/outside.txt','/..%2foutside.txt']:denied(path)
                done('profile:traversal')
                for path in ['/payload.php','/payload.exe','/payload.dll','/api/payload.php']:denied(path)
                done('profile:script-mapping')
                denied('/uploads/file.txt');done('profile:uploads-denied')
                for path in ['/actuator/env','/swagger-ui/index.html','/v3/api-docs']:denied(path)
                done('profile:management-denial');denied('/bundle.js.map');done('profile:sourcemap-denial');done('spa:guard-precedence')
                for method in ['POST','PUT','TRACE','PROPFIND','CONNECT']:
                    check(request('alpha.test','/index.html',method=method)[0] in (400,405),'Static method accepted')
                done('profile:methods')
                for path in ['/api','/storagewiz','/process_file']:
                    status,headers,data=request('alpha.test',path+'?x=1',method='POST');check(status==308 and headers['Location'].endswith(path+'/?x=1'),'Bare prefix fell into SPA')
                done('spa:canonical-http')
                status,headers,data=request('alpha.test','/documents/123');check(status==200 and data==b'SPA alpha.test\n','SPA fallback failed');done('spa:static-fallback')
                status,headers,data=request('alpha.test','/app.css');check(status==200 and data.startswith(b'.forge') and headers.get_content_type()=='text/css' and headers['X-Content-Type-Options']=='nosniff','CSS failed');done('spa:stylesheet-assets')
                csp=headers.get_all('Content-Security-Policy');check(len(csp)==1 and "style-src 'self' 'unsafe-inline'" in csp[0] and "script-src 'self';" in csp[0],'CSP boundaries failed');done('spa:style-policy');done('profile:browser-policy')
                status,headers,data=request('alpha.test','/app.mjs');check(status==200 and b'MODULE READY' in data and headers.get_content_type()=='application/javascript','Module MIME failed');done('spa:javascript-module-assets')
                for host,role in [('alpha.test','alpha'),('beta.test','beta')]:
                    status,headers,data=request(host,'/api/items?x=1');seen=json.loads(data.decode());check(status==200 and seen['role']==role and seen['path']=='/api/items?x=1','Wrong backend')
                done('profile:proxy-fixed-destination');done('site:virtualhost-backends')
                for method in ['GET','HEAD','POST','PUT','PATCH','DELETE','OPTIONS']:
                    check(request('alpha.test','/api/items',method=method)[0]==(204 if method=='OPTIONS' else 200),'REST method rejected')
                done('spa:rest-routing')
                status,headers,data=request('alpha.test','/storagewiz/items?x=2',method='POST');seen=json.loads(data.decode());check(status==200 and seen['role']=='storage' and seen['path']=='/storagewiz/items?x=2','Storage route failed');done('spa:storage-routing')
                status,headers,data=request('alpha.test','/process_file/status?x=3',method='POST',headers={'X-Forwarded-For':'203.0.113.55','X-Real-IP':'203.0.113.55','Forwarded':'for=203.0.113.55'})
                seen=json.loads(data.decode())['headers'];check(status==200 and seen['host']=='alpha.test' and seen['x-forwarded-for']=='127.0.0.1' and seen['x-real-ip']=='127.0.0.1' and seen['x-forwarded-proto']=='https' and 'forwarded' not in seen,'Forwarded headers trusted');done('profile:forwarded-headers');done('spa:forwarded-headers')
                for path in ['/api/items','/%61pi/items','/storagewiz/items','/process_file/status','/api/fail']:
                    status,headers,data=request('alpha.test',path);check(headers.get_all('Cache-Control')==['no-store'] and headers.get('Expires') is None,'API cache leaked')
                    if path.endswith('fail'):check(status==500 and b'SENSITIVE' not in data,'Backend error leaked')
                done('profile:api-no-store');done('spa:cache-isolation');done('profile:upstream-errors')
                status,headers,data=request('alpha.test','/api/items');cookies=headers.get_all('Set-Cookie')
                for name in ['JSESSIONID','SESSION']:
                    value=next(x.lower() for x in cookies if x.startswith(name+'='));check(all(f in value for f in ['secure','httponly','samesite=lax']),'Session flags missing')
                done('profile:session-cookie-flags');check('httponly' not in next(x.lower() for x in cookies if x.startswith('XSRF-TOKEN=')),'CSRF token became unreadable');done('profile:cookie-scope')
                check(request('alpha.test','/app.css')[1].get('Cache-Control') is None,'Static cache contaminated')
                status,headers,data=request('alpha.test','/api/items',headers={'Origin':origin('alpha.test')});check(status==200 and headers.get_all('Access-Control-Allow-Origin')==[origin('alpha.test')] and headers['Access-Control-Allow-Credentials']=='true','Same origin failed')
                check(request('alpha.test','/api/items',headers={'Origin':'https://alpha.test'})[0]==403,'Non-default Origin port was ignored')
                check(request('alpha.test','/api/items',headers={'Host':'alpha.test:443','Origin':'https://alpha.test'})[0]==200,'Default HTTPS port was not normalized');done('site:same-origin-port')
                status,headers,data=request('alpha.test','/api/items',method='OPTIONS',headers={'Origin':origin('alpha.test'),'Access-Control-Request-Method':'PATCH'});check(status==204 and 'PATCH' in headers['Access-Control-Allow-Methods'],'Preflight failed');done('profile:cors-preflight')
                for value in ['https://evil.invalid','null','https://alpha.test.evil.invalid']:
                    check(request('alpha.test','/api/items',headers={'Origin':value})[0]==403,'Unapproved origin accepted')
                check(request('alpha.test','/api/items',method='OPTIONS',headers={'Origin':origin('alpha.test'),'Access-Control-Request-Method':'TRACE'})[0]==403,'Preflight method bypass');done('profile:cors-rejection')
                status,headers,data=request('alpha.test','/api/items');check(status==200 and headers.get('Access-Control-Allow-Origin') is None and headers.get('Vary')=='Origin','Originless API rejected/reflected or Vary missing');done('profile:cors-no-origin')
                for host,expected in [('alpha.test',403),('beta.test',200)]:
                    status,headers,data=request(host,'/api/items',headers={'Origin':'https://portal.partner.test'});check(status==expected,'External allowance crossed vhosts')
                    if expected==200:check(headers.get_all('Access-Control-Allow-Origin')==['https://portal.partner.test'],'Origin reflected without validation')
                done('site:external-origin-isolation')
                for value,expected in [('https://one.trusted.test',200),('https://a.b.trusted.test',200),('https://trusted.test',403),('https://one.trusted.test.evil.invalid',403),('http://one.trusted.test',403),('https://one.trusted.test:8443',403)]:
                    check(request('beta.test','/api/items',headers={'Origin':value})[0]==expected,'Wildcard boundary failed: '+value)
                done('site:wildcard-boundaries')
                status,seen=websocket(echo=True);check(status==101 and seen['role']=='alpha' and seen['path']=='/process_file/echo?job=7' and seen['headers']['x-forwarded-for']=='127.0.0.1' and 'forwarded' not in seen['headers'],'WS tunnel/header failed');done('spa:websocket-tunnel')
                for value in ['https://evil.invalid','null',None]:check(websocket(value=value)[0]==403,'WS origin accepted')
                check(websocket('beta.test','https://portal.partner.test')[0]==101 and websocket('alpha.test','https://portal.partner.test')[0]==403,'WS external origins crossed sites');done('spa:websocket-origin')
                payload=b'--forge\r\nContent-Disposition: form-data; name="file"; filename="file.bin"\r\n\r\n'+b'x'*(6*1024*1024)+b'\r\n--forge--\r\n'
                status,headers,data=request('alpha.test','/api/upload',method='POST',body=payload,headers={'Content-Type':'multipart/form-data; boundary=forge'});check(status==200 and json.loads(data.decode())['body_bytes']==len(payload),'Large multipart did not reach backend');done('spa:upload-large-body')
                check(request('alpha.test','/api/upload',method='POST',headers={'Content-Length':str(1024**3+1)})[0]==413,'1 GiB cap failed');done('spa:upload-total-limit');done('profile:request-size')
                check(request('beta.test','/api/upload',method='POST',headers={'Content-Length':str(len(payload))})[0]==413,'Per-site body cap crossed vhosts');done('site:site-limit-isolation')
                for version,name in [('TLSv1.2','tls12'),('TLSv1.3','tls13')]:
                    ctx=ssl._create_unverified_context()
                    if version=='TLSv1.2':ctx.options|=getattr(ssl,'OP_NO_TLSv1_3',0)
                    else:ctx.options|=ssl.OP_NO_TLSv1|ssl.OP_NO_TLSv1_1|ssl.OP_NO_TLSv1_2
                    check(request('alpha.test','/index.html',tls=ctx)[0]==200,'TLS version failed');done('profile:'+name)
                if target.startswith('linux-'):
                    # try_files skips a blocked symlink and can serve the public SPA fallback.
                    # Accept only that exact public body or a denial, never the linked secret.
                    denied('/linked.txt',allow_spa=True);done('profile:linux-symlink-denial')
                else:
                    link_policy=policy_bytes['policies/server/symlinks.conf']
                    check(b'Windows' in link_policy and not any(line.strip().startswith(b'disable_symlinks ') for line in link_policy.splitlines()),'Windows claims native link protection');done('profile:windows-link-review-documented')
                limited=False
                for _ in range(100):
                    if request('alpha.test','/index.html',paced=False)[0]==429:limited=True;break
                check(limited,'IP rate limit absent');done('profile:rate-limit')

                # All changes below touch only the alpha section of site.conf.
                stop()
                def public_options(block):
                    block=block.replace('set $site_cors_mode restricted;','set $site_cors_mode public;')
                    block=re.sub(r'    set \$site_csp .*?;\n','    set $site_csp "";\n',block)
                    block=block.replace('    limit_req zone=site_requests burst=20 nodelay;','    # limit_req zone=site_requests burst=20 nodelay;')
                    block=block.replace('    proxy_intercept_errors on;','    proxy_intercept_errors off;')
                    for line in ['proxy_cookie_flags JSESSIONID secure httponly samesite=lax;','include policies/server/private-cache-spa.conf;']:
                        block=block.replace('    '+line,'    # '+line)
                    return block.replace('    location /api/ {','    location /api/admin/ { allow 192.0.2.123; deny all; proxy_pass http://'+specs[0]['spring']+'; }\n    location /api/ {')
                public=section_change(template,'alpha.test',public_options);start(public)
                for host,expected in [('alpha.test',200),('beta.test',403)]:
                    status,headers,data=request(host,'/api/items',headers={'Origin':'https://new.external.test'});check(status==expected,'Public API option crossed vhosts')
                    if expected==200:check(headers.get_all('Access-Control-Allow-Origin')==['*'] and headers.get('Access-Control-Allow-Credentials') is None,'Wildcard credentials conflict')
                done('site:public-api-isolation');done('site:public-api-credentials')
                check(websocket(value='https://new.external.test')[0]==403,'Public API silently opened WS')
                status,headers,data=request('alpha.test','/api/items');check(headers.get('Content-Security-Policy') is None and headers['X-Content-Type-Options']=='nosniff' and headers['Cache-Control']=='public, max-age=86400','Per-site CSP/cache option failed')
                check('httponly' not in next(x.lower() for x in headers.get_all('Set-Cookie') if x.startswith('JSESSIONID=')),'Per-site cookie option failed')
                check(request('beta.test','/api/items')[1].get('Content-Security-Policy') is not None,'Other site CSP changed')
                check(request('alpha.test','/api/fail')[0]==500 and b'SENSITIVE' in request('alpha.test','/api/fail')[2],'Error option failed')
                check(request('alpha.test','/api/admin/task')[0]==403 and request('beta.test','/api/admin/task')[0]==200,'Site administrator ACL crossed vhosts');done('profile:admin-acl')
                for _ in range(40):check(request('alpha.test','/index.html',paced=False)[0]==200,'Site rate OFF did not apply')
                done('profile:policy-toggle-isolation')
                stop()
                ws_public=section_change(template,'alpha.test',lambda b:b.replace('set $site_ws_mode restricted;','set $site_ws_mode public;').replace('set $site_allow_originless_ws 0;','set $site_allow_originless_ws 1;').replace('client_max_body_size 1g;','client_max_body_size 5m;'))
                start(ws_public)
                check(websocket(value='https://new.external.test')[0]==101 and request('alpha.test','/api/items',headers={'Origin':'https://new.external.test'})[0]==403,'WS/API public options not independent')
                check(websocket('beta.test','https://new.external.test')[0]==403,'WS public option crossed vhosts');done('site:websocket-api-independence')
                check(websocket(value=None)[0]==101 and websocket('beta.test',None)[0]==403,'Originless WS option crossed vhosts');done('site:originless-websocket-option');done('spa:policy-toggles')
                check(request('alpha.test','/api/upload',method='POST',headers={'Content-Length':str(len(payload))})[0]==413,'Site-only 5 MiB option failed');done('spa:upload-default-limit')
                (roots['alpha.test']/'index.html').unlink();check(request('alpha.test','/documents/123')[0]==404,'Missing index loop');done('spa:missing-index')
                stop()
                renamed=template.replace('server_name beta.test;','server_name gamma.test;')
                start(renamed)
                status,headers,data=request('gamma.test','/index.html')
                check(status==200 and data==b'SPA beta.test\n' and ('wss://gamma.test:'+str(https_port)) in headers['Content-Security-Policy'],'One-line domain change did not update CSP/routing')
                check(request('gamma.test','/api/items',headers={'Origin':origin('gamma.test')})[0]==200,'One-line domain change did not update same-origin API')
                check(request('gamma.test','/api/items',headers={'Origin':'https://portal.partner.test'})[0]==200,'Domain change broke site-ID external allowance')
                check(websocket('gamma.test')[0]==101,'One-line domain change did not update WebSocket')
                status,headers,data=request('gamma.test','/screen',secure=False)
                check(status==308 and headers['Location']==origin('gamma.test')+'/screen','One-line domain change did not update redirect')
                check(all((base/'conf'/name).read_bytes()==data for name,data in policy_bytes.items()),'Site changes mutated split policies');done('site:common-policy-unchanged')
            finally:stop();log.close()
    finally:
        for server in servers:server.shutdown();server.server_close()
