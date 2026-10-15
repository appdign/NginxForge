#!/usr/bin/env python3
"""Validate the native binary and package it with original third-party notices."""
import argparse
import gzip
import io
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import tarfile
import zipfile
from common import ROOT, asset_name, load, sha256, verify_plan, write

TARGETS = {'linux-amd64', 'linux-arm64', 'windows-amd64'}

def binary_identity(path, target):
    data = Path(path).read_bytes()
    if target.startswith('linux-'):
        if data[:6] != b'\x7fELF\x02\x01':
            raise ValueError('Expected ELF64 little endian binary')
        machine = struct.unpack_from('<H', data, 18)[0]
        if machine != (62 if target.endswith('amd64') else 183):
            raise ValueError('Wrong ELF architecture')
        phoff = struct.unpack_from('<Q', data, 32)[0]
        phsize, phnum = struct.unpack_from('<HH', data, 54)
        if phsize < 56 or phoff + phsize * phnum > len(data):
            raise ValueError('Malformed ELF program headers')
        for index in range(phnum):
            header = phoff + index * phsize
            segment = struct.unpack_from('<I', data, header)[0]
            if segment == 3:
                raise ValueError('ELF must have no dynamic loader (PT_INTERP)')
            if segment == 2:
                # Static PIE contains relocation metadata but needs no loader or DSOs.
                offset = struct.unpack_from('<Q', data, header + 8)[0]
                size = struct.unpack_from('<Q', data, header + 32)[0]
                if size % 16 or offset + size > len(data):
                    raise ValueError('Malformed ELF dynamic segment')
                for entry in range(offset, offset + size, 16):
                    tag = struct.unpack_from('<q', data, entry)[0]
                    if tag in (1, 0x7fffffff, 0x7ffffffd, 0x6ffffefb, 0x6ffffefc):
                        raise ValueError('ELF requires a shared library or audit DSO')
        return dict(format='ELF64', machine=machine, fully_static=True)
    if data[:2] != b'MZ':
        raise ValueError('Expected native PE executable')
    offset = struct.unpack_from('<I', data, 60)[0]
    if data[offset:offset+4] != b'PE\0\0' or struct.unpack_from('<H', data, offset+4)[0] != 0x8664:
        raise ValueError('Expected AMD64 PE executable')
    result = subprocess.check_output(['dumpbin', '/nologo', '/dependents', str(path)], text=True)
    dlls = sorted(set(re.findall(r'^\s+([\w.-]+\.dll)\s*$', result, re.I | re.M)))
    allowed = {'kernel32.dll', 'user32.dll', 'advapi32.dll', 'ws2_32.dll', 'crypt32.dll',
               'secur32.dll', 'bcrypt.dll', 'ntdll.dll', 'rpcrt4.dll', 'gdi32.dll', 'shell32.dll'}
    if not dlls or any(dll.lower() not in allowed and not dll.lower().startswith('api-ms-win-') for dll in dlls):
        raise ValueError('Non-system DLL dependency: ' + repr(dlls))
    return dict(format='PE32+', machine=0x8664, crt='static', system_dlls=dlls)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    parser.add_argument('--target', choices=sorted(TARGETS), required=True)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--options', required=True)
    parser.add_argument('--output', default='build/dist')
    args = parser.parse_args()
    plan = verify_plan(load(args.plan))
    binary = Path(args.binary).resolve()
    identity = binary_identity(binary, args.target)
    output = subprocess.check_output([str(binary), '-V'], stderr=subprocess.STDOUT, text=True)
    if 'nginx/' + plan['nginx']['version'] not in output:
        raise ValueError('Built binary has wrong NGINX version')
    for feature in ['--with-http_ssl_module', '--with-http_v2_module', '--with-pcre-jit',
                    '--with-zlib=', '--with-openssl=', '--add-module=../headers-more']:
        if feature not in output:
            raise ValueError('Required feature missing: ' + feature)
    stage = ROOT / 'build/stage' / args.target
    if stage.exists():
        raise ValueError('Packaging directory already exists')
    stage.mkdir(parents=True)
    binary_name = 'nginx.exe' if args.target.startswith('windows') else 'nginx'
    shutil.copy2(str(binary), str(stage / binary_name))
    (stage / binary_name).chmod(0o755)
    shutil.copytree(str(ROOT / 'config/runtime'), str(stage / 'conf'))
    for name in ['logs', 'temp', 'html']:
        (stage / name).mkdir()
        (stage / name / '.keep').touch()
    (stage / 'html/index.html').write_text('<!doctype html><title>Ready</title><p>Ready</p>\n')
    for name in ['LICENSE', 'THIRD_PARTY_LICENSES.md']:
        shutil.copy2(str(ROOT / name), str(stage / name))
    licenses = stage / 'licenses'
    licenses.mkdir()
    for source in ['nginx'] + sorted(plan['dependencies']['sources']):
        base = ROOT / 'build/src' / source
        candidates = [base / name for name in ['LICENSE', 'LICENSE.txt', 'LICENCE', 'COPYING', 'NOTICE'] if (base / name).is_file()]
        if source == 'zlib':
            candidates.append(base / 'zlib.h')
        if not candidates:
            raise ValueError('No license found for ' + source)
        for license_file in candidates:
            shutil.copy2(str(license_file), str(licenses / (source + '-' + license_file.name)))
    options = Path(args.options).read_text().splitlines()
    expected_options = plan['build_config']['configure']['common'] + plan['build_config']['configure'][args.target.split('-')[0]]
    if options != expected_options:
        raise ValueError('Configure options differ from common build plan')
    if args.target.startswith('linux-'):
        shutil.copytree(str(ROOT / 'config/notices'), str(licenses / 'toolchain'))
        toolchain = subprocess.check_output(['apk', 'info', '-v'], text=True)
    else:
        toolchain = subprocess.run(['cl'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
    metadata = dict(schema=1, target=args.target, plan_digest=plan['digest'],
                    source_revision=plan['source_revision'], nginx=plan['nginx'],
                    dependencies=plan['dependencies'], patches=plan['patches'],
                    configure_options=options, nginx_V=output, binary=identity,
                    binary_name=binary_name, binary_sha256=sha256(binary),
                    build_host=dict(system=platform.system(), machine=platform.machine(),
                                    release=platform.release()),
                    toolchain=toolchain,
                    source_date_epoch=int(os.environ.get('SOURCE_DATE_EPOCH', '0')))
    write(stage / 'build-info.json', metadata)
    dist = Path(args.output)
    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / asset_name(plan, args.target)
    files = sorted(path for path in stage.rglob('*') if path.is_file())
    if args.target.startswith('windows'):
        with zipfile.ZipFile(str(archive), 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in files:
                info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.external_attr = (0o100755 if path.name == binary_name else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, path.read_bytes())
    else:
        with open(str(archive), 'wb') as raw, gzip.GzipFile(fileobj=raw, filename='', mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as bundle:
                for path in files:
                    data = path.read_bytes()
                    info = tarfile.TarInfo(path.relative_to(stage).as_posix())
                    info.size = len(data)
                    info.mode = 0o755 if path.name == binary_name else 0o644
                    bundle.addfile(info, io.BytesIO(data))
    metadata['archive'] = archive.name
    metadata['archive_sha256'] = sha256(archive)
    write(dist / ('manifest-' + args.target + '.json'), metadata)
    print(archive)

if __name__ == '__main__':
    main()
