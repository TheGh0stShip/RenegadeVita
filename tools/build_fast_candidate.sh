#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_managed_builder_root=${RENEGADE_BUILDER_ROOT:-"/mnt/c/Users/${USER}/AppData/Local/RenegadeVitaBuilder"}
if [ -d "$rv_managed_builder_root" ] && [ -w "$rv_managed_builder_root" ]; then
	rv_builder_root=$rv_managed_builder_root
else
	rv_builder_root=$rv_root
fi

rv_candidate_label=${RENEGADE_CANDIDATE_LABEL:-A3.5-dev89}
case "$rv_candidate_label" in A[0-9]*.[0-9]*-dev[0-9]*) ;; *) echo "Invalid candidate label: $rv_candidate_label" >&2; exit 2 ;; esac
rv_candidate_stem=$(printf '%s' "$rv_candidate_label" | tr '[:upper:]' '[:lower:]' | tr -d '.')
rv_vpk_content_id=EP9000-RNEGA3101_00-RENGADEVITADEV89
rv_vitasdk=${RENEGADE_VITASDK:-/usr/local/vitasdk}
rv_build_jobs=${RENEGADE_BUILD_JOBS:-$(nproc)}
case "$rv_build_jobs" in ''|*[!0-9]*|0) echo "Invalid RENEGADE_BUILD_JOBS: $rv_build_jobs" >&2; exit 2 ;; esac
rv_fast_scope=${RENEGADE_FAST_SCOPE:-package}
case "$rv_fast_scope" in compile|package) ;; *) echo "Invalid RENEGADE_FAST_SCOPE: $rv_fast_scope (expected compile or package)" >&2; exit 2 ;; esac
rv_fast_tests=${RENEGADE_FAST_TESTS:-focused}
case "$rv_fast_tests" in focused|none) ;; *) echo "Invalid RENEGADE_FAST_TESTS: $rv_fast_tests (expected focused or none)" >&2; exit 2 ;; esac

rv_build=${RENEGADE_FAST_BUILD_DIR:-"$rv_root/build/vita-fast-candidate"}
rv_host_contract_build=${RENEGADE_FAST_HOST_CONTRACT_BUILD_DIR:-"$rv_root/build/host-a30-definitions-fast"}
rv_timestamp=$(date +%Y%m%d-%H%M%S)
rv_logs="$rv_builder_root/logs"
rv_dist="$rv_builder_root/dist"
rv_log="$rv_logs/${rv_candidate_stem}-fast-$rv_timestamp-build.log"
rv_runtime_log="ux0:data/renegade/user/logs/${rv_candidate_stem}-runtime.log"

mkdir -p "$rv_logs" "$rv_dist" "$rv_root/build"
exec > >(tee "$rv_log") 2>&1

on_error() {
	local rv_status=$?
	trap - ERR
	set +e
	echo
	echo "$rv_candidate_label FAST CANDIDATE BUILD FAILED (exit $rv_status)"
	echo "Complete log: $rv_log"
	echo "Causal output tail:"
	tail -n 120 "$rv_log"
	exit "$rv_status"
}
trap on_error ERR

require_command() {
	command -v "$1" >/dev/null 2>&1 || {
		echo "Required host command is unavailable: $1" >&2
		exit 2
	}
}

require_linked_symbol() {
	grep -Fq -- "$1" "$rv_symbols" || {
		echo "Required $rv_candidate_label linked symbol is absent: $1" >&2
		exit 8
	}
}

echo "Renegade Vita $rv_candidate_label fast incremental candidate build"
echo "Workspace: $rv_root"
echo "Build dir: $rv_build"
echo "Log: $rv_log"
echo "Fast scope: $rv_fast_scope"
echo "Fast tests: $rv_fast_tests"
echo "Scope: hardware-testable iteration only; this does not replace tools/build.sh canonical acceptance."

for rv_command in cmake ninja python3 git unzip sha256sum grep find tee wc ccache curl tar make; do
	require_command "$rv_command"
done
for rv_sdk_path in \
	"$rv_vitasdk/bin/arm-vita-eabi-readelf" \
	"$rv_vitasdk/bin/arm-vita-eabi-nm" \
	"$rv_vitasdk/share/vita.toolchain.cmake" \
	"$rv_vitasdk/share/vita.cmake" \
	"$rv_vitasdk/arm-vita-eabi/lib/libvitaGL.a" \
	"$rv_vitasdk/arm-vita-eabi/lib/libvitashark.a" \
	"$rv_vitasdk/arm-vita-eabi/lib/libSceShaccCgExt.a"; do
	test -e "$rv_sdk_path" || {
		echo "Required VitaSDK dependency is missing: $rv_sdk_path" >&2
		exit 2
	}
done
export VITASDK="$rv_vitasdk"
export CCACHE_DIR="$rv_root/build/ccache"
export CCACHE_BASEDIR="$rv_root"

