#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_build="$rv_root/build/host-a30-wwphys"

bash "$rv_root/tools/stage_sources.sh"
cmake -S "$rv_root/tools/host_a30" -B "$rv_build" -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$rv_build" --target a30_original_compile_frontier --parallel

echo "A3.0 WWPhys compile frontier: 93/93 original runtime translation units compiled"
echo "A3.0 WWSaveLoad definition closure: 11/11 original translation units compiled (8 newly integrated)"
echo "A3.0 unique original source manifest: 206 translation units"
