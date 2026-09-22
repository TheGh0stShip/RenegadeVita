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
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwsaveload" -p1 < "$rv_root/port/patches/wwsaveload-a30-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwtranslatedb" -p1 < "$rv_root/port/patches/wwtranslatedb-a31-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwtranslatedb" -p1 < "$rv_root/port/patches/wwtranslatedb-a35-empty-string-wide-abi.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a22-gcc15.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/ww3d2" -p1 < "$rv_root/port/patches/ww3d2-a22-vita-boundaries.patch"
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
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a31-vita-material-effect-boundary.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a31-vita-material-effect-close.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a30-pointer-tokens.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-static-object-load-diagnostics.patch"
patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
	-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-vita-durable-static-trace.patch"
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
echo "Applied: port/patches/wwsaveload-a30-abi.patch"
echo "Applied: port/patches/wwtranslatedb-a31-gcc15.patch"
echo "Applied: port/patches/wwtranslatedb-a35-empty-string-wide-abi.patch"
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
echo "Applied: port/patches/wwphys-a31-vita-material-effect-boundary.patch"
echo "Applied: port/patches/wwphys-a31-vita-material-effect-close.patch"
echo "Applied: port/patches/wwphys-a30-pointer-tokens.patch"
echo "Applied: port/patches/wwphys-a35-static-object-load-diagnostics.patch"
echo "Applied: port/patches/wwphys-a35-vita-durable-static-trace.patch"
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
if [[ "$rv_slot19_sha" != "7e6190ea669ce3e701332b7bc89c997eef80161f7fd17663ed77872892ade774" ]]; then
	echo "Refusing unanchored M13 slot19 timing patch: Test_Cinematic.cpp changed ($rv_slot19_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/scripts" -p1 < "$rv_root/port/patches/scripts-a35-m13-slot19-phases.patch"
echo "Applied: port/patches/scripts-a35-m13-slot19-phases.patch"
rv_model_install_sha=$(sha256sum "$rv_stage/wwphys/phys.cpp" | cut -d' ' -f1)
if [[ "$rv_model_install_sha" != "820e2552cb29ee7dba38ae1c37017043acb98a16dd6bed9263ec34e29fb571da" ]]; then
	echo "Refusing unanchored model install timing patch: phys.cpp changed ($rv_model_install_sha)" >&2
	exit 1
fi
patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-a35-model-install-timing.patch"
echo "Applied: port/patches/wwphys-a35-model-install-timing.patch"
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
python3 "$rv_root/tools/renegade_patch_inventory.py" --root "$rv_root" --write-staging-receipt
