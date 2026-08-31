#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_managed_builder_root=${RENEGADE_BUILDER_ROOT:-"/mnt/c/Users/${USER}/AppData/Local/RenegadeVitaBuilder"}
if [ -d "$rv_managed_builder_root" ] && [ -w "$rv_managed_builder_root" ]; then
	rv_builder_root=$rv_managed_builder_root
else
	rv_builder_root=$rv_root
fi

rv_candidate_label=${RENEGADE_CANDIDATE_LABEL:-A3.5-dev86}
rv_vitasdk=${RENEGADE_VITASDK:-${VITASDK:-/usr/local/vitasdk}}
rv_jobs=${RENEGADE_BUILD_JOBS:-4}
rv_repo=https://github.com/Rinnegatamante/Vita-MP4-Recorder.git
rv_commit=60c966a75356ea9a95f79479a3e647283586cf11
rv_source_cache=${RENEGADE_SOURCE_CACHE:-"$rv_builder_root/source-cache"}
rv_ref="$rv_source_cache/vita-mp4-recorder-$rv_commit"
rv_work="$rv_root/build/renegade-demo-recorder/vita-mp4-recorder-$rv_commit"
rv_build="$rv_root/build/renegade-demo-recorder/build"
rv_dist="$rv_builder_root/dist"
rv_patch="$rv_root/tools/vita_plugins/renegade_demo_recorder/vita-mp4-recorder-renegade-autostart.patch"
rv_out_stem="RenegadeDemoRecorder-$rv_candidate_label"

case "$rv_candidate_label" in A[0-9]*.[0-9]*-dev[0-9]*) ;; *) printf 'Invalid RENEGADE_CANDIDATE_LABEL: %s\n' "$rv_candidate_label" >&2; exit 2 ;; esac
case "$rv_jobs" in ''|*[!0-9]*|0) printf 'Invalid RENEGADE_BUILD_JOBS: %s\n' "$rv_jobs" >&2; exit 2 ;; esac

for rv_command in git cmake make patch sha256sum; do
	command -v "$rv_command" >/dev/null 2>&1 || {
		printf 'Required command is unavailable: %s\n' "$rv_command" >&2
		exit 2
	}
done

test -f "$rv_vitasdk/share/vita.toolchain.cmake" || {
	printf 'VitaSDK toolchain is unavailable: %s/share/vita.toolchain.cmake\n' "$rv_vitasdk" >&2
	exit 2
}
rv_mp4rec_include_root="$rv_vitasdk/arm-vita-eabi/include"
rv_mp4rec_header="$rv_mp4rec_include_root/psp2/mp4rec.h"
if [ ! -f "$rv_mp4rec_header" ]; then
	rv_mp4rec_include_root="$rv_root/tools/vita_plugins/renegade_demo_recorder/include"
	rv_mp4rec_header="$rv_mp4rec_include_root/psp2/mp4rec.h"
fi
test -f "$rv_mp4rec_header" || {
	printf 'SceLibMp4Recorder header is unavailable: checked VitaSDK and %s\n' "$rv_mp4rec_header" >&2
	exit 2
}
if [ ! -f "$rv_vitasdk/arm-vita-eabi/lib/libSceLibMp4Recorder_stub_weak.a" ] &&
	[ ! -f "$rv_vitasdk/arm-vita-eabi/lib/libSceLibMp4Recorder_stub.a" ]; then
	printf 'SceLibMp4Recorder stubs are unavailable under %s/arm-vita-eabi/lib\n' "$rv_vitasdk" >&2
	exit 2
fi
test -f "$rv_patch" || {
	printf 'Renegade demo recorder patch is missing: %s\n' "$rv_patch" >&2
	exit 2
}

mkdir -p "$rv_source_cache" "$rv_root/build/renegade-demo-recorder" "$rv_dist"

if [ ! -d "$rv_ref/.git" ]; then
	rm -rf "$rv_ref"
	git init "$rv_ref"
	git -C "$rv_ref" remote add origin "$rv_repo"
	git -C "$rv_ref" fetch --depth 1 origin "$rv_commit"
	git -C "$rv_ref" checkout --detach FETCH_HEAD
fi

rv_actual_commit=$(git -C "$rv_ref" rev-parse HEAD)
if [ "$rv_actual_commit" != "$rv_commit" ]; then
	printf 'Unexpected Vita-MP4-Recorder commit: %s\n' "$rv_actual_commit" >&2
	exit 3
fi

rm -rf "$rv_work" "$rv_build"
mkdir -p "$rv_work" "$rv_build/user" "$rv_build/kernel"
git -C "$rv_ref" archive --format=tar "$rv_commit" | tar -x -C "$rv_work"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_work" -p1 < "$rv_patch"
perl -0pi -e 's/\bsceIofilemgrForDriver_stub\b/SceIofilemgrForDriver_stub/g' "$rv_work/kernel/CMakeLists.txt"

export VITASDK="$rv_vitasdk"

cmake -S "$rv_work/user" -B "$rv_build/user" \
	-DCMAKE_TOOLCHAIN_FILE="$rv_vitasdk/share/vita.toolchain.cmake" \
	-DVITASDK="$rv_vitasdk" \
	-DRELEASE=ON \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_C_FLAGS="-I$rv_mp4rec_include_root -include psp2/mp4rec.h"
cmake --build "$rv_build/user" --parallel "$rv_jobs"

cmake -S "$rv_work/kernel" -B "$rv_build/kernel" \
	-DCMAKE_TOOLCHAIN_FILE="$rv_vitasdk/share/vita.toolchain.cmake" \
	-DVITASDK="$rv_vitasdk" \
	-DRELEASE=ON \
	-DCMAKE_BUILD_TYPE=Release
cmake --build "$rv_build/kernel" --parallel "$rv_jobs"

cp "$rv_build/user/VitaMP4Recorder.suprx" "$rv_dist/$rv_out_stem.suprx"
cp "$rv_build/kernel/kVitaMP4Recorder.skprx" "$rv_dist/$rv_out_stem.skprx"

cat > "$rv_dist/$rv_out_stem-tai-config.txt" <<EOF
# Renegade demo recording plugin for title-scoped $rv_candidate_label capture.
# Copy the two generated files to ur0:tai/ first, then add this to tai config.
*KERNEL
ur0:tai/$rv_out_stem.skprx
*RNEGA3101
ur0:tai/$rv_out_stem.suprx
EOF

(
	cd "$rv_dist"
	sha256sum "$rv_out_stem.suprx" "$rv_out_stem.skprx" "$rv_out_stem-tai-config.txt" > "$rv_out_stem-SHA256SUMS.txt"
)

printf 'Renegade demo recorder built from Vita-MP4-Recorder %s\n' "$rv_commit"
printf 'User plugin:   %s\n' "$rv_dist/$rv_out_stem.suprx"
printf 'Kernel plugin: %s\n' "$rv_dist/$rv_out_stem.skprx"
printf 'tai snippet:   %s\n' "$rv_dist/$rv_out_stem-tai-config.txt"
printf 'SHA manifest:  %s\n' "$rv_dist/$rv_out_stem-SHA256SUMS.txt"
printf 'Manual install only. This script did not touch the PS Vita filesystem.\n'
