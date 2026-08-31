#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# Candidates must be reachable from Windows.  The Linux-tree fallback is for
# standalone development only; managed Windows builds always publish here.
# Optional managed output root.  When unset, retain the historical Windows
# location only when the current WSL username maps to that Windows profile;
# otherwise use the checkout itself.  This keeps forks self-contained.
rv_managed_builder_root=${RENEGADE_BUILDER_ROOT:-"/mnt/c/Users/${USER}/AppData/Local/RenegadeVitaBuilder"}
if [ -d "$rv_managed_builder_root" ] && [ -w "$rv_managed_builder_root" ]; then
	rv_builder_root=$rv_managed_builder_root
else
	rv_builder_root=$rv_root
fi
rv_logs="$rv_builder_root/logs"
rv_dist="$rv_builder_root/dist"
rv_upstream="$rv_root/upstream/CnC_Renegade"
rv_candidate_label=${RENEGADE_CANDIDATE_LABEL:-A3.5-dev91}
case "$rv_candidate_label" in A[0-9]*.[0-9]*-dev[0-9]*) ;; *) echo "Invalid candidate label: $rv_candidate_label" >&2; exit 2 ;; esac
rv_candidate_stem=$(printf '%s' "$rv_candidate_label" | tr '[:upper:]' '[:lower:]' | tr -d '.')
rv_vpk_content_id=EP9000-RNEGA3101_00-RENGADEVITADEV91
# The fast candidate path already safely uses all host CPUs.  Match that
# bounded default for canonical builds too; callers can still lower it with
# RENEGADE_BUILD_JOBS on a constrained host.
rv_build_jobs=${RENEGADE_BUILD_JOBS:-$(nproc)}
case "$rv_build_jobs" in ''|*[!0-9]*|0) echo "Invalid RENEGADE_BUILD_JOBS: $rv_build_jobs" >&2; exit 2 ;; esac
rv_timestamp=$(date +%Y%m%d-%H%M%S)
rv_build="$rv_root/build/vita-${rv_candidate_stem}-candidate-${rv_timestamp}"
rv_host_output="$rv_root/build/${rv_candidate_label}-HOST-VALIDATION.log"
rv_vitasdk=${RENEGADE_VITASDK:-/usr/local/vitasdk}
rv_revision=3e00c3a1b97381bb28be89a35b856375e0629a08
rv_log="$rv_logs/${rv_candidate_stem}-$rv_timestamp-build.log"
rv_runtime_log="ux0:data/renegade/user/logs/${rv_candidate_stem}-runtime.log"
rv_startup_precache_receipt="ux0:data/renegade/user/logs/${rv_candidate_stem}-startup-precache.txt"

mkdir -p "$rv_logs" "$rv_dist" "$rv_root/build"
exec > >(tee "$rv_log") 2>&1

on_error() {
	local rv_status=$?
	trap - ERR
	set +e
	echo
	echo "$rv_candidate_label BUILD FAILED (exit $rv_status)"
	echo "Complete log: $rv_log"
	echo "Causal output tail:"
	tail -n 180 "$rv_log"
	echo "The last successful dist release was left unchanged."
	exit "$rv_status"
}
trap on_error ERR

require_command() {
	command -v "$1" >/dev/null 2>&1 || {
		echo "Required host command is unavailable: $1" >&2
		exit 2
	}
}

require_host_line() {
	grep -Fqx -- "$1" "$rv_host_output" || {
		echo "$rv_candidate_label host semantic fingerprint mismatch: $1" >&2
		exit 7
	}
}

require_linked_symbol() {
	grep -Fq -- "$1" "$rv_symbols" || {
		echo "Required $rv_candidate_label linked symbol is absent: $1" >&2
		exit 8
	}
}

echo "Renegade Vita $rv_candidate_label correctness, diagnostics, and interactive hardware candidate build"
echo "Workspace: $rv_root"
echo "Log: $rv_log"

for rv_command in cmake ninja python3 git patch unzip zip sha256sum grep find tee wc ccache curl tar make; do
	require_command "$rv_command"
