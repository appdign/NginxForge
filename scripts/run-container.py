#!/usr/bin/env python3
"""Use digest-pinned multiarch images on matching native runners only."""
import argparse
import os
import platform
import subprocess
from common import ROOT, load

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--arch', choices=['amd64', 'arm64'], required=True)
    parser.add_argument('--test-os', default='')
    args = parser.parse_args()
    expected = {'amd64': {'x86_64', 'amd64'}, 'arm64': {'aarch64', 'arm64'}}[args.arch]
    if platform.machine().lower() not in expected:
        raise ValueError('Native runner required; emulation is not accepted as release evidence')
    config = load(ROOT / 'config/build-config.yml')
    key = args.test_os or 'alpine'
    image = config['images'][key]
    if '@sha256:' not in image:
        raise ValueError('Container digest is required')
    command = ['docker', 'run', '--rm', '--platform', 'linux/' + args.arch,
               '--mount', 'type=bind,source={},target=/repo'.format(ROOT), '--workdir', '/repo']
    if not args.test_os:
        epoch = subprocess.check_output(['git', 'show', '-s', '--format=%ct', 'HEAD'], cwd=str(ROOT), text=True).strip()
        command += ['--env', 'SOURCE_DATE_EPOCH=' + epoch, image, '/bin/sh', '-c',
                    'apk add --no-cache bash && bash scripts/build-linux.sh ' + args.arch]
    else:
        command += [image, '/bin/bash', 'scripts/test-linux-container.sh', 'linux-' + args.arch, args.test_os]
    subprocess.run(command, cwd=str(ROOT), check=True)
