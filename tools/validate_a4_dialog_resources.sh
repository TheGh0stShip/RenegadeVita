#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_host_build="$rv_root/build/host-a4-dialog-resources"
rv_vita_build="$rv_root/build/vita-a4-dialog-resources"
rv_generated="$rv_vita_build/renegade_dialog_templates.inc"
rv_ccache="$rv_root/build/ccache"

mkdir -p "$rv_host_build" "$rv_vita_build"
export CCACHE_DIR="$rv_ccache"
export CCACHE_BASEDIR="$rv_root"

cmake -S "$rv_root/tools/host_a30_definitions" -B "$rv_host_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo -DRENEGADE_USE_CCACHE=ON
cmake --build "$rv_host_build" --target a4_dialog_resource_contract_selftest --parallel 4
"$rv_host_build/a4_dialog_resource_contract_selftest"

python3 "$rv_root/tools/generate_wwui_dialog_templates.py" \
	--rc "$rv_root/upstream/CnC_Renegade/Code/Commando/chat.rc" \
	--resource-h "$rv_root/upstream/CnC_Renegade/Code/Commando/resource.h" \
	--out "$rv_generated"

/usr/local/vitasdk/bin/arm-vita-eabi-g++ -std=gnu++17 -fshort-wchar \
	-fno-exceptions -fno-rtti -DRENEGADE_VITA_PORT=1 \
	-DRENEGADE_SHORT_WCHAR_ABI=1 \
	-I"$rv_root/port/compatibility/include" -I"$rv_root/port/platform" \
	-I"$rv_vita_build" \
	-include "$rv_root/port/compatibility/include/msvc_compat.h" \
	-c "$rv_root/port/platform/renegade_dialog_resource_provider.cpp" \
	-o "$rv_vita_build/renegade_dialog_resource_provider.o"

echo "A4 dialog resource validation PASS: host contract + ARM provider object"
