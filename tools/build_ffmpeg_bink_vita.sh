#!/usr/bin/env bash
set -euo pipefail

rv_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rv_builder_root="$(cd "$rv_root/../.." && pwd)"
rv_source_cache="${RENEGADE_SOURCE_CACHE:-$rv_builder_root/source-cache}"
rv_version="9.0.1"
rv_archive="ffmpeg-$rv_version.tar.xz"
rv_sha256="cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635"
rv_url="https://ffmpeg.org/releases/$rv_archive"
rv_source="$rv_source_cache/ffmpeg-$rv_version"
rv_prefix="$rv_root/build/deps/ffmpeg-bink-vita"
rv_build="$rv_root/build/deps/ffmpeg-bink-vita-build"
rv_vitasdk="${VITASDK:-/usr/local/vitasdk}"
rv_config_id="ffmpeg-$rv_version-vita-bink-video-audio-v3-speed"
rv_stamp="$rv_prefix/.renegade-bink-build"

mkdir -p "$rv_source_cache" "$rv_root/build/deps"
if [[ ! -f "$rv_source_cache/$rv_archive" ]]; then
	curl --fail --location --retry 3 --output "$rv_source_cache/$rv_archive" "$rv_url"
fi
printf '%s  %s\n' "$rv_sha256" "$rv_source_cache/$rv_archive" | sha256sum --check

if [[ -f "$rv_stamp" ]] && [[ "$(cat "$rv_stamp")" == "$rv_config_id" ]] && \
	[[ -f "$rv_prefix/lib/libavformat.a" ]] && \
	[[ -f "$rv_prefix/lib/libavcodec.a" ]] && \
	[[ -f "$rv_prefix/lib/libavutil.a" ]] && \
	[[ -f "$rv_prefix/lib/libswscale.a" ]] && \
	[[ -f "$rv_prefix/lib/libswresample.a" ]]; then
	echo "Bink-enabled Vita FFmpeg already available at: $rv_prefix"
	exit 0
fi

if [[ ! -x "$rv_source/configure" ]]; then
	rm -rf "$rv_source"
	tar -xJf "$rv_source_cache/$rv_archive" -C "$rv_source_cache"
fi

rm -rf "$rv_build" "$rv_prefix"
mkdir -p "$rv_build" "$rv_prefix"
cd "$rv_build"

"$rv_source/configure" \
	--prefix="$rv_prefix" \
	--enable-cross-compile \
	--cross-prefix="$rv_vitasdk/bin/arm-vita-eabi-" \
	--arch=armv7-a \
	--cpu=cortex-a9 \
	--target-os=none \
	--disable-shared \
	--enable-static \
	--disable-programs \
	--disable-doc \
	--disable-avdevice \
	--disable-avfilter \
	--disable-network \
	--disable-autodetect \
	--disable-runtime-cpudetect \
	--disable-armv5te \
	--disable-armv6t2 \
	--disable-everything \
	--enable-avformat \
	--enable-avcodec \
	--enable-avutil \
	--enable-swscale \
	--enable-swresample \
	--enable-demuxer=bink \
	--enable-decoder=bink,binkaudio_dct,binkaudio_rdft \
	--enable-protocol=file \
	--enable-pthreads \
	--disable-small \
	--optflags=-O3 \
	--disable-debug \
	--disable-bzlib \
	--disable-iconv \
	--disable-lzma \
	--disable-sdl2 \
	--disable-securetransport \
	--disable-xlib \
	--extra-cflags="-std=gnu11 -mcpu=cortex-a9 -mfpu=neon -mfloat-abi=hard -O2 -ffunction-sections -fdata-sections -fomit-frame-pointer -Wno-error=implicit-function-declaration -Wno-error=int-conversion -Wno-error=incompatible-pointer-types -D_BSD_SOURCE" \
	--extra-ldflags="-L$rv_vitasdk/arm-vita-eabi/lib -Wl,--gc-sections"

make -j"$(nproc)"
make install

test -f "$rv_prefix/lib/libavformat.a"
test -f "$rv_prefix/lib/libavcodec.a"
test -f "$rv_prefix/lib/libavutil.a"
test -f "$rv_prefix/lib/libswscale.a"
test -f "$rv_prefix/lib/libswresample.a"
printf '%s\n' "$rv_config_id" > "$rv_stamp"

echo "Bink-enabled Vita FFmpeg installed at: $rv_prefix"