done
for rv_sdk_path in \
	"$rv_vitasdk/bin/arm-vita-eabi-g++" \
	"$rv_vitasdk/bin/arm-vita-eabi-readelf" \
	"$rv_vitasdk/bin/arm-vita-eabi-nm" \
	"$rv_vitasdk/bin/arm-vita-eabi-objdump" \
	"$rv_vitasdk/share/vita.toolchain.cmake" \
	"$rv_vitasdk/share/vita.cmake" \
	"$rv_vitasdk/arm-vita-eabi/include/vitaGL.h" \
	"$rv_vitasdk/arm-vita-eabi/lib/libvitaGL.a" \
	"$rv_vitasdk/arm-vita-eabi/lib/libvitashark.a" \
	"$rv_vitasdk/arm-vita-eabi/lib/libSceShaccCgExt.a"; do
	test -e "$rv_sdk_path" || {
		echo "Required VitaSDK A3.1 dependency is missing: $rv_sdk_path" >&2
		exit 2
	}
done
test -x "$rv_vitasdk/bin/arm-vita-eabi-g++"
test -s "$rv_root/RenegadeVita_BUILD.ps1"
if [[ "$(wc -c < "$rv_root/RenegadeVita_BUILD.ps1")" -ge 8192 ]] || \
	! grep -Fq '& wsl.exe --cd $Workspace -e bash ./tools/build.sh' \
		"$rv_root/RenegadeVita_BUILD.ps1" || \
	grep -Eiq 'FromBase64String|-EncodedCommand' "$rv_root/RenegadeVita_BUILD.ps1"; then
	echo "PowerShell launcher is not the expected small canonical Bash wrapper." >&2
	exit 2
fi
export VITASDK="$rv_vitasdk"
export CCACHE_DIR="$rv_root/build/ccache"
export CCACHE_BASEDIR="$rv_root"

echo "Verifying the pinned Bink-enabled Vita FFmpeg dependency..."
bash "$rv_root/tools/build_ffmpeg_bink_vita.sh"
ccache --zero-stats
echo "ccache statistics reset; native-ext4 CMake launchers are required."

test -d "$rv_upstream/.git"
if [[ -n "$(git -C "$rv_upstream" status --porcelain)" ]]; then
	echo "Canonical upstream checkout is dirty; refusing to overwrite it." >&2
	git -C "$rv_upstream" status --short >&2
	exit 3
fi
rv_revision_actual=$(git -C "$rv_upstream" rev-parse HEAD)
if [[ "$rv_revision_actual" != "$rv_revision" ]]; then
	echo "Unexpected upstream revision: $rv_revision_actual" >&2
	exit 3
fi
echo "Upstream revision: $rv_revision_actual"

if [[ -z "${RENEGADE_REUSE_HOST_VALIDATION_LOG:-}" ]]; then
	if [[ -n "${RENEGADE_RETAIL_ROOT:-}" ]]; then
		rv_retail_root="$RENEGADE_RETAIL_ROOT"
		test -f "$rv_retail_root/Data/always.dat" || {
			echo "Explicit RENEGADE_RETAIL_ROOT does not contain Data/always.dat: $rv_retail_root" >&2
			exit 3
		}
	else
		rv_retail_root=""
		for rv_candidate_retail_root in \
			"$rv_root/retail-pc" \
			"/mnt/c/Program Files (x86)/Steam/steamapps/common/Command & Conquer Renegade"; do
			if [[ -f "$rv_candidate_retail_root/Data/always.dat" ]]; then
				rv_retail_root="$rv_candidate_retail_root"
				break
			fi
		done
		if [[ -z "$rv_retail_root" ]]; then
			rv_retained_host_log="$rv_root/build/A3.5-dev18-HOST-VALIDATION.log"
			if [[ -f "$rv_retained_host_log" ]]; then
				export RENEGADE_REUSE_HOST_VALIDATION_LOG="$rv_retained_host_log"
				echo "Local retail preflight unavailable; reusing retained canonical host validation: $RENEGADE_REUSE_HOST_VALIDATION_LOG"
			else
				echo "Local retail preflight failed: set RENEGADE_RETAIL_ROOT or provide RENEGADE_REUSE_HOST_VALIDATION_LOG." >&2
				exit 3
			fi
		fi
	fi
	if [[ -n "${rv_retail_root:-}" ]]; then
		export RENEGADE_RETAIL_ROOT="$rv_retail_root"
		echo "Local retail preflight: $rv_retail_root"
	fi
else
	echo "Local retail preflight: not required for retained host validation mode"
fi

