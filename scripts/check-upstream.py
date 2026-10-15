#!/usr/bin/env python3
"""Resolve ONE immutable source plan for every architecture. Fail closed on API errors."""
import argparse
import hashlib
import os
import re
from common import ROOT, canonical_digest, download, find_release, github, load, official_commit, release_inputs, sha256, write

def latest_version(page, channel):
    heading = 'Stable' if channel == 'stable' else 'Mainline'
    match = re.search(r'<h4[^>]*>\s*' + heading + r' version\s*</h4>(.*?)(?:<h4|$)',
                      page, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError('Official download page has no ' + heading + ' section')
    versions = re.findall(r'href="(?:https://nginx.org)?/download/nginx-(\d+\.\d+\.\d+)\.tar\.gz"', match[1])
    if len(set(versions)) != 1:
        raise ValueError('Ambiguous or missing official release')
    return versions[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='')
    parser.add_argument('--channel', choices=['stable', 'mainline'], default='stable')
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', ''))
    parser.add_argument('--revision', type=int)
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--output', default='build/plan.json')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        raise ValueError('A GitHub repository owner/name is required')
    config = load(ROOT / 'config/build-config.yml')
    version = args.version or latest_version(download('https://nginx.org/en/download.html').decode(), args.channel)
    commit = official_commit(version)
    url = 'https://codeload.github.com/nginx/nginx/tar.gz/' + commit
    source = download(url)
    revision = args.revision or config['revision']
    if revision < 1:
        raise ValueError('Revision must be positive')
    tag = 'v{}-r{}'.format(version, revision)
    existing = find_release(args.repository, tag)
    published = existing is not None and not existing['draft']
    # A tag without a release must never be silently moved.
    tag_ref = github('repos/{}/git/ref/tags/{}'.format(args.repository, tag), missing_ok=True)
    source_revision = os.environ.get('GITHUB_SHA', '')
    if not source_revision:
        import subprocess
        source_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True).strip()
    plan = dict(schema=1, repository=args.repository, source_revision=source_revision,
                nginx=dict(version=version, tag='release-' + version, commit=commit,
                           url=url, sha256=hashlib.sha256(source).hexdigest()),
                revision=revision, release_tag=tag, channel=args.channel,
                dependencies=load(ROOT / 'config/dependencies.lock.json'), build_config=config,
                release_inputs=release_inputs(),
                patches={str(p.relative_to(ROOT)).replace('\\', '/'): sha256(p)
                         for p in sorted((ROOT / 'patches').glob('*.patch'))})
    plan['digest'] = canonical_digest(plan)
    write(args.output, plan)
    should_build = args.rebuild or not published
    publishable = not published and (tag_ref is None or existing is not None and existing['draft'])
    if tag_ref is not None and existing is None:
        raise ValueError('Release tag exists without a release; inspect it or increment revision')
    outputs = dict(build=str(should_build).lower(), publishable=str(publishable).lower(),
                   tag=tag, version=version, digest=plan['digest'])
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            for key, value in outputs.items():
                stream.write('{}={}\n'.format(key, value))
    print(outputs)

if __name__ == '__main__':
    main()
