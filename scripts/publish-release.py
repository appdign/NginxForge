#!/usr/bin/env python3
"""Publish only gated assets, stage as draft, verify upload, then promote atomically."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile
from common import asset_name, github, load, sha256

def gh(*args):
    subprocess.run(['gh'] + list(args), check=True)

def version_key(version, revision):
    return tuple(map(int, version.split('.'))) + (revision,)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='build/release')
    parser.add_argument('--notes', default='build/release-notes.md')
    args = parser.parse_args()
    directory = Path(args.directory)
    manifest = load(directory / 'build-manifest.json')
    plan = manifest['plan']
    repo, tag = plan['repository'], plan['release_tag']
    expected = {asset_name(plan, target) for target in manifest['platforms']} | {'build-manifest.json', 'SHA256SUMS.txt'}
    if len(expected) != 5 or {path.name for path in directory.iterdir()} != expected:
        raise ValueError('Expected exactly three packages, manifest and checksums')
    for line in (directory / 'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if name not in expected - {'SHA256SUMS.txt'} or sha256(directory / name) != digest:
            raise ValueError('Release checksum mismatch')
    existing = github('repos/{}/releases/tags/{}'.format(repo, tag), missing_ok=True)
    if existing and not existing['draft']:
        raise ValueError('Refusing to overwrite a published release; increment revision')
    if existing:
        ref = github('repos/{}/git/ref/tags/{}'.format(repo, tag), missing_ok=True)
        # GitHub may defer creating a new tag until a draft is published.
        same_source = (ref is not None and ref['object']['type'] == 'commit'
                       and ref['object']['sha'] == plan['source_revision'])
        if ref is None:
            same_source = existing['target_commitish'] == plan['source_revision']
        if not same_source:
            raise ValueError('Draft release has a different source commit; increment revision')
        gh('release', 'upload', tag, '--repo', repo, '--clobber', *[str(directory / name) for name in sorted(expected)])
        gh('release', 'edit', tag, '--repo', repo, '--notes-file', args.notes)
    else:
        gh('release', 'create', tag, '--repo', repo, '--target', plan['source_revision'], '--draft',
           '--title', 'NginxForge ' + tag, '--notes-file', args.notes,
           *[str(directory / name) for name in sorted(expected)])
    # API verification uses the draft release ID: download the actual uploaded bytes.
    release = github('repos/{}/releases/tags/{}'.format(repo, tag))
    if {item['name'] for item in release['assets']} != expected:
        raise ValueError('Uploaded asset set mismatch; draft retained')
    with tempfile.TemporaryDirectory(prefix='nginxforge-upload-') as temp:
        gh('release', 'download', tag, '--repo', repo, '--dir', temp)
        for name in expected:
            if sha256(Path(temp) / name) != sha256(directory / name):
                raise ValueError('Uploaded asset corruption; draft retained')
    latest = github('repos/{}/releases/latest'.format(repo), missing_ok=True)
    promote_latest = plan['channel'] == 'stable'
    if latest:
        match = re.fullmatch(r'v(\d+\.\d+\.\d+)-r(\d+)', latest['tag_name'])
        if match and version_key(plan['nginx']['version'], plan['revision']) < version_key(match[1], int(match[2])):
            promote_latest = False
    gh('release', 'edit', tag, '--repo', repo, '--draft=false',
       '--prerelease=' + str(plan['channel'] == 'mainline').lower(),
       '--latest=' + str(promote_latest).lower())
    print('Published https://github.com/{}/releases/tag/{}'.format(repo, tag))

if __name__ == '__main__':
    main()