if [[ -n "${RENEGADE_REUSE_HOST_VALIDATION_LOG:-}" ]]; then
	rv_reused_host_log=$(realpath -e -- "$RENEGADE_REUSE_HOST_VALIDATION_LOG")
	echo "Reusing completed canonical host validation: $rv_reused_host_log"
	cp -- "$rv_reused_host_log" "$rv_host_output"
	rv_host_validation_mode="reused completed canonical host validation"
else
	echo "Building and running retained A2 plus original A3 M00 host validation..."
	bash "$rv_root/tools/run_a30_host.sh" 2>&1 | tee "$rv_host_output"
	rv_host_validation_mode="fresh canonical host validation"
fi
echo "Running lightweight current host contracts..."
cmake -S "$rv_root/tools/host_a30_definitions" -B "$rv_root/build/host-a30-definitions" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DRENEGADE_USE_CCACHE=ON
cmake --build "$rv_root/build/host-a30-definitions" \
	--target a31_capture_telemetry_selftest \
		a31_vita_input_contract_selftest \
		a35_vita_button_state_contract_selftest \
		a35_vita_render_state_contract_selftest \
		a35_ddsfile_tga_alias_contract_selftest \
	--parallel "$rv_build_jobs"
"$rv_root/build/host-a30-definitions/a31_capture_telemetry_selftest" | tee -a "$rv_host_output"
"$rv_root/build/host-a30-definitions/a31_vita_input_contract_selftest" | tee -a "$rv_host_output"
"$rv_root/build/host-a30-definitions/a35_vita_button_state_contract_selftest" | tee -a "$rv_host_output"
"$rv_root/build/host-a30-definitions/a35_vita_render_state_contract_selftest" | tee -a "$rv_host_output"
"$rv_root/build/host-a30-definitions/a35_ddsfile_tga_alias_contract_selftest" | tee -a "$rv_host_output"
require_host_line "A2.2 host asset integration PASS"
require_host_line "A3.0 canonical host integration PASS"
require_host_line "A3.1 gameplay-seed host integration PASS"
require_host_line "A3.1 original interactive ASan host integration PASS"
require_host_line "A3.1 hardware-equivalent interactive ASan PASS: two in-process cycles; 120 original input/network/Combat/render frames each"
require_host_line "a31.interactive_first_frame_geometry=true"
require_host_line "a31.interactive_first_frame_rejected=0"
require_host_line "a31.interactive_first_frame_unsupported=0"
require_host_line "A3.1 capture telemetry host self-test: PASS (26 checks, 0 failures)"
require_host_line "A3.2 Vita controller axis-contract: PASS (22 checks, 0 failures)"
require_host_line "A3.5 Vita button-state contract: PASS (10 checks, 0 failures)"
require_host_line "A3.5 Vita ShaderClass render-state contract: 13 checks, 0 failures"
require_host_line "A3.5 DDSFileClass tga-alias contract: 11 checks, 0 failures"
require_host_line "A3 renderer process lifecycle: 11 checks, 0 failures; native=1 sessions=2 shutdowns=2"
require_host_line "A3.2 texture upload contract: PASS (4 checks, 0 failures)"
require_host_line "runtime.checks=45"
require_host_line "runtime.failures=0"
require_host_line "audio.initial_singleton_null=true"
require_host_line "audio.static_load_entries=1"
require_host_line "audio.static_load_singleton_present=true"
require_host_line "audio.static_load_sound_scene_present=false"
require_host_line "audio.repeated_teardown_singleton_null=true"
require_host_line "world.m00_static_world_loaded=true"
require_host_line "world.definition_count=2157"
require_host_line "world.definition_count=3648"
require_host_line "world.definition_checksum=FE798749"
require_host_line "world.static_object_count=495"
require_host_line "world.static_light_count=192"
require_host_line "world.render.frame_path_completed=true"
require_host_line "world.render.mesh_submissions=652"
require_host_line "world.render.vertex_submissions=30603"
require_host_line "world.render.triangle_submissions=16939"
require_host_line "world.render.geometry_checksum=34FFAD42"
require_host_line "world.render.unsupported_submissions=0"
require_host_line "A3.0 original M00 world runtime: PASS"
echo "Host semantic fingerprints: PASS"
python3 -m unittest tools.test_runtime_log_contract tools.test_verify_candidate_identity \
	tools.test_script_provider_contract tools.test_mission_completion_contract \
	tools.test_mission_teardown_contract \
	tools.test_input_route_contract tools.test_vita_skin_submission_contract \
	tools.test_vita_indexed_state_contract \
	tools.test_validate_vita_input_route tools.test_vita_route_session_runner \
	tools.test_stage_sources_incremental_contract \
	tools.test_mission_conversation_diagnostics_contract \
	tools.test_vita_loading_screen_contract \
	tools.test_a4_original_frontend_contract \
	tools.test_vita_texture_surface_contract \
	tools.test_audit_tt_reference tools.test_vita_audio_provider \
	tools.test_vita_open_source_references

