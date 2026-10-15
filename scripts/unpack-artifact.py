#!/usr/bin/env python3
"""Unpack locally produced release packages after verifying archive and binary hashes."""
import argparse
import io
from pathlib import Path, PurePosixPath
import tarfile
import zipfile
from common import load, sha256

def unpack(directory, target, destination):
    directory, destination = Path(directory), Path(destination)
    manifest = load(directory / ('manifest-' + target + '.json'))
    archive = directory / manifest['archive']
    if archive.name != manifest['archive'] or sha256(archive) != manifest['archive_sha256']:
        raise ValueError('Archive SHA-256 mismatch')
    destination.mkdir(parents=True, exist_ok=True)
    def save(name, data):
        parts = PurePosixPath(name)
        if parts.is_absolute() or '..' in parts.parts or ':' in name or '\\' in name:
            raise ValueError('Unsafe package path')
        path = destination.joinpath(*parts.parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if target.startswith('windows'):
        with zipfile.ZipFile(str(archive)) as bundle:
            for name in bundle.namelist():
                save(name, bundle.read(name))
    else:
        with tarfile.open(str(archive), 'r:gz') as bundle:
            for member in bundle:
                if not member.isfile():
                    raise ValueError('Unexpected package entry')
                save(member.name, bundle.extractfile(member).read())
    binary = destination / manifest['binary_name']
    binary.chmod(0o755)
    if sha256(binary) != manifest['binary_sha256']:
        raise ValueError('Unpacked binary SHA-256 mismatch')
    return binary.resolve(), manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='build/artifacts')
    parser.add_argument('--target', required=True)
    parser.add_argument('--destination', default='build/runtime')
    args = parser.parse_args()
    print(unpack(args.directory, args.target, args.destination)[0])
