#!/usr/bin/env python3
import argparse
from common import ROOT, load

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['linux', 'windows'], required=True)
    args = parser.parse_args()
    config = load(ROOT / 'config/build-config.yml')
    for option in config['configure']['common'] + config['configure'][args.platform]:
        print(option)
