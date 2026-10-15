#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
arch=${1:?amd64 or arm64 required}
case "$arch:$(uname -m)" in
  amd64:x86_64|arm64:aarch64) ;;
  *) echo 'Native runner architecture mismatch' >&2; exit 1 ;;
esac
# This script runs inside the digest-pinned, native Alpine container.
apk add --no-cache build-base linux-headers perl python3 file binutils ca-certificates
python3 scripts/fetch-sources.py
python3 scripts/apply-patches.py
cd build/src/nginx
mapfile -t options < <(python3 ../../../scripts/configure-options.py --platform linux)
test "${#options[@]}" -gt 10
printf '%s\n' "${options[@]}" > ../../configure-options.txt
./auto/configure "${options[@]}"
make -j"$(getconf _NPROCESSORS_ONLN)"
cd ../../..
bash scripts/verify-binary.sh build/src/nginx/objs/nginx "$arch"
python3 scripts/package-release.py --plan build/plan.json --target "linux-$arch" \
  --binary build/src/nginx/objs/nginx --options build/configure-options.txt
