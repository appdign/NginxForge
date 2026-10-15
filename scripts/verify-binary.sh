#!/usr/bin/env bash
set -euo pipefail
binary=${1:?binary path required}
arch=${2:?amd64 or arm64 required}
file "$binary"
readelf -h "$binary"
if readelf -l "$binary" | grep -q 'INTERP'; then
    echo 'ELF interpreter found: binary is not fully static' >&2
    exit 1
fi
if readelf -d "$binary" | grep -q '(NEEDED)'; then
    echo 'Shared library dependency found' >&2
    exit 1
fi
case "$arch" in
  amd64) readelf -h "$binary" | grep -q 'Machine:.*Advanced Micro Devices X86-64' ;;
  arm64) readelf -h "$binary" | grep -q 'Machine:.*AArch64' ;;
  *) exit 1 ;;
esac
# ldd is diagnostic only; static binaries commonly return nonzero.
set +e
ldd "$binary"
set -e
"$binary" -v
"$binary" -V
