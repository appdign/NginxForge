"""Shared, dependency-free build and release utilities (Python 3.6+ on test hosts)."""
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SECURITY_DOCS = ['docs/SECURITY-CONFIG.md', 'docs/SECURITY-OWNERSHIP.md']
PLATFORM_POLICY_SOURCE = 'config/runtime/policy.conf'
PLATFORM_POLICY_MARKER = b'# NGINXFORGE_PLATFORM_POLICY'

def render_platform_policy(source, target):
    if target not in {'linux-amd64', 'linux-arm64', 'windows-amd64'}:
        raise ValueError('Unsupported configuration target')
    if source.count(PLATFORM_POLICY_MARKER) != 1:
        raise ValueError('Symlink policy must have exactly one platform marker')
    policy = (b'# Linux: native openat/fstatat link restriction.\ndisable_symlinks on;'
              if target.startswith('linux-') else
              b'# Windows: disable_symlinks is unavailable.\n'
              b'# Require OS ACL and reparse-point review; see SECURITY-CONFIG.md, WEB-12.')
    return source.replace(PLATFORM_POLICY_MARKER, policy)

def load(path):
    with open(str(path), encoding='utf-8') as stream:
        return json.load(stream)

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def sha256(path):
    digest = hashlib.sha256()
    with open(str(path), 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def download(url):
    if not url.startswith('https://'):
        raise ValueError('HTTPS is required: ' + url)
    req = urllib.request.Request(url, headers={'User-Agent': 'NginxForge-builder/1'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()

def github(path, missing_ok=False):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'NginxForge-builder/1',
               'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('https://api.github.com/' + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise

def official_commit(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid upstream version')
    obj = github('repos/nginx/nginx/git/ref/tags/release-' + version)['object']
    for _ in range(5):
        if obj['type'] == 'commit':
            if not re.fullmatch(r'[0-9a-f]{40}', obj['sha']):
                raise ValueError('Invalid upstream commit')
            return obj['sha']
        if obj['type'] != 'tag':
            break
        obj = github('repos/nginx/nginx/git/tags/' + obj['sha'])['object']
    raise ValueError('Official release tag does not resolve to a commit')

def find_release(repository, tag):
    """The tag endpoint only finds published releases; drafts require the list API."""
    release = github('repos/{}/releases/tags/{}'.format(repository, tag), missing_ok=True)
    if release is not None:
        return release
    page = 1
    while True:
        releases = github('repos/{}/releases?per_page=100&page={}'.format(repository, page))
        matches = [item for item in releases if item['tag_name'] == tag]
        if len(matches) > 1:
            raise ValueError('Duplicate draft release tags require review')
        if matches:
            return matches[0]
        if len(releases) < 100:
            return None
        page += 1

def archive_version(plan):
    revision = plan['revision']
    return plan['nginx']['version'] + ('' if revision == 1 else '-r' + str(revision))

def asset_name(plan, target):
    return 'nginxforge-{}-{}.{}'.format(archive_version(plan), target,
                                       'zip' if target.startswith('windows') else 'tar.gz')

def packaged_policy_path(name):
    if name.startswith('config/runtime/'):
        return 'conf/' + name[len('config/runtime/'):]
    return name[len('docs/'):] if name.startswith('docs/') else name

def release_inputs():
    paths = [p for p in (ROOT / 'config/runtime').rglob('*') if p.is_file()]
    paths += [ROOT / name for name in SECURITY_DOCS] + [ROOT / 'security/kisa-2026.json']
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)}

def site_templates():
    return {'config/site-template.conf': sha256(ROOT/'config/site-template.conf')}

def verify_plan(plan):
    stored = dict(plan)
    digest = stored.pop('digest')
    if canonical_digest(stored) != digest:
        raise ValueError('Build plan digest mismatch')
    config = load(ROOT / 'config/build-config.yml')
    if plan['dependencies'] != load(ROOT / 'config/dependencies.lock.json'):
        raise ValueError('Source lock differs from resolved plan')
    if plan['build_config'] != config:
        raise ValueError('Build configuration differs from resolved plan')
    if plan.get('release_inputs') != release_inputs():
        raise ValueError('Runtime configuration/security policy differs from resolved plan')
    if plan.get('site_templates') != site_templates():
        raise ValueError('Site configuration template differs from resolved plan')
    actual = {str(p.relative_to(ROOT)).replace('\\', '/'): sha256(p)
              for p in sorted((ROOT / 'patches').glob('*.patch'))}
    if actual != plan['patches']:
        raise ValueError('Patch set differs from resolved plan')
    return plan
