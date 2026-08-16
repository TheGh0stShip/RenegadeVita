#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# Keep the native-ext4 active checkout self-contained when the Windows managed
# root is not mounted/writable in this execution environment.
rv_managed_builder_root=${RENEGADE_BUILDER_ROOT:-"/mnt/c/Users/${USER}/AppData/Local/RenegadeVitaBuilder"}
if [ -d "$rv_managed_builder_root" ] && [ -w "$rv_managed_builder_root" ]; then
	rv_builder_root=$rv_managed_builder_root
else
	rv_builder_root=$rv_root
fi
rv_build="$rv_root/build/host-a22-ninja"
rv_runtime="$rv_root/build/host-a22-runtime"
rv_timestamp=$(date +%Y%m%d-%H%M%S)
rv_log="$rv_builder_root/logs/a22-$rv_timestamp-host-asset.log"

mkdir -p "$rv_build" "$rv_runtime/user" "$rv_runtime/cache" \
  "$rv_runtime/mods" "$rv_builder_root/logs"
exec > >(tee "$rv_log") 2>&1

echo "A2.2 original WW3D asset-manager host integration"
echo "Log: $rv_log"
bash "$rv_root/tools/stage_sources.sh"

rv_retail_root=${RENEGADE_RETAIL_ROOT:-"$rv_root/retail-pc"}
test -f "$rv_retail_root/Data/always.dat"

cmake -S "$rv_root/tools/host_a22" -B "$rv_build" -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$rv_build" --parallel
"$rv_build/a22_asset_selftest" "$rv_retail_root" \
  "$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"

echo "A2.2 host asset integration PASS"
echo "Complete log: $rv_log"
