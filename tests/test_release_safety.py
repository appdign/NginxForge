import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from common import canonical_digest, github, load, sha256, write, asset_name, verify_plan

def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), str(ROOT / 'scripts' / (name + '.py')))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

upstream = module('check-upstream')
fetch = module('fetch-sources')
patcher = module('apply-patches')
gate = module('gate-release')
packager = module('package-release')

def plan_fixture():
    plan = dict(schema=1, repository='example/NginxForge', source_revision='a'*40,
                nginx=dict(version='1.30.6', tag='release-1.30.6', commit='b'*40), revision=1,
                release_tag='v1.30.6-r1', channel='stable',
                dependencies=load(ROOT / 'config/dependencies.lock.json'),
                build_config=load(ROOT / 'config/build-config.yml'),
                patches={p.relative_to(ROOT).as_posix(): sha256(p) for p in (ROOT/'patches').glob('*.patch')})
    plan['digest'] = canonical_digest(plan)
    return plan

def elf(machine=62, dynamic=False):
    data = bytearray(120)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', data, 18, machine)
    struct.pack_into('<Q', data, 32, 64)
    struct.pack_into('<HH', data, 54, 56, 1 if dynamic else 0)
    if dynamic:
        struct.pack_into('<I', data, 64, 3)
    return bytes(data)

def pe():
    data = bytearray(96)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, 0x8664)
    return bytes(data)

class UpstreamSafety(unittest.TestCase):
    def test_official_channels_are_separate(self):
        page = '<h4>Mainline version</h4><a href="/download/nginx-1.31.7.tar.gz">x</a><h4>Stable version</h4><a href="/download/nginx-1.30.6.tar.gz">x</a><h4>Legacy versions</h4>'
        self.assertEqual(upstream.latest_version(page, 'stable'), '1.30.6')
        self.assertEqual(upstream.latest_version(page, 'mainline'), '1.31.7')

    def test_changed_page_is_failure(self):
        with self.assertRaises(ValueError):
            upstream.latest_version('<h4>Something different</h4>', 'stable')

    def test_network_error_is_not_no_new_version(self):
        for code in [401,403,429,500,503]:
            with self.subTest(code=code), patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError('https://api.github.com',code,'failure',{},None)):
                with self.assertRaises(urllib.error.HTTPError):
                    github('repos/example/repo/releases/latest', missing_ok=True)

    def test_only_404_is_missing(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError('https://api.github.com',404,'missing',{},None)):
            self.assertIsNone(github('repos/example/repo/releases/latest', missing_ok=True))

    def test_plan_tampering_rejected(self):
        plan = plan_fixture()
        plan['nginx']['version'] = '9.9.9'
        with self.assertRaises(ValueError):
            verify_plan(plan)

    def test_immutable_patch_set(self):
        plan = plan_fixture()
        plan['patches'] = {}
        plan.pop('digest')
        plan['digest'] = canonical_digest(plan)
        with self.assertRaises(ValueError):
            verify_plan(plan)

class SourceSafety(unittest.TestCase):
    def archive(self, name, kind=None):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as tar:
            member = tarfile.TarInfo(name)
            member.size = 1
            if kind:
                member.type = kind
                member.linkname = '../../outside'
                member.size = 0
            tar.addfile(member, io.BytesIO(b'x') if not kind else None)
        return data.getvalue()

    def test_traversal_rejected(self):
        for name in ['root/../../outside','/outside','root/C:/outside','root/..\\outside']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    fetch.extract(self.archive(name), Path(temp)/'source')

    def test_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                fetch.extract(self.archive('root/link', tarfile.SYMTYPE), Path(temp)/'source')

    def test_regular_source_extracts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'source'
            fetch.extract(self.archive('root/src/file'), path)
            self.assertEqual((path/'src/file').read_bytes(), b'x')

    def test_static_binary_architecture(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp)/'nginx'
            binary.write_bytes(elf(183))
            self.assertTrue(packager.binary_identity(binary, 'linux-arm64')['fully_static'])
            with self.assertRaises(ValueError):
                packager.binary_identity(binary, 'linux-amd64')
            binary.write_bytes(elf(62, True))
            with self.assertRaises(ValueError):
                packager.binary_identity(binary, 'linux-amd64')

    def test_patch_drift_and_double_apply_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'src/http/ngx_http_special_response.c'
            source.parent.mkdir(parents=True)
            source.write_text('"<hr><center>" NGINX_VER "</center>" CRLF\n"<hr><center>" NGINX_VER_BUILD "</center>" CRLF\n"<hr><center>nginx</center>" CRLF\nkeep\n')
            patch_file = ROOT/'patches/0001-remove-error-page-identity.patch'
            patcher.apply(temp, patch_file)
            self.assertEqual(source.read_text(), 'keep\n')
            with self.assertRaises(ValueError):
                patcher.apply(temp, patch_file)

class ReleaseGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.artifacts = self.base/'artifacts'
        self.reports = self.base/'reports'
        self.artifacts.mkdir()
        self.reports.mkdir()
        self.plan = plan_fixture()
        for target in ['linux-amd64','linux-arm64','windows-amd64']:
            binary = pe() if target.startswith('windows') else elf(183 if target.endswith('arm64') else 62)
            name = 'nginx.exe' if target.startswith('windows') else 'nginx'
            metadata = dict(target=target, plan_digest=self.plan['digest'],
                            source_revision=self.plan['source_revision'], nginx=self.plan['nginx'],
                            patches=self.plan['patches'], dependencies=self.plan['dependencies'],
                            binary_name=name, binary_sha256=hashlib.sha256(binary).hexdigest(),
                            binary=dict(format='PE32+',crt='static') if target.startswith('windows') else dict(format='ELF64',machine=183 if target.endswith('arm64') else 62,fully_static=True))
            archive = self.artifacts/asset_name(self.plan,target)
            files = {name:binary, 'build-info.json':json.dumps(metadata).encode()}
            if target.startswith('windows'):
                with zipfile.ZipFile(str(archive),'w') as bundle:
                    for key,value in files.items(): bundle.writestr(key,value)
            else:
                with tarfile.open(str(archive),'w:gz') as bundle:
                    for key,value in files.items():
                        info=tarfile.TarInfo(key); info.size=len(value)
                        bundle.addfile(info,io.BytesIO(value))
            metadata['archive']=archive.name
            metadata['archive_sha256']=sha256(archive)
            write(self.artifacts/('manifest-'+target+'.json'),metadata)
            systems = ['windows-2022'] if target.startswith('windows') else ['ubuntu-22.04','ubuntu-24.04','rocky-8','rocky-9']
            for system in systems:
                os_id,version=system.split('-',1)
                report=dict(status='passed',target=target,os=system,plan_digest=self.plan['digest'],
                            source_revision=self.plan['source_revision'],binary_sha256=metadata['binary_sha256'],
                            checks=gate.integration.REQUIRED_CHECKS,
                            identity=dict(id=os_id,version=version,machine='aarch64' if target.endswith('arm64') else 'x86_64',build=20348))
                write(self.reports/(target+'-'+system+'.json'),report)

    def tearDown(self):
        self.temp.cleanup()

    def run_gate(self):
        # Gate extraction is isolated from the real checkout.
        with patch.object(gate, 'ROOT', self.base):
            return gate.gate(self.plan,self.artifacts,self.reports,self.base/'release')

    def change(self, filename, transform):
        path = self.reports/filename
        value=load(path); transform(value); write(path,value)

    def test_complete_matrix_passes(self):
        self.assertEqual(len(self.run_gate()['verification']),9)
        self.assertEqual(len(list((self.base/'release').iterdir())),5)

    def test_each_missing_os_arch_blocks_entire_release(self):
        for path in sorted(self.reports.iterdir()):
            data=path.read_bytes(); path.unlink()
            with self.subTest(missing=path.name), self.assertRaises(ValueError):
                self.run_gate()
            path.write_bytes(data)

    def test_arm64_failure_blocks_release(self):
        self.change('linux-arm64-rocky-8.json', lambda v:v.update(status='failed'))
        with self.assertRaises(ValueError): self.run_gate()

    def test_mixed_source_plan_blocks_release(self):
        self.change('linux-arm64-ubuntu-24.04.json', lambda v:v.update(plan_digest='bad'))
        with self.assertRaises(ValueError): self.run_gate()

    def test_wrong_binary_blocks_release(self):
        self.change('linux-arm64-rocky-9.json', lambda v:v.update(binary_sha256='bad'))
        with self.assertRaises(ValueError): self.run_gate()

    def test_wrong_native_cpu_blocks_release(self):
        self.change('linux-arm64-rocky-8.json', lambda v:v['identity'].update(machine='x86_64'))
        with self.assertRaises(ValueError): self.run_gate()

    def test_skipped_security_test_blocks_release(self):
        self.change('linux-amd64-ubuntu-22.04.json', lambda v:v.update(checks=v['checks'][:-1]))
        with self.assertRaises(ValueError): self.run_gate()

    def test_archive_tampering_blocks_release(self):
        path=self.artifacts/asset_name(self.plan,'linux-arm64')
        path.write_bytes(path.read_bytes()+b'corruption')
        with self.assertRaises(ValueError): self.run_gate()

if __name__ == '__main__': unittest.main()
