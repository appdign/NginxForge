#!/usr/bin/env python3
"""Require all three packaged binaries and all nine native runtime test reports."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import struct
import sys
from common import ROOT, PLATFORM_POLICY_SOURCE, asset_name, load, packaged_policy_path, render_platform_policy, sha256, verify_plan, write

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

integration = module('integration', ROOT / 'tests/run-integration.py')
unpacker = module('unpack', ROOT / 'scripts/unpack-artifact.py')
packager = module('packager', ROOT / 'scripts/package-release.py')

def gate(plan, artifacts, reports, output):
    verify_plan(plan)
    required = {(target, os_name) for target in ['linux-amd64', 'linux-arm64']
                for os_name in ['ubuntu-22.04', 'ubuntu-24.04', 'rocky-8', 'rocky-9']}
    required.add(('windows-amd64', 'windows-2022'))
    actual = {}
    for path in Path(reports).glob('*.json'):
        report = load(path)
        key = (report['target'], report['os'])
        if key in actual or key not in required:
            raise ValueError('Unexpected or duplicate test report: ' + repr(key))
        if (report['status'] != 'passed' or report['plan_digest'] != plan['digest']
                or report['source_revision'] != plan['source_revision']
                or sorted(report['checks']) != sorted(integration.required_checks(report['target']))):
            raise ValueError('Failed, incomplete, or mismatched test report: ' + str(path))
        identity = report['identity']
        expected_arches = {'amd64': {'amd64', 'x86_64'}, 'arm64': {'arm64', 'aarch64'}}[key[0].rsplit('-', 1)[1]]
        if identity['machine'].lower() not in expected_arches:
            raise ValueError('Runtime evidence has wrong native CPU')
        expected_id, expected_version = key[1].split('-', 1)
        if identity['id'] != expected_id or (identity['version'] != expected_version and
                not (expected_id == 'rocky' and identity['version'].split('.')[0] == expected_version)):
            raise ValueError('Runtime evidence has wrong OS identity')
        if expected_id == 'windows' and identity.get('build') != 20348:
            raise ValueError('Windows Server 2022 evidence is required')
        actual[key] = report
    if set(actual) != required:
        raise ValueError('Required platform evidence missing: ' + repr(required - set(actual)))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    platforms = {}
    for target in ['linux-amd64', 'linux-arm64', 'windows-amd64']:
        binary, metadata = unpacker.unpack(artifacts, target, ROOT / 'build/gate' / target)
        if (metadata['target'] != target or metadata['plan_digest'] != plan['digest']
                or metadata['source_revision'] != plan['source_revision']
                or metadata['nginx'] != plan['nginx'] or metadata['patches'] != plan['patches']
                or metadata['dependencies'] != plan['dependencies']
                or metadata['release_inputs'] != plan['release_inputs']
                or metadata['archive'] != asset_name(plan, target)):
            raise ValueError('Inconsistent platform build: ' + target)
        if target.startswith('linux-'):
            identity = packager.binary_identity(binary, target)
            if identity != metadata['binary']:
                raise ValueError('Static ELF validation mismatch')
        else:
            data = binary.read_bytes()
            offset = struct.unpack_from('<I', data, 60)[0]
            if (data[:2] != b'MZ' or data[offset:offset+4] != b'PE\0\0'
                    or struct.unpack_from('<H', data, offset+4)[0] != 0x8664
                    or metadata['binary'].get('crt') != 'static'):
                raise ValueError('Windows AMD64 native PE/static CRT evidence required')
        embedded = load(binary.parent / 'build-info.json')
        source_by_package = {packaged_policy_path(name): name for name in plan['release_inputs']}
        if len(source_by_package) != len(plan['release_inputs']):
            raise ValueError('Colliding packaged policy paths')
        expected_configuration = set(source_by_package)
        expected_configuration.add('html/__nginxforge_error.html')
        if set(metadata['configuration_sha256']) != expected_configuration:
            raise ValueError('Incomplete security configuration package')
        for name,digest in metadata['configuration_sha256'].items():
            if '..' in name or name.startswith('/') or '\\' in name or ':' in name:
                raise ValueError('Unsafe configuration metadata path')
            if sha256(binary.parent/name) != digest:
                raise ValueError('Packaged security configuration digest mismatch: '+name)
            source_name = source_by_package.get(name)
            if source_name in plan['release_inputs']:
                expected_digest = plan['release_inputs'][source_name]
                if source_name == PLATFORM_POLICY_SOURCE:
                    expected_digest = hashlib.sha256(render_platform_policy((ROOT/source_name).read_bytes(), target)).hexdigest()
                if digest != expected_digest:
                    raise ValueError('Packaged policy differs from resolved source: '+name)
        for key in embedded:
            if embedded[key] != metadata[key]:
                raise ValueError('Embedded build metadata mismatch: ' + key)
        for (report_target, os_name), report in actual.items():
            if report_target == target and (report['binary_sha256'] != metadata['binary_sha256']
                    or report['archive_sha256'] != metadata['archive_sha256']):
                raise ValueError('Test did not execute the release binary: ' + os_name)
        shutil.copy2(str(Path(artifacts) / metadata['archive']), str(output / metadata['archive']))
        platforms[target] = metadata
    manifest = dict(schema=1, release_tag=plan['release_tag'], plan=plan,
                    platforms=platforms, verification=[actual[key] for key in sorted(actual)],
                    verification_scope='Native Linux userspace containers and GitHub-hosted Windows Server 2022. '
                    'Customer kernel, service integration, load and production validation are separate.')
    write(output / 'build-manifest.json', manifest)
    files = sorted(path for path in output.iterdir() if path.is_file())
    expected = {asset_name(plan, target) for target in platforms} | {'build-manifest.json'}
    if {path.name for path in files} != expected:
        raise ValueError('Unexpected files in release directory')
    (output / 'SHA256SUMS.txt').write_text(''.join('{}  {}\n'.format(sha256(path), path.name) for path in files), encoding='utf-8')
    versions = plan['dependencies']['sources']
    notes = '''NGINX {version}, NginxForge revision {revision} (unofficial community build).

Three required binary targets passed: Linux AMD64 (static musl), Linux ARM64 (static musl), Windows AMD64 (native MSVC /MT).
Runtime tests passed on Ubuntu 22.04/24.04 and Rocky Linux 8/9 for BOTH Linux architectures, and on a GitHub-hosted Windows Server 2022 runner.

Included: headers-more {headers}, OpenSSL {openssl}, PCRE2 {pcre2}, zlib {zlib}.
Patch: remove three built-in error-page identity footers. HTTP/HTTPS header filtering, TLS 1.2/1.3, HTTP/2 negotiation, proxy, gzip and rewrite are tested.
Includes reviewed KISA 2026 configuration examples and a 26-control applicability matrix. Examples do not certify compliance: OS ACLs, credentials, certificates, backend/application controls and production activation require review. Windows link enforcement requires OS controls.
Security policies are ON by default and individually selectable through commented include lines in conf.d/site.conf.example. Each policy is packaged under conf/policies; TLS is selected in nginx.conf because it needs HTTP context. Default execution, each individual OFF configuration, and representative OFF/ON isolation are tested. Replace deployment values and supply real certificates before activating site.conf. Code-only frontend/Spring Boot review prompts and an ownership guide are included.
A same-host SPA/REST/WebSocket example is included under conf/examples, with preserved backend URI prefixes, static-only method restrictions, complete upgrade/forwarding headers, origin validation and real WebSocket frame tests.
All source commits, SHA-256 digests, configure options and per-platform test evidence are in build-manifest.json.

Linux tests use native containers sharing the runner kernel. Customer Windows Server installation, production load, service integration and customer kernel testing are separate. Windows retains upstream NGINX/Windows scalability and service limitations. Configuration, certificates and log directories are external runtime resources. Header hiding does not fix vulnerabilities.

[Upstream changes](https://nginx.org/en/CHANGES) | [Official source tag](https://github.com/nginx/nginx/tree/{tag})
'''.format(version=plan['nginx']['version'], revision=plan['revision'],
           headers=versions['headers-more']['version'], openssl=versions['openssl']['version'],
           pcre2=versions['pcre2']['version'], zlib=versions['zlib']['version'], tag=plan['nginx']['tag'])
    # Release notes are kept outside the five published release assets.
    (output.parent / 'release-notes.md').write_text(notes, encoding='utf-8')
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', default='build/plan.json')
    parser.add_argument('--artifacts', default='build/artifacts')
    parser.add_argument('--reports', default='build/reports')
    parser.add_argument('--output', default='build/release')
    args = parser.parse_args()
    gate(load(args.plan), args.artifacts, args.reports, args.output)
    print('PASS: three binaries, nine OS/architecture reports, identical source plan')