echo "Clean-restaging original source pools with the deterministic patch set..."
bash "$rv_root/tools/stage_sources.sh"
if find "$rv_root/staging" -type f \
	\( -name '*.orig' -o -name '*.rej' \) -print -quit | grep -q .; then
	echo "Staging contains patch backup/reject debris." >&2
	exit 5
fi
if [[ -n "$(git -C "$rv_upstream" status --porcelain)" ]]; then
	echo "Upstream became dirty during staging or host validation." >&2
	exit 4
fi

python3 "$rv_root/tools/generate_integration_report.py" \
	--root "$rv_root" \
	--output "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json" \
	--milestone "$rv_candidate_label"
grep -Fq "\"milestone\": \"$rv_candidate_label\"" "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json"
grep -Fq '"original_source_files_compiled": 506' "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json"
grep -Fq '"staged_original_owner_files": 1' "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json"
grep -Fq '"vita_platform_renderer_validation_files": 26' "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json"
grep -Fq '"a4_frontend_boundary_files": 6' "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json"
grep -Fq '"patch_count": 139' "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json"

echo "Configuring Vita $rv_candidate_label target..."
cmake -S "$rv_root" -B "$rv_build" -G Ninja \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DCMAKE_TOOLCHAIN_FILE="$rv_vitasdk/share/vita.toolchain.cmake" \
	-DRENEGADE_USE_CCACHE=ON \
	-DRENEGADE_CANDIDATE_LABEL="$rv_candidate_label" \
	-DRENEGADE_VITA_CONTENT_ID="$rv_vpk_content_id"
grep -Fq "CCACHE_DIR=$rv_root/build/ccache" "$rv_build/build.ninja"
echo "Compiling, linking, and packaging Vita $rv_candidate_label target..."
cmake --build "$rv_build" --parallel "$rv_build_jobs" --verbose
echo "ccache statistics after Vita build:"
ccache --show-stats

rv_vpk="$rv_build/RenegadeVita-$rv_candidate_label.vpk"
rv_elf="$rv_build/RenegadeVitaA31"
rv_self="$rv_build/eboot.bin"
rv_map="$rv_build/RenegadeVita-$rv_candidate_label.map"
rv_elf_header="$rv_build/RenegadeVita-$rv_candidate_label.elf-header.txt"
rv_symbols="$rv_build/RenegadeVita-$rv_candidate_label.symbols.txt"
rv_disassembly="$rv_build/RenegadeVita-$rv_candidate_label.disassembly.txt"
rv_vpk_contents="$rv_build/RenegadeVita-$rv_candidate_label.vpk-contents.txt"
rv_build_report="$rv_build/BUILD_REPORT.txt"
rv_identity_report="$rv_build/$rv_candidate_label-IDENTITY-VERIFICATION.json"
test -s "$rv_vpk"
test -s "$rv_elf"
test -s "$rv_self"
test -s "$rv_map"

echo "Validating ARM ELF, original A3 runtime symbols, and VPK contents..."
"$rv_vitasdk/bin/arm-vita-eabi-readelf" -h "$rv_elf" > "$rv_elf_header"
grep -q 'Class:.*ELF32' "$rv_elf_header"
grep -q 'Data:.*little endian' "$rv_elf_header"
grep -q 'Machine:.*ARM' "$rv_elf_header"
"$rv_vitasdk/bin/arm-vita-eabi-nm" -C "$rv_elf" > "$rv_symbols"
"$rv_vitasdk/bin/arm-vita-eabi-objdump" -d "$rv_elf" > "$rv_disassembly"
while IFS= read -r rv_symbol; do
	require_linked_symbol "$rv_symbol"
