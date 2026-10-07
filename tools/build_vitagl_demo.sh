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
projective_patch="$root/port/renderer/vita/dependency-patches/vitagl-projective-immediate.patch"
attribute_patch="$root/port/renderer/vita/dependency-patches/vitagl-attribute-invalidation.patch"
records_patch="$root/port/renderer/vita/dependency-patches/vitagl-immediate-vertex-records.patch"
program_cache_patch="$root/port/renderer/vita/dependency-patches/vitagl-ffp-program-cache.patch"
work="$root/build/deps/vitagl-demo"
mkdir -p "$work"
exec 9>"$work/build.lock"
flock 9
# Opt-in content-addressed dependency cache; inert unless enabled.
source "$root/tools/dependency_cache.sh"
if [[ ! -f "$work/source.tar.gz" ]] &&
      ! { rv_depcache_compute_key vitagl-source-archive --value "revision=$revision" &&
          rv_depcache_restore vitagl-source-archive "$work" source.tar.gz; }; then
    curl --fail --location --retry 2 --max-time 120 \
        "https://codeload.github.com/Rinnegatamante/vitaGL/tar.gz/$revision" \
        -o "$work/source.tar.gz.part"
    mv "$work/source.tar.gz.part" "$work/source.tar.gz"
    rv_depcache_store vitagl-source-archive "$work" source.tar.gz
fi
if [[ ! -f "$work/source/Makefile" ]]; then
    mkdir -p "$work/source"
    tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source"
fi
# Command-line CFLAGS replace the upstream defaults and feature appends.
# Keep these defines explicit. Do not inherit upstream global fast-math.
flags='-g -Wl,-q -O3 -mtune=cortex-a9 -mfpu=neon -mfp16-format=ieee -Wno-incompatible-pointer-types -Wno-stringop-overflow -fno-math-errno -fno-trapping-math -DVGL_GIT_HASH=\"6e7fe40\" -Isource -DSKIP_ERROR_HANDLING -DSKIP_SPLASHSCREEN -DHAVE_SHADER_CACHE -DHAVE_VITA3K_SUPPORT -DDISABLE_HW_ETC1'
identity=$( { sha256sum "$root/tools/build_vitagl_demo.sh" "$work/source.tar.gz" "$layout_patch" "$indexed_patch" "$upload_patch" "$dds_patch" "$projective_patch" "$attribute_patch" "$records_patch" "$program_cache_patch"; arm-vita-eabi-gcc --version; printf '%s\n' "$flags"; } | sha256sum | cut -d' ' -f1)
if [[ -f "$work/libvitaGL.a" && -f "$work/build.identity" &&
      $(cat "$work/build.identity") == "$identity" ]]; then
    printf 'Pinned demo vitaGL already built: %s\n' "$work/libvitaGL.a"
    exit 0
fi
# Always stage the patched file from the pinned archive. Repeated dependency
# builds cannot stack the patch or depend on prior generated source contents.
tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source" \
    "vitaGL-$revision/source/ffp.c" "vitaGL-$revision/source/textures.c" \
    "vitaGL-$revision/source/gxm.c" "vitaGL-$revision/source/shared.h" \
    "vitaGL-$revision/source/vgl.c" \
    "vitaGL-$revision/source/shaders/ffp_v.h" "vitaGL-$revision/source/shaders/ffp_f.h"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$layout_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$indexed_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$upload_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$dds_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$projective_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$attribute_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$records_patch"
patch --batch --fuzz=0 --no-backup-if-mismatch -d "$work/source" -p1 < "$program_cache_patch"
# The persistent FFP GXP cache directory is versioned by this digest of the
# patched FFP shader generator and shader sources, so any patch that can
# change generated FFP shader text invalidates previously compiled GXPs.
ffp_cache_digest=$(cat "$work/source/source/ffp.c" "$work/source/source/shaders/ffp_v.h" \
    "$work/source/source/shaders/ffp_f.h" "$work/source/source/shaders/texture_combiners/"*.h |
    sha256sum | cut -c1-12)
