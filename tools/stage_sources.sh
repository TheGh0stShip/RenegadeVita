#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_upstream="$rv_root/upstream/CnC_Renegade"
rv_stage_target="$rv_root/staging"
rv_stage="$rv_stage_target"
python3 "$rv_root/tools/renegade_patch_inventory.py" --root "$rv_root" --count > /dev/null
rv_incremental_stage=${RENEGADE_INCREMENTAL_STAGE:-0}
case "$rv_incremental_stage" in 0|1) ;; *) echo "Invalid RENEGADE_INCREMENTAL_STAGE: $rv_incremental_stage" >&2; exit 2 ;; esac

rv_managed_stage_dirs=(
	wwbitpack wwutil wwdebug wwlib wwmath wwsaveload ww3d2 wwphys combat
	commando wwaudio wwnet wwtranslatedb wwui scripts
)

if [[ "$rv_incremental_stage" == "1" ]]; then
	mkdir -p "$rv_root/build"
	rv_stage=$(mktemp -d "$rv_root/build/staging-incremental.XXXXXX")
	rv_incremental_temp="$rv_stage"
	cleanup_incremental_stage() {
		rm -rf -- "$rv_incremental_temp"
	}
	trap cleanup_incremental_stage EXIT
	echo "Incremental staging enabled: unchanged files in $rv_stage_target will keep their mtimes."
fi

case "$rv_stage" in
	"$rv_stage_target"|"$rv_root"/build/staging-incremental.*) ;;
	*)
	echo "Refusing to clean an unexpected staging path: $rv_stage" >&2
	exit 2
		;;
esac
for rv_dir in "${rv_managed_stage_dirs[@]}"; do
	rm -rf -- "$rv_stage/$rv_dir"
	mkdir -p "$rv_stage/$rv_dir"
done

for rv_file in BitPacker.cpp BitPacker.h bitstream.cpp bitstream.h encoderlist.cpp encoderlist.h encodertypeentry.cpp encodertypeentry.h bitpackids.h; do
	cp "$rv_upstream/Code/wwbitpack/$rv_file" "$rv_stage/wwbitpack/$rv_file"
done
cp "$rv_upstream/Code/wwutil/mathutil.cpp" "$rv_stage/wwutil/mathutil.cpp"
find "$rv_upstream/Code/wwdebug" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/wwdebug/" \;

# Stage the complete source/header pools for the coherent WW3D dependency
# slice, while omitting headers deliberately supplied by the centralized
# portability boundary. CMake still lists every translation unit explicitly;
# staging a pool does not silently compile an upstream module.
find "$rv_upstream/Code/wwlib" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -name '*.h' \) \
	! -name 'bittype.h' ! -name 'mutex.h' ! -name 'osdep.h' \
	! -name 'win.h' -exec cp {} "$rv_stage/wwlib/" \;
# The original uppercase Targa header carries on-disk structure declarations.
cp "$rv_upstream/Code/wwlib/TARGA.H" "$rv_stage/wwlib/TARGA.H"
find "$rv_upstream/Code/WWMath" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -name '*.h' \) -exec cp {} "$rv_stage/wwmath/" \;
find "$rv_upstream/Code/wwsaveload" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -name '*.h' \) -exec cp {} "$rv_stage/wwsaveload/" \;
find "$rv_upstream/Code/ww3d2" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -name '*.h' \) -exec cp {} "$rv_stage/ww3d2/" \;
# Stage the complete original WWPhys source/header pool. The A3.0 manifest is
# intentionally derived from the original wwphys.dsp runtime source list and
# excludes only its editor-only PathfindSectorBuilder.cpp translation unit.
find "$rv_upstream/Code/wwphys" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -name '*.h' \) -exec cp {} "$rv_stage/wwphys/" \;
# Stage the coherent Combat/Commando declaration and first-world factory pool.
# CMake remains authoritative: staging a complete source pool never causes it
# to be compiled implicitly. WWAudio and WWNet are present here so the original
# Combat headers reach their real subsystem boundaries; behavior remains
# excluded until explicit original translation units are selected.
find "$rv_upstream/Code/Combat" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/combat/" \;
find "$rv_upstream/Code/Commando" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/commando/" \;
cp "$rv_upstream/Code/WWOnline/WOLLangCodes.h" "$rv_stage/commando/wollangcodes.h"
find "$rv_upstream/Code/WWAudio" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/wwaudio/" \;
find "$rv_upstream/Code/wwnet" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/wwnet/" \;
find "$rv_upstream/Code/wwtranslatedb" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/wwtranslatedb/" \;
# The A4 frontend must use the original WWUI stack.  Keep its source pool
# deterministic and separate from the selected runtime manifest until the
# DirectInput/message bridge is deliberately closed.
find "$rv_upstream/Code/wwui" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/wwui/" \;
# Stage the official mission-script source pool so the selected provider can
# receive deterministic portability fixes without modifying upstream.
find "$rv_upstream/Code/Scripts" -maxdepth 1 -type f \
	\( -iname '*.cpp' -o -iname '*.h' \) -exec cp {} "$rv_stage/scripts/" \;

patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwbitpack" -p1 < "$rv_root/port/patches/wwbitpack-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwbitpack" -p1 < "$rv_root/port/patches/wwbitpack-a31-utf16-get.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwdebug" -p1 < "$rv_root/port/patches/wwdebug-a36-vita-frame-profile.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a21-posix.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a22-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-thread-posix.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-notify-typename.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-wide-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-short-wchar-host.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-trim-overlap.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-buffer-array-delete.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a31-host-pointer-token-read.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-chunkio-open-chunk-breadcrumbs.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-buffered-relative-seek.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwmath" -p1 < "$rv_root/port/patches/wwmath-a22-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwmath" -p1 < "$rv_root/port/patches/wwmath-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwmath" -p1 < "$rv_root/port/patches/wwmath-a4-fastcall-vita.patch"
test "$(sha256sum "$rv_stage/wwmath/wwmath.h" | cut -d' ' -f1)" = \
	"031b73ee3f4f202c274dc5860c9745520dfe4892d34dec62c41de69860775fb8"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwmath" -p1 < "$rv_root/port/patches/wwmath-a35-valid-float-layout.patch"
