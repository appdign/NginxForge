#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../build/src/nginx"
mapfile -t options < <(python ../../../scripts/configure-options.py --platform windows)
test "${#options[@]}" -gt 10
printf '%s\n' "${options[@]}" > ../../configure-options.txt
./auto/configure "${options[@]}"