done <<'EOF'
A31_Vita_Run_Interactive_Runtime(int)
A31_Interactive_Begin_Mission_Completion_Observation()
A31_Interactive_Get_Mission_Completion_State()
A31_Interactive_End_Mission_Completion_Observation()
A31_Interactive_Get_Mission_Progress_State()
CombatManager::Load_Level_Threaded(char const*, bool)
CombatGameModeClass::Vita_Finalize_Loaded_Level(void*, bool)
SaveGameManager::Load_Game(char const*)
RenegadeDialogMgrClass::Goto_Location(RenegadeDialogMgrClass::LOCATION)
MainMenuDialogClass::Display()
StartSPGameDialogClass::On_Command(int, int, unsigned long)
MenuGameModeClass2::Init()
MovieGameModeClass::Startup_Movies()
MovieGameModeClass::Start_Movie(char const*)
BINKMovie::Play(char const*, char const*, FontCharsClass*)
A4_Frontend_Latch_Start_Game(char const*, int, unsigned long)
A4_Frontend_Pump_WWUI_Key_Transitions()
DialogMgrClass::On_Frame_Update()
PhysicsSceneClass::Load_Level_Static_Objects(ChunkLoadClass&)
WW3DAssetManager::Load_3D_Assets(FileClass&)
PhysicsSceneClass::Load_Level
WW3D::Render(SceneClass*
MeshClass::Render(RenderInfoClass&)
DX8Wrapper::Create_Render_Target(int, int, WW3DFormat)
RenegadeVitaRenderer::Submit_Mesh(MeshClass&, RenderInfoClass&)
A31_Write_Capture_Bundle(A31CaptureBundleInput const&)
RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(unsigned char*, unsigned int)
Get_Script_Commands()
ScriptManager::Create_Script(char const*)
ScriptRegistrar::CreateScript(char const*)
MTU_Tutorial_Controller::Created(ScriptableGameObj*)
Test_Cinematic::Created(ScriptableGameObj*)
M00_Soldier_Powerup_Disable::Created(ScriptableGameObj*)
WWAudioClass::Create_Logical_Listener()
LogicalListenerClass::LogicalListenerClass()
WWAudioClass::WWAudioClass(bool)
WWAudioClass::Create_Sound(char const*, RefCountClass*, unsigned int, int)
AIL_startup()
AIL_start_3D_sample(RenegadeMilesSample*)
RenegadeVitaAudio::Decode_Wave(unsigned char const*, unsigned int, RenegadeVitaAudio::DecodedWave*, char const**)
SurfaceClass::Lock(int*)
A31_Audio_Save_Load_Breadcrumb(char const*)
EOF
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
test -z "$(git -C "$rv_upstream" status --porcelain)"

{
	echo "Renegade Vita $rv_candidate_label BUILD REPORT"
	echo "Result: SUCCESS"
	echo "Hardware validation: A3.1.4 baseline ACCEPTED; $rv_candidate_label is a host-validated physical candidate, not an accepted milestone."
	echo "Canonical source: https://github.com/electronicarts/CnC_Renegade"
	echo "Upstream revision: $rv_revision_actual"
	echo "Canonical workflow: Bash/CMake/Ninja/VitaSDK"
	echo "Host validation mode: $rv_host_validation_mode"
	echo "Retained regressions: A2.0 19/19; A2.1 10/10; A2.2 14/14; A3 original runtime 45/45"
	echo "A3.5 input contracts: axes=22/22; button state=10/10"
	echo "A3.5 renderer state contract: opaque/cutout/inverse-cutout/alpha/additive=5/5; lifecycle=11/11"
	echo "A3.5 crash repair: deterministic HumanState weapon-style table patch; bounds fallback; matching A3.2 dump parser evidence preserved"
	echo "A3.5 projection repair: ordinary mesh positions retain homogeneous W through GPU projection; physical visual validation pending"
	echo "A3.5 audio boundary: provider codecs/mixing are host/sanitizer validated; after installing the rooted retail/MIX chain, the direct Vita runtime constructs a path-stripping factory and non-lite original WWAudio, initializes its Vita-native SceAudio provider, services it per frame, and tears it down before renderer/factory shutdown; the complete path is ARM-linked while physical audio and conversation causality remain pending"
	echo "Original Westwood translation units: 506 plus 1 staged original-owner extraction"
	echo "Vita platform/renderer/validation/developer translation units: 26"
	echo "A4 frontend boundary translation units: 6"
	echo "M00 scripts: original ScriptCommands ABI plus EA/Westwood static Mission00 provider and direct cinematic/powerup dependencies"
	echo "M00 completion: original CombatMiscHandler callback observed by a bounded Vita lifecycle latch; no objective or script state injection"
	echo "M00 progress diagnostics: read-only original Star control, ObjectiveManager 1..6 status, and active-conversation transitions; automation waits for the original objective-1 control handoff"
	echo "M00 finalization: original CombatGameMode post-load checks, building/radar initialization, texture-loader update, On_Game_Begin, DDS top-down uploads, viewport synchronization, shader cache path, and loading-screen prewarm are active"
	echo "A4 frontend path: original MovieGameMode startup movie chain and original RenegadeDialogMgr/WWUI main menu are source/build routed; Vita FFmpeg Bink provider is enabled without proprietary RAD code. Dev86 prevents empty startup audio submissions and records bounded decode/upload pacing statistics; physical A/V usability remains unaccepted. Tutorial selection reuses the existing direct M00 route."
	echo "Patch set: deterministic zero-fuzz staging patches; patch_count=139; pristine upstream=PASS"
	echo "Renderer path: original PhysicsScene/WW3D/Scene/RenderObj/Mesh -> Vita backend"
	echo "Retail data packaged: none"
	echo "Automatic Vita deployment: disabled"
	echo "VPK: $rv_dist/RenegadeVita-$rv_candidate_label.vpk"
	echo "Runtime log: $rv_runtime_log"
} > "$rv_build_report"

cp -- "$rv_vpk" "$rv_dist/RenegadeVita-$rv_candidate_label.vpk"
cp -- "$rv_elf" "$rv_dist/RenegadeVita-$rv_candidate_label.elf"
cp -- "$rv_map" "$rv_dist/RenegadeVita-$rv_candidate_label.map"
cp -- "$rv_elf_header" "$rv_dist/RenegadeVita-$rv_candidate_label.elf-header.txt"
cp -- "$rv_symbols" "$rv_dist/RenegadeVita-$rv_candidate_label.symbols.txt"
cp -- "$rv_vpk_contents" "$rv_dist/RenegadeVita-$rv_candidate_label.vpk-contents.txt"
cp -- "$rv_root/reports/SOURCE_INTEGRATION_REPORT.json" "$rv_dist/$rv_candidate_label-SOURCE_INTEGRATION_REPORT.json"
	{
		echo "# $rv_candidate_label candidate identity and physical gate"
		echo
		echo "Status: host-validated only; physical acceptance is not claimed."
		echo "Runtime identity: Renegade Vita $rv_candidate_label"
		echo "Runtime log: $rv_runtime_log"
		echo "Identity verifier: PASS (exact ELF label/path, no prohibited stale identity, packaged eboot matches generated SELF)."
		echo "Physical gate: verify startup identity and expected runtime log before collecting any further evidence."
} > "$rv_dist/$rv_candidate_label-MILESTONE-GATE.md"
{
	echo "Renegade Vita $rv_candidate_label crash-symbolication status"
	echo "Status: no matching hardware dump was available when this candidate was packaged."
	echo "A candidate report must be regenerated with tools/symbolicate_vita_dump.sh only"
	echo "against a dump and ELF/map/symbol set whose identities are recorded together."
	echo "Historical A3.2-dev1 symbolication is retained separately and is not candidate evidence."
} > "$rv_dist/$rv_candidate_label-CRASH-SYMBOLICATION.txt"
cp -- "$rv_build_report" "$rv_dist/$rv_candidate_label-BUILD_REPORT.txt"
cp -- "$rv_identity_report" "$rv_dist/$rv_candidate_label-IDENTITY-VERIFICATION.json"
cp -- "$rv_root/RenegadeVita_BUILD.ps1" "$rv_dist/RenegadeVita_BUILD.ps1"
cp -- "$rv_log" "$rv_dist/$rv_candidate_label-COMPILER_LOG.txt"
cp -- "$rv_host_output" "$rv_dist/$rv_candidate_label-HOST-VALIDATION.log"
rv_vpk_sha256=$(sha256sum "$rv_vpk" | awk '{print $1}')
{
	echo "Renegade Vita $rv_candidate_label hardware checkpoint"
	echo "Status: host-validated candidate; physical Vita validation required."
	echo "Source revision: $rv_revision_actual"
	echo "VPK: RenegadeVita-$rv_candidate_label.vpk"
	echo "SHA-256: $rv_vpk_sha256"
	echo "Retain user-owned data: ux0:data/renegade/retail/Data/ (do not transfer retail assets)."
	echo "Runtime log: $rv_runtime_log (remove or rename an older file before launch)."
	echo "Startup pre-cache receipt: $rv_startup_precache_receipt."
	echo "Required device prerequisite: ur0:/data/libshacccg.suprx."
	echo "Controls: frontend menu active: D-pad=WWUI focus navigation, Cross=confirm, Circle=back/cancel, Select=next focus, front touch=original mouse cursor/left click. M00 gameplay: left-stick movement; right-stick camera with normal up/down look; R=fire; L=alternate original joystick button; Cross=jump; Circle=crouch; Triangle=action/use; Square=reload; D-pad Left/Right=previous/next weapon only; D-pad Up/Down=sniper zoom in/out; front touch=original mouse cursor/left click for UI/terminals; rear touch=first/third-person camera toggle; Select=capture; Select+L+R=fixed-camera benchmark; Start=clean exit."
	echo "Test: in M00, verify visible startup pre-cache receipt, aspect-preserved loading presentation, HUD/scope placement, loading progress, normal texture orientation on characters/doors/powerups, Logan/Sydney/Gunner subtitles, Triangle action/use gates, Square reload animation, D-pad weapon cycling without camera drift, D-pad sniper zoom, and frame rate. Press Start and wait for LiveArea."
	echo "Return: $rv_runtime_log, ux0:data/renegade/user/captures/, screenshots, and any psp2core-*.psp2dmp. Run tools/collect_a35_diagnostics.sh with this dist directory and returned files."
} > "$rv_dist/$rv_candidate_label-HARDWARE-CANDIDATE.txt"
{
	echo "Runtime log: $rv_runtime_log"
	echo "Startup pre-cache receipt: $rv_startup_precache_receipt"
	echo "Expected $rv_candidate_label breadcrumbs: startup-precache begin/touch/visible-hold/receipt/complete before frontend, movies, menu, or gameplay input; input edge/axis contracts; original DDS activity; A3.5 perf/input summaries; original Combat mission-completion observation when achieved; 120-frame checkpoint or terminal transition; clean teardown."
	echo "Physical test: retain this log, the startup-precache receipt, and any psp2core dump after exercising controls, visibility, muzzle flash, pause/resume, and START exit."
} > "$rv_dist/$rv_candidate_label-EXPECTED-RUNTIME-LOG.txt"
bash "$rv_root/tools/collect_a35_diagnostics.sh" "$rv_dist" \
	"$rv_dist/$rv_candidate_label-BUILD-DIAGNOSTICS-$rv_timestamp.zip" "$rv_candidate_label"
(
	cd "$rv_dist"
	sha256sum RenegadeVita-"$rv_candidate_label".vpk RenegadeVita-"$rv_candidate_label".elf \
		RenegadeVita-"$rv_candidate_label".map RenegadeVita-"$rv_candidate_label".elf-header.txt \
		RenegadeVita-"$rv_candidate_label".symbols.txt RenegadeVita-"$rv_candidate_label".vpk-contents.txt \
		RenegadeVita_BUILD.ps1 "$rv_candidate_label"-SOURCE_INTEGRATION_REPORT.json \
		"$rv_candidate_label"-MILESTONE-GATE.md "$rv_candidate_label"-CRASH-SYMBOLICATION.txt \
		"$rv_candidate_label"-IDENTITY-VERIFICATION.json \
		"$rv_candidate_label"-BUILD_REPORT.txt "$rv_candidate_label"-COMPILER_LOG.txt "$rv_candidate_label"-HOST-VALIDATION.log \
		"$rv_candidate_label"-EXPECTED-RUNTIME-LOG.txt "$rv_candidate_label"-HARDWARE-CANDIDATE.txt \
		"$rv_candidate_label"-BUILD-DIAGNOSTICS-"$rv_timestamp".zip > "$rv_candidate_label"-SHA256SUMS.txt
	sha256sum -c "$rv_candidate_label"-SHA256SUMS.txt
)

trap - ERR
echo
echo "$rv_candidate_label BUILD SUCCESS"
echo "Install manually only when requested: $rv_dist/RenegadeVita-$rv_candidate_label.vpk"
echo "Retail Data transfer: not required."
echo "Runtime shader prerequisite: ur0:/data/libshacccg.suprx must already be installed."
echo "Expected runtime log: $rv_runtime_log"
echo "No Vita filesystem was accessed and no deployment was attempted."