test "$(sha256sum "$rv_stage/wwmath/wwmath.h" | cut -d' ' -f1)" = \
	"6f9d2deef7687cd7e0423d0e0dbfc2739fd0c99b52511a985a0e82d38b81fec5"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwmath" -p1 < "$rv_root/port/patches/wwmath-a35-portable-int-conversion.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a30-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwtranslatedb" -p1 < "$rv_root/port/patches/wwtranslatedb-a31-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwtranslatedb" -p1 < "$rv_root/port/patches/wwtranslatedb-a35-empty-string-wide-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwtranslatedb" -p1 < "$rv_root/port/patches/wwtranslatedb-a36-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a22-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a22-vita-boundaries.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-animated-sound-restore.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a315-texture-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a32-texture-apply-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a4-font3d-vita.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a4-render2d-runtime-init.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-render2d-dynamic-fvf-init.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-render2d-viewport-restore.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a4-freetype-fonts.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-freetype-glyph-raster-safety.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-render2d-text-atlas-vita-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-render2d-text-atlas-uv.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a315-dds-vita.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-particle-size-keyframe-guard.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-hanim-combo-null-motion-guard.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a30-vita-buffers.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a30-camera-apply.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-vita-scene-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a4-aggregate-vita-factory-lookup.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a30-pointer-tokens.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-static-object-load-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-vita-durable-static-trace.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-path-timeslice-underflow.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-grid-texture-release.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a30-pointer-tokens.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-assetdep-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-script-dll-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-spawn-loop-scope.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-weather-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-backgroundmgr-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-hud-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-conversation-loop-scope.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-mapmgr-const.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-combatsound-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-scriptcommands-utf16.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-tutorial-help.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-objective-message-varargs.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-ccamera-silent-listener.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a31-encyclopedia-zero-read.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-humanstate-weapon-style-table.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-observer-load-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-main-thread-level-load.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-durable-loader-trace.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-loading-progress-callback.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-teardown-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-conversation-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-conversation-reentrant-think.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-transition-action-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-logan-path-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vehicle-proximity-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-weaponview-reload-latch.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-m00-ui-hud-subtitles.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-hud-presentation-boundary.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-target-box-diagnostics.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-hud-think-presentation.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vita-messagewindow-presentation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-weaponview-animation-varargs.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-menu-clear-color.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a31-dx8-mesh-cache-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a31-wide-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-vita-renderobj-load-trace.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a30-datasafe-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a30-optional-services.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a30-datasafe-definitions-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a30-datasafe-ilp32.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-datasafe-invalid-handle-guard.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a31-gamedata-headless-ui.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a31-session-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a31-gdcnc-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a31-winevent-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-direct-client-round-identity.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a31-messages-headless-ui.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-frontend-include-case.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-singleplayer-frontend-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-singleplayer-frontend-routes.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-dialog-factory-reentry.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-frontend-console-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-mainmenu-singleplayer-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-mainmenu-version-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-mainmenu-instance-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-cnetwork-crc-file-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-campaign-catalog-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-dialogtests-singleplayer-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-loadsp-vita-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-textdisplay-vector-include.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-consolemode-add-message-return.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gamemode-console-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gamemenu-wol-include-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gameinitmgr-wol-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gameinitmgr-online-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gameinitmgr-skirmish-boundary.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gameinitmgr-lan-start-boundary.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-gameinitmgr-frontend-start-latch.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-movie-vita-provider-boundary.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-combatgmode-wol-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-announceevent-include-case.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-combatgmode-include-case.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-event-gamespy-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-event-portability.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-shared-loadingscreen-owner.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-combatgmode-vita-load-finalization.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a4-combatgmode-singleplayer-runtime.patch"
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-loading-status-text.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-loading-status-render.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a31-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a31-audio-lifecycle-breadcrumb.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-posix-runtime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-original-runtime-correctness.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-user-data-pointer-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-event-pointer-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-file-pointer-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-release-lock-order.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-sample-pointer-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-logical-removal-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-audible-removal-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-completed-sound-uniqueness.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-flush-enqueue-order.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a30-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a31-transport-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a31-packetmgr-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-stylemgr-font-provider.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-vita-cursor-clamp.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-ime-vita-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-ime-include-case.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-dialogparser-lp64-alignment.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-dialog-template-vita-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-dialogparser-utf16.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-listctrl-modern-scope.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-dialogbase-modern-scope.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-buttonctrl-modern-scope.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-imagectrl-border-precedence.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-textmarquee-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-multilinetext-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-editctrl-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a4-treectrl-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-parameter-array-delete.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a37-mx0-default-arguments.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a45-m13-intro-camera-trace.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/a4-post-movie-mainmenu-hardening.patch"

patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwbitpack" -p1 < "$rv_root/port/patches/wwbitpack-a35-read-position.patch"

# Original source projects were authored on case-insensitive filesystems. The
# staged copy is native ext4, so generate lower-case header aliases after all
# patches have applied. This is a filesystem compatibility boundary, not a
# source rewrite; manifests retain their original canonical filenames.
while IFS= read -r -d '' rv_header; do
	rv_header_dir=$(dirname "$rv_header")
	rv_header_name=$(basename "$rv_header")
	rv_header_lower=$(printf '%s' "$rv_header_name" | tr '[:upper:]' '[:lower:]')
	if [[ "$rv_header_name" != "$rv_header_lower" && ! -e "$rv_header_dir/$rv_header_lower" ]]; then
		cp -- "$rv_header" "$rv_header_dir/$rv_header_lower"
	fi
done < <(find "$rv_stage" -type f -name '*.h' -print0)

