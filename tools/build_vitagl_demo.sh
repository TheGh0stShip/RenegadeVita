#!/usr/bin/env bash
set -Eeuo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
sdk=${RENEGADE_VITASDK:-/usr/local/vitasdk}
export PATH="$sdk/bin:$PATH"
export VITASDK="$sdk"
revision=6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5
layout_patch="$root/port/renderer/vita/dependency-patches/vitagl-compact-unlit.patch"
indexed_patch="$root/port/renderer/vita/dependency-patches/vitagl-indexed-immediate.patch"
upload_patch="$root/port/renderer/vita/dependency-patches/vitagl-full-rgba-upload.patch"
dds_patch="$root/port/renderer/vita/dependency-patches/vitagl-dds-chain.patch"
work="$root/build/deps/vitagl-demo"
mkdir -p "$work"
exec 9>"$work/build.lock"
flock 9
if [[ ! -f "$work/source.tar.gz" ]]; then
    curl --fail --location --retry 2 --max-time 120 \
        "https://codeload.github.com/Rinnegatamante/vitaGL/tar.gz/$revision" \
        -o "$work/source.tar.gz.part"
    mv "$work/source.tar.gz.part" "$work/source.tar.gz"
fi
if [[ ! -f "$work/source/Makefile" ]]; then
    mkdir -p "$work/source"
    tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source"
fi
# Command-line CFLAGS replace the upstream defaults and feature appends.
# Keep these defines explicit. Do not inherit upstream global fast-math.
flags='-g -Wl,-q -O3 -mtune=cortex-a9 -mfpu=neon -mfp16-format=ieee -Wno-incompatible-pointer-types -Wno-stringop-overflow -DVGL_GIT_HASH=\"6e7fe40\" -Isource -DSKIP_ERROR_HANDLING -DSKIP_SPLASHSCREEN -DHAVE_SHADER_CACHE -DHAVE_VITA3K_SUPPORT -DDISABLE_HW_ETC1'
identity=$( { sha256sum "$root/tools/build_vitagl_demo.sh" "$work/source.tar.gz" "$layout_patch" "$indexed_patch" "$upload_patch" "$dds_patch"; arm-vita-eabi-gcc --version; printf '%s\n' "$flags"; } | sha256sum | cut -d' ' -f1)
if [[ -f "$work/libvitaGL.a" && -f "$work/build.identity" &&
      $(cat "$work/build.identity") == "$identity" ]]; then
    printf 'Pinned demo vitaGL already built: %s\n' "$work/libvitaGL.a"
    exit 0
fi
# Always stage the patched file from the pinned archive. Repeated dependency
# builds cannot stack the patch or depend on prior generated source contents.
tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source" \
    "vitaGL-$revision/source/ffp.c" "vitaGL-$revision/source/textures.c"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$layout_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$indexed_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$upload_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$dds_patch"
make -C "$work/source" -B -j"${RENEGADE_BUILD_JOBS:-8}" CFLAGS="$flags"
cp "$work/source/libvitaGL.a" "$work/libvitaGL.a"
{
    printf 'revision=%s\nflags=%s\n' "$revision" "$flags"
    printf 'splash=disabled\npersistent_shader_cache=enabled\nvita3k_support=enabled\n'
    printf 'physical_acceptance=false\n'
    printf 'unlit_immediate_layout=compact_position_uv_rgba_lit_layout_preserved\n'
    printf 'indexed_immediate=original_ffp_with_transient_copied_indices\n'
    printf 'full_rgba_replacement=skip_old_pixel_copy_preserve_gpu_retirement\n'
    printf 'dds_chain=single_allocation_native_blocks_transactional_surface_fallback\n'
    sha256sum "$layout_patch" "$indexed_patch" "$upload_patch" "$dds_patch" "$work/source/source/ffp.c" "$work/source/source/textures.c"
    sha256sum "$work/source.tar.gz" "$work/libvitaGL.a" "$work/source/source/vitaGL.h"
    arm-vita-eabi-gcc --version
} > "$work/provenance.txt"
printf '%s\n' "$identity" > "$work/build.identity"
