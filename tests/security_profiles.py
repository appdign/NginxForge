"""Exercise the configurations shipped inside the real release package."""
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
import subprocess
import tempfile
import threading
import time
from spa_profiles import SPA_CHECKS, run_spa_profiles

COMMON_CHECKS = ['profile:' + name for name in [
    'package-integrity', 'configuration', 'http-redirect', 'unknown-host', 'unknown-sni',
    'static-https', 'security-headers', 'directory-listing', 'hidden-files',
    'backup-config-files', 'traversal', 'script-mapping', 'methods', 'request-size',
    'proxy-fixed-destination', 'forwarded-headers', 'upstream-errors', 'uploads-denied',
    'session-cookie-flags', 'admin-acl', 'tls12', 'tls13', 'rate-limit',
    'browser-policy', 'cors-preflight', 'cors-rejection', 'cors-no-origin',
    'api-no-store', 'management-denial', 'sourcemap-denial', 'cookie-scope', 'policy-layout',
    'policy-toggle-syntax', 'policy-toggle-isolation']] + SPA_CHECKS

def platform_checks(target):
    return ['profile:linux-symlink-denial'] if target.startswith('linux-') else ['profile:windows-link-review-documented']

class Backend(BaseHTTPRequestHandler):
    server_version = 'SecretBackend/9'
    sys_version = ''
    def do_GET(self):
        data = (b'database password leaked in upstream error' if self.path == '/upstream-error'
                else json.dumps(dict(self.headers.items())).encode())
        self.send_response(500 if self.path == '/upstream-error' else 200)
        self.send_header('X-Powered-By', 'SecretRuntime/1')
        self.send_header('Set-Cookie', 'JSESSIONID=fixture; Path=/')
        self.send_header('Set-Cookie', 'SESSION=fixture; Path=/')
        self.send_header('Set-Cookie', 'XSRF-TOKEN=fixture; Path=/')
        # Edge ownership must replace these, rather than appending conflicting policies.
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.send_header('Expires', 'Thu, 01 Jan 2037 00:00:00 GMT')
        self.send_header('Content-Security-Policy', "default-src *")
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args): pass

