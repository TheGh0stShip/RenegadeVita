#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# In the normal Windows-managed checkout logs live beside workspace/A2.0.
# This active native-ext4 checkout is deliberately writable only at rv_root,
# so never select an existing but unwritable parent as the log destination.
rv_managed_builder_root=${RENEGADE_BUILDER_ROOT:-"/mnt/c/Users/${USER}/AppData/Local/RenegadeVitaBuilder"}
if [ -d "$rv_managed_builder_root" ] && [ -w "$rv_managed_builder_root" ]; then
	rv_builder_root=$rv_managed_builder_root
else
	rv_builder_root=$rv_root
fi
rv_build="$rv_root/build/host-a30-definitions"
rv_interactive_build="$rv_root/build/host-a31-asan"
rv_interactive_ubsan_build="$rv_root/build/host-a31-ubsan-visible"
rv_renderer_lifecycle_build="$rv_root/build/host-a30-renderer-lifecycle"
rv_runtime="$rv_root/build/host-a30-runtime"
rv_timestamp=$(date +%Y%m%d-%H%M%S)
rv_log="$rv_builder_root/logs/a30-$rv_timestamp-host-runtime.log"
export CCACHE_DIR="$rv_root/build/ccache"
export CCACHE_BASEDIR="$rv_root"

mkdir -p "$rv_build" "$rv_runtime/user" "$rv_runtime/cache" \
	"$rv_runtime/mods" "$rv_interactive_build" "$rv_builder_root/logs"
mkdir -p "$rv_interactive_ubsan_build"
exec > >(tee "$rv_log") 2>&1

echo "A3.0 canonical host validation: retained A2 regressions plus original M00 runtime"
echo "Log: $rv_log"

# This runner is the sole canonical host gate. The retained A2 runner owns its
# own deterministic restage and validates the accepted archive/asset path
# before this A3 target loads the original definitions and M00 static world.
bash "$rv_root/tools/run_a22_host.sh"

rv_retail_root=${RENEGADE_RETAIL_ROOT:-"$rv_root/retail-pc"}
test -f "$rv_retail_root/Data/always.dat"

cmake -S "$rv_root/tools/host_a30_definitions" -B "$rv_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DRENEGADE_USE_CCACHE=ON
grep -Fq "CCACHE_DIR=$rv_root/build/ccache" "$rv_build/build.ninja"
cmake --build "$rv_build" --target a30_wwphys_definition_runtime \
	 a31_gameplay_seed_runtime a31_interactive_runtime a31_capture_telemetry_selftest \
	 a31_vita_input_contract_selftest a35_vita_button_state_contract_selftest \
	 a35_vita_render_state_contract_selftest a32_texture_upload_contract_selftest \
	 a36_m01_mix_probe a36_mix_index a36_cache_health_contract_selftest \
	 a36_file_factory_telemetry_contract_selftest --parallel 4
"$rv_build/a31_capture_telemetry_selftest"
"$rv_build/a31_vita_input_contract_selftest"
"$rv_build/a35_vita_button_state_contract_selftest"
"$rv_build/a35_vita_render_state_contract_selftest"
"$rv_build/a32_texture_upload_contract_selftest"
"$rv_build/a36_cache_health_contract_selftest"
"$rv_build/a36_file_factory_telemetry_contract_selftest"
"$rv_build/a36_m01_mix_probe" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"
"$rv_build/a36_mix_index" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods" M01.mix \
	"$rv_runtime/cache/m01-mix-index-v1.txt"
"$rv_build/a36_mix_index" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods" M01.mix \
	"$rv_runtime/cache/m01-mix-index-v1-repeat.txt"
cmp "$rv_runtime/cache/m01-mix-index-v1.txt" \
	"$rv_runtime/cache/m01-mix-index-v1-repeat.txt"

cmake -S "$rv_root/tools/host_a30_renderer_lifecycle" \
	-B "$rv_renderer_lifecycle_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DRENEGADE_USE_CCACHE=ON
cmake --build "$rv_renderer_lifecycle_build" --target a30_renderer_lifecycle_selftest --parallel 4
"$rv_renderer_lifecycle_build/a30_renderer_lifecycle_selftest"
PYTHONPATH="$rv_root/tools" python3 -m unittest -q \
	"$rv_root/tools/test_compare_capture_bundles.py" \
	"$rv_root/tools/test_renegade_asset_manifest.py" \
	"$rv_root/tools/test_renegade_asset_cache_key.py" \
	"$rv_root/tools/test_renegade_asset_manifest_delta.py" \
	"$rv_root/tools/test_renegade_asset_cache_metadata.py" \
	"$rv_root/tools/test_renegade_asset_cache_verify.py"
