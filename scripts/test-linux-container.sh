#!/usr/bin/env bash
set -euo pipefail
cd /repo
target=${1:?target}
os_name=${2:?os}
if [[ "$os_name" == ubuntu-* ]]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y --no-install-recommends python3 ca-certificates
else
  dnf install -y python3 ca-certificates
fi
python3 tests/run-integration.py --target "$target" --os "$os_name" \
  --report "build/reports/$target-$os_name.json"
