"""Exercise the configurations shipped inside the real release package."""
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time

COMMON_CHECKS = ['profile:' + name for name in [
    'package-integrity', 'configuration', 'http-redirect', 'unknown-host', 'unknown-sni',
    'static-https', 'security-headers', 'directory-listing', 'hidden-files',
    'backup-config-files', 'traversal', 'script-mapping', 'methods', 'request-size',
    'proxy-fixed-destination', 'forwarded-headers', 'upstream-errors', 'uploads-denied',
    'optional-cookie-flags', 'admin-acl', 'tls12', 'tls13', 'rate-limit']]

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
        cookie_line=next(line[2:] for line in (base/'conf/examples/optional-policies.conf.example').read_text().splitlines()
                         if line.startswith('# proxy_cookie_flags '))
        for template in ['00-default-deny.conf.example','example.test.static.conf.example','app.example.test.proxy.conf.example']:
            text=(base/'conf/examples'/template).read_text(encoding='utf-8')
            text=text.replace('listen 80','listen 127.0.0.1:'+str(http_port)).replace('listen 443','listen 127.0.0.1:'+str(https_port))
            text=text.replace('127.0.0.1:9000','127.0.0.1:'+str(backend.server_port))
            if template.startswith('app.'):
                admin=(base/'conf/examples/admin-location.conf.example').read_text().replace(
                    'allow 127.0.0.1;','allow 192.0.2.123;').replace('127.0.0.1:9000','127.0.0.1:'+str(backend.server_port))
                text=text.replace('    location / {',admin+'\n    location / {')
                text=text.replace('proxy_intercept_errors on;','proxy_intercept_errors on;\n        '+cookie_line)
            (base/'conf/conf.d'/template[:-8]).write_text(text,encoding='utf-8')
        for domain in ['example.test','app.example.test']:
            dest=base/'conf/certs'/domain; dest.mkdir(parents=True)
            shutil.copy2(str(root/'tests/fixtures/cert.pem'),str(dest/'fullchain.pem'))
            shutil.copy2(str(root/'tests/fixtures/key.pem'),str(dest/'privkey.pem'))
        prefix=base.resolve().as_posix()+'/'
        command=[str(binary),'-p',prefix,'-c','conf/nginx.conf']
        result=subprocess.run(command+['-t'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=30)
        check(result.returncode==0,result.stdout)
        done('profile:configuration')
        log=open(str(base/'process.log'),'wb')
        def request(host,path='/',method='GET',headers=None,https=True):
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
        try:
            process=subprocess.Popen(command,stdout=log,stderr=log,
                **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
            for _ in range(100):
                check(process.poll() is None,'Profile server exited: '+(base/'process.log').read_text())
                try:
                    with socket.create_connection(('127.0.0.1',http_port),timeout=.2): break
                except OSError: time.sleep(.1)
            else: raise AssertionError('Profile server did not start')
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
            check(status==413,'Oversize upload was not rejected')
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
            done('profile:optional-cookie-flags')
            status,headers,data=request('app.example.test','/upstream-error')
            check(status==500 and b'database password' not in data and b'could not be completed' in data,'Upstream error leaked or status changed')
            done('profile:upstream-errors')
            blocked('/uploads/leak.txt'); done('profile:uploads-denied')
            status,headers,data=request('app.example.test','/admin/')
            check(status==403,'Management CIDR restriction failed')
            done('profile:admin-acl')
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
                policy=(runtime/'conf/platform.conf').read_text()
                check('requires_windows_os_acl_review'==metadata['security_capabilities']['symlink_enforcement']
                      and not any(line.strip().startswith('disable_symlinks ') for line in policy.splitlines()),
                      'Windows must not claim native link restriction')
                done('profile:windows-link-review-documented')
            # Run last: consume this profile's token bucket and verify real 429 responses.
            limited=False
            for _ in range(100):
                status,headers,data=request('example.test','/index.html')
                if status==429: limited=True; break
            check(limited,'Per-client request limit did not produce 429')
            done('profile:rate-limit')
        finally:
            if process is not None and process.poll() is None:
                try:
                    subprocess.run(command+['-s','quit'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
                    process.wait(timeout=10)
                except Exception:
                    process.kill(); process.wait(timeout=10)
            log.close()
            backend.shutdown(); backend.server_close()