echo "Verifying the pinned Bink-enabled Vita FFmpeg dependency..."
bash "$rv_root/tools/build_ffmpeg_bink_vita.sh"

rv_upstream="$rv_root/upstream/CnC_Renegade"
test -d "$rv_upstream/.git"
if [[ -n "$(git -C "$rv_upstream" status --porcelain)" ]]; then
	echo "Canonical upstream checkout is dirty; refusing fast candidate build." >&2
	git -C "$rv_upstream" status --short >&2
	exit 3
fi
rv_revision_actual=$(git -C "$rv_upstream" rev-parse HEAD)
echo "Upstream revision: $rv_revision_actual"

if [[ "${RENEGADE_FAST_RESTAGE:-0}" == "1" ]] || [[ ! -f "$rv_root/staging/wwlib/mixfile.cpp" ]]; then
	echo "Fast restage requested or staging missing: running deterministic staging."
	RENEGADE_INCREMENTAL_STAGE="${RENEGADE_INCREMENTAL_STAGE:-1}" bash "$rv_root/tools/stage_sources.sh"
else
	echo "Fast restage skipped: reusing current staged source pool."
fi
if find "$rv_root/staging" -type f \( -name '*.orig' -o -name '*.rej' \) -print -quit | grep -q .; then
	echo "Staging contains patch backup/reject debris." >&2
	exit 5
fi

if [[ "$rv_fast_tests" == "focused" ]]; then
	echo "Running focused fast contracts..."
	python3 -m unittest \
		tools.test_vita_loading_screen_contract \
		tools.test_vita_indexed_state_contract \
		tools.test_vita_skin_submission_contract \
		tools.test_vita_hanim_combo_guard \
		tools.test_mission_conversation_diagnostics_contract \
		tools.test_vita_texture_provenance_contract \
		tools.test_vita_texture_surface_contract \
		tools.test_a4_original_frontend_contract \
		tools.test_vita_camera_input_contract \
		tools.test_input_route_contract \
		tools.test_validate_vita_input_route \
		tools.test_stage_sources_incremental_contract \
		tools.test_vita_audio_provider
	echo "Running original DDSFileClass tga-alias executable contract..."
	cmake -S "$rv_root/tools/host_a30_definitions" -B "$rv_host_contract_build" -G Ninja \
		-DCMAKE_BUILD_TYPE=RelWithDebInfo \
		-DRENEGADE_USE_CCACHE=ON
	cmake --build "$rv_host_contract_build" \
		--target a35_ddsfile_tga_alias_contract_selftest \
		--parallel "$rv_build_jobs"
	"$rv_host_contract_build/a35_ddsfile_tga_alias_contract_selftest"
else
	echo "Focused fast contracts skipped by RENEGADE_FAST_TESTS=none."
fi

echo "Configuring stable Vita fast build tree..."
cmake -S "$rv_root" -B "$rv_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DCMAKE_TOOLCHAIN_FILE="$rv_vitasdk/share/vita.toolchain.cmake" \
	-DRENEGADE_USE_CCACHE=ON \
	-DRENEGADE_CANDIDATE_LABEL="$rv_candidate_label" \
	-DRENEGADE_VITA_CONTENT_ID="$rv_vpk_content_id"
grep -Fq "CCACHE_DIR=$rv_root/build/ccache" "$rv_build/build.ninja"

if [[ "$rv_fast_scope" == "compile" ]]; then
	echo "Building Vita ELF target incrementally; SELF/VPK packaging is skipped."
	cmake --build "$rv_build" --target RenegadeVitaA31 --parallel "$rv_build_jobs"
else
	echo "Building Vita target incrementally through SELF/VPK packaging."
	cmake --build "$rv_build" --parallel "$rv_build_jobs"
fi
echo "ccache statistics after fast Vita build:"
ccache --show-stats

rv_vpk="$rv_build/RenegadeVita-$rv_candidate_label.vpk"
rv_elf="$rv_build/RenegadeVitaA31"
rv_self="$rv_build/eboot.bin"
rv_map="$rv_build/RenegadeVita-$rv_candidate_label.map"
rv_elf_header="$rv_build/RenegadeVita-$rv_candidate_label.elf-header.txt"
rv_symbols="$rv_build/RenegadeVita-$rv_candidate_label.symbols.txt"
rv_vpk_contents="$rv_build/RenegadeVita-$rv_candidate_label.vpk-contents.txt"
rv_identity_report="$rv_build/$rv_candidate_label-FAST-IDENTITY-VERIFICATION.json"
rv_compile_report="$rv_build/$rv_candidate_label-FAST-COMPILE-REPORT.txt"
rv_build_report="$rv_build/$rv_candidate_label-FAST-BUILD-REPORT.txt"
test -s "$rv_elf"
test -s "$rv_map"