# The cache key hashes the exact compiled tree (pinned archive plus ordered
# patches as applied above), the compiler identity and the flags, never paths.
vitagl_cache_hit=
if rv_depcache_enabled && rv_depcache_compute_key vitagl-demo \
        --script "$root/tools/build_vitagl_demo.sh" --value "revision=$revision" \
        --source "$work/source.tar.gz" \
        --patch "$layout_patch" --patch "$indexed_patch" --patch "$upload_patch" --patch "$dds_patch" \
        --patch "$projective_patch" --patch "$attribute_patch" --patch "$records_patch" \
        --patch "$program_cache_patch" \
        --tree-exclude '*.o' --tree-exclude '*.a' --tree "compiled_tree=$work/source" \
        --value "sdk_root=$(realpath -e -- "$sdk")" --file "gcc_driver=$sdk/bin/arm-vita-eabi-gcc" \
        --file "sdk_version_info=$sdk/version_info.txt" \
        --value "gcc_version=$(arm-vita-eabi-gcc --version)" \
        --flags="$flags" --value "ffp_cache_digest=$ffp_cache_digest" &&
    rv_depcache_restore vitagl-demo "$work" libvitaGL.a; then
    vitagl_cache_hit=$rv_depcache_key
    printf 'Pinned demo vitaGL restored from the dependency cache: %s\n' "$work/libvitaGL.a"
else
    make -C "$work/source" -B -j"${RENEGADE_BUILD_JOBS:-8}" \
        CFLAGS="$flags -DRENEGADE_VGL_FFP_CACHE_DIGEST=\\\"$ffp_cache_digest\\\""
    cp "$work/source/libvitaGL.a" "$work/libvitaGL.a"
    rv_depcache_store vitagl-demo "$work" libvitaGL.a
fi
{
    printf 'revision=%s\nflags=%s\n' "$revision" "$flags"
    printf 'splash=disabled\npersistent_shader_cache=enabled\nvita3k_support=enabled\n'
    printf 'physical_acceptance=false\n'
    printf 'unlit_immediate_layout=compact_position_uv_rgba_lit_layout_preserved\n'
    printf 'indexed_immediate=original_ffp_with_transient_copied_indices\n'
    printf 'full_rgba_replacement=skip_old_pixel_copy_preserve_gpu_retirement\n'
    printf 'dds_chain=single_allocation_native_blocks_transactional_surface_fallback\n'
    printf 'projective_immediate=opt_in_float3_uv_divisor_fragment_division_distinct_shader_key\n'
    printf 'attribute_invalidation=array_immediate_layout_transition_full_vertex_repatch\n'
    printf 'immediate_vertex_records=unlit_nonprojective_packed_append_same_stream_current_attributes_unchanged\n'
    printf 'ffp_program_cache=app_root_versioned_gxp_cache_validated_reads_loading_prewarm_telemetry\n'
    printf 'ffp_cache_digest=%s\n' "$ffp_cache_digest"
    sha256sum "$layout_patch" "$indexed_patch" "$upload_patch" "$dds_patch" "$projective_patch" "$attribute_patch" "$records_patch" "$program_cache_patch" "$work/source/source/ffp.c" "$work/source/source/textures.c" "$work/source/source/gxm.c" "$work/source/source/shared.h" "$work/source/source/vgl.c" "$work/source/source/shaders/ffp_v.h" "$work/source/source/shaders/ffp_f.h"
    sha256sum "$work/source.tar.gz" "$work/libvitaGL.a" "$work/source/source/vitaGL.h"
    arm-vita-eabi-gcc --version
} > "$work/provenance.txt"
if [[ -n "$vitagl_cache_hit" ]]; then
    printf 'dependency_cache=restored key=%s\n' "$vitagl_cache_hit" >> "$work/provenance.txt"
fi
printf '%s\n' "$identity" > "$work/build.identity"
