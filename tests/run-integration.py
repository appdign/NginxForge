#!/usr/bin/env python3
"""Execute the same real HTTP/TLS/proxy suite on every required native OS/CPU."""
import argparse
import gzip
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client
import importlib.util
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load, sha256, write
from security_profiles import COMMON_CHECKS, platform_checks, run_profiles

spec = importlib.util.spec_from_file_location('unpack', str(ROOT / 'scripts/unpack-artifact.py'))
unpack_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(unpack_module)

REQUIRED_CHECKS = ['version', 'build-options', 'configuration', 'invalid-configuration',
                   'http2', 'tls12', 'tls13', 'runtime-config'] + [
    protocol + ':' + mode + ':' + operation
    for protocol in ['http', 'https'] for mode in ['clear', 'custom']
    for operation in ['static', 'head', '404', '500', 'proxy', 'proxy-error', 'gzip', 'rewrite']]

def required_checks(target):
    return REQUIRED_CHECKS + COMMON_CHECKS + platform_checks(target)

def check(condition, message):
    if not condition:
        raise AssertionError(message)

def os_identity(expected, arch):
    actual_arch = platform.machine().lower()
    check(actual_arch in ({'x86_64', 'amd64'} if arch == 'amd64' else {'aarch64', 'arm64'}), 'Native architecture mismatch')
    if expected == 'windows-2022':
        check(os.name == 'nt', 'Expected Windows')
        check(sys.getwindowsversion().build == 20348, 'Expected Windows Server 2022 build 20348')
        return dict(id='windows', version='2022', build=sys.getwindowsversion().build,
                    machine=actual_arch, scope='GitHub-hosted Windows Server 2022 runner')
    values = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value.strip('"')
    distro, version = expected.split('-', 1)
    check(values['ID'] == distro, 'Wrong Linux distribution: ' + str(values))
    check(values['VERSION_ID'] == version or distro == 'rocky' and values['VERSION_ID'].split('.')[0] == version,
          'Wrong Linux release: ' + str(values))
    return dict(id=values['ID'], version=values['VERSION_ID'], machine=actual_arch,
                scope='native userspace container on native GitHub runner; host kernel is shared')

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

class Backend(BaseHTTPRequestHandler):
    server_version = 'Backend/1'
    sys_version = ''
    def do_GET(self):
        self.send_response(503 if self.path == '/error' else 200)
        self.send_header('X-Powered-By', 'BackendRuntime/1')
        self.send_header('X-Backend', 'present')
        self.end_headers()
        self.wfile.write(b'backend response')
    def log_message(self, *args):
        pass

