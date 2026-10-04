#!/usr/bin/env bash
# Stages the VitaD3D graphics variant.
#
# The committed staging tree is copied unchanged, then the WW3D branches that
# route rendering into the vitaGL boundary renderer are returned to the
# original DX8 path. Every other platform, portability and correctness change
# in staging is kept. The result is generated and lives under build/.
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_source="$rv_root/staging"
rv_target="$rv_root/build/staging-d3dvita"

rv_patches=(
	ww3d2-d3dvita-original-renderer.patch
	ww3d2-d3dvita-dx8wrapper-gcc.patch
	ww3d2-d3dvita-thumbnail-boundary.patch
)

rm -rf -- "$rv_target"
mkdir -p "$rv_root/build"
cp -a -- "$rv_source" "$rv_target"

for rv_patch in "${rv_patches[@]}"; do
	patch --batch --forward --fuzz=0 --no-backup-if-mismatch \
		-d "$rv_target/ww3d2" -p1 < "$rv_root/port/patches/d3dvita/$rv_patch"
	echo "Applied: port/patches/d3dvita/$rv_patch"
done

# The case alias is a copy, as in tools/stage_sources.sh.
cp -- "$rv_target/ww3d2/dx8wrapper.h" "$rv_target/ww3d2/Dx8Wrapper.h"

if find "$rv_target" -type f \( -name '*.orig' -o -name '*.rej' \) -print -quit | grep -q .; then
	echo "VitaD3D staging contains patch backup/reject debris." >&2
	exit 5
fi
echo "VitaD3D staging: $rv_target"
