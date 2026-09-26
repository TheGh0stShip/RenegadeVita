#!/usr/bin/env bash
set -euo pipefail

rv_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rv_builder="$(cd "$rv_root/../.." && pwd)"
rv_cache="${RENEGADE_SOURCE_CACHE:-$rv_builder/source-cache}"
rv_sdk="${VITASDK:-/usr/local/vitasdk}"
export VITASDK="$rv_sdk"
rv_prefix="$rv_root/build/deps/ttfs-https-vita"
rv_work="$rv_root/build/deps/ttfs-https-vita-build"
rv_jobs="${RENEGADE_DEPENDENCY_JOBS:-2}"
# Version/hash pins from VitaSDK packages 39efc30332ffeadf6db52dab3e096d62a054466b.
# Do not overwrite the user's global SDK curl/OpenSSL installation.
mkdir -p "$rv_cache" "$rv_prefix" "$rv_work"
inputs() {
    sha256sum "$rv_root/tools/build_ttfs_https_vita.sh" \
        "$rv_root/port/platform/vita/renegade_mbedtls_platform.c" \
        "$rv_sdk/bin/arm-vita-eabi-gcc" "$rv_sdk/share/vita.toolchain.cmake" \
        "$rv_sdk/arm-vita-eabi/lib/libz.a" "$rv_sdk/arm-vita-eabi/lib/libpthread.a"
}
if [[ -f "$rv_prefix/.https-inputs.sha256" && -f "$rv_prefix/.https-libraries.sha256" ]] && \
    cmp -s "$rv_prefix/.https-inputs.sha256" <(inputs) && \
    sha256sum --check --status "$rv_prefix/.https-libraries.sha256"; then
    echo "Verified project-local HTTPS dependencies are unchanged: $rv_prefix"
    exit 0
fi
fetch() {
    local file="$1" hash="$2" url="$3"
    if [[ ! -f "$rv_cache/$file" ]]; then
        curl --fail --location --retry 2 --max-time 180 --output "$rv_cache/$file.part" "$url"
        mv "$rv_cache/$file.part" "$rv_cache/$file"
    fi
    printf '%s  %s\n' "$hash" "$rv_cache/$file" | sha256sum --check
}
fetch mbedtls-3.6.5.tar.bz2 4a11f1777bb95bf4ad96721cac945a26e04bf19f57d905f241fe77ebeddf46d8 \
    https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-3.6.5/mbedtls-3.6.5.tar.bz2
fetch curl-8.22.0.tar.xz f7ef3ae8a22e521f289803fe93543eb64c329b58aa73a9e224dfd915a2a5f4f7 \
    https://github.com/curl/curl/releases/download/curl-8_22_0/curl-8.22.0.tar.xz
if [[ ! -d "$rv_work/mbedtls-3.6.5" ]]; then
    tar -xf "$rv_cache/mbedtls-3.6.5.tar.bz2" -C "$rv_work"
fi
if [[ ! -d "$rv_work/curl-8.22.0" ]]; then
    tar -xf "$rv_cache/curl-8.22.0.tar.xz" -C "$rv_work"
fi
rv_mbed="$rv_work/mbedtls-3.6.5"
# Original implementation through documented platform providers, no imported
# unlicensed recipe patch. Curl owns sockets; Mbed TLS owns TLS/crypto only.
for option in MBEDTLS_THREADING_C MBEDTLS_THREADING_PTHREAD MBEDTLS_NO_PLATFORM_ENTROPY \
              MBEDTLS_ENTROPY_HARDWARE_ALT MBEDTLS_PLATFORM_MS_TIME_ALT; do
    if ! rg -q "^#define $option([[:space:]]|$)" "$rv_mbed/include/mbedtls/mbedtls_config.h"; then
        python3 "$rv_mbed/scripts/config.py" -f "$rv_mbed/include/mbedtls/mbedtls_config.h" set "$option"
    fi
done
for option in MBEDTLS_NET_C MBEDTLS_TIMING_C; do
    if rg -q "^#define $option([[:space:]]|$)" "$rv_mbed/include/mbedtls/mbedtls_config.h"; then
        python3 "$rv_mbed/scripts/config.py" -f "$rv_mbed/include/mbedtls/mbedtls_config.h" unset "$option"
    fi
done
rv_flags="-mcpu=cortex-a9 -mfpu=neon -mfloat-abi=hard -mthumb -ffunction-sections -fdata-sections"
cmake -S "$rv_mbed" -B "$rv_work/mbed-build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$rv_sdk/share/vita.toolchain.cmake" \
    -DCMAKE_INSTALL_PREFIX="$rv_prefix" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="$rv_flags" -DENABLE_PROGRAMS=OFF -DENABLE_TESTING=OFF \
    -DMBEDTLS_FATAL_WARNINGS=OFF
cmake --build "$rv_work/mbed-build" --target install -j"$rv_jobs"
cmake -S "$rv_work/curl-8.22.0" -B "$rv_work/curl-build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$rv_sdk/share/vita.toolchain.cmake" \
    -DCMAKE_INSTALL_PREFIX="$rv_prefix" -DCMAKE_PREFIX_PATH="$rv_prefix" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="$rv_flags" \
    -DBUILD_CURL_EXE=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF \
    -DBUILD_LIBCURL_DOCS=OFF -DBUILD_MISC_DOCS=OFF -DENABLE_CURL_MANUAL=OFF \
    -DENABLE_IPV6=OFF -DCURL_DISABLE_SOCKETPAIR=ON -DHAVE_FCNTL_O_NONBLOCK=OFF \
    -DENABLE_THREADED_RESOLVER=OFF -DHAVE_PIPE2=0 -DCMAKE_DISABLE_FIND_PACKAGE_Threads=ON \
    -DCURL_USE_MBEDTLS=ON -DCURL_USE_OPENSSL=OFF -DCURL_USE_LIBPSL=OFF \
    -DCURL_USE_LIBSSH2=OFF -DCURL_USE_LIBSSH=OFF -DCURL_ZSTD=OFF -DCURL_BROTLI=OFF \
    -DUSE_NGHTTP2=OFF -DUSE_LIBIDN2=OFF -DHTTP_ONLY=ON \
    -DCURL_CA_BUNDLE=none -DCURL_CA_PATH=none
cmake --build "$rv_work/curl-build" --target install -j"$rv_jobs"
mkdir -p "$rv_prefix/share/renegade-licenses"
cp "$rv_mbed/LICENSE" "$rv_prefix/share/renegade-licenses/mbedtls-LICENSE"
cp "$rv_work/curl-8.22.0/COPYING" "$rv_prefix/share/renegade-licenses/curl-COPYING"
inputs > "$rv_prefix/.https-inputs.sha256"
sha256sum "$rv_prefix/lib/libcurl.a" "$rv_prefix/lib/libmbedtls.a" \
    "$rv_prefix/lib/libmbedx509.a" "$rv_prefix/lib/libmbedcrypto.a" > "$rv_prefix/.https-libraries.sha256"
printf '%s\n' 'TTFS HTTPS dependency build complete; explicit CA bundle and device acceptance still required.'