python3 "$rv_root/tools/renegade_asset_manifest.py" "$rv_retail_root/Data" \
	--profile m01 --output "$rv_runtime/cache/m01-retail-manifest.json"
python3 "$rv_root/tools/renegade_asset_manifest.py" "$rv_retail_root/Data" \
	--profile city --output "$rv_runtime/cache/city-retail-manifest.json"
python3 "$rv_root/tools/renegade_asset_cache_metadata.py" "$rv_runtime/cache" \
	"$rv_runtime/cache/m01-retail-manifest.json" \
	--options "$rv_root/tools/a36_mix_index_cache_options.json" \
	--entry m01.mix=m01-mix-index-v1.txt \
	--output "$rv_runtime/cache/cache-metadata-v1.json"
python3 "$rv_root/tools/renegade_asset_cache_verify.py" "$rv_runtime/cache" \
	"$rv_runtime/cache/m01-retail-manifest.json" \
	--options "$rv_root/tools/a36_mix_index_cache_options.json" \
	--output "$rv_runtime/cache/cache-verification.json"
"$rv_build/a30_m00_world_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"
"$rv_build/a31_m00_gameplay_seed_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"

# The complete interactive test runs under AddressSanitizer.  The regular
# host probe is LP64 while the target is ILP32 and deliberately exercises
# pointer-token compatibility paths; ASan gives a deterministic lifetime
# check without treating that non-target ABI as a Vita verdict.
cmake -S "$rv_root/tools/host_a30_definitions" -B "$rv_interactive_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DCMAKE_CXX_FLAGS="-fsanitize=address -fno-omit-frame-pointer" \
	-DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address" \
	-DRENEGADE_USE_CCACHE=ON
cmake --build "$rv_interactive_build" --target a31_interactive_runtime --parallel 4
ASAN_OPTIONS='abort_on_error=1:detect_leaks=0:halt_on_error=1' timeout 120s \
	"$rv_interactive_build/a31_m00_interactive_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"

# The direct M00 route now follows the original Combat/GameInit level and
# session teardown. Keep LeakSanitizer enabled in the canonical gate so a
# repeated-load ownership regression cannot be hidden by the fast ASan pass.
ASAN_OPTIONS='abort_on_error=1:detect_leaks=1:halt_on_error=1' timeout 120s \
	"$rv_interactive_build/a31_m00_interactive_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"

# Targeted undefined-behavior validation covers the same shared visible-frame
# path.  The original desktop source deliberately relies on x64-only
# alignment, signed-wrap, and shift behavior outside the Vita ILP32 contract;
# those diagnostics are excluded explicitly rather than being misreported as a
# Vita verdict.  All remaining undefined behavior is a candidate blocker.
cmake -S "$rv_root/tools/host_a30_definitions" -B "$rv_interactive_ubsan_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DCMAKE_CXX_FLAGS="-fsanitize=undefined -fno-omit-frame-pointer -fno-sanitize=alignment,signed-integer-overflow,shift" \
	-DCMAKE_EXE_LINKER_FLAGS="-fsanitize=undefined" \
	-DRENEGADE_USE_CCACHE=ON
cmake --build "$rv_interactive_ubsan_build" --target a31_interactive_runtime --parallel 4
UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1' timeout 120s \
	"$rv_interactive_ubsan_build/a31_m00_interactive_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods"

# A distinct original campaign scene must retain the same combat/session/load
# ownership. M01 is intentionally run after accepted M00 sanitizer coverage;
# this is a normal host regression, not a physical-render claim.
timeout 180s "$rv_build/a31_m00_interactive_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods" M01.mix

# This selected multiplayer-map archive exercises a distinct original world,
# visibility, lighting, and resource set through the same offline Combat route.
# It is a rendering/lifecycle smoke only: no multiplayer session is claimed.
timeout 180s "$rv_build/a31_m00_interactive_runtime" "$rv_retail_root" \
	"$rv_runtime/user" "$rv_runtime/cache" "$rv_runtime/mods" C\&C_City.mix

echo "A3.0 canonical host integration PASS"
echo "A3.1 gameplay-seed host integration PASS"
echo "A3.1 original interactive ASan host integration PASS"
echo "A3.1 original interactive LeakSanitizer host integration PASS"
echo "A3.1 hardware-equivalent interactive ASan PASS: two in-process cycles; 120 original input/network/Combat/render frames each"
echo "A3.1 hardware-equivalent interactive targeted UBSan PASS: same two-cycle visible-frame path; ILP32-irrelevant alignment/signed-wrap/shift checks excluded explicitly"
echo "A3.6 original M01 interactive host runtime PASS: two original Combat load/render/teardown cycles"
echo "A3.6 original C&C City host map smoke PASS: two original Combat load/render/teardown cycles; not multiplayer gameplay"
echo "Complete log: $rv_log"