def run_profiles(binary, runtime, metadata, target, root, check, done):
    runtime, binary, root = Path(runtime), Path(binary), Path(root)
    for name,digest in metadata['configuration_sha256'].items():
        check(hashlib.sha256((runtime/name).read_bytes()).hexdigest() == digest, 'Packaged policy was modified: '+name)
    mapping = json.loads((runtime/'security/kisa-2026.json').read_text(encoding='utf-8'))
    check(mapping['control_count']==26 and not mapping['certification_claim'], 'KISA matrix must disclose scope')
    check(len(mapping['controls'])==26, 'Incomplete KISA applicability matrix')
    done('profile:package-integrity')
    config_files={p.relative_to(runtime/'conf').as_posix() for p in (runtime/'conf').rglob('*') if p.is_file()}
    policy_files={p.relative_to(runtime/'conf').as_posix() for p in (runtime/'conf/policies').rglob('*.conf')}
    source_policies={p.relative_to(root/'config/runtime').as_posix() for p in (root/'config/runtime/policies').rglob('*.conf')}
    check(policy_files==source_policies and len(policy_files)==37, 'Missing or unexpected policy files')
    check(config_files=={'nginx.conf','mime.types','conf.d/site.conf.example','conf.d/README.md',
                         'examples/spa-api-websocket.conf.example','maps/spa-api-websocket.conf'}|policy_files,
          'Unexpected configuration files: '+repr(config_files))
    site_template=(runtime/'conf/conf.d/site.conf.example').read_text(encoding='utf-8')
    main_template=(runtime/'conf/nginx.conf').read_text(encoding='utf-8')
    spa_template=(runtime/'conf/examples/spa-api-websocket.conf.example').read_text(encoding='utf-8')
    base_policies=set(re.findall(r'^\s*include (policies/[^;]+);',main_template+'\n'+site_template,re.M))
    selected=base_policies|set(re.findall(r'^\s*include (policies/[^;]+);',spa_template,re.M))
    check(selected==policy_files, 'Policies must have explicit ON switches, without wildcard loading')
    done('profile:policy-layout')
    def port():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            return sock.getsockname()[1]
    ports = set()
    while len(ports)<3: ports.add(port())
    http_port, https_port, preview_port = sorted(ports)
    backend = HTTPServer(('127.0.0.1',0),Backend)
    threading.Thread(target=backend.serve_forever,daemon=True).start()
    process = None
    context = ssl._create_unverified_context()
    with tempfile.TemporaryDirectory(prefix='forge-profiles-') as temp:
        base = Path(temp)
        shutil.copytree(str(runtime/'conf'),str(base/'conf'))
        shutil.copytree(str(runtime/'html'),str(base/'html'))
        (base/'logs').mkdir(); (base/'temp').mkdir()
        site = base/'sites/example.test/public'
        site.mkdir(parents=True)
        (site/'index.html').write_bytes(b'PUBLIC SITE\n')
        (site/'listing').mkdir(); (site/'listing/file.txt').write_bytes(b'NOT A DIRECTORY INDEX')
        (site/'uploads').mkdir(); (site/'uploads/leak.txt').write_bytes(b'UPLOAD MUST NOT BE PUBLIC')
        for name in ['.env','backup.bak','nginx.conf','secret.key','payload.php','payload.cgi','payload.shtml','payload.exe','payload.dll']:
            (site/name).write_bytes(b'PRIVATE FIXTURE MUST NOT BE SERVED')
        (base/'outside-secret.txt').write_bytes(b'OUTSIDE WEB ROOT SECRET')
        if target.startswith('linux-'):
            (site/'linked.txt').symlink_to(base/'outside-secret.txt')
        config = (base/'conf/nginx.conf').read_text(encoding='utf-8')
        config='daemon off;\nmaster_process off;\n'+config.replace('127.0.0.1:8080','127.0.0.1:'+str(preview_port))
        (base/'conf/nginx.conf').write_text(config,encoding='utf-8')
        # Activate the shipped switch catalog as-is. Only ports/backend/test CIDR differ.
        text=site_template.replace('listen 80','listen 127.0.0.1:'+str(http_port)).replace('listen 443','listen 127.0.0.1:'+str(https_port))
        text=text.replace('127.0.0.1:9000','127.0.0.1:'+str(backend.server_port))
        (base/'conf/conf.d/site.conf').write_text(text,encoding='utf-8')
        defaults=base/'conf/policies/http/default-listeners.conf'
        defaults.write_text(defaults.read_text(encoding='utf-8').replace('listen 80','listen 127.0.0.1:'+str(http_port))
                            .replace('listen 443','listen 127.0.0.1:'+str(https_port)),encoding='utf-8')
        admin=base/'conf/policies/server/admin-acl.conf'
        admin.write_text(admin.read_text(encoding='utf-8').replace('allow 127.0.0.1;','allow 192.0.2.123;'),encoding='utf-8')
        for domain in ['example.test','app.example.test']:
            dest=base/'conf/certs'/domain; dest.mkdir(parents=True)
            shutil.copy2(str(root/'tests/fixtures/cert.pem'),str(dest/'fullchain.pem'))
            shutil.copy2(str(root/'tests/fixtures/key.pem'),str(dest/'privkey.pem'))
        prefix=base.resolve().as_posix()+'/'
        command=[str(binary),'-p',prefix,'-c','conf/nginx.conf']
        result=subprocess.run(command+['-t'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=30)
        check(result.returncode==0,result.stdout)
        done('profile:configuration')
        def switched_off(source, policies):
            return '\n'.join('# '+line if any(line.lstrip().startswith('include '+name+';') for name in policies)
                             else line for line in source.splitlines())+'\n'
        try:
            # Each individual OFF switch and the combined OFF state must parse natively.
            for disabled in [{name} for name in sorted(base_policies)]+[base_policies]:
                (base/'conf/nginx.conf').write_text(switched_off(config,disabled),encoding='utf-8')
                (base/'conf/conf.d/site.conf').write_text(switched_off(text,disabled),encoding='utf-8')
                result=subprocess.run(command+['-t'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                      universal_newlines=True,timeout=30)
                check(result.returncode==0,'OFF '+repr(sorted(disabled))+': '+result.stdout)
        finally:
            (base/'conf/nginx.conf').write_text(config,encoding='utf-8')
            (base/'conf/conf.d/site.conf').write_text(text,encoding='utf-8')
        done('profile:policy-toggle-syntax')
        log=open(str(base/'process.log'),'wb')
        def request(host,path='/',method='GET',headers=None,https=True,paced=True):
            # Isolate functional cases from the real shipped 10 requests/s bucket.
            # The separate burst below stays unpaced and MUST demonstrate 429.
            if paced: time.sleep(.12)
            if https:
                # Preserve the reviewed domain as SNI while connecting only to loopback.
                raw=socket.create_connection(('127.0.0.1',https_port),timeout=10)
                sock=context.wrap_socket(raw,server_hostname=host)
                connection=http.client.HTTPConnection('127.0.0.1',https_port,timeout=10)
                connection.sock=sock
            else:
                connection=http.client.HTTPConnection('127.0.0.1',http_port,timeout=10)
            values={'Host':host,'Connection':'close'}
            values.update(headers or {})
            connection.request(method,path,headers=values)
            response=connection.getresponse(); data=response.read(); hdrs=response.headers
            status=response.status; connection.close()
            return status,hdrs,data
        def blocked(path):
            status,headers,data=request('example.test',path)
            check(status in (400,403,404), 'Forbidden resource response: '+str((path,status,data)))
            check(b'PRIVATE FIXTURE' not in data and b'OUTSIDE WEB ROOT' not in data and b'UPLOAD MUST' not in data,'Sensitive file served')
        def stop_server():
            if process is not None and process.poll() is None:
                try:
                    subprocess.run(command+['-s','quit'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
                    process.wait(timeout=10)
                except (subprocess.TimeoutExpired, OSError):
                    process.kill(); process.wait(timeout=10)
        def start_server():
            nonlocal process
            process=subprocess.Popen(command,stdout=log,stderr=log,
                **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
            for _ in range(100):
                check(process.poll() is None,'Profile server exited: '+(base/'process.log').read_text())
                try:
                    with socket.create_connection(('127.0.0.1',http_port),timeout=.2): return
                except OSError: time.sleep(.1)
            raise AssertionError('Profile server did not start')
        try:
            start_server()
            status,headers,data=request('example.test','/safe?x=1',https=False)
            check(status==308 and headers.get('Location')=='https://example.test/safe?x=1','HTTPS canonical redirect failed')
            done('profile:http-redirect')
            try: request('unknown.invalid',https=False)
            except http.client.RemoteDisconnected: pass
            else: raise AssertionError('Unknown HTTP host was accepted')
            done('profile:unknown-host')
            try:
                with socket.create_connection(('127.0.0.1',https_port),timeout=10) as raw:
                    with context.wrap_socket(raw,server_hostname='unknown.invalid'): pass
            except ssl.SSLError: pass
            else: raise AssertionError('Unknown SNI handshake was accepted')
            done('profile:unknown-sni')
            status,headers,data=request('example.test','/index.html')
            check(status==200 and data==b'PUBLIC SITE\n','Static domain failed')
            done('profile:static-https')
            for path in ['/index.html','/missing']:
                status,headers,data=request('example.test',path)
                for key,value in [('X-Content-Type-Options','nosniff'),('X-Frame-Options','SAMEORIGIN'),
                                  ('Referrer-Policy','strict-origin-when-cross-origin'),('Strict-Transport-Security','max-age=31536000')]:
                    check(headers.get_all(key)==[value], 'Missing/duplicate security header '+key)
                check(headers.get('Server') is None and headers.get('X-Powered-By') is None,'Identity header leaked')
            done('profile:security-headers')
            status,headers,data=request('example.test','/listing/')
            check(status==403 and b'file.txt' not in data,'Directory listing exposed')
            done('profile:directory-listing')
            blocked('/.env'); done('profile:hidden-files')
            for path in ['/backup.bak','/nginx.conf','/secret.key','/conf/nginx.conf']: blocked(path)
            done('profile:backup-config-files')
            for path in ['/%2e%2e/outside-secret.txt','/../outside-secret.txt']: blocked(path)
            done('profile:traversal')
            for path in ['/payload.php','/payload.cgi','/payload.shtml','/payload.exe','/payload.dll']: blocked(path)
            done('profile:script-mapping')
            for method in ['TRACE','PUT','PROPFIND','MKCOL','CONNECT']:
                status,headers,data=request('example.test','/index.html',method=method)
                check(status in (400,405), 'Disallowed method accepted: '+method)
            done('profile:methods')
            status,headers,data=request('app.example.test','/upload',method='POST',headers={'Content-Length':str(5*1024*1024+1)})
            check(status==413,'Oversize upload response: '+str((status,data)))
            done('profile:request-size')
            status,headers,data=request('app.example.test','/echo',headers={
                'X-Forwarded-For':'203.0.113.55','X-Real-IP':'203.0.113.55','Forwarded':'for=203.0.113.55'})
            check(status==200,'Fixed reverse proxy failed')
            check(headers.get('Server') is None and headers.get('X-Powered-By') is None,'Backend headers leaked')
            done('profile:proxy-fixed-destination')
            seen={k.lower():v for k,v in json.loads(data.decode()).items()}
            check(seen.get('x-forwarded-for')=='127.0.0.1' and seen.get('x-real-ip')=='127.0.0.1'
                  and seen.get('x-forwarded-proto')=='https' and seen.get('host')=='app.example.test'
                  and 'forwarded' not in seen,'Untrusted forwarding headers reached backend')
            done('profile:forwarded-headers')
            cookie=headers.get('Set-Cookie','').lower()
            check(all(flag in cookie for flag in ['secure','httponly','samesite=lax']),'Selected session-cookie flags failed')
            done('profile:session-cookie-flags')
            cookies=headers.get_all('Set-Cookie') or []
            session=next((item.lower() for item in cookies if item.startswith('SESSION=')), '')
            csrf=next((item.lower() for item in cookies if item.startswith('XSRF-TOKEN=')), '')
            check(all(flag in session for flag in ['secure','httponly','samesite=lax'])
                  and csrf and 'httponly' not in csrf,'Session flags leaked onto a JS-readable CSRF cookie')
            done('profile:cookie-scope')
            check(headers.get_all('Cache-Control')==['no-store'] and headers.get('Expires') is None,
                  'Private API cache policy leaked or duplicated upstream headers')
            done('profile:api-no-store')
            check(headers.get('Access-Control-Allow-Origin') is None
                  and headers.get('Access-Control-Allow-Credentials') is None,
                  'No-Origin request inherited a backend CORS grant')
            done('profile:cors-no-origin')
            status,headers,data=request('app.example.test','/upstream-error')
            check(status==500 and b'database password' not in data and b'could not be completed' in data,'Upstream error leaked or status changed')
            done('profile:upstream-errors')
            blocked('/uploads/leak.txt'); done('profile:uploads-denied')
            for path in ['/admin/','/api/admin/']:
                status,headers,data=request('app.example.test',path)
                check(status==403,'Management CIDR restriction failed: '+path)
            done('profile:admin-acl')
            csp="default-src 'self'; connect-src 'self' https://app.example.test; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'"
            for host,path,expected in [('example.test','/index.html',200),('example.test','/missing',404),
                                       ('app.example.test','/echo',200),('app.example.test','/upstream-error',500)]:
                status,headers,data=request(host,path,headers={'Origin':'https://portal.example.test'})
                check(status==expected and headers.get_all('Content-Security-Policy')==[csp]
                      and headers.get_all('Permissions-Policy')==['camera=(), microphone=(), geolocation=()']
                      and headers.get_all('X-Frame-Options')==['SAMEORIGIN']
                      and headers.get_all('Strict-Transport-Security')==['max-age=31536000'],
                      'Browser/identity policy missing or duplicated on success/error response')
                if host.startswith('app.'):
                    check(headers.get_all('Access-Control-Allow-Origin')==['https://portal.example.test']
                          and headers.get_all('Cache-Control')==['no-store'],
                          'API CORS/cache headers lost on error interception')
            done('profile:browser-policy')
            status,headers,data=request('app.example.test','/api/items',method='OPTIONS',headers={
                'Origin':'https://portal.example.test','Access-Control-Request-Method':'POST',
                'Access-Control-Request-Headers':'Content-Type, X-XSRF-TOKEN'})
            check(status==204 and not data
                  and headers.get_all('Access-Control-Allow-Origin')==['https://portal.example.test']
                  and headers.get_all('Access-Control-Allow-Credentials')==['true']
                  and headers.get('Access-Control-Allow-Methods')=='GET, HEAD, POST, OPTIONS'
                  and headers.get('Access-Control-Allow-Headers')=='Content-Type, Authorization, X-CSRF-TOKEN, X-XSRF-TOKEN'
                  and 'Origin' in ','.join(headers.get_all('Vary') or []), 'Reviewed CORS preflight failed')
            status,headers,data=request('app.example.test','/api/items',method='OPTIONS',headers={
                'Origin':'https://portal.example.test','Access-Control-Request-Method':'POST',
                'Access-Control-Request-Headers':'X-Arbitrary-Untrusted'})
            check('X-Arbitrary-Untrusted' not in headers.get('Access-Control-Allow-Headers',''),
                  'Arbitrary preflight headers were reflected')
            done('profile:cors-preflight')
            for origin in ['https://evil.invalid','https://portal.example.test.evil.invalid','null']:
                status,headers,data=request('app.example.test','/echo',headers={'Origin':origin})
                check(status==403 and headers.get('Access-Control-Allow-Origin') is None
                      and headers.get('Access-Control-Allow-Credentials') is None,'Unreviewed CORS origin accepted')
            status,headers,data=request('app.example.test','/api/items',method='OPTIONS',headers={
                'Origin':'https://portal.example.test','Access-Control-Request-Method':'PATCH'})
            check(status==403,'Unreviewed CORS preflight method accepted')
            done('profile:cors-rejection')
            for path in ['/actuator/env','/swagger-ui/index.html','/swagger-ui.html','/v3/api-docs','/h2-console/']:
                status,headers,data=request('app.example.test',path)
                check(status==404,'Public management/diagnostic path reached the backend: '+path)
            done('profile:management-denial')
            (site/'bundle.js.map').write_bytes(b'PRIVATE SOURCE MAP')
            status,headers,data=request('example.test','/bundle.js.map')
            check(status==404 and b'PRIVATE SOURCE MAP' not in data,'Source-map publishing guard failed')
            done('profile:sourcemap-denial')
            for version,name in [('TLSv1.2','tls12'),('TLSv1.3','tls13')]:
                client=ssl._create_unverified_context()
                if version=='TLSv1.2': client.options |= getattr(ssl,'OP_NO_TLSv1_3',0)
                else: client.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
                with socket.create_connection(('127.0.0.1',https_port),timeout=10) as raw:
                    with client.wrap_socket(raw,server_hostname='example.test') as tls:
                        check(tls.version()==version,'Profile TLS negotiation failed')
                done('profile:'+name)
            if target.startswith('linux-'):
                blocked('/linked.txt'); done('profile:linux-symlink-denial')
            else:
                policy=(runtime/'conf/policies/server/symlinks.conf').read_text()
                check('requires_windows_os_acl_review'==metadata['security_capabilities']['symlink_enforcement']
                      and not any(line.strip().startswith('disable_symlinks ') for line in policy.splitlines()),
                      'Windows must not claim native link restriction')
                done('profile:windows-link-review-documented')
            # Run last: consume this profile's token bucket and verify real 429 responses.
            limited=False
            for _ in range(100):
                status,headers,data=request('example.test','/index.html',paced=False)
                if status==429: limited=True; break
            check(limited,'Per-client request limit did not produce 429')
            done('profile:rate-limit')

            # Disable one shipped policy at a time; other policies must remain active.
            for name in ['csp','nosniff','cors','private-cache','session-cookies','admin-acl',
                         'generic-errors','identity','secret-files','request-rate']:
                stop_server()
                disabled={'policies/server/'+name+'.conf'}
                (base/'conf/conf.d/site.conf').write_text(switched_off(text,disabled),encoding='utf-8')
                start_server()
                path='/admin/' if name=='admin-acl' else '/upstream-error' if name=='generic-errors' else '/echo'
                origin='https://evil.invalid' if name=='cors' else 'https://portal.example.test'
                status,headers,data=request('app.example.test',path,headers={'Origin':origin})
                check(status==(500 if name=='generic-errors' else 200),'OFF policy changed routing: '+name)
                check(headers.get_all('X-Frame-Options')==['SAMEORIGIN']
                      and headers.get_all('Strict-Transport-Security')==['max-age=31536000'],
                      'Disabling one policy removed unrelated headers: '+name)
                check(headers.get_all('Content-Security-Policy')==["default-src *" if name=='csp' else csp],
                      'CSP toggle isolation failed: '+name)
                check(headers.get('X-Content-Type-Options')==(None if name=='nosniff' else 'nosniff'),
                      'MIME header toggle isolation failed: '+name)
                check(headers.get('Cache-Control')==('public, max-age=86400' if name=='private-cache' else 'no-store'),
                      'Cache toggle isolation failed: '+name)
                check(headers.get('Access-Control-Allow-Origin')==('*' if name=='cors' else origin),
                      'CORS toggle isolation failed: '+name)
                cookie=next(item.lower() for item in headers.get_all('Set-Cookie') if item.startswith('JSESSIONID='))
                check(('httponly' in cookie)==(name!='session-cookies'),'Cookie toggle isolation failed')
                check((headers.get('Server') is not None)==(name=='identity'),'Identity toggle isolation failed')
                check((b'database password' in data)==(name=='generic-errors'),'Error interception toggle failed')
                if name=='secret-files':
                    status,headers,data=request('example.test','/backup.bak')
                    check(status==200 and b'PRIVATE FIXTURE' in data,'File guard did not switch OFF')
                if name=='request-rate':
                    for _ in range(40):
                        status,headers,data=request('example.test','/index.html',paced=False)
                        check(status==200,'Rate limiting remained active after its switch was OFF')
            done('profile:policy-toggle-isolation')
        finally:
            stop_server()
            log.close()
            backend.shutdown(); backend.server_close()
    run_spa_profiles(binary,runtime,target,root,check,done)
