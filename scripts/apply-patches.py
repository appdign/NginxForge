#!/usr/bin/env python3
"""Apply the tiny, identity-only patch with exact deletions; fail on upstream drift."""
import argparse
from pathlib import Path
from common import ROOT, load, verify_plan

def apply(source, patch):
    # Restricted deletion-only unified diff. Every deletion must match exactly once.
    # No fuzzy matching, offset acceptance, or changing any other source content.
    lines = patch.read_text(encoding='utf-8').splitlines()
    targets = [line[6:] for line in lines if line.startswith('+++ b/')]
    if len(targets) != 1 or targets[0] != 'src/http/ngx_http_special_response.c':
        raise ValueError('Unexpected patch target')
    deletions = [line[1:] for line in lines if line.startswith('-') and not line.startswith('---')]
    if len(deletions) != 3 or any(line.startswith('+') and not line.startswith('+++') for line in lines):
        raise ValueError('Unexpected patch format')
    target = Path(source) / targets[0]
    data = target.read_text(encoding='utf-8')
    for deletion in deletions:
        needle = deletion + '\n'
        if data.count(needle) != 1:
            raise ValueError('Patch no longer applies exactly: ' + deletion)
        data = data.replace(needle, '', 1)
    with open(str(target), 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', default='build/plan.json')
    parser.add_argument('--source', default='build/src/nginx')
    args = parser.parse_args()
    plan = verify_plan(load(args.plan))
    for patch in sorted(plan['patches']):
        apply(args.source, ROOT / patch)