echo "Validating fast candidate ELF identity..."
"$rv_vitasdk/bin/arm-vita-eabi-readelf" -h "$rv_elf" > "$rv_elf_header"
grep -q 'Class:.*ELF32' "$rv_elf_header"
grep -q 'Data:.*little endian' "$rv_elf_header"
grep -q 'Machine:.*ARM' "$rv_elf_header"
"$rv_vitasdk/bin/arm-vita-eabi-nm" -C "$rv_elf" > "$rv_symbols"
while IFS= read -r rv_symbol; do
	require_linked_symbol "$rv_symbol"
done <<'EOF'
A31_Vita_Run_Interactive_Runtime(int)
CombatManager::Load_Level_Threaded(char const*, bool)
CombatGameModeClass::Vita_Finalize_Loaded_Level(void*, bool)
RenegadeDialogMgrClass::Goto_Location(RenegadeDialogMgrClass::LOCATION)
MainMenuDialogClass::Display()
StartSPGameDialogClass::On_Command(int, int, unsigned long)
MenuGameModeClass2::Init()
MovieGameModeClass::Startup_Movies()
MovieGameModeClass::Start_Movie(char const*)
BINKMovie::Play(char const*, char const*, FontCharsClass*)
A4_Frontend_Latch_Start_Game(char const*, int, unsigned long)
A4_Frontend_Pump_WWUI_Key_Transitions()
WW3D::Render(SceneClass*
MeshClass::Render(RenderInfoClass&)
RenegadeVitaRenderer::Submit_Mesh(MeshClass&, RenderInfoClass&)
MenuBackDropClass::Render()
CampaignManager::Select_Backdrop_Number(int)
Render2DClass::Render()
WWAudioClass::WWAudioClass(bool)
AIL_startup()
RenegadeVitaAudio::Decode_Wave(unsigned char const*, unsigned int, RenegadeVitaAudio::DecodedWave*, char const**)
EOF
if [[ "$rv_fast_scope" == "compile" ]]; then
	{
		echo "Renegade Vita $rv_candidate_label FAST COMPILE REPORT"
		echo "Result: SUCCESS"
		echo "Scope: compile/link iteration only; SELF/VPK packaging and deployment artifacts were intentionally skipped."
		echo "Build dir: $rv_build"
		echo "Upstream revision: $rv_revision_actual"
		echo "Restage mode: ${RENEGADE_FAST_RESTAGE:-0}"
		echo "Fast tests: $rv_fast_tests"
		echo "Built target: RenegadeVitaA31"
		echo "ELF: $rv_elf"
		echo "Runtime log if later packaged: $rv_runtime_log"
	} > "$rv_compile_report"
	cp -- "$rv_elf" "$rv_dist/RenegadeVita-$rv_candidate_label.elf"
	cp -- "$rv_map" "$rv_dist/RenegadeVita-$rv_candidate_label.map"
	cp -- "$rv_elf_header" "$rv_dist/RenegadeVita-$rv_candidate_label.elf-header.txt"
	cp -- "$rv_symbols" "$rv_dist/RenegadeVita-$rv_candidate_label.symbols.txt"
	cp -- "$rv_compile_report" "$rv_dist/$rv_candidate_label-FAST-COMPILE-REPORT.txt"
	cp -- "$rv_log" "$rv_dist/$rv_candidate_label-FAST-COMPILE_LOG.txt"
	(
		cd "$rv_dist"
		sha256sum RenegadeVita-"$rv_candidate_label".elf \
			RenegadeVita-"$rv_candidate_label".map \
			RenegadeVita-"$rv_candidate_label".elf-header.txt \
			RenegadeVita-"$rv_candidate_label".symbols.txt \
			"$rv_candidate_label"-FAST-COMPILE-REPORT.txt \
			"$rv_candidate_label"-FAST-COMPILE_LOG.txt > "$rv_candidate_label"-FAST-COMPILE-SHA256SUMS.txt
		sha256sum -c "$rv_candidate_label"-FAST-COMPILE-SHA256SUMS.txt
	)
	trap - ERR
	echo
	echo "$rv_candidate_label FAST COMPILE SUCCESS"
	echo "ELF linked: $rv_dist/RenegadeVita-$rv_candidate_label.elf"
	echo "Package only when needed: RENEGADE_FAST_SCOPE=package bash tools/build_fast_candidate.sh"
	exit 0
fi

test -s "$rv_vpk"
test -s "$rv_self"
echo "Validating fast candidate SELF/VPK package identity..."
unzip -tq "$rv_vpk"
unzip -Z1 "$rv_vpk" > "$rv_vpk_contents"
grep -Fxq 'eboot.bin' "$rv_vpk_contents"
grep -Fxq 'sce_sys/param.sfo' "$rv_vpk_contents"
test "$(wc -l < "$rv_vpk_contents")" -eq 2
unzip -p "$rv_vpk" sce_sys/param.sfo | strings | grep -Fxq "$rv_vpk_content_id"
if grep -Eiq '(^|/)(retail|data)(/|$)|(^|/)(always[^/]*\.(dat|dbs)|[^/]+\.(mix|w3d|rva))$' "$rv_vpk_contents"; then
	echo "Retail or custom asset content was unexpectedly packaged in the VPK." >&2
	exit 9
fi
python3 "$rv_root/tools/verify_candidate_identity.py" \
	--elf "$rv_elf" --self "$rv_self" --vpk "$rv_vpk" \
	--candidate "$rv_candidate_label" --runtime-log "$rv_runtime_log" \
	--output "$rv_identity_report"
grep -Fq '"status": "PASS"' "$rv_identity_report"

{
	echo "Renegade Vita $rv_candidate_label FAST BUILD REPORT"
	echo "Result: SUCCESS"
	echo "Scope: fast hardware-candidate iteration only; canonical acceptance still requires bash ./tools/build.sh and physical Vita evidence."
	echo "Build dir: $rv_build"
	echo "Upstream revision: $rv_revision_actual"
	echo "Restage mode: ${RENEGADE_FAST_RESTAGE:-0}"
	echo "Fast tests: $rv_fast_tests"
	echo "Focused contracts: loading screen, CombatGameMode load-finalization, shader cache/prewarm, indexed state, direct mesh base-pass replay, stage-1 multitexture boundary, streamed-dialogue fact/duration runtime metadata, skin submission, animation combo guard, conversation diagnostics, texture provenance, texture surface copy/upload ownership, retail DDS top-down upload ownership, DDS retained surface levels, camera/input route, audio provider, DDS-first texture boundary, original DDSFileClass tga-to-dds alias, original Commando frontend source/movie/menu/tutorial route"
	echo "VPK contains: eboot.bin and sce_sys/param.sfo only"
	echo "Runtime log: $rv_runtime_log"
} > "$rv_build_report"

cp -- "$rv_vpk" "$rv_dist/RenegadeVita-$rv_candidate_label.vpk"
cp -- "$rv_elf" "$rv_dist/RenegadeVita-$rv_candidate_label.elf"
cp -- "$rv_map" "$rv_dist/RenegadeVita-$rv_candidate_label.map"
cp -- "$rv_elf_header" "$rv_dist/RenegadeVita-$rv_candidate_label.elf-header.txt"
cp -- "$rv_symbols" "$rv_dist/RenegadeVita-$rv_candidate_label.symbols.txt"
cp -- "$rv_vpk_contents" "$rv_dist/RenegadeVita-$rv_candidate_label.vpk-contents.txt"
cp -- "$rv_identity_report" "$rv_dist/$rv_candidate_label-FAST-IDENTITY-VERIFICATION.json"
cp -- "$rv_build_report" "$rv_dist/$rv_candidate_label-FAST-BUILD-REPORT.txt"
cp -- "$rv_log" "$rv_dist/$rv_candidate_label-FAST-COMPILER_LOG.txt"
{
	echo "Renegade Vita $rv_candidate_label fast hardware checkpoint"
	echo "Status: fast candidate; physical Vita validation required; not canonical acceptance."
	echo "VPK: RenegadeVita-$rv_candidate_label.vpk"
	echo "Runtime log: $rv_runtime_log"
	echo "No Vita filesystem was accessed and no deployment was attempted."
} > "$rv_dist/$rv_candidate_label-FAST-HARDWARE-CANDIDATE.txt"
(
	cd "$rv_dist"
	sha256sum RenegadeVita-"$rv_candidate_label".vpk RenegadeVita-"$rv_candidate_label".elf \
		RenegadeVita-"$rv_candidate_label".map RenegadeVita-"$rv_candidate_label".elf-header.txt \
		RenegadeVita-"$rv_candidate_label".symbols.txt RenegadeVita-"$rv_candidate_label".vpk-contents.txt \
		"$rv_candidate_label"-FAST-IDENTITY-VERIFICATION.json \
		"$rv_candidate_label"-FAST-BUILD-REPORT.txt "$rv_candidate_label"-FAST-COMPILER_LOG.txt \
		"$rv_candidate_label"-FAST-HARDWARE-CANDIDATE.txt > "$rv_candidate_label"-FAST-SHA256SUMS.txt
	sha256sum -c "$rv_candidate_label"-FAST-SHA256SUMS.txt
)

trap - ERR
echo
echo "$rv_candidate_label FAST CANDIDATE BUILD SUCCESS"
echo "Install manually only when requested: $rv_dist/RenegadeVita-$rv_candidate_label.vpk"
echo "Canonical acceptance remains: bash ./tools/build.sh plus physical Vita evidence."