def execute(binary, *args):
    result = subprocess.run([str(binary)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True, timeout=30,
                            **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
    check(result.returncode == 0, result.stdout)
    return result.stdout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--os', required=True)
    parser.add_argument('--artifacts', default='build/artifacts')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    target_arch = args.target.rsplit('-', 1)[1]
    identity = os_identity(args.os, target_arch)
    plan = load(ROOT / 'build/plan.json')
    binary, metadata = unpack_module.unpack(args.artifacts, args.target, ROOT / 'build/runtime')
    check(metadata['plan_digest'] == plan['digest'], 'Wrong build plan')
    passed = []
    def done(name):
        passed.append(name)
        print('PASS ' + name, flush=True)
    check('nginx/' + plan['nginx']['version'] in execute(binary, '-v'), 'Wrong version')
    done('version')
    options = execute(binary, '-V')
    for required in ['--with-http_ssl_module', '--with-http_v2_module', '--with-pcre-jit', '--add-module=../headers-more']:
        check(required in options, 'Missing build option ' + required)
    done('build-options')
    # The distributed site.conf is a ready-to-personalize Windows deployment profile whose
    # certificate/root paths belong to the operator. Validate its complete policy wiring
    # with disposable fixture paths; never read customer certificates or bind production ports.
    packaged_conf=ROOT/'build/runtime/conf'
    packaged_site=(packaged_conf/'site.conf').read_text(encoding='utf-8')
    packaged_mime=(packaged_conf/'mime.types').read_text(encoding='utf-8')
    check('server_name edoc-dev.sogang.ac.kr;' in packaged_site and
          'set $site_embed_domain "*.sogang.ac.kr";' in packaged_site,
          'Requested default site/iframe values missing')
    check(packaged_site.count('script-src')==1 and
          "img-src 'self' blob:;" in packaged_site and
          "script-src 'self' 'wasm-unsafe-eval';" in packaged_site and
          "connect-src 'self' blob: wss://$host$site_origin_port;" in packaged_site,
          'Default CSP values are missing or duplicated')
    check('application/javascript js mjs;' in packaged_mime,
          'MJS module MIME mapping missing from the default package')
    with tempfile.TemporaryDirectory(prefix='nginxforge-runtime-config-') as temp:
        runtime_test=Path(temp).resolve()
        shutil.copytree(str(ROOT/'build/runtime/conf'),str(runtime_test/'conf'))
        shutil.copytree(str(ROOT/'build/runtime/html'),str(runtime_test/'html'))
        for directory in ['logs','temp']:(runtime_test/directory).mkdir()
        shutil.copy2(str(ROOT/'tests/fixtures/cert.pem'),str(runtime_test/'conf/cert.pem'))
        shutil.copy2(str(ROOT/'tests/fixtures/key.pem'),str(runtime_test/'conf/key.pem'))
        site_path=runtime_test/'conf/site.conf'
        site=site_path.read_text(encoding='utf-8')
        site=re.sub(r'(?m)^\s*ssl_certificate\s+.*?;',
                    '    ssl_certificate "'+(runtime_test/'conf/cert.pem').as_posix()+'";',site,count=1)
        site=re.sub(r'(?m)^\s*ssl_certificate_key\s+.*?;',
                    '    ssl_certificate_key "'+(runtime_test/'conf/key.pem').as_posix()+'";',site,count=1)
        site=re.sub(r'(?m)^\s*root\s+.*?;',
                    '    root "'+(runtime_test/'html').as_posix()+'";',site,count=1)
        http_test_port,https_test_port=free_port(),free_port()
        while https_test_port==http_test_port:https_test_port=free_port()
        site=site.replace('listen 80','listen 127.0.0.1:'+str(http_test_port))
        site=site.replace('listen 443 ssl','listen 127.0.0.1:'+str(https_test_port)+' ssl')
        check(len(re.findall(r'(?m)^\s*ssl_certificate\s+',site))==1 and
              len(re.findall(r'(?m)^\s*ssl_certificate_key\s+',site))==1 and
              len(re.findall(r'(?m)^\s*root\s+',site))==1 and
              site.count('listen 127.0.0.1:'+str(http_test_port))==2 and
              site.count('listen 127.0.0.1:'+str(https_test_port)+' ssl')==2,
              'Configured deployment paths could not be replaced safely')
        site_path.write_text(site,encoding='utf-8')
        runtime_prefix=runtime_test.as_posix()+'/'
        execute(binary,'-p',runtime_prefix,'-c','conf/nginx.conf','-t')
    done('runtime-config')
    backend = HTTPServer(('127.0.0.1', 0), Backend)
    thread = threading.Thread(target=backend.serve_forever, daemon=True)
    thread.start()
    process = None
    with tempfile.TemporaryDirectory(prefix='nginxforge-test-') as temp:
        base = Path(temp)
        for directory in ['conf', 'logs', 'html', 'temp']:
            (base / directory).mkdir()
        data = ('NginxForge static fixture. ' * 1024).encode()
        (base / 'html/data.txt').write_bytes(data)
        shutil.copy2(str(ROOT / 'tests/fixtures/cert.pem'), str(base / 'conf/cert.pem'))
        shutil.copy2(str(ROOT / 'tests/fixtures/key.pem'), str(base / 'conf/key.pem'))
        http_port, https_port = free_port(), free_port()
        config = '''daemon off;
master_process off;
worker_processes 1;
error_log logs/error.log info;
pid logs/nginx.pid;
pcre_jit on;
events { worker_connections 128; }
http {
    default_type text/plain;
    access_log off;
    server_tokens off;
    more_clear_headers Server X-Powered-By;
    gzip on;
    gzip_min_length 1;
    gzip_types text/plain;
    ssl_certificate cert.pem;
    ssl_certificate_key key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
'''
        for mode in ['clear', 'custom']:
            config += '''server {
    listen 127.0.0.1:%d;
    listen 127.0.0.1:%d ssl;
    http2 on;
    server_name %s.test;
    %s
    more_set_headers 'X-Forge: yes';
    more_clear_headers X-Powered-By;
    location /static/ { alias html/; }
    location /error500 { return 500; }
    location /proxy { proxy_pass http://127.0.0.1:%d/; }
    location /proxy-error { proxy_pass http://127.0.0.1:%d/error; }
    location /rewrite/ { rewrite ^/rewrite/(.*)$ /static/$1 last; }
}
''' % (http_port, https_port, mode,
       "more_set_headers 'Server: CustomServer';" if mode == 'custom' else 'more_clear_headers Server;',
       backend.server_port, backend.server_port)
        config += '}\n'
        (base / 'conf/nginx.conf').write_text(config)
        (base / 'conf/invalid.conf').write_text('this_directive_does_not_exist;\n')
        prefix = base.resolve().as_posix() + '/'
        execute(binary, '-p', prefix, '-c', 'conf/nginx.conf', '-t')
        done('configuration')
        invalid = subprocess.run([str(binary), '-p', prefix, '-c', 'conf/invalid.conf', '-t'],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        check(invalid.returncode != 0, 'Invalid configuration accepted')
        done('invalid-configuration')
        try:
            log = open(str(base / 'process.log'), 'wb')
            process = subprocess.Popen([str(binary), '-p', prefix, '-c', 'conf/nginx.conf'],
                                       stdout=log, stderr=log,
                                       **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
            for _ in range(100):
                check(process.poll() is None, 'NGINX exited: ' + (base / 'process.log').read_text())
                try:
                    with socket.create_connection(('127.0.0.1', http_port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise AssertionError('HTTP server did not start')
            for protocol in ['http', 'https']:
                for mode in ['clear', 'custom']:
                    for operation in ['static', 'head', '404', '500', 'proxy', 'proxy-error', 'gzip', 'rewrite']:
                        paths = dict(static='/static/data.txt', head='/static/data.txt',
                                     gzip='/static/data.txt', rewrite='/rewrite/data.txt',
                                     proxy='/proxy', **{'proxy-error': '/proxy-error', '404': '/missing', '500': '/error500'})
                        context = ssl._create_unverified_context()
                        connection = (http.client.HTTPSConnection('127.0.0.1', https_port, context=context, timeout=10)
                                      if protocol == 'https' else http.client.HTTPConnection('127.0.0.1', http_port, timeout=10))
                        headers = {'Host': mode + '.test', 'Accept-Encoding': 'gzip' if operation == 'gzip' else 'identity'}
                        connection.request('HEAD' if operation == 'head' else 'GET', paths[operation], headers=headers)
                        response = connection.getresponse()
                        body = response.read()
                        status = {'404': 404, '500': 500, 'proxy-error': 503}.get(operation, 200)
                        check(response.status == status, repr((operation, response.status, body)))
                        servers = response.headers.get_all('Server', [])
                        check(servers == (['CustomServer'] if mode == 'custom' else []), 'Server header: ' + repr(servers))
                        check(response.getheader('X-Powered-By') is None, 'X-Powered-By leaked')
                        check(response.getheader('X-Forge') == 'yes', 'Arbitrary header modification failed')
                        if operation in ['404', '500']:
                            check(b'nginx' not in body.lower(), 'Error page identifies NGINX')
                        elif operation.startswith('proxy'):
                            check(body == b'backend response', 'Reverse proxy body mismatch')
                            check(response.getheader('X-Backend') == 'present', 'Backend not reached')
                        elif operation == 'head':
                            check(not body, 'HEAD returned a body')
                        elif operation == 'gzip':
                            check(response.getheader('Content-Encoding') == 'gzip', 'gzip inactive')
                            check(gzip.decompress(body) == data, 'gzip body mismatch')
                        else:
                            check(body == data, 'Static/rewrite response mismatch')
                        connection.close()
                        done(protocol + ':' + mode + ':' + operation)
            for version in ['TLSv1.2', 'TLSv1.3']:
                context = ssl._create_unverified_context()
                if version == 'TLSv1.2':
                    context.options |= ssl.OP_NO_TLSv1_3 if hasattr(ssl, 'OP_NO_TLSv1_3') else 0
                else:
                    context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
                with socket.create_connection(('127.0.0.1', https_port), timeout=10) as raw:
                    with context.wrap_socket(raw, server_hostname='clear.test') as tls:
                        check(tls.version() == version, 'Unexpected TLS negotiation: ' + tls.version())
                done('tls12' if version == 'TLSv1.2' else 'tls13')
            context = ssl._create_unverified_context()
            context.set_alpn_protocols(['h2'])
            with socket.create_connection(('127.0.0.1', https_port), timeout=10) as raw:
                with context.wrap_socket(raw, server_hostname='clear.test') as tls:
                    check(tls.selected_alpn_protocol() == 'h2', 'HTTP/2 ALPN unavailable')
                    tls.sendall(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n' + b'\0\0\0\x04\0\0\0\0\0')
                    header = b''
                    while len(header) < 9:
                        chunk = tls.recv(9 - len(header))
                        check(bool(chunk), 'HTTP/2 connection closed')
                        header += chunk
                    check(header[3] == 4, 'Expected HTTP/2 SETTINGS frame')
            done('http2')
        finally:
            if process is not None and process.poll() is None:
                try:
                    execute(binary, '-p', prefix, '-c', 'conf/nginx.conf', '-s', 'quit')
                    process.wait(timeout=10)
                except Exception:
                    process.kill()
                    process.wait(timeout=10)
            if 'log' in locals():
                log.close()
            backend.shutdown()
            backend.server_close()
    run_profiles(binary,ROOT/'build/runtime',metadata,args.target,ROOT,check,done)
    check(sorted(passed) == sorted(required_checks(args.target)), 'Incomplete test suite')
    write(args.report, dict(schema=1, status='passed', target=args.target, os=args.os,
                            identity=identity, binary_sha256=sha256(binary),
                            archive_sha256=metadata['archive_sha256'],
                            plan_digest=plan['digest'], source_revision=plan['source_revision'],
                            checks=sorted(passed)))

if __name__ == '__main__':
    main()