# Explicit mixed-case aliases required by the current A3.1 source closure.
cp -- "$rv_stage/ww3d2/dx8wrapper.h" "$rv_stage/ww3d2/Dx8Wrapper.h"
cp -- "$rv_stage/wwphys/PathfindSector.h" "$rv_stage/wwphys/pathfindsector.h"
cp -- "$rv_stage/wwphys/PathfindPortal.h" "$rv_stage/wwphys/pathfindportal.h"
cp -- "$rv_stage/wwlib/vector.h" "$rv_stage/wwaudio/Vector.H"
cp -- "$rv_stage/wwmath/vector3.h" "$rv_stage/wwaudio/Vector3.H"
cp -- "$rv_root/port/compatibility/include/bittype.h" "$rv_stage/wwaudio/BitType.H"
cp -- "$rv_stage/wwaudio/SoundScene.h" "$rv_stage/wwaudio/SoundScene.H"
cp -- "$rv_stage/wwaudio/SoundSceneObj.h" "$rv_stage/wwaudio/SoundSceneObj.H"
cp -- "$rv_stage/wwaudio/WWAudio.h" "$rv_stage/wwaudio/WWAudio.H"
cp -- "$rv_stage/wwaudio/sound3d.h" "$rv_stage/wwaudio/Sound3D.H"
cp -- "$rv_stage/wwmath/matrix3d.h" "$rv_stage/wwaudio/Matrix3D.H"
cp -- "$rv_stage/wwmath/matrix3d.h" "$rv_stage/combat/matrix3D.h"
cp -- "$rv_stage/combat/messagewindow.h" "$rv_stage/combat/MessageWindow.h"
cp -- "$rv_stage/wwlib/always.h" "$rv_stage/wwlib/Always.h"
cp -- "$rv_stage/wwsaveload/definition.h" "$rv_stage/wwsaveload/Definition.h"
cp -- "$rv_stage/wwsaveload/persistfactory.h" "$rv_stage/wwsaveload/PersistFactory.h"
cp -- "$rv_stage/wwsaveload/definitionfactory.h" "$rv_stage/wwsaveload/DefinitionFactory.h"
cp -- "$rv_stage/wwsaveload/simpledefinitionfactory.h" "$rv_stage/wwsaveload/SimpleDefinitionFactory.h"
cp -- "$rv_stage/combat/combatchunkid.h" "$rv_stage/combat/CombatChunkID.h"
cp -- "$rv_stage/combat/playertype.h" "$rv_stage/combat/PlayerType.h"
cp -- "$rv_stage/combat/debug.h" "$rv_stage/combat/Debug.h"
cp -- "$rv_stage/combat/viseme.h" "$rv_stage/combat/Viseme.h"
cp -- "$rv_stage/wwtranslatedb/translateobj.h" "$rv_stage/wwtranslatedb/TranslateObj.h"
cp -- "$rv_stage/wwtranslatedb/translatedb.h" "$rv_stage/wwtranslatedb/TranslateDB.h"
for rv_audio_header in "$rv_stage/wwaudio"/*.h; do
	rv_audio_base=$(basename "$rv_audio_header" .h)
	cp -- "$rv_audio_header" "$rv_stage/wwaudio/$rv_audio_base.H"
done
touch "$rv_stage/wwbitpack"/* "$rv_stage/wwutil/mathutil.cpp" "$rv_stage/wwdebug"/* \
	"$rv_stage/wwlib"/* "$rv_stage/wwmath"/* "$rv_stage/wwsaveload"/* \
	"$rv_stage/ww3d2"/* "$rv_stage/wwphys"/* "$rv_stage/combat"/* \
	"$rv_stage/commando"/* "$rv_stage/wwaudio"/* "$rv_stage/wwnet"/* \
	"$rv_stage/wwtranslatedb"/* "$rv_stage/scripts"/*

echo "Staged complete dependency pools; build manifests select translation units explicitly."
echo "Applied: port/patches/wwbitpack-gcc15.patch"
echo "Applied: port/patches/wwbitpack-a31-utf16-get.patch"
echo "Applied: port/patches/wwlib-a21-posix.patch"
echo "Applied: port/patches/wwlib-a22-gcc15.patch"
echo "Applied: port/patches/wwlib-a30-gcc15.patch"
echo "Applied: port/patches/wwlib-a31-gcc15.patch"
echo "Applied: port/patches/wwlib-a31-thread-posix.patch"
echo "Applied: port/patches/wwlib-a31-notify-typename.patch"
echo "Applied: port/patches/wwlib-a31-wide-abi.patch"
echo "Applied: port/patches/wwlib-a31-short-wchar-host.patch"
echo "Applied: port/patches/wwlib-a31-trim-overlap.patch"
echo "Applied: port/patches/wwlib-a31-buffer-array-delete.patch"
echo "Applied: port/patches/wwlib-a31-host-pointer-token-read.patch"
echo "Applied: port/patches/wwlib-a35-chunkio-open-chunk-breadcrumbs.patch"
echo "Applied: port/patches/wwlib-a35-buffered-relative-seek.patch"
echo "Applied: port/patches/scripts-a35-parameter-array-delete.patch"
echo "Applied: port/patches/wwmath-a22-gcc15.patch"
echo "Applied: port/patches/wwmath-a30-gcc15.patch"
echo "Applied: port/patches/wwmath-a4-fastcall-vita.patch"
echo "Applied: port/patches/wwmath-a35-valid-float-layout.patch"
echo "Applied: port/patches/wwsaveload-a30-abi.patch"
echo "Applied: port/patches/wwtranslatedb-a31-gcc15.patch"
echo "Applied: port/patches/wwtranslatedb-a35-empty-string-wide-abi.patch"
echo "Applied: port/patches/wwtranslatedb-a36-load-admission.patch"
echo "Applied: port/patches/ww3d2-a22-gcc15.patch"
echo "Applied: port/patches/ww3d2-a22-vita-boundaries.patch"
echo "Applied: port/patches/ww3d2-a315-texture-lifecycle.patch"
echo "Applied: port/patches/ww3d2-a32-texture-apply-boundary.patch"
echo "Applied: port/patches/ww3d2-a4-font3d-vita.patch"
echo "Applied: port/patches/ww3d2-a4-render2d-runtime-init.patch"
echo "Applied: port/patches/ww3d2-a35-render2d-dynamic-fvf-init.patch"
echo "Applied: port/patches/ww3d2-a35-render2d-viewport-restore.patch"
echo "Applied: port/patches/ww3d2-a4-freetype-fonts.patch"
echo "Applied: port/patches/ww3d2-a35-freetype-glyph-raster-safety.patch"
echo "Applied: port/patches/ww3d2-a35-render2d-text-atlas-vita-diagnostics.patch"
echo "Applied: port/patches/ww3d2-a35-render2d-text-atlas-uv.patch"
echo "Applied: port/patches/ww3d2-a315-dds-vita.patch"
echo "Applied: port/patches/ww3d2-a30-gcc15.patch"
echo "Applied: port/patches/ww3d2-a30-vita-buffers.patch"
echo "Applied: port/patches/ww3d2-a30-camera-apply.patch"
echo "Applied: port/patches/ww3d2-a35-vita-scene-state.patch"
echo "Applied: port/patches/wwphys-a30-gcc15.patch"
echo "Applied: port/patches/wwphys-a30-pointer-tokens.patch"
echo "Applied: port/patches/wwphys-a35-static-object-load-diagnostics.patch"
echo "Applied: port/patches/wwphys-a35-vita-durable-static-trace.patch"
echo "Applied: port/patches/wwphys-a36-path-timeslice-underflow.patch"
echo "Applied: port/patches/wwphys-a36-grid-texture-release.patch"
echo "Applied: port/patches/combat-a30-pointer-tokens.patch"
echo "Applied: port/patches/combat-a30-gcc15.patch"
echo "Applied: port/patches/combat-a31-gcc15.patch"
echo "Applied: port/patches/combat-a31-assetdep-gcc15.patch"
echo "Applied: port/patches/combat-a31-script-dll-boundary.patch"
echo "Applied: port/patches/combat-a31-spawn-loop-scope.patch"
echo "Applied: port/patches/combat-a31-weather-gcc15.patch"
echo "Applied: port/patches/combat-a31-backgroundmgr-gcc15.patch"
echo "Applied: port/patches/combat-a31-hud-gcc15.patch"
echo "Applied: port/patches/combat-a31-conversation-loop-scope.patch"
echo "Applied: port/patches/combat-a31-mapmgr-const.patch"
echo "Applied: port/patches/combat-a31-combatsound-gcc15.patch"
echo "Applied: port/patches/combat-a31-scriptcommands-utf16.patch"
echo "Applied: port/patches/combat-a35-vita-tutorial-help.patch"
echo "Applied: port/patches/combat-a35-objective-message-varargs.patch"
echo "Applied: port/patches/combat-a31-ccamera-silent-listener.patch"
echo "Applied: port/patches/combat-a31-encyclopedia-zero-read.patch"
echo "Applied: port/patches/combat-a35-humanstate-weapon-style-table.patch"
echo "Applied: port/patches/combat-a35-observer-load-diagnostics.patch"
echo "Applied: port/patches/combat-a35-vita-main-thread-level-load.patch"
echo "Applied: port/patches/combat-a35-vita-durable-loader-trace.patch"
echo "Applied: port/patches/combat-a35-vita-loading-progress-callback.patch"
echo "Applied: port/patches/combat-a35-teardown-lifecycle.patch"
echo "Applied: port/patches/combat-a35-conversation-diagnostics.patch"
echo "Applied: port/patches/combat-a35-conversation-reentrant-think.patch"
echo "Applied: port/patches/combat-a35-transition-action-diagnostics.patch"
echo "Applied: port/patches/combat-a35-vehicle-proximity-diagnostics.patch"
echo "Applied: port/patches/combat-a35-weaponview-reload-latch.patch"
echo "Applied: port/patches/combat-a35-target-box-diagnostics.patch"
echo "Applied: port/patches/combat-a35-vita-hud-think-presentation.patch"
echo "Applied: port/patches/combat-a35-vita-messagewindow-presentation.patch"
echo "Applied: port/patches/combat-a35-weaponview-animation-varargs.patch"
echo "Applied: port/patches/commando-a35-menu-clear-color.patch"
echo "Applied: port/patches/ww3d2-a31-dx8-mesh-cache-boundary.patch"
echo "Applied: port/patches/ww3d2-a31-wide-abi.patch"
echo "Applied: port/patches/ww3d2-a35-vita-renderobj-load-trace.patch"
echo "Applied: port/patches/commando-a30-datasafe-gcc15.patch"
echo "Applied: port/patches/commando-a30-optional-services.patch"
echo "Applied: port/patches/commando-a30-datasafe-definitions-gcc15.patch"
echo "Applied: port/patches/commando-a30-datasafe-ilp32.patch"
echo "Applied: port/patches/commando-a31-gamedata-headless-ui.patch"
echo "Applied: port/patches/commando-a31-session-gcc15.patch"
echo "Applied: port/patches/commando-a31-gdcnc-gcc15.patch"
echo "Applied: port/patches/commando-a31-winevent-gcc15.patch"
echo "Applied: port/patches/commando-a36-direct-client-round-identity.patch"
echo "Applied: port/patches/commando-a4-frontend-include-case.patch"
echo "Applied: port/patches/commando-a4-singleplayer-frontend-boundary.patch"
echo "Applied: port/patches/commando-a4-singleplayer-frontend-routes.patch"
echo "Applied: port/patches/commando-a4-frontend-console-boundary.patch"
echo "Applied: port/patches/commando-a4-mainmenu-singleplayer-boundary.patch"
echo "Applied: port/patches/commando-a4-mainmenu-version-abi.patch"
echo "Applied: port/patches/commando-a4-mainmenu-instance-lifecycle.patch"
echo "Applied: port/patches/commando-a4-cnetwork-crc-file-lifetime.patch"
echo "Applied: port/patches/commando-a4-campaign-catalog-lifetime.patch"
echo "Applied: port/patches/commando-a4-dialogtests-singleplayer-boundary.patch"
echo "Applied: port/patches/commando-a4-loadsp-vita-boundary.patch"
echo "Applied: port/patches/commando-a4-textdisplay-vector-include.patch"
echo "Applied: port/patches/commando-a35-consolemode-add-message-return.patch"
echo "Applied: port/patches/commando-a4-gamemode-console-boundary.patch"
echo "Applied: port/patches/commando-a4-gamemenu-wol-include-boundary.patch"
echo "Applied: port/patches/commando-a4-gameinitmgr-wol-boundary.patch"
echo "Applied: port/patches/commando-a4-gameinitmgr-online-boundary.patch"
echo "Applied: port/patches/commando-a4-gameinitmgr-skirmish-boundary.patch"
echo "Applied: port/patches/commando-a4-gameinitmgr-lan-start-boundary.patch"
echo "Applied: port/patches/commando-a4-gameinitmgr-frontend-start-latch.patch"
echo "Applied: port/patches/commando-a4-movie-vita-provider-boundary.patch"
echo "Applied: port/patches/commando-a4-combatgmode-wol-boundary.patch"
echo "Applied: port/patches/commando-a4-announceevent-include-case.patch"
echo "Applied: port/patches/commando-a4-combatgmode-include-case.patch"
echo "Applied: port/patches/commando-a4-event-gamespy-boundary.patch"
echo "Applied: port/patches/commando-a4-event-portability.patch"
echo "Applied: port/patches/commando-a35-shared-loadingscreen-owner.patch"
echo "Applied: port/patches/commando-a35-combatgmode-vita-load-finalization.patch"
echo "Applied: port/patches/commando-a4-combatgmode-singleplayer-runtime.patch"
echo "Applied: port/patches/commando-a35-loading-status-text.patch"
echo "Applied: port/patches/commando-a35-loading-status-render.patch"
echo "Applied: port/patches/wwaudio-a30-gcc15.patch"
echo "Applied: port/patches/wwaudio-a31-gcc15.patch"
echo "Applied: port/patches/wwaudio-a31-audio-lifecycle-breadcrumb.patch"
echo "Applied: port/patches/wwaudio-a35-posix-runtime.patch"
echo "Applied: port/patches/wwaudio-a35-original-runtime-correctness.patch"
echo "Applied: port/patches/wwnet-a30-gcc15.patch"
echo "Applied: port/patches/wwui-a4-stylemgr-font-provider.patch"
echo "Applied: port/patches/wwui-a35-vita-cursor-clamp.patch"
echo "Applied: port/patches/wwui-a4-ime-vita-boundary.patch"
echo "Applied: port/patches/wwui-a4-ime-include-case.patch"
echo "Applied: port/patches/wwui-a4-dialogparser-lp64-alignment.patch"
echo "Applied: port/patches/wwui-a35-dialog-template-vita-diagnostics.patch"
echo "Applied: port/patches/wwui-a35-dialogparser-utf16.patch"
echo "Applied: port/patches/wwui-a4-listctrl-modern-scope.patch"
echo "Applied: port/patches/wwui-a4-dialogbase-modern-scope.patch"
echo "Applied: port/patches/wwui-a4-buttonctrl-modern-scope.patch"
echo "Applied: port/patches/wwui-a4-imagectrl-border-precedence.patch"
echo "Applied: port/patches/wwui-a4-textmarquee-gcc15.patch"
echo "Applied: port/patches/wwui-a4-multilinetext-gcc15.patch"
echo "Applied: port/patches/wwui-a4-editctrl-gcc15.patch"
echo "Applied: port/patches/wwui-a4-treectrl-gcc15.patch"
echo "Applied: port/patches/a4-post-movie-mainmenu-hardening.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-render2d-texture-readiness.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-map-texture-readiness.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-map-texture-readiness.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-unavailable-text-row.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-dds-disk-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-pause-save-help.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-loading-animation-evidence.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-demo-disabled-menu-options.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-disabled-menu-navigation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-loading-presentation-clock.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-campaign-retail-loading.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-catalog-readiness.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-demo-singleplayer-options.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-eva-optional-network-modes.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-eva-native-dependencies.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-pause-save-help-entry.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-pause-deferred-load.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-eva-viewer-audit.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-pause-native-options.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-pause-save-controller.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-pause-options-persistence.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-controller-button-focus.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a35-native-text-entry.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-render2d-direct-atlas-upload.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-mix-index-allocation-bounds.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-dds-block-palette-precompute.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-dynamic-buffer-growth.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-texture-wrapper-surface-release.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-mix-failure-file-release.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-targa-fixed-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-format-table-init.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage" -p1 < "$rv_root/port/patches/commando-a35-loading-animation-varargs.patch"
echo "Applied: port/patches/commando-a35-loading-animation-varargs.patch"
rv_gameobjmanager_sha=$(sha256sum "$rv_stage/combat/gameobjmanager.cpp" | cut -d' ' -f1)
if [[ "$rv_gameobjmanager_sha" != "6519ba7668825baf9f5821253b7d033cd4b1790af2898f062deeaf6cfac06ece" ]]; then
	echo "Refusing unanchored PostThink timing patch: gameobjmanager.cpp changed ($rv_gameobjmanager_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-postthink-owner-timing.patch"
echo "Applied: port/patches/combat-a35-postthink-owner-timing.patch"
rv_hud_target_sha=$(sha256sum "$rv_stage/combat/hud.cpp" | cut -d' ' -f1)
if [[ "$rv_hud_target_sha" != "01cfa037602fc74edb7812af8fa1776ba567fbc17dee1d496dfcf2d7f1ecf1d9" ]]; then
	echo "Refusing unanchored HUD target-box patch: hud.cpp changed ($rv_hud_target_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-hud-target-box-nan-guard.patch"
echo "Applied: port/patches/combat-a35-hud-target-box-nan-guard.patch"
rv_scriptable_post_sha=$(sha256sum "$rv_stage/combat/scriptablegameobj.cpp" | cut -d' ' -f1)
if [[ "$rv_scriptable_post_sha" != "995ab56c511d88b940ff8f55630f8b7bc02ee393b3e9ee75f9de33460635016d" ]]; then
	echo "Refusing unanchored script timer timing patch: scriptablegameobj.cpp changed ($rv_scriptable_post_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-script-timer-timing.patch"
echo "Applied: port/patches/combat-a35-script-timer-timing.patch"
rv_cinematic_command_sha=$(sha256sum "$rv_stage/scripts/Test_Cinematic.cpp" | cut -d' ' -f1)
if [[ "$rv_cinematic_command_sha" != "40750609e4be927c4ceceb36fc291395c023662c8ad69ce34d185f95d6eb050d" ]]; then
	echo "Refusing unanchored cinematic command timing patch: Test_Cinematic.cpp changed ($rv_cinematic_command_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-command-timing.patch"
echo "Applied: port/patches/scripts-a35-cinematic-command-timing.patch"
rv_slot19_sha=$(sha256sum "$rv_stage/scripts/Test_Cinematic.cpp" | cut -d' ' -f1)
if [[ "$rv_slot19_sha" != "457f4d2053a3e16a4b8c1526cafbc8e4907356f3906267efa8e87c557bb6091e" ]]; then
	echo "Refusing unanchored M13 slot19 timing patch: Test_Cinematic.cpp changed ($rv_slot19_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-m13-slot19-phases.patch"
echo "Applied: port/patches/scripts-a35-m13-slot19-phases.patch"
rv_m01_duncan_beacon_sha=$(sha256sum "$rv_stage/scripts/Mission01.cpp" | cut -d' ' -f1)
if [[ "$rv_m01_duncan_beacon_sha" != "ebc0373a57ecf2b751fd3e8b009a6d51892b6a162b9f59fdc7033a215cfabd56" ]]; then
	echo "Refusing unanchored M01 Duncan beacon handoff patch: Mission01.cpp changed ($rv_m01_duncan_beacon_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-m01-duncan-beacon-handoff.patch"
echo "Applied: port/patches/scripts-a35-m01-duncan-beacon-handoff.patch"
rv_model_install_sha=$(sha256sum "$rv_stage/wwphys/phys.cpp" | cut -d' ' -f1)
if [[ "$rv_model_install_sha" != "820e2552cb29ee7dba38ae1c37017043acb98a16dd6bed9263ec34e29fb571da" ]]; then
	echo "Refusing unanchored model install timing patch: phys.cpp changed ($rv_model_install_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-model-install-timing.patch"
echo "Applied: port/patches/wwphys-a35-model-install-timing.patch"
rv_prepared_render_obj_sha=$(sha256sum "$rv_stage/wwphys/phys.cpp" | cut -d' ' -f1)
if [[ "$rv_prepared_render_obj_sha" != "202bd6f57a0aeda46ee020bd566cb7b03ff87a799c4a9c6c444cccb50d2e63b9" ]]; then
	echo "Refusing unanchored prepared render object patch: phys.cpp changed ($rv_prepared_render_obj_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-prepared-render-object-cache.patch"
echo "Applied: port/patches/wwphys-a35-prepared-render-object-cache.patch"
rv_trackedvehicle_sha=$(sha256sum "$rv_stage/wwphys/trackedvehicle.cpp" | cut -d' ' -f1)
if [[ "$rv_trackedvehicle_sha" != "c414a11697da26a7e21fc2e481cf59383c065473481642f19a921b20765d962a" ]]; then
	echo "Refusing unanchored tracked vehicle mesh-name patch: trackedvehicle.cpp changed ($rv_trackedvehicle_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-trackedvehicle-mesh-names.patch"
echo "Applied: port/patches/wwphys-a35-trackedvehicle-mesh-names.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-trackedvehicle-delta-time.patch"
echo "Applied: port/patches/wwphys-a35-trackedvehicle-delta-time.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-trackedvehicle-repeat-render.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-human-jump-finite.patch"
echo "Applied: port/patches/wwphys-a35-human-jump-finite.patch"
rv_path_sha=$(sha256sum "$rv_stage/wwphys/Path.cpp" | cut -d' ' -f1)
if [[ "$rv_path_sha" != "7c8d88c83db6401010274eb8cc53493ef8f832de4fb1cfa056936239351e6184" ]]; then
	echo "Refusing unanchored zero-length path patch: Path.cpp changed ($rv_path_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-zero-length-path.patch"
echo "Applied: port/patches/wwphys-a35-zero-length-path.patch"
rv_prev_animation_sha=$(sha256sum "$rv_stage/wwphys/animcollisionmanager.cpp" | cut -d' ' -f1)
if [[ "$rv_prev_animation_sha" != "1087c76adabc61910a94841f4c44806adee8d577ba39d08bd6d221a7c6d49595" ]]; then
	echo "Refusing unanchored previous-animation ref patch: animcollisionmanager.cpp changed ($rv_prev_animation_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-prev-animation-load-ref.patch"
echo "Applied: port/patches/wwphys-a35-prev-animation-load-ref.patch"
rv_raw_animation_sha=$(sha256sum "$rv_stage/ww3d2/hrawanim.cpp" | cut -d' ' -f1)
if [[ "$rv_raw_animation_sha" != "8e86f98902adc33842c01b83af7155b3b84e62a25c09b13d08df6f70a28b26a0" ]]; then
	echo "Refusing unanchored raw-animation frame patch: hrawanim.cpp changed ($rv_raw_animation_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-raw-animation-frame-floor.patch"
echo "Applied: port/patches/ww3d-a35-raw-animation-frame-floor.patch"
rv_pathaction_sha=$(sha256sum "$rv_stage/combat/pathaction.cpp" | cut -d' ' -f1)
if [[ "$rv_pathaction_sha" != "239633e2c55ed42f7d15b27419de92443b359379915ae16eb9128a9f47443263" ]]; then
	echo "Refusing unanchored borrowed path-action remap patch: pathaction.cpp changed ($rv_pathaction_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-pathaction-borrowed-remap.patch"
echo "Applied: port/patches/combat-a35-pathaction-borrowed-remap.patch"
rv_vehicledriver_sha=$(sha256sum "$rv_stage/combat/vehicledriver.cpp" | cut -d' ' -f1)
if [[ "$rv_vehicledriver_sha" != "31f65d6648671fa7d959f36b6fa4a44b627cfbaa8f0fe634229677cf27d79fc1" ]]; then
	echo "Refusing unanchored vehicle-driver remap patch: vehicledriver.cpp changed ($rv_vehicledriver_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-vehicledriver-borrowed-remap.patch"
echo "Applied: port/patches/combat-a35-vehicledriver-borrowed-remap.patch"
rv_decalmesh_sha=$(sha256sum "$rv_stage/ww3d2/decalmsh.cpp" | cut -d' ' -f1)
if [[ "$rv_decalmesh_sha" != "aaa99b948b868ee3b52fc1b75e0bfd139ae1e31379559f28b89ffa15383c7785" ]]; then
	echo "Refusing unanchored decal release-range patch: decalmsh.cpp changed ($rv_decalmesh_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-decal-release-range.patch"
echo "Applied: port/patches/ww3d-a35-decal-release-range.patch"
rv_ww3d_create_sha=$(sha256sum "$rv_stage/ww3d2/assetmgr.cpp" | cut -d' ' -f1)
if [[ "$rv_ww3d_create_sha" != "290ac62041c1de14327cfb10fa6cfe14a6b55c544c9b9d0c237ac2f60fb43b93" ]]; then
	echo "Refusing unanchored WW3D create timing patch: assetmgr.cpp changed ($rv_ww3d_create_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-create-depth-timing.patch"
echo "Applied: port/patches/ww3d2-a35-create-depth-timing.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-m13-aggregate-template.patch"
echo "Applied: port/patches/ww3d2-a35-m13-aggregate-template.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-m13-effect-template.patch"
echo "Applied: port/patches/ww3d2-a35-m13-effect-template.patch"
rv_m13_hlod_template_sha=$(sha256sum "$rv_stage/ww3d2/hlod.cpp" | cut -d' ' -f1)
if [[ "$rv_m13_hlod_template_sha" != "bdd059fb9826b20f01a1cefba306807e0a9900415732e7e6d3ff3fab6ba419b7" ]]; then
	echo "Refusing unanchored M13 HLOD template patch: hlod.cpp changed ($rv_m13_hlod_template_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-m13-hlod-template.patch"
echo "Applied: port/patches/ww3d2-a35-m13-hlod-template.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage" -p1 < "$rv_root/port/patches/dev168-m13-loader-summary.patch"
echo "Applied: port/patches/dev168-m13-loader-summary.patch"
python3 - "$rv_stage/combat/objlibrary.cpp" "$rv_stage/scripts/Test_Cinematic.cpp" "$rv_stage/ww3d2/agg_def.cpp" "$rv_stage/wwphys/trackedvehicle.cpp" <<'PY'
from pathlib import Path
import sys

for name in sys.argv[1:]:
	path = Path(name)
	data = path.read_bytes()
	while data.endswith(b"\n\n"):
		data = data[:-1]
	path.write_bytes(data)
PY
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage" -p1 < "$rv_root/port/patches/a35-dev190-staging-preserve.patch"
echo "Applied: port/patches/a35-dev190-staging-preserve.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-action-stall-logical-time.patch"
echo "Applied: port/patches/combat-a36-action-stall-logical-time.patch"
rv_gameobjmanager_preserved_sha=$(sha256sum "$rv_stage/combat/gameobjmanager.cpp" | cut -d' ' -f1)
if [[ "$rv_gameobjmanager_preserved_sha" != "eeba783cab1f52778dcc98e0287d39ab1ee956999041a29eb06373bcab600d91" ]]; then
	echo "Refusing unanchored PostThink sampler restoration: gameobjmanager.cpp changed ($rv_gameobjmanager_preserved_sha)" >&2
	exit 1
fi
python3 "$rv_root/tools/restore_postthink_sampler.py" "$rv_stage/combat/gameobjmanager.cpp"
echo "Restored sampled PostThink timing in staged GameObjManager::Post_Think"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-detailed-timing-opt-in.patch"
echo "Applied: port/patches/combat-a36-detailed-timing-opt-in.patch"
test "$(sha256sum "$rv_stage/ww3d2/assetmgr.cpp" | cut -d' ' -f1)" = \
	"67a92432c2a58e5206b2e421097c79febd6dfdbf07db93d34ca5dcd8df4a26a6"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-unresolved-prototype-reload-cache.patch"
echo "Applied: port/patches/ww3d2-a35-unresolved-prototype-reload-cache.patch"
test "$(sha256sum "$rv_stage/ww3d2/agg_def.cpp" | cut -d' ' -f1)" = \
	"627e337408e733890a219a86363a412dfd7dc705efb425cc23b6d7ee7d4fecf9"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-aggregate-duplicate-load.patch"
echo "Applied: port/patches/ww3d2-a35-aggregate-duplicate-load.patch"
test "$(sha256sum "$rv_stage/wwsaveload/twiddler.h" | cut -d' ' -f1)" = \
	"5e2ae5e16dcc11bc1ee6bd74a09454c20b4ab1024a7b123298fb4b5d87220af7"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a35-twiddler-preparation-access.patch"
echo "Applied: port/patches/wwsaveload-a35-twiddler-preparation-access.patch"
test "$(sha256sum "$rv_stage/combat/physicalgameobj.h" | cut -d' ' -f1)" = \
	"b7bc5f686cdda28fb7a59243a630ed79f7a3d07b22885d0e3fb02acd4de56cd9"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-killed-explosion-query.patch"
echo "Applied: port/patches/combat-a35-killed-explosion-query.patch"
test "$(sha256sum "$rv_stage/combat/scriptcommands.cpp" | cut -d' ' -f1)" = \
	"8f11e19303092b71f9af7b773c08b01d4788bb8137bf8dcf8918ab4f083029ca"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-host-script-file-handles.patch"
echo "Applied: port/patches/combat-a35-host-script-file-handles.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-skirmish-unused-hud-include.patch"
echo "Applied: port/patches/commando-a35-skirmish-unused-hud-include.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-server-config-root.patch"
echo "Applied: port/patches/commando-a35-server-config-root.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-player-heading-optional-wol.patch"
echo "Applied: port/patches/commando-a35-player-heading-optional-wol.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-fixed-packet-words.patch"
echo "Applied: port/patches/wwnet-a35-fixed-packet-words.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-receive-bounds.patch"
echo "Applied: port/patches/wwnet-a35-receive-bounds.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-optional-network-modes.patch"
echo "Applied: port/patches/commando-a35-optional-network-modes.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-client-options-handoff.patch"
echo "Applied: port/patches/commando-a35-client-options-handoff.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-direct-ip-session.patch"
echo "Applied: port/patches/commando-a35-direct-ip-session.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-timeout-host-lifetime.patch"
echo "Applied: port/patches/wwnet-a35-timeout-host-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-client-world-lifetime.patch"
echo "Applied: port/patches/commando-a35-client-world-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-conversation-guard-release.patch"
echo "Applied: port/patches/combat-a35-conversation-guard-release.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-vita-libc-receive.patch"
echo "Applied: port/patches/wwnet-a35-vita-libc-receive.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-client-protocol-failure.patch"
echo "Applied: port/patches/commando-a35-client-protocol-failure.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-md5-word-width.patch"
echo "Applied: port/patches/wwlib-a35-md5-word-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-client-identity.patch"
echo "Applied: port/patches/commando-a35-client-identity.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-client-admission-message.patch"
echo "Applied: port/patches/commando-a35-client-admission-message.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-multiplayer-utf16-format.patch"
echo "Applied: port/patches/commando-a35-multiplayer-utf16-format.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-multihud-static-owner.patch"
echo "Applied: port/patches/commando-a35-multihud-static-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-crc-word-width.patch"
echo "Applied: port/patches/wwlib-a35-crc-word-width.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-network-compatibility-key.patch"
echo "Applied: port/patches/commando-a35-network-compatibility-key.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-client-preflight-abort.patch"
echo "Applied: port/patches/wwnet-a35-client-preflight-abort.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-tt-server-info.patch"
echo "Applied: port/patches/wwnet-a35-tt-server-info.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-network-preset-validation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-network-object-failure.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-network-announcements.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-control-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-harvester-observer-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-purchase-runtime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-purchase-ui-provider.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/commando-a35-purchase-bounds.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/wwui-a35-chat-utf16-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-tt-resource-queue.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/commando-a35-tt-resource-world.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-direct-client-round-validity.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-tt-client-greeting.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-tt-client-profile.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-tt-options-layout.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-tt-camera-shake.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwbitpack" -p1 < "$rv_root/port/patches/wwbitpack-a35-bounded-reads.patch"
cp -- "$rv_stage/wwbitpack/BitPacker.h" "$rv_stage/wwbitpack/bitpacker.h"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-network-weapon-validation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-packet-decode-failure.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-physical-rare.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-physical-creation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-weapon-list.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-soldier-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-shared-frequent.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwbitpack" -p1 < "$rv_root/port/patches/wwbitpack-a35-tt-defense-precision.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-occasional-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-datasafe-long-conversion.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-tt-soldier-network-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-soldier-frequent.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-vehicle-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-network-history-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-tt-mix-index-order.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-soldier-occasional-selection.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-purchase-catalog.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-tt-purchase-catalog.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwnet" -p1 < "$rv_root/port/patches/wwnet-a35-tt-purchase-catalog.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-tt-c4-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-original-owner-cpp.patch"
rv_cinematic_budget_sha=$(sha256sum "$rv_stage/scripts/Test_Cinematic.cpp" | cut -d' ' -f1)
if [[ "$rv_cinematic_budget_sha" != "6ea137fedd3a31409a5615a924ccf3776efec5a5727b88a68979ee359a76b10d" ]]; then
	echo "Refusing unanchored cinematic time-budget patch: Test_Cinematic.cpp changed ($rv_cinematic_budget_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-time-budget-only.patch"
test "$(sha256sum "$rv_stage/scripts/Test_Cinematic.cpp" | cut -d' ' -f1)" = \
	"f422957863652a66c89b13c23c1458992615ae441ed6f23d9b99a80645463174"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-camera-save.patch"
test "$(sha256sum "$rv_stage/ww3d2/sortingrenderer.cpp" | cut -d' ' -f1)" = \
	"b4687cdd516789a73ae2b99d7c80486c476a6a6613fd2cffbd275fe60363a609"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-original-sorting-port.patch"
test "$(sha256sum "$rv_stage/ww3d2/ww3d.cpp" | cut -d' ' -f1)" = \
	"8057238f6948b90f3790e30e3c263ad1b48ca62f5f5e1415c411fd0345973575"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-original-sorting-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-script-lookup-telemetry.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a35-thread-completion-acquire.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-texture-worker-cancellation.patch"
test "$(sha256sum "$rv_stage/wwaudio/sound3dhandle.cpp" | cut -d' ' -f1)" = \
	"11b6c2b0edc90c897083bd8241b08264dd9b8cbf9375171b53af2ce79720df97"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a35-bounded-3d-sample.patch"
test "$(sha256sum "$rv_stage/combat/activeconversation.cpp" | cut -d' ' -f1)" = \
	"2d6b71e85dff3fb3b49be20e4749915143e2dabe74f3f9291f2008e0fc872704"
test "$(sha256sum "$rv_stage/combat/activeconversation.h" | cut -d' ' -f1)" = \
	"c8d0c60aa32eaa222d6a584dae8ddc6a5a99102401ea81c1c4e8fdf007788938"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-conversation-transition-telemetry.patch"
test "$(sha256sum "$rv_stage/scripts/scripts.cpp" | cut -d' ' -f1)" = \
	"ac9ffd308e636f6d715bedf20c34daccc113d0982eed31beda5dfc6cb496eca7"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-vector-parameter-initialization.patch"
test "$(sha256sum "$rv_stage/combat/scriptablegameobj.cpp" | cut -d' ' -f1)" = \
	"9503f9408bcc5941a624b13e0523e432ba3a4b04efb7b1c79ef31f5b170c0388"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-observer-timer-miss-telemetry.patch"
test "$(sha256sum "$rv_stage/combat/action.cpp" | cut -d' ' -f1)" = \
	"9e630666e9b1c2a2e6a960225d9e18c6c784794cb03d2d602e3781479563295e"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-action-observer-miss-telemetry.patch"
test "$(sha256sum "$rv_stage/combat/savegame.cpp" | cut -d' ' -f1)" = \
	"8589a02e13ce7de0c505f0d4d0250c82233160b92524e54e59849f8be0726564"
test "$(sha256sum "$rv_stage/combat/savegame.h" | cut -d' ' -f1)" = \
	"a380d7e66a3f000c03a7bb2db2019cbaa659f25ee868efb84d02d3cf37f23e07"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-required-level-load-failure.patch"
test "$(sha256sum "$rv_stage/scripts/Test_Cinematic.cpp" | cut -d' ' -f1)" = \
	"32e962cf48da38f2c37afb05129fea3a9608e84ddd27bf037c7f2ad7d576b008"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-filename-diagnostics.patch"
# Compare final patched contents, never an intermediate source revision.
test "$(sha256sum "$rv_stage/combat/scriptcommands.cpp" | cut -d' ' -f1)" = \
	"6cfd546a6b22eea05940a5e084301722a2ac877f25b13fb2943d44feae0f96fc"
test "$(sha256sum "$rv_stage/combat/smartgameobj.cpp" | cut -d' ' -f1)" = \
	"56b807fe528a576e72274f78660f5eade8c6260611a4b71772197daa87f38dbd"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-logical-stimulus-telemetry.patch"
test "$(sha256sum "$rv_stage/scripts/Test_Cinematic.cpp" | cut -d' ' -f1)" = \
	"4196cdbae396e06dd4a5e1d5946509be01191f75735274763c223aea50c64d97"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-primary-id-buffer.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-script-load-capacity.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-command-load-bounds.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-host-m03-pointer-exchange.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-m09-camera-bounds.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-apache-controller-bounds.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-rmv-engineer-dead-pointer-roundtrip.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a36-m13-finale-delivery-trace.patch"
test "$(sha256sum "$rv_stage/ww3d2/dazzle.cpp" | cut -d' ' -f1)" = \
	"2bbcba91d75327b7fa35b4c1f50718ab05d3b252a687a78d0b3c62a90dfefd58"
test "$(sha256sum "$rv_stage/ww3d2/ww3d.cpp" | cut -d' ' -f1)" = \
	"e213b455754c3580ab82412c682044e2bfb9c210c6f8f1143ecc3eac8e3a95c3"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-original-dazzle-lifecycle.patch"
test "$(sha256sum "$rv_stage/ww3d2/ww3d.cpp" | cut -d' ' -f1)" = \
	"3ce7b24a1e3075414c22b9b2a6ae7d8ef8de23c35534ba366f3e81bccbe09322"
test "$(sha256sum "$rv_stage/ww3d2/decalmsh.cpp" | cut -d' ' -f1)" = \
	"a235a5a53c279f59d92099b1efb7ccaa039ba83cec176b9162ede5c7e1d64d4b"
test "$(sha256sum "$rv_stage/ww3d2/mesh.cpp" | cut -d' ' -f1)" = \
	"628232c017e9ffe25ec68d4732e133b31f13094c2653322c95a5e06319d137ca"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-original-decal-submission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a37-prim-anim-sphere-gcc15.patch"
test "$(sha256sum "$rv_stage/ww3d2/dx8renderer.cpp" | cut -d' ' -f1)" = \
	"7fb5704ac01edc93f00129b17b25335b6bf9b4a3e05d8d9ed3a26ac66195ae57"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a35-dx8renderer-gcc-syntax.patch"
test "$(sha256sum "$rv_stage/ww3d2/ww3d.cpp" | cut -d' ' -f1)" = \
	"9a21216f71e413e0a8d364cc65b22075cad98c7e8a46b5ce4ed6be4cbeb86e1b"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-original-statistics-lifecycle.patch"
test "$(sha256sum "$rv_stage/commando/dialogtests.cpp" | cut -d' ' -f1)" = \
	"6addde867fc812575af68d3afd5ecf2bc407abad3fcd20a0880f963d453d5acc"
test "$(sha256sum "$rv_stage/commando/dialogtests.h" | cut -d' ' -f1)" = \
	"55cd200d7bda5d0adc422df3cd2db9d44baca690464fa4c2da386aa2279bce67"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-options-staging-closure.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-trim-overlap.patch"
test "$(sha256sum "$rv_stage/ww3d2/ww3d.cpp" | cut -d' ' -f1)" = \
	"01c3bb2704d463da88f3358f25edfa08ef74e9d4b3b76e8fea82edfa1ba801f1"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d-a35-pointgroup-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a35-suspend-viewer-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-cinematic-original-dispatch.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a35-save-phase-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-static-mesh-cache-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwmath" -p1 < "$rv_root/port/patches/wwmath-a36-fabs-vabs.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-sorting-depth-sort-and-runs.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-powerup-text-once.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a36-write-failure-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-save-write-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-save-metadata-open-failure.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-beacon-armed-sound-postload.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-beacon-save-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-quicksave-write-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-radio-route.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-radio-input-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-chat-input-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwui" -p1 < "$rv_root/port/patches/wwui-a36-native-text-submit.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-autosave-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-core-restart-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-pending-exit-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-required-reload-failure.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-win-screen.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-score-forced-teardown.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-death-flow.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-replay-flow.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-load-failure-unwind.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-manual-save-write-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-save-state-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-state-validation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-load-menu-save-validation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-credits-route.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-movies-route.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-movie-audio-teardown.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-movie-skip-edge-lifetime.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-audio-service-yield.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-vita-control-profile-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-level-cinematic-camera-release.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-input-config-user-root.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-input-config-lifecycle.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-controls-route.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-reload-loading-presentation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-original-overlay-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-player-list-input-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-multihud-optional-network-mode.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-cnc-reference-exit-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-multiplayer-info-dialogs.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-multiplayer-info-input-owner.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-channel-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-service-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-list-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-host-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-nic-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-network-callbacks.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-frontend-route.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-launch-classification.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-native-material-pass-queue.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-required-player-save-subsystems.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-required-save-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-required-player-save-subsystems.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-level-start-origin.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-required-network-player-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-required-playerdata-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-required-player-record.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-required-world-save-subsystems.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-required-dynamic-save-subsystem.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a36-required-dynamic-save-subsystem.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-required-inner-save-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-required-inner-dynamic-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-required-manager-save-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a36-required-inner-dynamic-state.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-rejected-load-postload-discard.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-rejected-load-postload-order.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-required-map-values.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-player-save-envelope-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-save-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a36-chunk-structural-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-chunk-error-propagation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-chunk-error-propagation.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-dynamic-scene-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-gameobj-save-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-encyclopedia-size-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-conversation-object-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-physics-path-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-script-manager-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a36-logical-write-abort.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-logical-save-abort.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-save-envelope-preflight.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-radar-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-objective-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-objective-field-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-objective-semantic-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-spawner-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-spawner-field-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-gameobj-observer-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-weapon-view-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-armed-def-weapon-id.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-bullet-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-persistent-observer-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-hud-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-screen-fade-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-background-dynamic-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-weather-dynamic-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-cover-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-combat-manager-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-active-conversation-monitor-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-unresolved-remap-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-script-timer-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-gameobj-reference-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-persist-factory-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-scriptable-object-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-playerdata-field-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-player-field-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a36-chunk-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-persist-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-custom-persist-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-child-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-child-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-child-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-script-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-boss-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-god-save-state-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwlib" -p1 < "$rv_root/port/patches/wwlib-a36-chunk-load-status-report.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-script-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-core-shutdown-idempotence.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-gameplay-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-gameobj-hierarchy-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-special-gameobj-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-building-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-mission-combat-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/combat-a36-interactive-world-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-physical-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-moving-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a36-scene-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwaudio" -p1 < "$rv_root/port/patches/wwaudio-a36-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-mission-manager-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/combat-a36-world-state-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-damage-owner-save-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-action-weapon-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-gameobj-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-building-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-special-object-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-boss-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-base-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-derived-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a36-definition-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-definition-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-corrupt-ddb-rejects-level-data.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-definition-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-definition-hierarchy-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-definition-child-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-defense-definition-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-definition-catalog-transaction.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a36-definition-rejection-hook.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-eva-settings-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-global-definition-rollback.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-purchase-definition-transaction.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-catalog-reinit.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-asset-load-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-dazzle-load-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-fixed-prototype-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a36-primitive-animation-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-browser-factory.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-state-source-binding.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-asset-dependency-admission.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-a36-asset-dependency-close-status.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-load-inventory-commit.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-campaign-backdrop-selection.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/wwlib-a36-registry-checked-string-write.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/commando-a36-save-campaign-source-binding.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage" -p1 < "$rv_root/port/patches/commando-a36-direct-ip-frontend-dialog.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-team-selection.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-server-presets.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-multiplayer-pause-route.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/commando" -p1 < "$rv_root/port/patches/commando-a36-lan-connect-refusal.patch"
# PersistFactory.h is a required mixed-case include alias.  Refresh it after
# all lowercase factory patches so case-sensitive Vita builds cannot select a
# stale pre-admission template.
cp -- "$rv_stage/wwsaveload/persistfactory.h" "$rv_stage/wwsaveload/PersistFactory.h"
cp -- "$rv_stage/wwsaveload/definition.h" "$rv_stage/wwsaveload/Definition.h"
if [[ "$rv_incremental_stage" == "1" ]]; then
	rv_sync_args=()
	for rv_dir in "${rv_managed_stage_dirs[@]}"; do
		rv_sync_args+=(--managed-dir "$rv_dir")
	done
	python3 "$rv_root/tools/sync_staged_tree.py" \
		--source "$rv_stage" \
		--target "$rv_stage_target" \
		"${rv_sync_args[@]}"
	rv_stage="$rv_stage_target"
fi
python3 "$rv_root/tools/renegade_patch_inventory.py" --root "$rv_root" --write-staging-receipt
