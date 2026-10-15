#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import tarfile
import io
from common import ROOT, download, load, verify_plan, write

def extract(data, destination):
    """Extract only regular files/directories; reject links and traversal on every OS."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Source destination already exists: ' + str(destination))
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = archive.getmembers()
        roots = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or '\\' in member.name
                    or ':' in member.name or not path.parts):
                raise ValueError('Unsafe archive path: ' + member.name)
            roots.add(path.parts[0])
            if not (member.isfile() or member.isdir()):
                raise ValueError('Unsupported archive entry: ' + member.name)
        if len(roots) != 1:
            raise ValueError('Source archive must have one root directory')
        for member in members:
            relative = PurePosixPath(member.name).parts[1:]
            if not relative:
                continue
            target = destination.joinpath(*relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, open(str(target), 'wb') as dst:
                    dst.write(src.read())
                target.chmod(member.mode & 0o755)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', default='build/plan.json')
    parser.add_argument('--destination', default='build/src')
    args = parser.parse_args()
    plan = verify_plan(load(args.plan))
    sources = dict(plan['dependencies']['sources'], nginx=plan['nginx'])
    for name, item in sources.items():
        data = download(item['url'])
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('SHA-256 mismatch: ' + name)
        extract(data, Path(args.destination) / name)
    source = Path(args.destination) / 'nginx'
    header = (source / 'src/core/nginx.h').read_text()
    version = re.search(r'#define\s+NGINX_VERSION\s+"([^"]+)"', header)
    if not version or version[1] != plan['nginx']['version']:
        raise ValueError('Official tag/archive version mismatch')
    # Upstream archives may not include a configure wrapper; auto/configure is official.
    print('Verified all immutable sources for ' + plan['nginx']['version'])

if __name__ == '__main__':
    main()
