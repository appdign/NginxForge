#!/usr/bin/env python3
"""Recover publication after a failed upload without replacing verified binaries."""
import argparse
from pathlib import Path
import shutil
import importlib.util
import os
from common import ROOT, asset_name, github, load, sha256, verify_plan, write

def verify_origin(run, jobs, plan, repository):
    if (run['repository']['full_name'] != repository or run['head_sha'] != plan['source_revision']
            or run['status'] != 'completed' or run['path'] != '.github/workflows/release.yml'):
        raise ValueError('Candidate must come from this repository and the original source commit')
    found = [step for job in jobs if job['name'] == 'release' for step in job['steps']
             if step['name'] == 'Enforce complete architecture and OS evidence']
    if len(found) != 1 or found[0]['conclusion'] != 'success':
        raise ValueError('Original run did not pass the full release gate')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True, type=int)
    parser.add_argument('--candidate', default='build/candidate')
    args = parser.parse_args()
    candidate = Path(args.candidate) / 'release'
    manifest = load(candidate / 'build-manifest.json')
    plan = verify_plan(manifest['plan'])
    repo = os.environ['GITHUB_REPOSITORY']
    if plan['repository'] != repo:
        raise ValueError('Cross-repository publication is forbidden')
    run = github('repos/{}/actions/runs/{}'.format(repo, args.run_id))
    jobs, page = [], 1
    while True:
        response = github('repos/{}/actions/runs/{}/jobs?filter=latest&per_page=100&page={}'.format(repo,args.run_id,page))
        jobs.extend(response['jobs'])
        if len(jobs) >= response['total_count']:
            break
        page += 1
    verify_origin(run,jobs,plan,repo)
    names = {asset_name(plan,target) for target in ['linux-amd64','linux-arm64','windows-amd64']} | {'build-manifest.json'}
    checksums = {}
    for line in (candidate/'SHA256SUMS.txt').read_text().splitlines():
        digest,name = line.split('  ',1)
        if name not in names or name in checksums or sha256(candidate/name) != digest:
            raise ValueError('Invalid verified candidate checksums')
        checksums[name] = digest
    if set(checksums) != names:
        raise ValueError('Incomplete verified candidate')
    write(ROOT/'build/plan.json',plan)
    artifacts = ROOT/'build/artifacts'
    reports = ROOT/'build/reports'
    artifacts.mkdir(parents=True,exist_ok=True)
    reports.mkdir(parents=True,exist_ok=True)
    for target,metadata in manifest['platforms'].items():
        if target not in ['linux-amd64','linux-arm64','windows-amd64']:
            raise ValueError('Unexpected target')
        name = asset_name(plan,target)
        shutil.copy2(str(candidate/name),str(artifacts/name))
        write(artifacts/('manifest-'+target+'.json'),metadata)
    for report in manifest['verification']:
        name = report['target']+'-'+report['os']+'.json'
        if '/' in name or '\\' in name or '..' in name:
            raise ValueError('Unexpected evidence filename')
        write(reports/name,report)
    spec=importlib.util.spec_from_file_location('gate_release',str(ROOT/'scripts/gate-release.py'))
    gate=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.gate(plan,artifacts,reports,ROOT/'build/release')
    for name in names | {'SHA256SUMS.txt'}:
        if sha256(candidate/name) != sha256(ROOT/'build/release'/name):
            raise ValueError('Reconstructed release differs from the original verified candidate')
    print('Verified original gate, source provenance, all nine reports and unchanged release bytes')

if __name__ == '__main__': main()
